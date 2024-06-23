import os

import dotenv
import singleton
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from utils.texttools import split_text

dotenv.load_dotenv()


class BaseBot(AsyncTeleBot):
    token = ""
    bot_type = "telegram"
    me = ""
    webhook_route = ""

    @property
    def link(self):
        if self.bot_type == "telegram":
            base_link = "https://t.me"
        elif self.bot_type == "bale":
            base_link = "https://ble.ir"
        return f"{base_link}/{self.me}"

    def __init__(self, token=None, *args, **kwargs):
        if token:
            self.token = token
        super(BaseBot, self).__init__(
            self.token,
            parse_mode="markdown",
            *args,
            **kwargs,
        )

    def __str__(self):
        return self.link

    async def edit_message_text(self, *args, **kwargs):
        try:
            await super().edit_message_text(*args, **kwargs)
        except ApiTelegramException as e:
            if not (
                "message is not modified:" in str(e)
                or "message text is empty" in str(e)
            ):
                raise e

    async def send_message(self, chat_id: int | str, text: str, *args, **kwargs):
        try:
            messages = split_text(text)
            for msg in messages:
                sent = await super().send_message(chat_id, msg, *args, **kwargs)
            return sent
        except ApiTelegramException as e:
            raise e


class PixieeTelegramBot(BaseBot, metaclass=singleton.Singleton):
    token = os.getenv("TELEGRAM_TOKEN")
    bot_type = "telegram"
    me = "pixiee_ai_bot"  # todo change the name
    webhook_route = "pixiee-telegram"


class TGTelegramBot(BaseBot, metaclass=singleton.Singleton):
    token = os.getenv("TELEGRAM_TOKEN_dev")
    bot_type = "telegram"
    me = "tgyt_bot"  # todo change the name
    webhook_route = "pixiee-telegram-dev"


# class BaleBot(BaseBot, metaclass=singleton.Singleton):
#     token = os.getenv("BALE_TOKEN")
#     bot_type = "bale"
#     me = "pixiee_bot"
#     webhook_route = "pixiee-bale"
