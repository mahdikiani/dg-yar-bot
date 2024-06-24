import uuid
from typing import Literal

from apps.base.models import Language
from apps.base.schemas import OwnedEntitySchema, StepStatus, TaskSchema
from apps.renders.schemas import ContentAIData
from apps.webpage.schemas import SourceAIData
from pydantic import BaseModel


class ProjectData(SourceAIData, ContentAIData):
    pass
    # title: str | None = None
    # description: str | None = None
    # user_state: ProjectState | None = None


class ProjectStatus(BaseModel):
    # source: StepStatus = StepStatus.none
    brief: StepStatus = StepStatus.none
    content: StepStatus = StepStatus.none
    # image: StepStatus = StepStatus.none
    # bg_removal: StepStatus = StepStatus.none
    render: StepStatus = StepStatus.none


class Relation(BaseModel):
    id: uuid.UUID
    object_type: str


class Project(TaskSchema, OwnedEntitySchema):
    url: str
    mode: Literal["manual", "auto"] = "manual"
    language: Language = Language.Persian
    brand_id: uuid.UUID | None = None
    # project_status: ProjectState = ProjectState.source_archive_draft
    project_step: Literal["source", "brief", "content", "image", "render"] = (
        "source"
    )
    project_status: ProjectStatus = ProjectStatus()
    related_objects: list[Relation] | None = None

    data: ProjectData | None = None
