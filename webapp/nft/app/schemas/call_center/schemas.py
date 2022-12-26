from pydantic import BaseModel


class NFTConversionsDetail(BaseModel):
    collection: str | None = None
    nft_id: str | None = None
    status: str


class NFTConversionsCheckResponse(BaseModel):
    conversions: list[NFTConversionsDetail]
