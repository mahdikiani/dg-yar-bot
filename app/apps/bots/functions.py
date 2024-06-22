import logging
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO

import httpx
import openai
from apps.accounts.schemas import Profile
from apps.ai.models import AIEngines
from apps.bots import handlers, keyboards, models
from server.config import Settings
from tapsage.async_tapsage import AsyncTapSageBot
from tapsage.taptypes import Session
from usso.session import UssoSession
from utils.texttools import split_text

logger = logging.getLogger("bot")
usso_session = UssoSession(
    os.getenv("USSO_REFRESH_URL"), os.getenv("PIXIEE_REFRESH_TOKEN")
)


def get_tapsage(profile: Profile):
    for engine in AIEngines:
        if profile.data.ai_engine.name == engine.name:
            return AsyncTapSageBot(os.getenv("TAPSAGE_API_KEY"), engine.tapsage_bot_id)


def get_openai():
    openai.api_key = os.getenv("OPENAI_API_KEY")
    proxy_url = os.getenv("PROXY")
    if proxy_url:
        proxies = {
            "http://": proxy_url,
            "https://": proxy_url,
        }
        http_client = httpx.AsyncClient(proxies=proxies)
    else:
        http_client = httpx.AsyncClient()

    client = client = openai.AsyncOpenAI(
        api_key=openai.api_key, http_client=http_client
    )

    return client


async def get_tapsage_session(
    tapsage: AsyncTapSageBot = None,
    user_id: str = None,
    max_session_idle_time: timedelta | int = Settings.MAX_SESSION_IDLE_TIME,
) -> Session:
    if user_id is None:
        raise ValueError("user_id is required")
    if tapsage is None:
        raise ValueError("tapsage is required")
    if isinstance(max_session_idle_time, int):
        max_session_idle_time = timedelta(seconds=max_session_idle_time)

    try:
        sessions = await tapsage.list_sessions(user_id)
        if not sessions:
            session = await tapsage.create_session(user_id)
            return session

        session = await tapsage.retrieve_session(sessions[-1].id)
        if (
            session.messages
            and datetime.now(timezone.utc) - session.messages[-1].timestamp
            > max_session_idle_time
        ):
            session = await tapsage.create_session(user_id)
            return session

        return session
    except Exception as e:
        logging.error(e)
        return


async def ai_response(
    *,
    message: str,
    profile: Profile,
    chat_id: str = None,
    response_id: str = None,
    inline_message_id: str = None,
    bot_name: str = None,
    **kwargs,
):
    bot = handlers.get_bot(bot_name)
    tapsage = get_tapsage(profile)
    session = await get_tapsage_session(tapsage, profile.user_id, **kwargs)
    stream = tapsage.stream_messages(session, message, split_criteria={"words": True})

    resp_text = ""
    new_piece = ""
    async for msg in stream:
        new_piece += msg.message.content
        if new_piece[-1] == " " or len(new_piece) > 100:
            resp_text += new_piece
            if resp_text.count("`") % 2 == 0:
                try:
                    await bot.edit_message_text(
                        text=resp_text,
                        chat_id=chat_id,
                        message_id=response_id,
                        inline_message_id=inline_message_id,
                        parse_mode="markdown",
                    )
                except Exception as e:
                    logger.error(f"Error:\n{e}\n")

            new_piece = ""
    if new_piece:
        resp_text += new_piece

    msg_obj = models.Message(user_id=profile.user_id, content=resp_text)
    await msg_obj.save()

    if resp_text:
        try:
            logging.warning(f"Final response: {len(resp_text)}")
            messages = split_text(resp_text)
            if inline_message_id is None:
                for i, msg in enumerate(messages):
                    if i == 0:
                        await bot.edit_message_text(
                            text=msg,
                            chat_id=chat_id,
                            message_id=response_id,
                            inline_message_id=inline_message_id,
                            parse_mode="markdown",
                            reply_markup=(
                                keyboards.read_keyboard(msg_obj.uid)
                                if i == len(messages) - 1
                                else None
                            ),
                        )
                    else:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=msg,
                            parse_mode="markdown",
                            reply_markup=(
                                keyboards.read_keyboard(msg_obj.uid)
                                if i == len(messages) - 1
                                else None
                            ),
                        )
                # bot.delete_message(chat_id, response_id)

            else:
                await bot.edit_message_text(
                    text=messages[0],
                    chat_id=chat_id,
                    message_id=response_id,
                    inline_message_id=inline_message_id,
                    parse_mode="markdown",
                    reply_markup=(
                        keyboards.read_keyboard(msg_obj.uid)
                        if bot.bot_type != "bale"
                        and inline_message_id is None
                        and len(messages) == 1
                        else None
                    ),
                )

        except Exception as e:
            logger.error(f"Error:\n{e}\n{resp_text}")


async def url_response(
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

    authenticated_session = usso_session.get_session()

    r = authenticated_session.post(
        "https://api.pixiee.io/webpages/",
        json={
            "url": url,
            "metadata": {
                "webhook": webhook_url,
                "user_id": str(user_id),
                "chat_id": chat_id,
                "message_id": response_id,
                "bot_name": bot_name,
            },
        },
    )
    if kwargs.get("raise_for_status", True):
        r.raise_for_status()
    webpage = dto.WebpageDTO(**r.json())
    r_start = authenticated_session.post(
        f"https://api.pixiee.io/webpages/{webpage.uid}/start"
    )
    r_start.raise_for_status()


async def content_response(
    *,
    wid: str,
    user_id: str,
    chat_id: str = None,
    response_id: str = None,
    bot_name: str = None,
    **kwargs,
):
    bot = handlers.get_bot(bot_name)
    user = User.objects.get(username=user_id)
    session = usso_session.get_session()
    r = session.get(f"https://api.pixiee.io/webpages/{wid}")
    r.raise_for_status()
    webpage = dto.WebpageDTO(**r.json())

    key = "ads_for_brand"
    data = webpage.ai_data.model_dump()
    data["brief"] = str(webpage.ai_data.brief)
    r = session.post(f"https://api.pixiee.io/ai/{key}", json=data)
    r.raise_for_status()
    response = r.json()

    text = ""
    for k, v in response.items():
        text += f"*{k.capitalize()}*:\n"
        for i, msg in enumerate(v):
            text += f"{i+1}. `{msg}`\n"
        text += "\n"

    bot.send_message(
        text=text,
        chat_id=chat_id,
        parse_mode="markdown",
        reply_markup=keyboards.content_keyboard(),
    )
    bot.delete_message(chat_id, response_id)


def voice_response(voice_bytes: BytesIO, **kwargs):
    client = get_openai()
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=voice_bytes
    )
    return transcription.text


async def send_voice_response(text: str, chat_id: str, bot_name: str, **kwargs):
    bot = get_bot(bot_name)
    client = get_openai()

    response = client.audio.speech.create(model="tts-1", voice="alloy", input=text)

    buffer = BytesIO()
    for data in response.response.iter_bytes():
        buffer.write(data)
    buffer.seek(0)
    bot.send_voice(chat_id, buffer)


async def content_submit(text: str, chat_id: str, bot_name: str, **kwargs):
    bot = get_bot(bot_name)
    client = get_openai()

    response = client.images.create(model="clip-vit-base-patch32", prompt=text)

    buffer = BytesIO()
    for data in response.response.iter_bytes():
        buffer.write(data)
    buffer.seek(0)
    bot.send_image(chat_id, buffer)
