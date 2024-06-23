import logging
from datetime import datetime, timedelta, timezone
from io import BytesIO

import httpx
import openai
from apps.accounts.schemas import Profile
from apps.ai.models import AIEngines
from apps.bots import handlers, keyboards, models
from apps.webpage.schemas import Webpage
from server.config import Settings
from tapsage.async_tapsage import AsyncTapSageBot
from tapsage.taptypes import Session
from usso.async_session import AsyncUssoSession
from utils.texttools import split_text

logger = logging.getLogger("bot")


def get_tapsage(profile: Profile):
    for engine in AIEngines:
        if profile.data.ai_engine.name == engine.name:
            return AsyncTapSageBot(Settings.TAPSAGE_API_KEY, engine.tapsage_bot_id)


def get_openai() -> openai.AsyncOpenAI:
    openai.api_key = Settings.OPENAI_API_KEY
    proxy_url = Settings.PROXY

    if proxy_url:
        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }
        http_client = httpx.AsyncClient(proxies=proxies)
    else:
        http_client = httpx.AsyncClient()

    client = client = openai.AsyncOpenAI(
        api_key=openai.api_key, http_client=http_client
    )

    return client


async def get_tapsage_session(
    profile: Profile,
    tapsage: AsyncTapSageBot | None = None,
    max_session_idle_time: timedelta | int = Settings.MAX_SESSION_IDLE_TIME,
) -> Session:
    if profile is None:
        raise ValueError("profile is required")
    if tapsage is None:
        tapsage = get_tapsage(profile)
    if isinstance(max_session_idle_time, int):
        max_session_idle_time = timedelta(seconds=max_session_idle_time)

    user_id = str(profile.user_id)

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
    session = await get_tapsage_session(profile=profile, tapsage=tapsage, **kwargs)
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
            # logging.warning(f"Final response: {len(resp_text)}")
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
    from apps.bots.routes import get_reverse_url

    reverse_url = get_reverse_url("webpage_webhook")
    webhook_url = f"https://{Settings.root_url}{reverse_url}"

    async with AsyncUssoSession(
        Settings.USSO_REFRESH_URL, Settings.PIXIEE_REFRESH_TOKEN
    ) as session:
        async with session.post(
            Webpage.create_url(),
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
        ) as r:
            if kwargs.get("raise_for_status", True):
                r.raise_for_status()
            webpage = Webpage(**await r.json())

        async with session.post(
            f"https://api.pixiee.io/webpages/{webpage.uid}/start"
        ) as r_start:
            r_start.raise_for_status()


async def content_response(
    *,
    wid: str,
    chat_id: str = None,
    response_id: str = None,
    bot_name: str = None,
    **kwargs,
):
    bot = handlers.get_bot(bot_name)
    async with AsyncUssoSession(
        Settings.USSO_REFRESH_URL, Settings.PIXIEE_REFRESH_TOKEN
    ) as session:
        async with session.get(f"https://api.pixiee.io/webpages/{wid}") as r:
            r.raise_for_status()
            webpage = Webpage(**await r.json())

        key = "ads_for_brand"
        data = webpage.ai_data.model_dump()
        data["brief"] = str(webpage.ai_data.brief)

        async with session.post(f"https://api.pixiee.io/ai/{key}", json=data) as r:
            r.raise_for_status()
            response: dict[str, list] = await r.json()

    text = ""
    for k, v in response.items():
        text += f"*{k.capitalize()}*:\n"
        for i, msg in enumerate(v):
            text += f"{i+1}. `{msg}`\n"
        text += "\n"

    await bot.send_message(
        text=text,
        chat_id=chat_id,
        parse_mode="markdown",
        reply_markup=keyboards.content_keyboard(),
    )
    await bot.delete_message(chat_id, response_id)


async def stt_response(voice_bytes: BytesIO, **kwargs):
    client = get_openai()
    transcription = await client.audio.transcriptions.create(
        model="whisper-1", file=voice_bytes
    )
    return transcription.text


async def tts_response(text: str, **kwargs):
    client = get_openai()

    response = await client.audio.speech.create(
        model="tts-1", voice="alloy", input=text
    )

    buffer = BytesIO()
    for data in response.response.iter_bytes():
        buffer.write(data)
    buffer.seek(0)
    return buffer


async def content_submit(text: str, chat_id: str, bot_name: str, **kwargs):
    pass
