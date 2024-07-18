import json
import uuid

import asyncpg
import beartype
import psycopg2
from beartype.typing import Any, Callable, Literal, Optional, Protocol
from loguru import logger
from pydantic import BaseModel

from workraft.models import DBConfig, WorkerState


class PostRunHandlerFn(Protocol):
    def __call__(
        self,
        result: Any,
        status: Literal["FAILURE", "SUCCESS", "RUNNING", "PENDING"],
        *args,
        **kwargs,
    ): ...


class PreRunHandlerFn(Protocol):
    def __call__(
        self,
        *args,
        **kwargs,
    ): ...


class Workraft:
    """Workraft: A simple distributed task system."""

    def __init__(self):
        self.tasks: dict[str, Callable] = {}
        self.prerun_handler_fn: Optional[Callable] = None
        self.postrun_handler_fn: Optional[Callable] = None

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

    @staticmethod
    @beartype.beartype
    def send_task_sync(
        name: str,
        task_args: list,
        task_kwargs: dict,
        db_config: DBConfig,
        queue: str = "DEFAULT",
        prerun_handler_args: list = [],
        prerun_handler_kwargs: dict = {},
        postrun_handler_args: list = [],
        postrun_handler_kwargs: dict = {},
        retry_on_failure: bool = False,
        retry_limit: int = 3,
    ) -> None:
        logger.info(f"Sending task {name} to queue {queue} with id {id}")
        conn = None
        try:
            conn = psycopg2.connect(**db_config.dict())
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bountyboard (id, status, payload, queue, retry_on_failure, retry_limit)
                    VALUES (%s, 'PENDING', %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        {
                            "name": name,
                            "task_args": task_args,
                            "task_kwargs": task_kwargs,
                            "prerun_handler_args": prerun_handler_args,
                            "prerun_handler_kwargs": prerun_handler_kwargs,
                            "postrun_handler_args": postrun_handler_args,
                            "postrun_handler_kwargs": postrun_handler_kwargs,
                        },
                        queue,
                        retry_on_failure,
                        retry_limit,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to send task: {e}")
            raise e
        finally:
            if conn:
                conn.close()

    @staticmethod
    @beartype.beartype
    async def send_task_async(
        name: str,
        db_config: DBConfig,
        task_args: list[Any] = [],
        task_kwargs: dict[str, Any] = {},
        queue: str = "DEFAULT",
        prerun_handler_args: list[Any] = [],
        prerun_handler_kwargs: dict[str, Any] = {},
        postrun_handler_args: list[Any] = [],
        postrun_handler_kwargs: dict[str, Any] = {},
        retry_on_failure: bool = False,
        retry_limit: int = 3,
    ) -> None:
        pool = await asyncpg.create_pool(**db_config.model_dump())
        if not pool:
            raise Exception("Failed to create connection pool")
        n_tasks = 5
        async with pool.acquire() as conn:
            await conn.execute(
                """
                        INSERT INTO bountyboard (id, status, payload, queue, retry_on_failure, retry_limit)
                        VALUES ($1, 'PENDING', $2, $3, $4, $5)
                        """,
                uuid.uuid4(),
                json.dumps(
                    {
                        "name": name,
                        "task_args": task_args,
                        "task_kwargs": task_kwargs,
                        "prerun_handler_args": prerun_handler_args,
                        "prerun_handler_kwargs": prerun_handler_kwargs,
                        "postrun_handler_args": postrun_handler_args,
                        "postrun_handler_kwargs": postrun_handler_kwargs,
                    }
                ),
                queue,
                retry_on_failure,
                retry_limit,
            )


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
