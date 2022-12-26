from dependency_injector import containers, providers
from ml.platform.client import MLPlatformAsyncClient

from nft.app.config import settings
from nft.app.dependencies import NotificationSender, ScannerDatabaseState
from nft.app.resources import (DbManagerResource, EventScannerResource,
                               LoggerResource)


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=['.routers.nft',
                 '.routers.call_center',
                 '.internal.event_handler',
                 '.internal.scanner_actions',
                 '.'
                 ])

    logger = providers.Resource(
        LoggerResource,
        logger_name=settings.LOGGER_NAME,
        logger_level=settings.LOGGER_LEVEL,
        logstash_host=settings.LOGSTASH_HOST,
        logstash_port=settings.LOGSTASH_PORT
    )

    db_manager = providers.Resource(
        DbManagerResource,
        host=settings.MONGO_CONNECTION_STRING,
        ca_file=settings.CA_FILE_NAME
    )

    state = providers.Singleton(
        ScannerDatabaseState,
        state=db_manager,
        logger=logger
    )

    scanner = providers.Resource(
        EventScannerResource,
        state=state,
        logger=logger
    )

    mlp_client = providers.Singleton(
        MLPlatformAsyncClient,
        client_id=settings.MLP_CLIENT,
        client_secret=settings.MLP_SECRET
    )

    notification_sender = providers.Singleton(
        NotificationSender,
        notification_name=settings.NFT_CONVERSION_NOTIFICATION_NAME
    )
