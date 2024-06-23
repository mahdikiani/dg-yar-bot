from utils import basic

from .models import BaseEntity, TaskMixin
from .schemas import TaskReference


async def get_task_item(task: TaskReference) -> BaseEntity | None:
    task_classes = {
        subclass.__name__: subclass
        for subclass in basic.get_all_subclasses(TaskMixin)
        if issubclass(subclass, BaseEntity)
    }

    task_class = task_classes.get(task.task_type)
    if not task_class:
        raise ValueError(f"Task type {task.task_type} is not supported.")

    task_item = await task_class.find_one(task_class.uid == task.task_id)
    if not task_item:
        raise ValueError(
            f"No task found with id {task.task_id} of type {task.task_type}."
        )

    return task_item
