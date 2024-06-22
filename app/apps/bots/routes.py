from apps.bots.handlers import update_bot
from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/bots")


@router.post("/webhook/{bot}")
async def bot_update(bot: str, data: dict, background_tasks: BackgroundTasks):
    background_tasks.add_task(update_bot, bot, data)
