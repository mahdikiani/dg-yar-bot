import logging
import telebot

from django.contrib.auth.models import User
from django.utils import timezone
from singleton import Singleton
from telebot.handler_backends import BaseMiddleware

from utils.basic import get_all_subclasses

from . import Bot


def get_all_subclasses(cls: type):
    subclasses = cls.__subclasses__()
    return subclasses + [
        sub for subclass in subclasses for sub in get_all_subclasses(subclass)
    ]


logger = logging.getLogger("bot")


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
        save_username = f"{messenger}:{from_user.id}:{from_user.username}"
        save_name = " ".join(
            [
                f'{from_user.first_name if from_user.first_name else ""}',
                f'{from_user.last_name if from_user.last_name else ""}',
            ]
        )
        qs = User.objects.filter(
            username=save_username,
            first_name=from_user.first_name,
            last_name=from_user.last_name,
        )
        if not qs.exists():
            try:
                user = User.objects.create(
                    username=save_username,
                    first_name=from_user.first_name,
                    last_name=from_user.last_name,
                )
            except Exception as e:
                logger.error(f"Error creating user: {e}")
                return

        user.last_login = timezone.now()

        if save_name != user.first_name:
            user.first_name = save_name
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
    bot.reply_to(message, message.text)


def message(message: telebot.types.Message, bot: Bot.BaseBot):
    if message.text.startswith("/"):
        command(message, bot)
    else:
        prompt(message, bot)


def callback(call: telebot.types.CallbackQuery, bot: Bot.BaseBot):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Callback received")


class BotFunctions:
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
    bot.register_callback_query_handler(
        callback,
        func=lambda _: True,
        pass_bot=True,
    )
    bot.register_message_handler(
        message,
        func=lambda _: True,
        content_types=["text"],
        pass_bot=True,
    )


def main():
    BotFunctions()
    bot = Bot.TelegramBot()
    setup_bot(bot)
    bot.delete_webhook()
    bot.polling()


if __name__ == "__main__":
    main()
