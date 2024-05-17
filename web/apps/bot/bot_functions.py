import os
from io import BytesIO
import logging

import telebot
from django.contrib.auth.models import User
from django.utils import timezone
from singleton import Singleton
from telebot.handler_backends import BaseMiddleware
from utils.basic import get_all_subclasses
from celery import shared_task
import usso.api

from . import Bot
from . import functions

from functools import lru_cache


def get_all_subclasses(cls: type):
    subclasses = cls.__subclasses__()
    return subclasses + [
        sub for subclass in subclasses for sub in get_all_subclasses(subclass)
    ]


logger = logging.getLogger("bot")


# @lru_cache
def get_usso_api(creds: dict):
    usso_api = usso.api.UssoAPI(
        url="https://sso.pixiee.io", api_key=os.getenv("USSO_API_KEY")
    )
    u = usso_api.get_user_by_credentials(creds)
    if "error" in u:
        u = usso_api.create_user_by_credentials(creds)
    return u


class UserMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot.BaseBot, *args, **kwargs):
        self.update_sensitive = True
        self.update_types = [
            "message",
            #  "edited_message",
            "callback_query",
            # "inline_query"
        ]
        self.bot = bot
        self.bot_type = bot.bot_type
        super().__init__(*args, **kwargs)

    def pre_process_message(self, message: telebot.types.Message, data):
        messenger = self.bot_type
        from_user = message.from_user if message.from_user else message.chat

        creds = {"auth_method": messenger, "representor": f"{from_user.id}"}
        u = get_usso_api(creds)
        user, _ = User.objects.get_or_create(username=u["uid"])

        user.last_login = timezone.now()

        save_name = " ".join(
            [
                f'{from_user.first_name if from_user.first_name else ""}',
                f'{from_user.last_name if from_user.last_name else ""}',
            ]
        )
        if save_name != user.first_name:
            user.first_name = save_name
        if from_user.username and from_user.username != user.last_name:
            user.last_name = from_user.username
        user.save()

        message.user = user

    def pre_process_callback_query(self, call: telebot.types.CallbackQuery, data):
        self.pre_process_message(call.message, data)

    def post_process_message(self, message: telebot.types.Message, data, exception):
        pass

    def post_process_callback_query(
        self, call: telebot.types.CallbackQuery, data, exception
    ):
        pass


command_key = {
    "/start": "start",
    "/help": "help",
}


def command(message: telebot.types.Message, bot: Bot.BaseBot):
    format_dict = {
        "username": message.from_user.username,
        "id": message.chat.id,
        "first": message.from_user.first_name,
        "last": message.from_user.last_name,
        "language": message.from_user.language_code,
    }

    query = message.text if message.text in command_key else "/start"
    if command_key[query] == "start":
        bot.reply_to(message, "Welcome to the bot!")
    elif command_key[query] == "help":
        bot.reply_to(message, "Just send a message")


def prompt(message: telebot.types.Message, bot: Bot.BaseBot):
    response = bot.reply_to(message, "Please wait ...")
    try:
        functions.ai_response.delay(
            message=message.text,
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            response_id=response.message_id,
        )
    except Exception as e:
        logging.error(e)


def voice(message: telebot.types.Message, bot: Bot.BaseBot):
    response = bot.reply_to(message, "Please wait voice ...")
    try:
        voice_info = bot.get_file(message.voice.file_id)
        voice_file = bot.download_file(voice_info.file_path)
        voice_bytes = BytesIO(voice_file)
        voice_bytes.name = "voice.ogg"
        transcription = functions.voice_response(voice_bytes)
        bot.edit_message_text(
            text=transcription, chat_id=message.chat.id, message_id=response.message_id
        )
    except Exception as e:
        logging.error(e)


def message(message: telebot.types.Message, bot: Bot.BaseBot):
    if message.voice:
        return voice(message, bot)
    if message.text.startswith("/"):
        return command(message, bot)

    return prompt(message, bot)


def callback(call: telebot.types.CallbackQuery, bot: Bot.BaseBot):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Callback received")


class BotFunctions(metaclass=Singleton):
    is_setup = False

    def __init__(self):
        self.setup()

    def setup(self):
        if self.is_setup:
            return

        for bot_cls in get_all_subclasses(Bot.BaseBot):
            bot = bot_cls()
            setup_bot(bot)

        self.is_setup = True


def setup_bot(bot: Bot.BaseBot):
    middleware = UserMiddleware(bot)
    bot.setup_middleware(middleware)
    bot.register_callback_query_handler(callback, func=lambda _: True, pass_bot=True)
    bot.register_message_handler(
        message, func=lambda _: True, content_types=["text", "voice"], pass_bot=True
    )


@shared_task
def update_bot(update: dict, request_url: str):
    BotFunctions()

    if request_url.split("/")[-1].startswith("telegram"):
        bot = Bot.TelegramBot()
    # elif request_url.split("/")[-1].startswith("bale"):
    #     bot = Bot.BaleBot()

    update = telebot.types.Update.de_json(update)

    if update:
        bot.process_new_updates([update])

    return


def main():
    BotFunctions()
    bot = Bot.TelegramBot()
    setup_bot(bot)
    bot.delete_webhook()
    bot.polling()


if __name__ == "__main__":
    main()
