from dependency_injector import resources
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class DbManagerResource(resources.Resource):
    def init(self, host: str, ca_file: str) -> AsyncIOMotorDatabase:
        client = AsyncIOMotorClient(host,
                                    tlsCAFile=ca_file,
                                    tlsAllowInvalidCertificates=False)
        return client.nft_backend
