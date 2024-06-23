import uuid

from apps.ai.models import AIEngines
from apps.base.schemas import BusinessOwnedEntitySchema
from pydantic import BaseModel


class ProfileData(BaseModel):
    ai_engine: AIEngines


class Profile(BusinessOwnedEntitySchema):
    data: ProfileData


class ProfileCreate(BaseModel):
    user_id: uuid.UUID
    data: ProfileData
