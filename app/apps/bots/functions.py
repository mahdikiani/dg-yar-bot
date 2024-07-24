import logging
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO

import aiohttp.client_exceptions
import httpx
import openai
from apps.accounts.schemas import Profile
from apps.ai.models import AIEngines, WebpageResponse
from apps.ai.schemas import AIRequest
from apps.base.schemas import StepStatus
from apps.bots import handlers, keyboards, models
from apps.project.schemas import Project, ProjectStatus
from apps.webpage.schemas import Webpage
from json_advanced import dumps
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
        logger.error(e)
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
                            logger.error(f"Error:\n{repr(e)}\n")

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
            if inline_message_id is None:
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
    profile: Profile,
    chat_id: str = None,
    response_id: str = None,
    bot_name: str = None,
    **kwargs,
):
    async with AsyncUssoSession(
        Settings.USSO_REFRESH_URL, Settings.PIXIEE_REFRESH_TOKEN
    ) as session:
        async with session.get(f"https://api.pixiee.io/webpages/{wid}") as r:
            r.raise_for_status()
            webpage = Webpage(**await r.json())

        from apps.bots.routes import get_reverse_url

        reverse_url = get_reverse_url("ai_webpage_response")
        webhook_url = f"https://{Settings.root_url}{reverse_url}"
        key = "ads_for_brand"
        data = webpage.ai_data.model_dump()
        data["brief"] = str(webpage.ai_data.brief)
        ai_request = AIRequest(
            # prompt: str | None = None
            context=data,
            user_id=profile.user_id,
            task_status="init",
            # answer: dict[str, Any] | None = None
            # model: AIEngines = AIEngines.gpt_4o
            template_key=key,
            # ai_status
            metadata={
                "webhook": webhook_url,
                "user_id": str(profile.user_id),
                "chat_id": chat_id,
                "message_id": response_id,
                "bot_name": bot_name,
                "url": webpage.url,
                "webpage_id": webpage.uid,
            },
        )
        try:
            async with session.post(
                f"https://api.pixiee.io/ai/",
                data=dumps(ai_request.model_dump(exclude_none=True)),
                headers={"Content-Type": "application/json"},
            ) as r:
                r.raise_for_status()
                ai_response = AIRequest(**await r.json())

            async with session.post(
                f"https://api.pixiee.io/ai/{ai_response.uid}/start"
            ) as r_start:
                r_start.raise_for_status()
                logging.info(f"AIRequest started processing {ai_response.uid}")
        except Exception as e:
            logging.error(f"Content submit failed {e} for {ai_response.uid}")

            #

            # async with session.post(f"https://api.pixiee.io/ai/{key}", json=data) as r:
            #     r.raise_for_status()
            #     response: dict[str, list] = await r.json()

    # webpage_response = WebpageResponse(
    #     **response, url=webpage.url, webpage_id=webpage.uid
    # )
    # await webpage_response.save()

    # bot = handlers.get_bot(bot_name)
    # await bot.send_message(
    #     text=str(webpage_response),
    #     chat_id=chat_id,
    #     parse_mode="markdown",
    #     reply_markup=keyboards.content_keyboard(webpage_response.uid),
    # )

    # await bot.delete_message(chat_id, response_id)


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


async def content_submit(
    wrid: uuid.UUID,
    chat_id: str,
    bot_name: str,
    profile: Profile,
    state: tuple[int, int, int, int, int],
    response_id: str,
    **kwargs,
):
    from apps.bots.routes import get_reverse_url

    reverse_url = get_reverse_url("project_webhook")
    webhook_url = f"https://{Settings.root_url}{reverse_url}"

    try:
        handlers.get_bot(bot_name)
        webpage_response: WebpageResponse = await WebpageResponse.get_item(wrid)
        project = Project(
            user_id=profile.user_id,
            url=webpage_response.url,
            mode="auto",
            project_step="image",
            project_status=ProjectStatus(
                brief=StepStatus.init,
                content=StepStatus.done,
                image=StepStatus.none,
                render=StepStatus.none,
            ),
            related_objects=[
                {"id": webpage_response.webpage_id, "object_type": "Webpage"},
                {"id": webpage_response.ai_id, "object_type": "AIRequest"},
            ],
            data=webpage_response.get_project_data(state),
            metadata={
                "webhook": webhook_url,
                "user_id": str(profile.user_id),
                "chat_id": chat_id,
                "message_id": response_id,
                "bot_name": bot_name,
                "state": state,
            },
        )
        async with AsyncUssoSession(
            Settings.USSO_REFRESH_URL, Settings.PIXIEE_REFRESH_TOKEN
        ) as session:
            async with session.post(
                Project.create_url(),
                data=dumps(project.model_dump(exclude_none=True)),
                headers={"Content-Type": "application/json"},
            ) as r:
                r.raise_for_status()
                project = Project(**await r.json())

            async with session.post(
                f"https://api.pixiee.io/projects/{project.uid}/start"
            ) as r_start:
                r_start.raise_for_status()
    except Exception as e:
        logging.error(f"Content submit failed {e} for {project.uid}")

    logger.info(f"Content submit: {project}")
