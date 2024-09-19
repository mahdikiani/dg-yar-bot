import logging
import uuid
from io import BytesIO

from telebot import async_telebot

from apps.accounts.handlers import get_user_profile, get_usso_user
from apps.ai.models import AIEngines
from apps.bots import Bot, functions, keyboards, models, schemas
from utils.b64tools import b64_decode_uuid
from utils.texttools import is_valid_url
from server.config import Settings
from apps.bots.schemas import MessageStruct

logger = logging.getLogger("bot")


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
    "/menu": "menu",
    "منو": "menu",
    "menu": "menu",
}


async def send_msg(bot: Bot.BaseBot, chat_id, key, **kwargs):
    try:
        msg_struct = MessageStruct(**Settings().bot_messages(key))
        keyboard = keyboards.dynamic_keyboard(msg_struct.btn)
        return await bot.send_message(
            chat_id=chat_id,
            text=msg_struct.msg.format(**kwargs),
            reply_markup=keyboard,
        )
    except Exception as e:
        logging.error(e)


async def command(message: schemas.MessageOwned, bot: Bot.BaseBot):
    format_dict = {
        "username": message.from_user.username,
        "id": message.chat.id,
        "first": message.from_user.first_name,
        "last": message.from_user.last_name,
        "language": message.from_user.language_code,
    }

    query = message.text if message.text in command_key else "/start"
    logging.info(message.text)
    match command_key[query]:
        case "start":
            return await send_msg(
                bot, message.chat.id, "welcome_new_user", **format_dict
            )
        case "help":
            return await send_msg(bot, message.chat.id, "help", **format_dict)
        case "menu":
            return await send_msg(bot, message.chat.id, "return_to_menu", **format_dict)
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
            return await bot.reply_to(
                message,
                template.format(**format_dict),
                reply_markup=keyboards.select_ai_keyboard(message.profile),
                parse_mode="markdownV2",
            )


async def prompt(message: schemas.MessageOwned, bot: Bot.BaseBot):
    response = await bot.reply_to(message, "دارم فکر می‌کنم 🤔 ...")
    try:
        await functions.ai_response(
            message=message.text,
            profile=message.profile,
            chat_id=message.chat.id,
            response_id=response.message_id,
            bot_name=bot.me,
        )
    except Exception as e:
        logging.error(e)


async def photo(message: schemas.MessageOwned, bot: Bot.BaseBot):
    response: schemas.MessageOwned = await bot.reply_to(message, "لطفا منتظر باشید ...")
    photo = message.photo[-1]
    photo_info = await bot.get_file(photo.file_id)
    photo_file = await bot.download_file(photo_info.file_path)
    photo_bytes = BytesIO(photo_file)
    photo_bytes.name = "photo.jpg"
    await functions.image_response(
        photo_bytes=photo_bytes,
        user_id=message.user.uid,
        chat_id=message.chat.id,
        response_id=response.message_id,
        bot_name=bot.me,
    )



async def message(message: schemas.MessageOwned, bot: Bot.BaseBot):
    
    if message.photo:
        return await photo(message, bot)

    if (
        message.text.startswith("/")
        or message.text in command_key
        or message.text in command_key.values()
    ):
        return await command(message, bot)

    return await prompt(message, bot)



async def callback(call: async_telebot.types.CallbackQuery, bot: Bot.BaseBot):
    if bot.bot_type == "telegram":
        await bot.answer_callback_query(call.id, text="Processing ...")

