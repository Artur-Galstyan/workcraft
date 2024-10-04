import uuid

import beartype
from beartype.typing import Callable
from loguru import logger
from sqlalchemy import text

from workraft.constants import DEFAULT_QUEUE
from workraft.db import DBEngineSingleton
from workraft.models import (
    DBConfig,
    PostRunHandlerFn,
    PreRunHandlerFn,
    SetupHandlerFn,
    TaskPayload,
    WorkerState,
)


class WorkerStateSingleton:
    _worker_state: WorkerState = WorkerState(
        id=str(uuid.uuid4()), status="IDLE", current_task=None, queues=DEFAULT_QUEUE
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


class Workraft:
    """Workraft: A simple distributed task system."""

    def __init__(self):
        self.tasks: dict[str, Callable] = {}
        self.setup_handler_fn: Callable | None = None
        self.prerun_handler_fn: Callable | None = None
        self.postrun_handler_fn: Callable | None = None

    def task(self, name: str):
        def decorator(func: Callable):
            self.tasks[name] = func
            return func

        return decorator

    def prerun_handler(self):
        def decorator(func: PreRunHandlerFn):
            self.prerun_handler_fn = func
            return func

        return decorator

    def postrun_handler(self):
        def decorator(func: PostRunHandlerFn):
            self.postrun_handler_fn = func
            return func

        return decorator

    def setup_handler(self):
        def decorator(func: SetupHandlerFn):
            self.setup_handler_fn = func
            return func

        return decorator

    @staticmethod
    @beartype.beartype
    def send_task_sync(
        db_config: DBConfig,
        payload: TaskPayload,
        queue: str = "DEFAULT",
        retry_on_failure: bool = False,
        retry_limit: int = 3,
    ) -> str:
        id = str(uuid.uuid4())
        logger.info(f"Sending task {payload.name} to queue {queue} with id {id}")
        try:
            with DBEngineSingleton.get(db_config).connect() as conn:
                statement = text(
                    """
    INSERT INTO bountyboard (id, status, payload, queue, retry_on_failure, retry_limit)
    VALUES (:id, 'PENDING', :payload, :queue, :retry_on_failure, :retry_limit)
                    """
                )
                conn.execute(
                    statement,
                    {
                        "id": id,
                        "payload": payload.model_dump_json(),
                        "queue": queue,
                        "retry_on_failure": retry_on_failure,
                        "retry_limit": retry_limit,
                    },
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to send task: {e}")
            raise e
        return id
