import uuid

import beartype
from beartype.typing import Callable
from loguru import logger
from sqlalchemy import text

from workcraft.constants import DEFAULT_QUEUE
from workcraft.db import DBEngineSingleton
from workcraft.models import (
    DBConfig,
    PostRunHandlerFn,
    PreRunHandlerFn,
    SetupHandlerFn,
    Task,
    TaskHandlerFn,
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


class Workcraft:
    """Workcraft: A simple distributed task system."""

    def __init__(self):
        self.tasks: dict[str, Callable] = {}
        self.setup_handler_fn: Callable | None = None
        self.prerun_handler_fn: Callable | None = None
        self.postrun_handler_fn: Callable | None = None

    def task(self, name: str):
        def decorator(func: TaskHandlerFn):
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
        task_name: str,
        queue: str = "DEFAULT",
        retry_on_failure: bool = False,
        retry_limit: int = 3,
    ) -> str:
        id = str(uuid.uuid4())
        logger.info(f"Sending task {task_name} to queue {queue} with id {id}")
        try:
            with DBEngineSingleton.get(db_config).connect() as conn:
                statement = text(
                    """
INSERT INTO bountyboard (id, task_name, status, payload, queue, retry_on_failure, retry_limit)
VALUES (:id, :task_name, 'PENDING', :payload, :queue, :retry_on_failure, :retry_limit)
                    """  # noqa
                )
                conn.execute(
                    statement,
                    {
                        "id": id,
                        "task_name": task_name,
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

    @staticmethod
    @beartype.beartype
    def get_task_sync(db_config: DBConfig, task_id: str) -> Task | None:
        try:
            with DBEngineSingleton.get(db_config).connect() as conn:
                statement = text(
                    """
                    SELECT * FROM bountyboard WHERE id = :id
                    """
                )
                result = conn.execute(statement, {"id": task_id}).fetchone()
                if result:
                    return Task.from_db_data(result._asdict())
                else:
                    logger.info(f"Task {task_id} not found")
                    return None
        except Exception as e:
            logger.error(f"Failed to get task: {e}")
            raise e
