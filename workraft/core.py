import uuid

from beartype.typing import Callable, Literal, Optional
from loguru import logger
from pydantic import BaseModel

from workraft.models import WorkerState


class Workraft:
    """Workraft: A simple distributed task system."""

    def __init__(self):
        self.tasks: dict[str, Callable] = {}

    def task(self, name: str):
        def decorator(func: Callable):
            self.tasks[name] = func
            # logger.info(f"Registered task: {name}")
            # logger.debug(f"Function arguments: {func.__code__.co_varnames}")
            # logger.debug(f"Function name: {func.__name__}")
            # logger.debug(f"Function arg types: {func.__annotations__}")
            return func

        return decorator

    def postrun_handler(self):
        def decorator(func: Callable):
            self.postrun_handler = func
            return func

        return decorator


class WorkerStateSingleton:
    _worker_state: WorkerState = WorkerState(
        id=str(uuid.uuid4()), status="IDLE", current_task=None
    )

    @staticmethod
    def get():
        return WorkerStateSingleton._worker_state

    @staticmethod
    def update(**kwargs):
        WorkerStateSingleton._worker_state = (
            WorkerStateSingleton._worker_state.model_copy(update=kwargs)
        )
        return WorkerStateSingleton._worker_state
