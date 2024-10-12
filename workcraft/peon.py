import asyncio
import json
import random

from beartype.typing import Any
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import Connection, text

from workcraft.core import Workcraft, WorkerStateSingleton
from workcraft.db import (
    DBEngineSingleton,
    update_worker_state_sync,
    verify_database_setup,
)
from workcraft.models import DBConfig, Task, TaskStatus
from workcraft.settings import settings


def dequeue_task(db_config: DBConfig, workcraft: Workcraft) -> Task | None:
    def _mark_task_as_invalid(conn: Connection, task_id: str):
        logger.error(f"Marking task {task_id} as INVALID")
        statement = text("""
            UPDATE bountyboard
            SET status = 'INVALID'
            WHERE id = :id
        """)
        conn.execute(statement, {"id": task_id})
        conn.commit()

    registered_tasks = workcraft.tasks.keys()
    with DBEngineSingleton.get(db_config).connect() as conn:
        try:
            statement = text("""
SELECT * FROM bountyboard
WHERE status = 'PENDING' OR (status = 'FAILURE' AND retry_on_failure = TRUE AND retry_count < retry_limit)
AND JSON_UNQUOTE(JSON_EXTRACT(payload, '$.name')) IN :registered_tasks
ORDER BY created_at ASC
LIMIT 1
FOR UPDATE
            """)  # noqa: E501
            result = conn.execute(
                statement, {"registered_tasks": tuple(registered_tasks)}
            ).fetchone()
        except Exception as e:
            logger.error(f"Error querying task: {e}")
            return None
        if result:
            resultdict = result._asdict()
            try:
                task = Task.from_db_data(resultdict)
                statement = text("""
                    UPDATE bountyboard
                    SET status = 'RUNNING',
                        worker_id = :worker_id
                    WHERE id = :id
                """)
                conn.execute(
                    statement,
                    {"id": task.id, "worker_id": WorkerStateSingleton.get().id},
                )
                conn.commit()
                WorkerStateSingleton.update(status="WORKING", current_task=task.id)
                update_worker_state_sync(
                    db_config, worker_state=WorkerStateSingleton.get()
                )
                return task
            except ValidationError as e:
                logger.error(f"Error validating task: {e}. Invalid task: {resultdict}")
                _mark_task_as_invalid(conn, resultdict["id"])
                return None
            except Exception as e:
                logger.error(f"Error dequeuing task: {e}")
                _mark_task_as_invalid(conn, resultdict["id"])
                return None
        else:
            return None


async def run_peon(db_config: DBConfig, workcraft: Workcraft):
    verify_database_setup(db_config)
    WorkerStateSingleton.update(status="IDLE", current_task=None)
    update_worker_state_sync(db_config, worker_state=WorkerStateSingleton.get())

    logger.info("Tasks:")
    for name, _ in workcraft.tasks.items():
        logger.info(f"- {name}")

    logger.info("Ready to work!")

    try:
        while True:
            task = dequeue_task(db_config, workcraft)
            if task:
                logger.info(f"Dequeued task: {task}")
                await execute_task(db_config, task, workcraft)
            else:
                await asyncio.sleep(settings.DB_POLLING_INTERVAL)
            random_noise = random.normalvariate(
                settings.DB_POLLING_INTERVAL_RANDOMNESS_MEAN,
                settings.DB_POLLING_INTERVAL_RANDOMNESS_STDDEV,
            )
            await asyncio.sleep(settings.DB_POLLING_INTERVAL + random_noise)
    except asyncio.CancelledError:
        logger.info("Main loop cancelled. Shutting down...")


async def execute_task(
    db_config: DBConfig,
    task: Task,
    workcraft: Workcraft,
) -> None:
    try:
        await execute_prerun_handler(workcraft, task)
    except Exception as e:
        logger.error(f"Prerun handler failed: {e}, continuing...")

    result = None
    status = TaskStatus.RUNNING

    try:
        result = await execute_main_task(workcraft, task)
        logger.info(f"Task {task.payload.name} returned: {result}")
        status = TaskStatus.SUCCESS
    except Exception as e:
        logger.error(f"Task {task.payload.name} failed: {e}")
        status = TaskStatus.FAILURE
        result = str(e)
    finally:
        logger.info(f"Task {task.payload.name} finished with status: {status}")
        with DBEngineSingleton.get(db_config).connect() as conn:
            result = json.dumps(result)
            update_task_status(conn, task.id, status, result)
        task.status = status
        task.result = result
        WorkerStateSingleton.update(status="IDLE", current_task=None)
        update_worker_state_sync(db_config, WorkerStateSingleton.get())
    try:
        await execute_postrun_handler(workcraft, task)
    except Exception as e:
        logger.error(f"Postrun handler failed: {e}")


async def execute_prerun_handler(workcraft: Workcraft, task: Task) -> None:
    if workcraft.prerun_handler_fn is not None:
        await execute_handler(
            workcraft.prerun_handler_fn,
            [task.id, task.payload.name] + task.payload.prerun_handler_args,
            task.payload.prerun_handler_kwargs,
        )


async def execute_main_task(workcraft: Workcraft, task: Task) -> Any:
    task_handler = workcraft.tasks[task.payload.name]
    if asyncio.iscoroutinefunction(task_handler):
        return await task_handler(
            task.id, *task.payload.task_args, **task.payload.task_kwargs
        )
    else:
        return task_handler(
            task.id, *task.payload.task_args, **task.payload.task_kwargs
        )


async def execute_postrun_handler(
    workcraft: Workcraft,
    task: Task,
) -> None:
    if workcraft.postrun_handler_fn is not None:
        await execute_handler(
            workcraft.postrun_handler_fn,
            [task.id, task.payload.name, task.result, task.status.value]
            + task.payload.postrun_handler_args,
            task.payload.postrun_handler_kwargs,
        )


async def execute_handler(handler: Any, args: list, kwargs: dict) -> None:
    if asyncio.iscoroutinefunction(handler):
        await handler(*args, **kwargs)
    else:
        handler(*args, **kwargs)


def update_task_status(
    conn: Connection, task_id: str, status: TaskStatus, result: Any | None
) -> None:
    try:
        conn.execute(
            text(
                "UPDATE bountyboard SET status = :status, result = :res WHERE id = :id"
            ),
            {
                "status": status.value,
                "res": result,
                "id": task_id,
            },
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to update task {task_id} status to {status}: {e}")
        raise e
