"""FastAPI server configuration."""

import dataclasses
import logging
import logging.config
import os
from pathlib import Path

import dotenv
from singleton import Singleton

dotenv.load_dotenv()
base_dir = Path(__file__).resolve().parent.parent


@dataclasses.dataclass
class Settings(metaclass=Singleton):
    """Server config settings."""

    root_url: str = os.getenv("DOMAIN", default="http://localhost:8000")
    mongo_uri: str = os.getenv("MONGO_URI", default="mongodb://localhost:27017")
    redis_uri: str = os.getenv("REDIS_URI", default="redis://localhost:6379")
    project_name: str = os.getenv("PROJECT_NAME", default="FastAPI Launchpad")

    profile_service_url: str = "https://profile.pixiee.bot.inbeet.tech"

    MAX_SESSION_IDLE_TIME: int = 60 * 60 * 12  # 24 hours

    testing: bool = os.getenv("TESTING", default=False)

    log_config = {
        "version": 1,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "INFO",
                "filename": base_dir / "logs" / "info.log",
                "formatter": "standard",
            },
        },
        "formatters": {
            "standard": {
                "format": "[{levelname} : {filename}:{lineno} : {asctime} -> {funcName:10}] {message}",
                # "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                "style": "{",
            }
        },
        "loggers": {
            "": {
                "handlers": [
                    "console",
                    "file",
                ],
                "level": "INFO",
                "propagate": True,
            }
        },
    }

    def config_logger(self):
        if not (base_dir / "logs").exists():
            (base_dir / "logs").mkdir()

        logging.config.dictConfig(self.log_config)

    def config_bots(self):
        from telebot import TeleBot

        self.bot = TeleBot(os.getenv("BOT_TOKEN"))
        if self.bot.get_webhook_info().url != self.telegram_webhook:
            self.bot.set_webhook(url=self.telegram_webhook)