import logging
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO

import openai
from celery import shared_task
from celery.signals import worker_ready
from django.contrib.auth import get_user_model
from tapsage import TapSageBot
from tapsage.tapsagebot import Session

from utils.texttools import telegram_markdown_formatter

from . import Bot, keyboards, models

tapsage = TapSageBot(os.getenv("TAPSAGE_API_KEY"), os.getenv("TAPSAGE_BOT_ID"))
logger = logging.getLogger("bot")
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
User = get_user_model()


def get_session(user_id: str, max_session_idle_time: timedelta | int = 3600) -> Session:
    if isinstance(max_session_idle_time, int):
        max_session_idle_time = timedelta(seconds=max_session_idle_time)
    try:
        sessions = tapsage.list_sessions(user_id)
        if not sessions:
            session = tapsage.create_session(user_id)
            return session

        session = tapsage.retrieve_session(sessions[-1].id)
        if (
            session.dialogueLength > 0
            and datetime.now(timezone.utc) - session.messages[-1].timestamp
            > max_session_idle_time
        ):
            session = tapsage.create_session(user_id)
            return session

        # logging.info(f"\n{len(sessions)}\n{sessions[0]}\n{session}\n\n")
        return session
    except Exception as e:
        logging.error(e)
        return


@shared_task
def ai_response(
    message: str,
    user_id: str,
    chat_id: str,
    response_id: str,
    **kwargs,
):
    bot = (
        Bot.TelegramBot()
        if kwargs.get("bot", "telegram") == "telegram"
        else Bot.BaleBot()
    )
    session = get_session(user_id)
    stream = tapsage.stream_messages(session, message, split_criteria={"words": True})
    
    resp_text = ""
    new_piece = ""
    for msg in stream:
        new_piece += msg.message.content
        if new_piece[-1] == " " or len(new_piece) > 50:
            resp_text += new_piece
            if resp_text.count("`") % 2 == 0:
                try:
                    # logger.info(f"Partial response: {resp_text}")
                    bot.edit_message_text(
                        text=telegram_markdown_formatter(resp_text, **kwargs),
                        chat_id=chat_id,
                        message_id=response_id,
                        parse_mode="markdownV2",
                    )
                except Exception as e:
                    logger.error(f"Error:\n{e}\n{resp_text}")

            new_piece = ""

    msg = models.Message.objects.create(
        user=User.objects.get(username=user_id), content=resp_text
    )

    if resp_text:
        try:
            # logger.info(f"Final response: {resp_text}")
            bot.edit_message_text(
                text=telegram_markdown_formatter(resp_text, **kwargs),
                chat_id=chat_id,
                message_id=response_id,
                parse_mode="markdownV2",
                reply_markup=(
                    keyboards.read_keyboard(msg.pk) if bot.bot_type != "bale" else None
                ),
            )
        except Exception as e:
            logger.error(f"Error:\n{e}\n{resp_text}")


@shared_task
def url_response(
    url: str,
    user_id: str,
    chat_id: str,
    response_id: str,
    **kwargs,
):
    pass


def voice_response(voice_bytes: BytesIO, **kwargs):
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=voice_bytes
    )
    return transcription.text


@shared_task
def send_voice_response(text: str, chat_id: str, **kwargs):
    bot = (
        Bot.TelegramBot()
        if kwargs.get("bot", "telegram") == "telegram"
        else Bot.BaleBot()
    )
    response = client.audio.speech.create(model="tts-1", voice="alloy", input=text)

    buffer = BytesIO()
    for data in response.response.iter_bytes():
        buffer.write(data)
    buffer.seek(0)
    bot.send_voice(chat_id, buffer)


@worker_ready.connect
def at_start(sender, **kwargs):
    # This will run the startup_task when the worker is ready
    logging.warning(f"Celery Startup {models.Message.objects.all().count()}")
