from ml.platform.client import MLPlatformAsyncClient


class NotificationSender:
    def __init__(self, notification_name: str):
        self._notification_name = notification_name

    async def send_telegram_notification(self,
                                         sender: MLPlatformAsyncClient,
                                         nft_id: str, nft_category: str,
                                         gifts: list, phone: str):
        return await sender.post_notification(
            notification_type=self._notification_name,
            metadata={
                'nft_id': nft_id,
                'nft_category': nft_category,
                'gifts': gifts,
                'phone': phone
            }
        )

    async def send_sms_converted_gifts_by_nft(self,
                                              sender: MLPlatformAsyncClient,
                                              gifts: list, phone: str):
        return await sender.post_sms(mobile_phone=phone,
                                     message=self.prepare_message(gifts))

    @staticmethod
    def prepare_message(gifts: list) -> str:
        return '\n'.join(
            [f'{gift["smsShortName"]} - {gift["promoCode"]}' for gift in gifts])
