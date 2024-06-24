import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Literal

from beanie import (
    Document,
    Insert,
    Replace,
    Save,
    SaveChanges,
    Update,
    before_event,
)
from json_advanced import dumps
from singleton import Singleton
from utils import aionetwork, basic

from .schemas import (
    BaseEntitySchema,
    BusinessEntitySchema,
    BusinessOwnedEntitySchema,
    OwnedEntitySchema,
    TaskLogRecord,
    TaskSchema,
)


class BaseEntity(BaseEntitySchema, Document):
    class Settings:
        keep_nulls = False
        validate_on_save = True

    @before_event([Insert, Replace, Save, SaveChanges, Update])
    async def pre_save(self):
        self.updated_at = datetime.now()

    @classmethod
    def get_query(cls, *args, **kwargs):
        query = cls.find(cls.is_deleted == False)
        return query

    @classmethod
    async def get_item(cls, uid, *args, **kwargs) -> "BaseEntity":
        query = cls.get_query(*args, **kwargs).find(cls.uid == uid)
        items = await query.to_list()
        if not items:
            return None
        return items[0]


class OwnedEntity(OwnedEntitySchema, BaseEntity):
    @classmethod
    def get_query(cls, user_id, *args, **kwargs):
        query = cls.find(cls.is_deleted == False, cls.user_id == user_id)
        return query

    @classmethod
    async def get_item(cls, uid, user_id, *args, **kwargs) -> "OwnedEntity":
        query = cls.get_query(user_id, *args, **kwargs).find(cls.uid == uid)
        items = await query.to_list()
        if not items:
            return None
        return items[0]


class BusinessEntity(BusinessEntitySchema, BaseEntity):
    @classmethod
    def get_query(cls, business_id, *args, **kwargs):
        query = cls.find(
            cls.is_deleted == False, cls.business_id == business_id
        )
        return query

    @classmethod
    async def get_item(
        cls, uid, business_id, *args, **kwargs
    ) -> "BusinessEntity":
        query = cls.get_query(business_id, *args, **kwargs).find(
            cls.uid == uid
        )
        items = await query.to_list()
        if not items:
            return None
        return items[0]


class BusinessOwnedEntity(BusinessOwnedEntitySchema, BaseEntity):

    @classmethod
    def get_query(cls, business_id, user_id, *args, **kwargs):
        query = cls.find(
            cls.is_deleted == False,
            cls.business_id == business_id,
            cls.user_id == user_id,
        )
        return query

    @classmethod
    async def get_item(
        cls, uid, business_id, user_id, *args, **kwargs
    ) -> "BusinessEntity":
        query = cls.get_query(business_id, user_id, *args, **kwargs).find(
            cls.uid == uid
        )
        items = await query.to_list()
        if not items:
            return None
        return items[0]


class SignalRegistry(metaclass=Singleton):
    def __init__(self):
        self.signal_map: dict[
            str,
            list[
                Callable[..., None] | Callable[..., Coroutine[Any, Any, None]]
            ],
        ] = {}


class TaskMixin(TaskSchema):
    @classmethod
    def signals(cls):
        registry = SignalRegistry()
        if cls.__name__ not in registry.signal_map:
            registry.signal_map[cls.__name__] = []
        return registry.signal_map[cls.__name__]

    @classmethod
    def add_signal(
        cls,
        signal: Callable[..., None] | Callable[..., Coroutine[Any, Any, None]],
    ):
        cls.signals().append(signal)

    @classmethod
    async def emit_signals(cls, task_instance, **kwargs):
        if task_instance.metadata:
            webhook = task_instance.metadata.get(
                "webhook"
            ) or task_instance.metadata.get("webhook_url")
            if webhook:
                task_dict = task_instance.model_dump()
                task_dict.update(
                    {"task_type": task_instance.__class__.__name__}
                )
                task_dict.update(kwargs)
                webhook_signals = [
                    basic.try_except_wrapper(aionetwork.aio_request)(
                        method="post",
                        url=webhook,
                        headers={"Content-Type": "application/json"},
                        data=dumps(task_dict),
                        raise_exception=False,
                    )
                ]
        else:
            webhook_signals = []

        signals = webhook_signals + [
            (
                basic.try_except_wrapper(signal)(task_instance)
                if asyncio.iscoroutinefunction(signal)
                else basic.try_except_wrapper(signal)(task_instance)
                # asyncio.to_thread(signal, task_instance)
            )
            for signal in cls.signals()
        ]

        await asyncio.gather(*signals)

    async def save_status(
        self,
        status: Literal["draft", "init", "processing", "done", "error"],
        **kwargs,
    ):
        self.task_status = status
        await self.add_log(
            TaskLogRecord(
                task_status=self.task_status,
                message=f"Status changed to {status}",
            ),
            **kwargs,
        )

    async def add_reference(self, task_id: uuid.UUID, **kwargs):
        self.task_references.append(task_id)
        await self.add_log(
            TaskLogRecord(
                task_status=self.task_status,
                message=f"Added reference to task {task_id}",
            ),
            **kwargs,
        )

    async def save_report(self, report: str, **kwargs):
        self.task_report = report
        await self.add_log(
            TaskLogRecord(
                task_status=self.task_status,
                message=report,
            ),
            **kwargs,
        )

    async def add_log(
        self, log_record: TaskLogRecord, *, emit: bool = True, **kwargs
    ):
        self.task_logs.append(log_record)
        if emit:
            # await self.emit_signals(self)
            await self.save_and_emit()

    async def start_processing(self):
        if self.task_references is None:
            raise NotImplementedError(
                "Subclasses should implement this method"
            )

        await self.task_references.list_processing()

    async def save_and_emit(self):
        try:
            await asyncio.gather(self.save(), self.emit_signals(self))
        except Exception as e:
            logging.error(f"An error occurred: {e}")

    async def update_and_emit(self, **kwargs):
        if kwargs.get("task_status") == "done":
            kwargs["task_progress"] = kwargs.get("task_progress", 100)
            # kwargs["task_report"] = kwargs.get("task_report")

        for key, value in kwargs.items():
            setattr(self, key, value)

        if kwargs.get("task_report"):
            await self.add_log(
                TaskLogRecord(
                    task_status=self.task_status,
                    message=kwargs["task_report"],
                ),
                emit=False,
            )

        await self.save_and_emit()


class TaskBaseEntity(TaskMixin, BaseEntity):
    pass


class TaskOwnedEntity(TaskMixin, OwnedEntity):
    pass


class Language(str, Enum):
    English = "English"
    Persian = "Persian"
