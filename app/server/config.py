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
    project_name: str = os.getenv("PROJECT_NAME", default="Pixbot")
    page_max_limit: int = 100

    profile_service_url: str = "https://profile.pixiee.bot.inbeet.tech"

    MAX_SESSION_IDLE_TIME: int = 60 * 60 * 12  # 24 hours
    MESSAGE_LENGTH: int = 128
    MIN_MESSAGE_LENGTH: int = 128

    USSO_REFRESH_URL: str = os.getenv("USSO_REFRESH_URL")
    PIXIEE_REFRESH_TOKEN: str = os.getenv("PIXIEE_REFRESH_TOKEN")
    TAPSAGE_API_KEY: str = os.getenv("TAPSAGE_API_KEY")
    METIS_API_KEY: str = os.getenv("METIS_API_KEY")
    USSO_API_KEY: str = os.getenv("USSO_API_KEY")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN")
    REPLICATE_SERVICE: str = (
        "lucataco/remove-bg:95fcc2a26d3899cd6c2691c900465aaeff466285a65c14638cc5f36f34befaf1"
    )
    GOOGLE_SECRET: str = os.getenv("GOOGLE_SECRET")
    PROXY: str = os.getenv("PROXY")

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
            "bot_file": {
                "class": "logging.FileHandler",
                "level": "INFO",
                "filename": base_dir / "logs" / "bot.log",
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
            },
            "bot": {
                "handlers": [
                    "console",
                    "bot_file",
                ],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    def config_logger(self):
        if not (base_dir / "logs").exists():
            (base_dir / "logs").mkdir()

        logging.config.dictConfig(self.log_config)
