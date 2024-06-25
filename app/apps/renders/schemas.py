import uuid
from typing import Any, Literal

from pydantic import BaseModel

from apps.base.schemas import OwnedEntitySchema, TaskSchema


class ContentAIData(BaseModel):
    texts: list[str] | None = None
    images: list[str] | None = None
    logo: str | None = None
    cta: str | None = None
    colors: list[str] | None = None
    fonts: list[str] | None = None
    caption: str | None = None
    cta_link: str | None = None


class Render(TaskSchema, OwnedEntitySchema):
    project_id: uuid.UUID

    contents: ContentAIData
    # state: Literal["draft", "init", "error", "done"] = "draft"

    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class Creative(OwnedEntitySchema):
    # project_id: uuid.UUID
    render_id: uuid.UUID
    template_id: uuid.UUID | None = None

    state: Literal["draft", "init", "error", "done"] = "draft"

    address: str | None = None
    caption: str | None = None
    template_name: str | None = None

    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
