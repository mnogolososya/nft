from logging import Logger
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from nft.app.config import settings
from nft.app.internal import IntentRequestStatus


async def get_nft_conversions_detail(
        phone: str, db: AsyncIOMotorDatabase,
        logger: Logger) -> dict[str, list[dict[str, Any]]]:
    intent_requests = []

    if not phone.startswith('+'):
        phone = f'+{phone}'

    async for intent_request in db.intent_ids.find(
            filter={'phone': phone}):
        intent_requests.append(
            {
                'collection': settings.as_dict().get(
                    'NFT_CATEGORY_MAP').get(intent_request['category_id']),
                'nft_id': intent_request['nft_id'],
                'status': _get_status(intent_request['status'])
            }
        )

    if not intent_requests:
        intent_requests.append({'status': 'Не было попытки конвертации'})

    return {'conversions': intent_requests}


def _get_status(status: str) -> str:
    match status:
        case IntentRequestStatus.PENDING.value:
            return 'Конвертация не завершена'

        case IntentRequestStatus.COMPLETED.value:
            return 'Конвертация прошла успешно'
