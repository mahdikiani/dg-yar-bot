import asyncio
import logging
from .schemas import DGWebhook
from fastapi import APIRouter
import fastapi
from apps.bots.handlers import update_bot
from apps.digikala.digikala import DGClient
router = APIRouter()


@router.post("/bots/webhook/{bot}")
async def bot_update(bot: str, data: dict):
    asyncio.create_task(update_bot(bot, data))
