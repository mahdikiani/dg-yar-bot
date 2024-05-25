import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel


class Language(str, Enum):
    English = "English"
    Persian = "Persian"


class ProductInfo(BaseModel):
    name: str
    description: str


class ProjectBrief(BaseModel):
    description: str | None = None
    attention: str | None = None
    interest: str | None = None
    desire: str | None = None
    action: str | None = None

    def __str__(self, lang: Language = Language.Persian):
        match lang:
            case Language.Persian:
                introduction = "معرفی"
                attention = "توجه"
                interest = "علاقه"
                desire = "خواست"
                action = "عمل"

            case _:
                introduction = "Introduction"
                attention = "Attention"
                interest = "Interest"
                desire = "Desire"
                action = "Action"

        return "\n\n".join(
            [
                f"{introduction}: {self.description}",
                f"{attention}: {self.attention}",
                f"{interest}: {self.interest}",
                f"{desire}: {self.desire}",
                f"{action}: {self.action}",
            ]
        ).strip()


class SourceAIData(BaseModel):
    favicon: str | None = None
    colors: list[str] | None = None
    fonts: list[str] | None = None
    audience: str | None = None
    tone: Literal["friendly", "professional", "informal", "enthusiastic"] | None = None
    products: list[ProductInfo] | None = None
    product_index: int | None = None
    brief: ProjectBrief | None = None


class WebpageDTO(BaseModel):
    id: str | None = None
    uid: uuid.UUID
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    metadata: dict[str, Any] | None = None

    task_status: Literal["draft", "init", "processing", "done", "error"] = "draft"
    task_report: str | None = None
    task_progress: int = -1
    task_logs: list = []
    task_references: list[uuid.UUID | list] | None = None

    url: str
    page_source: str | None = None
    crawl_method: str | None = None
    screenshot: str | None = None
    ai_data: SourceAIData | None = None
