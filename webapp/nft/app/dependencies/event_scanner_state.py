import datetime
import time
from logging import Logger

from motor.motor_asyncio import AsyncIOMotorDatabase
from web3.datastructures import AttributeDict

from nft.app.utils import EventScannerState


class ScannerDatabaseState(EventScannerState):
    """Store the state of scanned blocks and all events."""

    def __init__(self, state: AsyncIOMotorDatabase, logger: Logger):
        self.current_state: dict | None = None
        self.db = state
        self.logger = logger
        self.last_save = 0

    def reset(self):
        """Create initial state of nothing scanned."""

        self.current_state = {
            "last_scanned_block": 0,
            "blocks": {},
        }

    async def restore(self):
        """Restore the last scan state from a database."""

        if not (state := await self.db.blocks.find_one(filter={})):
            print("State starting from scratch")
            self.reset()

        else:
            print(f"Restored the state, previously "
                  f"{state['last_scanned_block']} blocks have been scanned")

            self.current_state = state

    async def save(self):
        """Save everything we have scanned so far in a database."""
        await self.db.blocks.find_one_and_replace(
            filter={},
            replacement=self.current_state,
            upsert=True
        )
        self.last_save = time.time()

    def get_last_scanned_block(self) -> int:
        """The number of the last block we have stored."""
        return self.current_state["last_scanned_block"]

    def delete_data(self, since_block):
        """Remove potentially reorganised blocks from the scan data."""
        for block_num in range(since_block, self.get_last_scanned_block()):
            if block_num in self.current_state["blocks"]:
                del self.current_state["blocks"][block_num]

    def start_chunk(self, block_number: int):
        pass

    async def end_chunk(self, block_number):
        """Save at the end of each block, so we can resume
         in the case of a crash or CTRL+C
         """
        # Next time the scanner is started we will resume from this block
        self.current_state["last_scanned_block"] = block_number

        # Save into the database for every minute
        if time.time() - self.last_save > 60:
            await self.save()

    async def process_event(self, block_when: datetime.datetime | None,
                            event: AttributeDict) -> str:
        """Process event data."""
        # Events are keyed by their transaction hash and log index
        # One transaction may contain multiple events
        # and each one of those gets their own log index

        print(f'Get event data from block #{event["blockNumber"]}: {event}')

        log_index = str(event['logIndex'])  # Log index within the block
        txhash = event['transactionHash'].hex()  # Transaction hash
        block_number = str(event['blockNumber'])

        args = event["args"]
        event_data = {
            'token_id': args['tokenId'],
            'token_id_in_level': args['tokenTokenIdInLevel'],
            'present_intent': args['presentIntent'],
            'level': args['level'],
            'timestamp': block_when.isoformat() if block_when else None
        }

        # Create empty dict as the block
        # that contains all transactions by txhash
        if block_number not in self.current_state["blocks"]:
            self.current_state["blocks"][block_number] = {}

        block = self.current_state["blocks"][block_number]
        if txhash not in block:
            # One transaction may contain multiple events if executed by a
            # smart contract. Create a tx entry that contains all events by
            # a log index
            self.current_state["blocks"][block_number][txhash] = {}

        self.current_state["blocks"][block_number][txhash][
            log_index] = event_data

        from nft.app.internal import check_event_and_send_gifts
        await check_event_and_send_gifts(args)

        # Return a pointer that allows us to look up this event later if needed
        return f"{block_number}-{txhash}-{log_index}"
