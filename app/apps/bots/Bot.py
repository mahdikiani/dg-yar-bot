import asyncio
import logging
import os

import singleton
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException

from server.config import Settings
from utils.texttools import split_text

logger = logging.getLogger("bot")


async def reduce_message_length():
    await asyncio.sleep(60 * 60)
    Settings.MESSAGE_LENGTH = max(
        Settings.MESSAGE_LENGTH // 2, Settings.MIN_MESSAGE_LENGTH
    )


class BaseBot(AsyncTeleBot):
    token = ""
    # bot_type = "telegram"
    me = ""
    webhook_route = ""

    @property
    def bot_type(self):
        return "bale" if len(self.token) == 51 else "telegram"

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
            parse_mode="html",
            *args,
            **kwargs,
        )

    def __str__(self):
        return self.link

    async def edit_message_text(self, text, *args, **kwargs):
        try:
            await super().edit_message_text(text=text[:4096], *args, **kwargs)
        except ApiTelegramException as e:
            if "message is not modified:" in str(e) or "message text is empty" in str(
                e
            ):
                logger.warning(f"edit_message_text error: {e}")
            elif "MESSAGE_TOO_LONG" in str(e):
                logger.warning(f"edit_message_text error: {e}")
            elif "Too Many Requests" in str(e):
                Settings.MESSAGE_LENGTH *= 2
                asyncio.create_task(reduce_message_length())
                logger.warning(f"edit_message_text error: {e}")
            elif "can't parse entities" in str(e):
                kwargs["parse_mode"] = ""
                await self.edit_message_text(text, *args, **kwargs)
                logger.warning(f"edit_message_text error: {e}, {text}")
            else:
                raise e

    async def send_message(self, chat_id: int | str, text: str, *args, **kwargs):
        try:
            messages = split_text(text)
            for msg in messages:
                sent = await super().send_message(chat_id, msg, *args, **kwargs)
            return sent
        except ApiTelegramException as e:
            if "MESSAGE_TOO_LONG" in str(e):
                logger.warning(f"send_message error: {e}")
            elif "Too Many Requests" in str(e):
                Settings.MESSAGE_LENGTH *= 2
                asyncio.create_task(reduce_message_length())
                logger.warning(f"send_message error: {e}")
            elif "can't parse entities" in str(e):
                kwargs["parse_mode"] = ""
                await self.send_message(chat_id, text, *args, **kwargs)
                logger.warning(f"send_message error: {e}")
            else:
                raise e


class DGYarBaleTelegramBot(BaseBot, metaclass=singleton.Singleton):
    token = os.getenv("TELEGRAM_TOKEN")
    # bot_type = "telegram"
    me = "dgyarbot"  # todo change the name
    webhook_route = "dgyar-telegram"


# class DGYarBale(BaseBot, metaclass=singleton.Singleton):
#     token = os.getenv("BALE_TOKEN")
#     bot_type = "bale"
#     me = "dgyarbot"  # todo change the name
#     webhook_route = "dgyar-bale"
