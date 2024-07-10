import asyncio
import logging

from apps.ai.models import WebpageResponse
from apps.ai.schemas import AIRequest
from apps.bots import keyboards
from apps.bots.handlers import get_bot, update_bot
from apps.project.schemas import Project, ProjectDetails
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

    if webpage.ai_data and webpage.ai_data.brief:
        text = str(webpage.ai_data)
        markup = keyboards.brief_keyboard(webpage.uid)
    else:
        text = f"{webpage.task_report} ..."
        markup = None

    if webpage.metadata.get("chat_id") and webpage.metadata.get("message_id"):
        bot = get_bot(webpage.metadata.get("bot_name"))
        asyncio.create_task(
            try_except_wrapper(bot.edit_message_text)(
                text=text,
                chat_id=webpage.metadata.get("chat_id"),
                message_id=webpage.metadata.get("message_id"),
                parse_mode="markdown",
                reply_markup=markup,
            )
        )

    return JSONResponse({"ok": f"Webpage webhook request processed for {webpage.uid}"})


@router.post("/ai-webhook/ai_webpage_response")
async def ai_webpage_response(ai_request: AIRequest):
    if not ai_request.metadata:
        return JSONResponse({"error": "metadata not found"})

    webpage_response = WebpageResponse(
        **ai_request.answer,
        ai_id=ai_request.uid,
        webpage_id=ai_request.metadata.get("webpage_id"),
        url=ai_request.metadata.get("url"),
    )
    await webpage_response.save()

    if ai_request.metadata.get("chat_id") and ai_request.metadata.get("message_id"):
        bot = get_bot(ai_request.metadata.get("bot_name"))
        asyncio.create_task(
            try_except_wrapper(bot.edit_message_text)(
                text=str(webpage_response),
                chat_id=ai_request.metadata.get("chat_id"),
                message_id=ai_request.metadata.get("message_id"),
                parse_mode="markdown",
                reply_markup=keyboards.content_keyboard(webpage_response.uid),
            )
        )

    return JSONResponse(
        {"ok": f"AI webhook request processed for {ai_request.uid}"}
    )


@router.post("/project-webhook")
async def project_webhook(project: Project):
    logging.info(project)
    bot = get_bot(project.metadata.get("bot_name"))

    if project.project_status.render == "done":
        project_detail = await ProjectDetails.get_item(project.uid)
        if project_detail.results:
            for result in project_detail.results:
                asyncio.create_task(
                    try_except_wrapper(bot.send_photo)(
                        chat_id=project.metadata.get("chat_id"),
                        photo=result.get("address"),
                        caption=result.get("caption"),
                        parse_mode="markdown",
                    )
                )
    else:
        text = f"{project.task_report} ..."
        if project.metadata.get("chat_id") and project.metadata.get("message_id"):
            asyncio.create_task(
                try_except_wrapper(bot.edit_message_text)(
                    text=text,
                    chat_id=project.metadata.get("chat_id"),
                    message_id=project.metadata.get("message_id"),
                    parse_mode="markdown",
                )
            )

    return JSONResponse({"ok": f"Project webhook request processed for {project.uid}"})


def get_reverse_url(name: str, **kwargs) -> str:
    for route in router.routes:
        if route.name == name:
            return route.path.format(**kwargs)
