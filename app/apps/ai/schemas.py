from enum import Enum
from typing import Any

from apps.ai.models import AIEngines
from apps.base.schemas import OwnedEntitySchema, TaskSchema


class AIStatus(str, Enum):
    none = "none"
    draft = "draft"
    init = "init"
    queue = "queue"
    waiting = "waiting"
    running = "running"
    processing = "processing"
    done = "done"
    completed = "completed"
    error = "error"


class AIRequest(TaskSchema, OwnedEntitySchema):
    prompt: str | None = None
    context: dict[str, Any] | None = None
    answer: dict[str, Any] | None = None
    model: AIEngines = AIEngines.gpt_4o
    template_key: str | None = None
    ai_status: AIStatus = AIStatus.draft
