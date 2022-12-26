import re

from pydantic import BaseModel, Field, validator

from nft.app.config import settings


class NFTConversionRequest(BaseModel):
    category_id: str
    nft_id: str
    phone: str

    @validator('phone')
    def check_phone(cls, v):
        if not re.match('^\\+?[1-9][0-9]{7,14}$', v):
            raise ValueError('An invalid phone provided')
        return v

    @validator('category_id', 'nft_id')
    def check_nft_in_category(cls, v, **kwargs):
        if kwargs['field'].name == 'category_id':
            if not (total := settings.as_dict()['CATEGORY_TOKEN_MAP'].get(v)):
                raise ValueError('Invalid category')
            cls.category_limit = total

        elif not v.isdigit() or not 1 <= int(v) <= cls.category_limit:
            raise ValueError('Invalid token')
        return v


class IntentRequestIdResponse(BaseModel):
    intent_id: int


class GiftDescription(BaseModel):
    type: str
    for_attribute_name: str = Field(alias='forAttributeName')
    for_attribute_value: str = Field(alias='forAttributeValue')
    name: str
    description: str
    image: str

    class Config:
        allow_population_by_field_name = True


class NFTGifts(BaseModel):
    category_id: str
    nft_id: str
    gifts: list[GiftDescription]


class NFTGiftsResponse(BaseModel):
    data: list[NFTGifts]


class NFTIdInCategory(BaseModel):
    category_id: str
    nft_id: str


class NFTIdsRequest(BaseModel):
    nft_ids: list[NFTIdInCategory]


class NFTStatusResponse(BaseModel):
    status: str
