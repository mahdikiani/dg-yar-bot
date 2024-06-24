import asyncio

from apps.bots import keyboards
from apps.bots.handlers import get_bot, update_bot
from apps.webpage.schemas import Webpage
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from utils.basic import try_except_wrapper

router = APIRouter(prefix="/bots")


@router.post("/webhook/{bot}")
async def bot_update(bot: str, data: dict):
    asyncio.create_task(update_bot(bot, data))


@router.post("/webpage-webhook")
async def webpage_webhook(webpage: Webpage, background_tasks: BackgroundTasks):
    if not webpage.metadata:
        return JSONResponse({"error": "metadata not found"})

    bot = get_bot(webpage.metadata.get("bot_name"))

    if webpage.ai_data and webpage.ai_data.brief:
        text = str(webpage.ai_data)
        markup = keyboards.brief_keyboard(webpage.uid)
    else:
        text = f"{webpage.task_report} ..."
        markup = None

    if webpage.metadata.get("chat_id") and webpage.metadata.get("message_id"):
        asyncio.create_task(
            try_except_wrapper(bot.edit_message_text)(
                text=text,
                chat_id=webpage.metadata.get("chat_id"),
                message_id=webpage.metadata.get("message_id"),
                parse_mode="markdown",
                reply_markup=markup,
            )
        )

    return JSONResponse(
        {"ok": f"Webpage webhook request processed for {webpage.uid}"}
    )


@router.post("/project-webhook")
async def project_webhook(data: dict, background_tasks: BackgroundTasks):
    pass


def get_reverse_url(name: str, **kwargs) -> str:
    for route in router.routes:
        if route.name == name:
            return route.path.format(**kwargs)
