import logging
import os
from io import BytesIO

import telebot
import usso.api
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from singleton import Singleton
from telebot.handler_backends import BaseMiddleware
from usso import UserData

from utils.basic import get_all_subclasses
from utils.texttools import is_valid_url

from . import Bot, functions, keyboards, models

User = get_user_model()


def get_all_subclasses(cls: type):
    subclasses = cls.__subclasses__()
    return subclasses + [
        sub for subclass in subclasses for sub in get_all_subclasses(subclass)
    ]


logger = logging.getLogger("bot")


# @lru_cache
def get_usso_api(credentials: dict) -> UserData:
    usso_api = usso.api.UssoAPI(
        url="https://sso.pixiee.io", api_key=os.getenv("USSO_API_KEY")
    )
    try:
        u = usso_api.get_user_by_credentials(credentials)
    except Exception as e:
        logging.warning(e)
        u = usso_api.create_user_by_credentials(credentials=credentials)
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
        if from_user.id == self.bot.get_me().id:
            from_user = message.chat

        credentials = {
            "auth_method": messenger,
            "representor": f"{from_user.id}",
        }
        u = get_usso_api(credentials)
        user, _ = User.objects.get_or_create(username=u.uid)

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
    "راهنما": "help",
    "/getuserid": "getuserid",
    "مکالمه جدید": "new_conversation",
    "نمایش مکالمه": "show_conversation",
    "مکالمه‌ها": "conversations",
    "ناحیه کاربری": "profile",
    "/profile": "profile",
    "profile": "profile",
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
    match command_key[query]:
        case "start":
            return bot.reply_to(
                message,
                "Welcome to the bot!",
                reply_markup=keyboards.main_keyboard(),
            )
        case "help":
            return bot.reply_to(
                message,
                "Just send a message or voice",
                reply_markup=keyboards.main_keyboard(),
            )
        case "getuserid" | "profile":
            template = "\n".join(
                [
                    "username: `{username}`",
                    "id: `{id}`",
                    "first name: {first}",
                    "last name: {last}",
                    "language: {language}",
                ]
            )
            return bot.reply_to(
                message,
                template.format(**format_dict),
                reply_markup=keyboards.select_ai_keyboard(message.user),
                parse_mode="markdownV2",
            )
        case "new_conversation":
            session = functions.get_session(message.user.username)
            if session.dialogueLength:
                session = functions.tapsage.create_session(message.user.username)
            return bot.reply_to(message, "New session created")
        case "show_conversation":
            session = functions.get_session(message.user.username)
            logging.warning(f"********\n\n{session.messages}\n\n********")
            return bot.reply_to(
                message,
                "\n\n".join(
                    ["Your conversation in this session:"]
                    + [f"{msg.type}: {msg.content}" for msg in session.messages]
                ),
            )
        case "conversations":
            sessions = functions.tapsage.list_sessions(message.user.username)
            return bot.reply_to(
                message,
                "\n\n".join(
                    [f"{session.id} {session.dialogueLength}" for session in sessions]
                ),
                reply_markup=keyboards.main_keyboard(),
            )


def prompt(message: telebot.types.Message, bot: Bot.BaseBot):
    response = bot.reply_to(message, "Please wait ...")
    try:
        functions.ai_response.delay(
            message=message.text,
            user_id=message.user.username,
            chat_id=message.chat.id,
            response_id=response.message_id,
            bot=bot.bot_type,
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

        msg = models.Message.objects.create(user=message.user, content=transcription)

        if message.forward_from:
            return bot.edit_message_text(
                text=transcription,
                chat_id=message.chat.id,
                message_id=response.message_id,
                reply_markup=keyboards.answer_keyboard(msg.pk),
            )

        bot.edit_message_text(
            text=transcription,
            chat_id=message.chat.id,
            message_id=response.message_id,
        )

        response.text = transcription
        response.user = message.user
        prompt(response, bot)

    except Exception as e:
        logging.error(e)


def url_response(message: telebot.types.Message, bot: Bot.BaseBot):
    response = bot.reply_to(message, "Please wait ...")
    try:
        functions.url_response.delay(
            url=message.text,
            user_id=message.user.username,
            chat_id=message.chat.id,
            response_id=response.message_id,
        )
    except Exception as e:
        logging.error(e)


def message(message: telebot.types.Message, bot: Bot.BaseBot):
    if message.voice:
        return voice(message, bot)
    if (
        message.text.startswith("/")
        or message.text in command_key
        or message.text in command_key.values()
    ):
        return command(message, bot)

    if is_valid_url(message.text):
        return url_response(message, bot)

    return prompt(message, bot)


def callback_read(call: telebot.types.CallbackQuery, bot: Bot.BaseBot):
    message_id = int(call.data.split("_")[1])
    message = models.Message.objects.get(id=message_id)
    functions.send_voice_response(
        message.content, call.message.chat.id, bot=bot.bot_type
    )


def callback_answer(call: telebot.types.CallbackQuery, bot: Bot.BaseBot):
    message_id = int(call.data.split("_")[1])
    message = models.Message.objects.get(id=message_id)
    call.message.text = message.content

    prompt(call.message, bot)


def callback_select_ai(call: telebot.types.CallbackQuery, bot: Bot.BaseBot):
    user = call.message.user
    user.ai_engine = call.data.split("_")[2]
    user.save()
    bot.edit_message_text(
        text="AI Engine selected",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.select_ai_keyboard(user),
    )


def callback(call: telebot.types.CallbackQuery, bot: Bot.BaseBot):
    bot.answer_callback_query(call.id)
    logging.warning(
        f"Callback: {call.message.from_user.username} {bot.bot_type} {call.data}"
    )

    if call.data.startswith("read_"):
        return callback_read(call, bot)
    elif call.data.startswith("answer_"):
        return callback_answer(call, bot)
    elif call.data.startswith("select_ai_"):
        return callback_select_ai(call, bot)


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
        message,
        func=lambda _: True,
        content_types=["text", "voice"],
        pass_bot=True,
    )


@shared_task
def update_bot(update: dict, request_url: str):
    BotFunctions()

    if request_url.split("/")[-1].startswith("telegram"):
        bot = Bot.TelegramBot()
    elif request_url.split("/")[-1].startswith("bale"):
        bot = Bot.BaleBot()

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
