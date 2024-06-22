import logging
import os
import uuid
from io import BytesIO

import telebot
import usso.api
from apps.accounts.models import AIEngines
from celery import shared_task
from celery.signals import worker_ready
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from singleton import Singleton
from telebot.handler_backends import BaseMiddleware
from usso import UserData
from utils.basic import get_all_subclasses
from utils.texttools import is_valid_url, split_text

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
                f"{self.bot.me}: "
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
            session = functions.get_session(user_id=message.user.username)

            if len(session.messages) > 0:
                session = functions.get_tapsage(message.user).create_session(
                    user_id=message.user.username
                )
            return bot.reply_to(message, "New session created")
        case "show_conversation":
            session = functions.get_session(user_id=message.user.username)
            messages = split_text(
                "\n\n".join(
                    ["Your conversation in this session:"]
                    + [f"{msg.type}: {msg.content}" for msg in session.messages]
                )
            )
            for msg in messages:
                bot.send_message(
                    chat_id=message.chat.id, text=msg, parse_mode="markdown"
                )
            return
        case "conversations":
            sessions = functions.get_tapsage(message.user).list_sessions(
                message.user.username
            )
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
            bot_name=bot.me,
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

        if message.forward_origin:
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
    response = bot.reply_to(message, "Please wait url ...")
    try:
        functions.url_response.delay(
            url=message.text,
            user_id=message.user.username,
            chat_id=message.chat.id,
            response_id=response.message_id,
            bot_name=bot.me,
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
    functions.send_voice_response.delay(
        message.content, call.message.chat.id, bot_name=bot.me
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


def callback_brief(call: telebot.types.CallbackQuery, bot: Bot.BaseBot):
    # bot.edit_message_reply_markup(
    #     chat_id=call.message.chat.id,
    #     message_id=call.message.message_id,
    #     reply_markup=None,
    # )
    wid = call.data.split("_")[2]
    response = bot.reply_to(call.message, "Please wait for content ...")
    functions.content_response.delay(
        wid=wid,
        user_id=call.message.user.username,
        chat_id=call.message.chat.id,
        response_id=response.id,
        bot_name=bot.me,
    )


def callback_content_select(call: telebot.types.CallbackQuery, bot: Bot.BaseBot):
    tuple_string = call.data.split("_")[2]
    tuple_elements = tuple_string.strip("()").split(",")
    new_state = tuple(map(int, tuple_elements))
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.content_keyboard(new_state),
    )


def callback_content_submit(call: telebot.types.CallbackQuery, bot: Bot.BaseBot):
    tuple_string = call.data.split("_")[2]
    tuple_elements = tuple_string.strip("()").split(",")
    tuple(map(int, tuple_elements))
    functions.content_submit.delay()


def callback(call: telebot.types.CallbackQuery, bot: Bot.BaseBot):
    bot.answer_callback_query(call.id, text="Processing ...")

    if call.data.startswith("read_"):
        return callback_read(call, bot)
    elif call.data.startswith("answer_"):
        return callback_answer(call, bot)
    elif call.data.startswith("select_ai_"):
        return callback_select_ai(call, bot)
    elif call.data.startswith("brief_textai_"):
        return callback_brief(call, bot)
    elif call.data.startswith("content_select_"):
        callback_content_select(call, bot)
    elif call.data.startswith("content_submit_"):
        callback_content_submit(call, bot)


def inline_query(inline_query: telebot.types.InlineQuery, bot: Bot.BaseBot):
    credentials = {
        "auth_method": bot.bot_type,
        "representor": f"{inline_query.from_user.id}",
    }
    u = get_usso_api(credentials)
    user, _ = User.objects.get_or_create(username=u.uid)
    ai_thumbnail_url = AIEngines.thumbnail_url(user.ai_engine)

    results = [
        telebot.types.InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="Generate with AI",
            input_message_content=telebot.types.InputTextMessageContent(
                message_text=f"Answer with AI (⏳)\n\n{inline_query.query}"
            ),
            reply_markup=keyboards.inline_keyboard(),
            thumbnail_url=ai_thumbnail_url,
        )
    ]
    bot.answer_inline_query(inline_query.id, results, cache_time=300)


def inline_query_ai(inline_result: telebot.types.ChosenInlineResult, bot: Bot.BaseBot):
    credentials = {
        "auth_method": bot.bot_type,
        "representor": f"{inline_result.from_user.id}",
    }
    u = get_usso_api(credentials)
    user, _ = User.objects.get_or_create(username=u.uid)

    functions.ai_response.delay(
        message=inline_result.query,
        user_id=user.username,
        inline_message_id=inline_result.inline_message_id,
        bot_name=bot.me,
    )


class BotFunctions(metaclass=Singleton):
    is_setup = False

    def __init__(self):
        self.setup()

    def setup(self):
        if self.is_setup:
            return

        for bot_cls in get_all_subclasses(Bot.BaseBot):
            bot: Bot.BaseBot = bot_cls()

            reverse_url = reverse(
                "bot_webhook", kwargs={"bot_route": bot.webhook_route}
            )
            webhook_url = f'https://{os.getenv("DOMAIN")}{reverse_url}'
            if bot.get_webhook_info().url != webhook_url:
                bot.delete_webhook()
                res = bot.set_webhook(url=webhook_url)
                logging.warning(f"set webhook for {bot} with result: {res}")
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
    if bot.bot_type == "telegram":
        bot.register_inline_handler(inline_query, func=lambda _: True, pass_bot=True)
        bot.register_chosen_inline_handler(
            inline_query_ai, func=lambda _: True, pass_bot=True
        )


@shared_task
def update_bot(update: dict, request_url: str, bot_route: str, *args, **kwargs):
    BotFunctions()

    for bot_cls in get_all_subclasses(Bot.BaseBot):
        bot: Bot.BaseBot = bot_cls()
        if bot.webhook_route == bot_route:
            break
    else:
        raise ValueError(f"Bot not found for {bot_route}")

    update = telebot.types.Update.de_json(update)

    if update:
        bot.process_new_updates([update])

    return


@worker_ready.connect
def at_start(sender, **kwargs):
    logging.warning("celery startup")
    BotFunctions()


def main():
    BotFunctions()
    bot = Bot.PixieeTelegramBot()
    setup_bot(bot)
    bot.delete_webhook()
    bot.polling()


if __name__ == "__main__":
    main()
