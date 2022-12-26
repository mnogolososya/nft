from logging import Logger

from dependency_injector.wiring import inject, Provide
from ml.platform.client import MLPlatformAsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from web3.datastructures import AttributeDict

from nft.app.config import settings
from nft.app.containers import Container
from nft.app.dependencies import NotificationSender
from nft.app.internal import IntentRequestStatus


@inject
async def check_event_and_send_gifts(
        args: AttributeDict,
        mlp_client: MLPlatformAsyncClient = Provide[
            Container.mlp_client],
        notification_sender: NotificationSender = Provide[
            Container.notification_sender],
        db_manager: AsyncIOMotorDatabase = Provide[
            Container.db_manager],
        logger: Logger = Provide[Container.logger]):

    intent_request: dict | None = await db_manager.intent_ids.find_one_and_update(
        filter={'$and': [{'intent_id': args['presentIntent']},
                         {'nft_id': str(args['tokenTokenIdInLevel'])},
                         {'category_id': str(args['level'])}]},
        update={'$set': {'status': IntentRequestStatus.COMPLETED.value}},
        return_document=ReturnDocument.AFTER
    )

    if intent_request:
        print(f'Intent request #{intent_request["intent_id"]} status '
              f'changed to "{intent_request["status"]}"')

        nft = await db_manager.gifts.find_one(
            filter={'$and': [{'nft_id': intent_request['nft_id']},
                             {'category_id': intent_request['category_id']}]})

        await notification_sender.send_sms_converted_gifts_by_nft(
            sender=mlp_client,
            gifts=nft['gifts'],
            phone=intent_request['phone']
        )

        print(f'NFT #{intent_request["nft_id"]} gifts sent via sms '
              f'to phone number {intent_request["phone"]}')

        await notification_sender.send_telegram_notification(
            mlp_client,
            nft_id=intent_request['nft_id'],
            nft_category=settings.as_dict().get(
                'NFT_CATEGORY_MAP').get(intent_request['category_id']),
            gifts=nft['gifts'],
            phone=intent_request['phone']
        )
