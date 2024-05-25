import logging
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO

import httpx
import openai
import requests
from apps.accounts.models import AIEngines, BotUser
from celery import shared_task
from django.contrib.auth import get_user_model
from django.urls import reverse
from tapsage import TapSageBot
from tapsage.taptypes import Session
from utils.basic import get_all_subclasses

from . import Bot, dto, keyboards, models

logger = logging.getLogger("bot")
User = get_user_model()


def get_tapsage(user: BotUser):
    for engine in AIEngines:
        if user.ai_engine == engine.name:
            return TapSageBot(os.getenv("TAPSAGE_API_KEY"), engine.tapsage_bot_id)


def get_openai():
    openai.api_key = os.getenv("OPENAI_API_KEY")
    proxy_url = os.getenv("PROXY")
    client = (
        openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if proxy_url is None or proxy_url == ""
        else openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=httpx.Client(proxy=proxy_url),
        )
    )
    return client


def get_session(
    tapsage: TapSageBot = None,
    user_id: str = None,
    max_session_idle_time: timedelta | int = 3600,
) -> Session:
    if user_id is None:
        raise ValueError("user_id is required")
    if tapsage is None:
        tapsage = get_tapsage(User.objects.get(username=user_id))
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
    *,
    message: str,
    user_id: str,
    chat_id: str = None,
    response_id: str = None,
    inline_message_id: str = None,
    bot_name: str = None,
    **kwargs,
):
    for bot_cls in get_all_subclasses(Bot.BaseBot):
        bot: Bot.BaseBot = bot_cls()
        if bot.me == bot_name:
            break
    else:
        raise ValueError("Bot not found")

    user = User.objects.get(username=user_id)
    tapsage = get_tapsage(user)
    session = get_session(tapsage, user_id)
    stream = tapsage.stream_messages(session, message, split_criteria={"words": True})

    resp_text = ""
    new_piece = ""
    for msg in stream:
        new_piece += msg.message.content
        if new_piece[-1] == " " or len(new_piece) > 100:
            resp_text += new_piece
            if resp_text.count("`") % 2 == 0:
                try:
                    # logger.info(f"Partial response: {resp_text}")
                    bot.edit_message_text(
                        text=resp_text,
                        chat_id=chat_id,
                        message_id=response_id,
                        inline_message_id=inline_message_id,
                        parse_mode="markdown",
                    )
                except Exception as e:
                    logger.error(f"Error:\n{e}\n")

            new_piece = ""

    msg = models.Message.objects.create(user=user, content=resp_text)

    if resp_text:
        try:
            # logger.info(f"Final response: {resp_text}")
            bot.edit_message_text(
                text=resp_text,
                chat_id=chat_id,
                message_id=response_id,
                inline_message_id=inline_message_id,
                parse_mode="markdown",
                reply_markup=(
                    keyboards.read_keyboard(msg.pk)
                    if bot.bot_type != "bale" and inline_message_id
                    else None
                ),
            )
        except Exception as e:
            logger.error(f"Error:\n{e}\n{resp_text}")


@shared_task
def url_response(
    *,
    url: str,
    user_id: str,
    chat_id: str,
    response_id: str,
    bot_name: str = None,
    **kwargs,
):
    reverse_url = reverse("webpage_webhook")
    webhook_url = f'https://{os.getenv("DOMAIN")}{reverse_url}'

    r = requests.post(
        "https://api.pixiee.io/webpages/",
        headers={"Authorization": f'Bearer {os.getenv("PIXIEE_REFRESH_TOKEN")}'},
        json={
            "url": url,
            "metadata": {
                "webhook": webhook_url,
                "user_id": user_id,
                "chat_id": chat_id,
                "message_id": response_id,
                "bot_name": bot_name,
            },
        },
    )
    if kwargs.get("raise_for_status", True):
        r.raise_for_status()
    webpage = dto.WebpageDTO(**r.json())
    r_start = requests.post(f"https://api.pixiee.io/webpages/{webpage.uid}/start")
    r_start.raise_for_status()


def voice_response(voice_bytes: BytesIO, **kwargs):
    client = get_openai()
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=voice_bytes
    )
    return transcription.text


@shared_task
def send_voice_response(text: str, chat_id: str, **kwargs):
    bot = (
        Bot.PixieeTelegramBot()
        if kwargs.get("bot", "telegram") == "telegram"
        else Bot.BaleBot()
    )
    client = get_openai()

    response = client.audio.speech.create(model="tts-1", voice="alloy", input=text)

    buffer = BytesIO()
    for data in response.response.iter_bytes():
        buffer.write(data)
    buffer.seek(0)
    bot.send_voice(chat_id, buffer)
