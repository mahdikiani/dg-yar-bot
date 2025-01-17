import uuid

from pydantic import BaseModel, Field

from apps.ai.models import AIEngines
from apps.base.schemas import BaseEntitySchema


class ProfileData(BaseModel):
    ai_engine: AIEngines = AIEngines.gpt_4o


class Profile(BaseEntitySchema):
    user_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    data: ProfileData = ProfileData()


class ProfileCreate(BaseModel):
    user_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    data: ProfileData = ProfileData()
