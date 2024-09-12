import logging
from datetime import datetime, timedelta, timezone
from io import BytesIO

import aiohttp.client_exceptions
import httpx
import openai
from metisai.async_metis import AsyncMetisBot
from metisai.metistypes import Session as MetisSession
from tapsage.async_tapsage import AsyncTapSageBot
from tapsage.taptypes import Session as TapSession

from apps.accounts.schemas import Profile
from apps.ai.models import AIEngines
from apps.bots import handlers, keyboards, models, services
from server.config import Settings
from utils.texttools import split_text

logger = logging.getLogger("bot")

Session = MetisSession | TapSession


def get_tapsage(profile: Profile) -> AsyncTapSageBot | AsyncMetisBot:
    for engine in AIEngines:
        if profile.data.ai_engine.name == engine.name:
            return AsyncMetisBot(Settings.METIS_API_KEY, engine.metis_bot_id)
            # return AsyncTapSageBot(Settings.TAPSAGE_API_KEY, engine.tapsage_bot_id)
    return AsyncMetisBot(Settings.METIS_API_KEY, AIEngines.gpt_4o.metis_bot_id)


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
    tapsage: AsyncTapSageBot | AsyncMetisBot | None = None,
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

        session = await tapsage.retrieve_session(sessions[0].id)
        if (
            session.messages
            and datetime.now(timezone.utc) - session.messages[-1].timestamp
            > max_session_idle_time
        ):
            session = await tapsage.create_session(user_id)
            return session

        return session
    except Exception as e:
        logger.error(e)
        raise


async def ai_response(
    *,
    message: str,
    profile: Profile,
    chat_id: str | None = None,
    response_id: str | None = None,
    inline_message_id: str | None = None,
    bot_name: str = "telegram",
    **kwargs,
):
    try:
        bot = handlers.get_bot(bot_name)
        tapsage = get_tapsage(profile)
        session = await get_tapsage_session(profile=profile, tapsage=tapsage, **kwargs)
        stream = tapsage.stream_messages(session, message, split_criteria={})

        resp_text = ""
        new_piece = ""
        try:
            async for msg in stream:
                new_piece += msg.message.content
                if (
                    new_piece
                    and new_piece[-1] == " "
                    or len(new_piece) > Settings.MESSAGE_LENGTH
                ):
                    resp_text += new_piece
                    if resp_text.count("`") % 2 == 0:
                        try:
                            # logger.info(f"Response: {len(resp_text)}")
                            await bot.edit_message_text(
                                text=resp_text,
                                chat_id=chat_id,
                                message_id=response_id,
                                inline_message_id=inline_message_id,
                                parse_mode="markdown",
                            )
                        except Exception as e:
                            logger.error(
                                f"Error:\n{repr(e)}\n{len(resp_text)}\t{resp_text}"
                            )

                    new_piece = ""
        except aiohttp.client_exceptions.ClientPayloadError as e:
            logger.warning(f"ai_response Error:\n{e}")

        if new_piece:
            resp_text += new_piece
        resp_text = resp_text.strip()

        msg_obj = models.Message(user_id=profile.user_id, content=resp_text)
        await msg_obj.save()

        if resp_text:
            # logger.warning(f"Final response: {len(resp_text)}")
            messages = split_text(resp_text)
            if inline_message_id is None and chat_id is not None:
                for i, msg in enumerate(messages):
                    if i == 0:
                        await bot.edit_message_text(
                            message_id=response_id,
                            # await bot.send_message(
                            text=msg,
                            chat_id=chat_id,
                            # inline_message_id=inline_message_id,
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
                # await bot.delete_message(chat_id, response_id)

            else:
                await bot.edit_message_text(
                    text=messages[0],
                    chat_id=chat_id,
                    message_id=response_id,
                    inline_message_id=inline_message_id,
                    parse_mode="markdown",
                )

    except Exception as e:
        import traceback

        logger.error(f"ai_response Error:\n{e}\n{traceback.format_exc()}")
        logger.error(resp_text)


async def url_response(
    *,
    url: str,
    user_id: str,
    chat_id: str,
    response_id: str,
    bot_name: str,
    **kwargs,
):
    bot = handlers.get_bot(bot_name)
    sheet_url = await services.get_sheet_url()
    if "amazon" in url:
        provider = "Amazon"

    elif "digikala" in url:
        provider = "Digikala"

    else:
        # Sazito
        if url[-1] == "/":
            url = url[:-1]

        try:
            product_list = await services.aio_request(
                method="get", url=f"{url}/api/v1/products"
            )
        except aiohttp.client_exceptions.ClientResponseError as e:
            logger.error(f"{type(e)}: {e}")
            await bot.edit_message_text(
                chat_id=chat_id, message_id=response_id, text="فروشنده پشتیبانی نمیشود"
            )
            return

        if product_list:
            provider = "Sazito"

        else:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=response_id, text="فروشنده پشتیبانی نمیشود"
            )

    text = "\n".join(
        [f"Provider: {provider}", f"URL: {url}", "", f"Sheet URL: {sheet_url}"]
    )

    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=response_id,
        text=text,
        reply_markup=keyboards.sheet_keyboard(sheet_url),
    )


async def image_response(
    *,
    photo_bytes: BytesIO,
    user_id,
    chat_id,
    response_id,
    bot_name,
):
    import replicate

    client = replicate.Client(api_token=Settings.REPLICATE_API_TOKEN)

    output = client.run(Settings.REPLICATE_SERVICE, input={"image": photo_bytes})

    bot = handlers.get_bot(bot_name)

    await bot.edit_message_text(
        chat_id=chat_id, message_id=response_id, text=f"Image received {output}"
    )

    image = httpx.get(output).content
    await bot.send_photo(chat_id=chat_id, photo=image)
