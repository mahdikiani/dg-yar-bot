import os

import dotenv
import singleton
import telebot

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
            *args,
            **kwargs,
        )

    def __str__(self):
        return self.link


class TelegramBot(BaseBot, metaclass=singleton.Singleton):
    token = os.getenv("TELEGRAM_TOKEN")
    bot_type = "telegram"
    me = "tbot"  # todo change the name


# class BaleBot(BaseBot, metaclass=singleton.Singleton):
#     token = os.getenv("BALE_TOKEN")
#     bot_type = "bale"
#     me = "bale_bot"  # todo change the name
