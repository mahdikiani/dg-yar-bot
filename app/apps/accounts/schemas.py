import uuid
from datetime import datetime
from typing import Any

from apps.ai.models import AIEngines
from pydantic import BaseModel


class ProfileData(BaseModel):
    ai_engine: AIEngines


class Profile(BaseModel):
    uid: uuid.UUID
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    metadata: dict[str, Any] | None = None

    user_id: str
    business_id: str

    data: ProfileData


class ProfileCreate(BaseModel):
    user_id: uuid.UUID
    data: ProfileData
