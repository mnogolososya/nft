import asyncio
import datetime
import time
from logging import Logger

from eth_abi.codec import ABICodec
from web3 import Web3
from web3._utils.events import get_event_data
from web3._utils.filters import construct_event_filter_params
from web3.contract import Contract
from web3.exceptions import BlockNotFound

from nft.app.config import settings
from nft.app.utils import EventScannerState


class EventScanner:
    """Scan blockchain for events and try not to abuse JSON-RPC API too
    much.
    """

    def __init__(self, web3: Web3, contract: Contract,
                 state: EventScannerState, events: list, filters: dict,
                 logger: Logger):
        """
        :param contract: Contract
        :param events: List of web3 Event we scan
        :param filters: Filters passed to getLogs
        :param state: Scanner state
        :param web3: Web3 object
        :param logger: Logger object
        """

        self.contract = contract
        self.web3 = web3
        self.state = state
        self.events = events
        self.filters = filters
        self.logger = logger

        # Our JSON-RPC throttling parameters
        self.min_scan_chunk_size = settings.MIN_SCAN_CHUNK_SIZE
        self.max_scan_chunk_size = settings.MAX_SCAN_CHUNK_SIZE
        self.max_request_retries = settings.MAX_REQUEST_RETRIES
        self.request_retry_seconds = settings.REQUEST_RETRY_SECONDS

        # Factor how fast we increase the chunk size if results are found
        # # (slow down scan after starting to get hits)
        self.chunk_size_decrease = settings.CHUNK_SIZE_DECREASE

        # Factor how was we increase chunk size if no results found
        self.chunk_size_increase = settings.CHUNK_SIZE_INCREASE

    async def get_block_timestamp(self, block_num: int) -> datetime.datetime | None:
        """Get Ethereum block timestamp"""

        try:
            block_info = await self.web3.eth.get_block(block_num)
        except BlockNotFound:
            # Block was not mined yet or
            # minor chain reorganisation
            return None
        last_time = block_info["timestamp"]
        return datetime.datetime.utcfromtimestamp(last_time)

    def get_suggested_scan_start_block(self) -> int:
        """Get where we should start to scan for new token events."""

        end_block = self.get_last_scanned_block()
        if end_block:
            return max(1, end_block - settings.CHAIN_REORG_SAFETY_BLOCKS)
        return 1

    async def get_suggested_scan_end_block(self) -> int:
        """Get the last mined block on Ethereum chain we are following."""

        # Do not scan all the way to the final block, as this
        # block might not be mined yet
        return await self.web3.eth.block_number - 1

    def get_last_scanned_block(self) -> int:
        return self.state.get_last_scanned_block()

    def delete_potentially_forked_block_data(self, after_block: int) -> None:
        """Purge old data in the case of blockchain reorganisation."""
        self.state.delete_data(after_block)

    async def scan_chunk(self, start_block, end_block) -> tuple[
            int, datetime.datetime, list]:
        """Read and process events between to block numbers.

        Dynamically decrease the size of the chunk if the case JSON-RPC server pukes out.

        :return: tuple(actual end block number, when this block was mined, processed events)
        """

        block_timestamps = {}
        get_block_timestamp = self.get_block_timestamp

        # Cache block timestamps to reduce some RPC overhead
        async def get_block_when(block_num) -> datetime.datetime:
            if block_num not in block_timestamps:
                block_timestamps[block_num] = await get_block_timestamp(
                    block_num)
            return block_timestamps[block_num]

        all_processed = []

        for event_type in self.events:

            # Callable that takes care of the underlying web3 call
            async def _fetch_events(_start_block, _end_block) -> list:
                return await _fetch_events_for_all_contracts(
                    self.web3,
                    event_type,
                    self.filters,
                    from_block=_start_block,
                    to_block=_end_block)

            # Do `n` retries on `eth_getLogs`,
            # throttle down block range if needed
            end_block, events = await _retry_web3_call(
                _fetch_events,
                start_block=start_block,
                end_block=end_block,
                retries=self.max_request_retries,
                delay=self.request_retry_seconds)

            for evt in events:
                # Integer of the log index position
                # in the block, null when its pending
                idx = evt["logIndex"]

                # We cannot avoid minor chain reorganisations, but
                # at least we must avoid blocks that are not mined yet
                assert idx is not None, "Tried to scan a pending block"

                from nft.app.internal import IntentRequestStatus

                event_is_processed = await self.state.db.intent_ids.find_one(
                    filter={'$and': [{'intent_id': evt['args']['presentIntent']},
                                     {'status': IntentRequestStatus.COMPLETED.value}]})

                if event_is_processed:
                    continue

                block_number = evt["blockNumber"]

                # Get UTC time when this event happened (block mined timestamp)
                # from our in-memory cache
                block_when = await get_block_when(block_number)

                print(
                    f"Processing event {evt['event']}, block #{evt['blockNumber']}")
                processed = await self.state.process_event(block_when, evt)
                all_processed.append(processed)

        end_block_timestamp = await get_block_when(end_block)
        return end_block, end_block_timestamp, all_processed

    def estimate_next_chunk_size(self, current_chunk_size: int,
                                 event_found_count: int) -> int:
        """Try to figure out optimal chunk size."""

        if event_found_count > 0:
            # When we encounter first events, reset the chunk size window
            current_chunk_size = self.min_scan_chunk_size
        else:
            current_chunk_size *= self.chunk_size_increase

        current_chunk_size = max(self.min_scan_chunk_size, current_chunk_size)
        current_chunk_size = min(self.max_scan_chunk_size, current_chunk_size)
        return int(current_chunk_size)

    async def scan(self, start_block, end_block, start_chunk_size=5) -> tuple[
            list, int]:
        """Perform chunks scan.

        :param start_block: The first block included in the scan
        :param end_block: The last block included in the scan
        :param start_chunk_size: How many blocks we try to fetch over
        JSON-RPC on the first attempt
        :return: tuple(All processed events, number of chunks used)
        """

        assert start_block <= end_block, ("Chunks are processed faster than"
                                          " new blocks are mined")

        current_block = start_block

        # Scan in chunks, commit between
        chunk_size = start_chunk_size
        last_scan_duration = last_logs_found = 0
        total_chunks_scanned = 0

        # All processed entries we got on this scan cycle
        all_processed = []

        while current_block <= end_block:
            estimated_end_block = current_block + chunk_size
            print(
                f"Scanning token's conversion for blocks: "
                f"{current_block} - {estimated_end_block}, chunk size "
                f"{chunk_size}, last chunk scan took {last_scan_duration},"
                f" last logs found {last_logs_found}")

            start = time.time()
            actual_end_block, end_block_timestamp, new_entries = await self.scan_chunk(
                current_block, estimated_end_block)

            current_end = actual_end_block

            last_scan_duration = time.time() - start
            all_processed += new_entries

            # Try to guess how many blocks to fetch over `eth_getLogs` API
            # next time
            chunk_size = self.estimate_next_chunk_size(chunk_size,
                                                       len(new_entries))

            # Set where the next chunk starts
            current_block = current_end + 1
            total_chunks_scanned += 1
            await self.state.end_chunk(current_end)

        return all_processed, total_chunks_scanned


