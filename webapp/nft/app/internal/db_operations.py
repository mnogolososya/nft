import uuid
from datetime import datetime
from logging import Logger

import pytz
from motor.motor_asyncio import AsyncIOMotorDatabase

from nft.app.config import settings
from nft.app.internal import IntentRequestStatus
from nft.app.schemas import NFTConversionRequest, NFTIdsRequest


async def save_intent_request(db: AsyncIOMotorDatabase,
                              intent_request_data: NFTConversionRequest,
                              logger: Logger):
    rand = ''.join(c for c in str(uuid.uuid4()) if c.isnumeric())
    intent_request_id = int(f'{rand[:3]}{rand[4:7]}{rand[9:12]}')

    await db.intent_ids.insert_one(
        document={
            'intent_id': intent_request_id,
            'category_id': intent_request_data.category_id,
            'nft_id': intent_request_data.nft_id,
            'phone': intent_request_data.phone,
            'request_datetime': datetime.now(
                pytz.timezone(settings.MSK_TZ)),
            'status': IntentRequestStatus.PENDING.value
        })

    print(f'Intent request #{intent_request_id} processed')
    return {'intent_id': intent_request_id}


async def get_nft_gifts(db: AsyncIOMotorDatabase, ids: NFTIdsRequest,
                        logger: Logger):
    gifts_list = []

    for nft_path in ids.nft_ids:
        nft: dict | None = await db.gifts.find_one(
            filter={'$and': [{'category_id': nft_path.category_id},
                             {'nft_id': nft_path.nft_id}]})

        gifts_list.append(
            {
                'category_id': nft_path.category_id,
                'nft_id': nft_path.nft_id,
                'gifts': nft['gifts'] if nft else []
            }
        )

    print(f'Got the following gifts for tokens: {gifts_list}')
    return {'data': gifts_list}


async def get_nft_status(db: AsyncIOMotorDatabase,
                         category_id: str, nft_id: str, logger: Logger):
    if not (nft := await db.intent_ids.find_one(
            filter={'$and': [{'category_id': category_id},
                             {'nft_id': nft_id}]},
            sort=[('request_datetime', -1)]) or {}):
        print(f'NFT #{nft_id} conversion status in '
              f'collection #{category_id} not found')

    return {'status': nft.get('status') or 'Intent request not found'}
