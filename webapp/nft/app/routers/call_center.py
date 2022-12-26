from logging import Logger

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from nft.app.containers import Container
from nft.app.internal import get_nft_conversions_detail
from nft.app.schemas import NFTConversionsCheckResponse, \
    InternalServerErrorResponse

router = APIRouter(prefix='/conversions/check',
                   tags=['call center'])


@router.get('',
            summary='Get converted NFT by phone',
            description='Returns NFT list',
            response_model=NFTConversionsCheckResponse,
            responses={500: {'model': InternalServerErrorResponse}})
@inject
async def get_converted_nft_by_phone(
        phone: str = Query(..., regex='^\\+?[1-9][0-9]{7,14}$'),
        db: AsyncIOMotorDatabase = Depends(Provide[Container.db_manager]),
        logger: Logger = Depends(Provide[Container.logger])):
    return await get_nft_conversions_detail(phone, db, logger)
