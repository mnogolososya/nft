import asyncio
import time
from logging import Logger

from dependency_injector.wiring import inject, Provide

from nft.app.config import settings
from nft.app.containers import Container
from nft.app.dependencies import EventScanner, ScannerDatabaseState


@inject
async def run_scanner(state: ScannerDatabaseState = Provide[Container.state],
                      scanner: EventScanner = Provide[Container.scanner],
                      logger: Logger = Provide[Container.logger]):
    while True:
        try:
            await state.restore()

            scanner.delete_potentially_forked_block_data(
                state.get_last_scanned_block() - settings.CHAIN_REORG_SAFETY_BLOCKS)

            start_block = max(
                state.get_last_scanned_block() - settings.CHAIN_REORG_SAFETY_BLOCKS, settings.START_BLOCK)
            end_block = await scanner.get_suggested_scan_end_block()

            print(f"Scanning events from blocks {start_block} - {end_block}")

            start = time.time()

            result, total_chunks_scanned = await scanner.scan(start_block, end_block)

            await state.save()

            duration = time.time() - start

            print(
                f"Scanned total {len(result)} PresentIntent events, in {duration} "
                f"seconds, total {total_chunks_scanned} chunk scans performed")
        except Exception as e:
            print(e)

        await asyncio.sleep(settings.SCAN_DELAY)
