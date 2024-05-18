import os

import dotenv
import singleton
import telebot
from telebot.apihelper import ApiTelegramException

dotenv.load_dotenv()


class BaseBot(telebot.TeleBot):
    token = ""
    bot_type = "telegram"
    me = ""

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
            parse_mode="HTML" if self.bot_type == "telegram" else "markdownV2",
            use_class_middlewares=True,
            threaded=False,
            *args,
            **kwargs,
        )

    def __str__(self):
        return self.link

    def edit_message_text(self, *args, **kwargs):
        try:
            super().edit_message_text(*args, **kwargs)
        except ApiTelegramException as e:
            if "message is not modified:" not in str(e):
                raise e


class TelegramBot(BaseBot, metaclass=singleton.Singleton):
    token = os.getenv("TELEGRAM_TOKEN")
    bot_type = "telegram"
    me = "tbot"  # todo change the name


class BaleBot(BaseBot, metaclass=singleton.Singleton):
    token = os.getenv("BALE_TOKEN")
    bot_type = "bale"
    me = "pixiee_bot"
