import json
from logging import Logger

from dependency_injector import resources
from web3 import AsyncHTTPProvider, Web3
from web3.eth import AsyncEth
from web3.middleware import async_geth_poa_middleware

from nft.app.config import settings
from nft.app.dependencies import EventScanner
from nft.app.utils import EventScannerState


class EventScannerResource(resources.Resource):
    def init(self, state: EventScannerState, logger: Logger) -> EventScanner:
        provider = AsyncHTTPProvider(settings.BLOCKCHAIN_ADDRESS)

        web3 = Web3(provider,
                    modules={'eth': (AsyncEth,)},
                    middlewares=[async_geth_poa_middleware])

        with open(settings.CONTRACT_ABI_FILE_NAME) as file:
            abi = json.loads(file.read())['abi']

        contract = web3.eth.contract(abi=abi)

        return EventScanner(
            web3=web3,
            contract=contract,
            state=state,
            events=[contract.events.PresentIntent],
            filters={'address': settings.CONTRACT_ADDRESS},
            logger=logger
        )
