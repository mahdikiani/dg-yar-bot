import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field


class BaseEntitySchema(BaseModel):
    uid: uuid.UUID = Field(default_factory=uuid.uuid4, index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_deleted: bool = False
    metadata: dict[str, Any] | None = None

    @property
    def create_exclude_set(self) -> list[str]:
        return ["uid", "created_at", "updated_at", "is_deleted"]

    @property
    def create_field_set(self) -> list:
        return []

    @property
    def update_exclude_set(self) -> list:
        return ["uid", "created_at", "updated_at"]

    @property
    def update_field_set(self) -> list:
        return []

    def model_dump_create(self):
        assert not (self.create_exclude_set and self.create_field_set)
        if self.create_field_set:
            return self.model_dump(fields=self.create_field_set)

        return self.model_dump(exclude=self.create_exclude_set)

    def model_dump_update(self):
        assert not (self.update_exclude_set and self.update_field_set)
        if self.update_field_set:
            return self.model_dump(fields=self.update_field_set)

        return self.model_dump(exclude=self.update_exclude_set)

    def expired(self, days: int = 3):
        return (datetime.now() - self.updated_at).days > days


class OwnedEntitySchema(BaseEntitySchema):
    user_id: uuid.UUID

    @property
    def create_exclude_set(self) -> list[str]:
        return ["uid", "created_at", "updated_at", "is_deleted", "user_id"]

    @property
    def update_exclude_set(self) -> list[str]:
        return ["uid", "created_at", "updated_at", "user_id"]

    def model_dump_create(self, user_id: uuid.UUID):
        assert not (self.create_exclude_set and self.create_field_set)
        if self.create_field_set:
            return self.model_dump(fields=self.create_field_set) | {"user_id": user_id}

        return self.model_dump(exclude=self.create_exclude_set) | {"user_id": user_id}


class BusinessEntitySchema(BaseEntitySchema):
    business_id: uuid.UUID

    @property
    def create_exclude_set(self) -> list[str]:
        return ["uid", "created_at", "updated_at", "is_deleted", "business_id"]

    @property
    def update_exclude_set(self) -> list[str]:
        return ["uid", "created_at", "updated_at", "business_id"]

    def model_dump_create(self, business_id: uuid.UUID):
        assert not (self.create_exclude_set and self.create_field_set)
        if self.create_field_set:
            return self.model_dump(fields=self.create_field_set) | {
                "business_id": business_id
            }

        return self.model_dump(exclude=self.create_exclude_set) | {
            "business_id": business_id
        }


class BusinessOwnedEntitySchema(OwnedEntitySchema, BusinessEntitySchema):
    @property
    def create_exclude_set(self) -> list[str]:
        return [
            "uid",
            "created_at",
            "updated_at",
            "is_deleted",
            "user_id",
            "business_id",
        ]

    @property
    def update_exclude_set(self) -> list[str]:
        return ["uid", "created_at", "updated_at", "user_id", "business_id"]

    def model_dump_create(self, business_id: uuid.UUID, user_id: uuid.UUID):
        assert not (self.create_exclude_set and self.create_field_set)
        if self.create_field_set:
            return self.model_dump(fields=self.create_field_set) | {
                "user_id": user_id,
                "business_id": business_id,
            }

        return self.model_dump(exclude=self.create_exclude_set) | {
            "user_id": user_id,
            "business_id": business_id,
        }


class StepStatus(str, Enum):
    none = "null"
    draft = "draft"
    init = "init"
    processing = "processing"
    paused = "paused"
    done = "done"
    error = "error"


class StepStatus(str, Enum):
    none = "null"
    draft = "draft"
    init = "init"
    processing = "processing"
    paused = "paused"
    done = "done"
    error = "error"


class TaskLogRecord(BaseModel):
    reported_at: datetime = Field(default_factory=datetime.now)
    message: str
    task_status: StepStatus
    duration: int = 0
    data: dict | None = None

    def __eq__(self, other):
        if isinstance(other, TaskLogRecord):
            return (
                self.reported_at == other.reported_at
                and self.message == other.message
                and self.task_status == other.task_status
                and self.duration == other.duration
                and self.data == other.data
            )
        return False

    def __hash__(self):
        return hash((self.reported_at, self.message, self.task_status, self.duration))


class TaskReference(BaseModel):
    task_id: uuid.UUID
    task_type: str

    def __eq__(self, other):
        if isinstance(other, TaskReference):
            return self.task_id == other.task_id and self.task_type == other.task_type
        return False

    def __hash__(self):
        return hash((self.task_id, self.task_type))


class TaskReferenceList(BaseModel):
    tasks: list[Union[TaskReference, "TaskReferenceList"]] = []
    mode: Literal["serial", "parallel"] = "serial"

    async def list_processing(self):
        task_items = [task.get_task_item() for task in self.tasks]
        match self.mode:
            case "serial":
                for task_item in task_items:
                    await task_item.start_processing()
            case "parallel":
                await asyncio.gather(*[task.start_processing() for task in task_items])


class TaskSchema(BaseModel):
    task_status: StepStatus = StepStatus.draft
    task_report: str | None = None
    task_progress: int = -1
    task_logs: list[TaskLogRecord] = []
    task_references: TaskReferenceList | None = None