async def _retry_web3_call(func, start_block,
                           end_block, retries, delay) -> tuple[int, list]:
    """A custom retry loop to throttle down block range.

    If our JSON-RPC server cannot serve all incoming `eth_getLogs` in a
    single request, we retry and throttle down block range for every retry.

    :param func: A callable that triggers Ethereum JSON-RPC,
     as func(start_block, end_block)
    :param start_block: The initial start block of the block range
    :param end_block: The initial start block of the block range
    :param retries: How many times we retry
    :param delay: Time to sleep between retries
    """
    for i in range(retries):
        try:
            return end_block, await func(start_block, end_block)
        except Exception as e:
            if i < retries - 1:
                print(
                    f"Retrying events for block range"
                    f" {start_block} - {end_block} ({end_block - start_block})"
                    f" failed with {e}, retrying in {delay} seconds")

                # Decrease the `eth_getBlocks` range
                end_block = start_block + ((end_block - start_block) // 2)
                # Let the JSON-RPC to recover e.g. from restart
                await asyncio.sleep(delay)
                continue
            else:
                print("Out of retries")
                raise


async def _fetch_events_for_all_contracts(
        web3,
        event,
        argument_filters: dict,
        from_block: int,
        to_block: int) -> list:
    """Get events using eth_getLogs API."""

    if from_block is None:
        raise TypeError(
            "Missing mandatory keyword argument to getLogs: fromBlock")

    # This will return raw underlying ABI JSON object for the event
    abi = event._get_event_abi()

    # Depending on the Solidity version used to compile
    # the contract that uses the ABI,
    # it might have Solidity ABI encoding v1 or v2.
    # We just assume the default that you set on Web3 object here.
    codec: ABICodec = web3.codec

    # Here we need to poke a bit into Web3 internals, as this functionality
    # is not exposed by default. Construct JSON-RPC raw filter presentation
    # based on human-readable Python descriptions. Namely, convert event
    # names to their keccak signatures
    data_filter_set, event_filter_params = construct_event_filter_params(
        abi,
        codec,
        address=argument_filters.get("address"),
        argument_filters=argument_filters,
        fromBlock=from_block,
        toBlock=to_block
    )

    print(f"Querying eth_getLogs with the following parameters: {event_filter_params}")

    # Call JSON-RPC API on your Ethereum node.
    # get_logs() returns raw AttributedDict entries
    logs = await web3.eth.get_logs(event_filter_params)

    # Convert raw binary data to Python proxy objects as described by ABI
    all_events = []
    for log in logs:
        evt = get_event_data(codec, abi, log)
        all_events.append(evt)

    print(f"Retrieved the following event data "
          f"from blocks {from_block} - {to_block}: {all_events}")
    return all_events
