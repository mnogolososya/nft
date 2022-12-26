from logging import Logger

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from nft.app.containers import Container
from nft.app.internal import get_nft_gifts, get_nft_status, save_intent_request
from nft.app.schemas import (IntentRequestIdResponse, InternalServerErrorResponse,
                             NFTConversionRequest, NFTGiftsResponse,
                             NFTIdsRequest, NFTStatusResponse)

router = APIRouter(prefix='/gifts',
                   tags=['gifts'])


@router.post('',
             summary='Get gifts list by NFT ids',
             description='Returns a list of gifts',
             response_model=NFTGiftsResponse,
             responses={'500': {'model': InternalServerErrorResponse}})
@inject
async def get_gifts_by_nft_ids(nft_ids: NFTIdsRequest,
                               db: AsyncIOMotorDatabase = Depends(
                                   Provide[Container.db_manager]),
                               logger: Logger = Depends(
                                   Provide[Container.logger])):
    return await get_nft_gifts(db, nft_ids, logger)


@router.post('/redeem',
             summary='Send intent request to convert NFT',
             description='Returns intent id',
             response_model=IntentRequestIdResponse,
             status_code=status.HTTP_201_CREATED,
             responses={'500': {'model': InternalServerErrorResponse}})
@inject
async def convert_nft(intent_request_data: NFTConversionRequest,
                      db: AsyncIOMotorDatabase = Depends(
                          Provide[Container.db_manager]),
                      logger: Logger = Depends(
                          Provide[Container.logger])):
    return await save_intent_request(db, intent_request_data, logger)


@router.get('/{category_id}/{nft_id}/status',
            summary='Get NFT conversion status into gifts',
            description='Returns NFT conversion status',
            response_model=NFTStatusResponse,
            responses={'500': {'model': InternalServerErrorResponse}})
@inject
async def get_nft_conversion_status(category_id: str,
                                    nft_id: str,
                                    db: AsyncIOMotorDatabase = Depends(
                                        Provide[Container.db_manager]),
                                    logger: Logger = Depends(
                                        Provide[Container.logger])):
    return await get_nft_status(db, category_id, nft_id, logger)
