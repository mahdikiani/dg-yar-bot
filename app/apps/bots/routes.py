import asyncio

from apps.bots.handlers import update_bot
from fastapi import APIRouter

router = APIRouter(prefix="/bots")


@router.post("/webhook/{bot}")
async def bot_update(bot: str, data: dict):
    asyncio.create_task(update_bot(bot, data))
