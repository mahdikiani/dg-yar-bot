import asyncio

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from apps.digikala.workers import check_new_notifications

irst_timezone = pytz.timezone("Asia/Tehran")


async def init_workers():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_new_notifications, "interval", minutes=10)

    scheduler.start()

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        scheduler.shutdown()
