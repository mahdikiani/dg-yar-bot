import asyncio

from fastapi import APIRouter

from apps.bots.handlers import update_bot

router = APIRouter(prefix="/bots")


@router.post("/webhook/{bot}")
async def bot_update(bot: str, data: dict):
    import logging
    logging.info(f'webhook retrieve')
    asyncio.create_task(update_bot(bot, data))
