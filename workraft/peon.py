import asyncio
import json

import asyncpg
import tenacity
from asyncpg import Record
from asyncpg.pool import Pool
from beartype.typing import Any, Optional
from loguru import logger
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    RetryError,
    stop_after_attempt,
    wait_exponential,
)

from workraft.constants import NEW_TASK_CHANNEL, TASK_QUEUE_SEPARATOR
from workraft.core import WorkerStateSingleton, Workraft
from workraft.db import (
    get_connection_pool,
    get_task_listener_conenction,
    update_worker_state_async,
    verify_database_setup,
)
from workraft.models import TaskPayload


class NoTaskAvailable(Exception):
    pass


async def run_peon(db_config, workraft):
    pool = await get_connection_pool(db_config)
    await verify_database_setup(pool)

    listener_connection = await get_task_listener_conenction(db_config)

    async with pool.acquire() as conn:
        WorkerStateSingleton.update(status="IDLE", current_task=None)
        await update_worker_state_async(conn)
        await listener_connection.add_listener(
            "new_task",
            lambda conn, pid, channel, payload: asyncio.create_task(
                notification_handler(pool, payload, channel, workraft)
            ),
        )

        await listener_connection.add_listener(
            WorkerStateSingleton.get().id,
            lambda conn, pid, channel, payload: asyncio.create_task(
                notification_handler(pool, payload, channel, workraft)
            ),
        )

    logger.info("Tasks:")
    for name, _ in workraft.tasks.items():
        logger.info(f"- {name}")

    logger.info("Ready to work!")

    try:
        while True:
            await asyncio.sleep(1)  # Avoid busy-waiting
    except asyncio.CancelledError:
        logger.info("Main loop cancelled. Shutting down...")
    finally:
        await listener_connection.close()
        await pool.close()
        logger.info("Database connection closed.")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(NoTaskAvailable),
)
async def get_next_task_with_retry(pool, worker_id):
    async with pool.acquire() as conn:
        task_id = await conn.fetchval("SELECT get_next_task($1)", worker_id)
        if task_id is None:
            raise NoTaskAvailable("No task available in the queue")
        task_id = str(task_id)
        return task_id


async def notification_handler(
    pool: Pool, data: str, channel: str, workraft: Workraft
) -> None:
    logger.debug(f"Received notification: {data}")
    row_id, queue = data.split(TASK_QUEUE_SEPARATOR)

    if not should_process_notification(channel, queue):
        return

    try:
        # Create a task and wait for it with a timeout
        task = asyncio.create_task(process_notification(pool, row_id, workraft))
        await asyncio.gather(task, return_exceptions=True)
    except asyncio.CancelledError:
        logger.warning("Task was cancelled")
    except Exception as e:
        logger.error(f"Unhandled exception in notification_handler: {str(e)}")


def should_process_notification(channel: str, queue: str) -> bool:
    worker = WorkerStateSingleton.get()
    if channel != NEW_TASK_CHANNEL and channel != worker.id:
        logger.debug(f"Ignoring notification from channel {channel}")
        return False
    if queue not in worker.queues:
        logger.debug(f"Ignoring notification from queue {queue}")
        return False
    if worker.status != "IDLE":
        logger.debug(f"Worker status is {worker.status}, ignoring notification.")
        return False
    return True


async def process_notification(pool: Pool, row_id: str, workraft: Workraft) -> None:
    WorkerStateSingleton.update(status="PREPARING")
    async with pool.acquire() as conn:
        await update_worker_state_async(conn)

    try:
        task_id = await get_next_task_with_retry(pool, WorkerStateSingleton.get().id)
        logger.info(f"Successfully acquired task: {task_id}")
    except (NoTaskAvailable, RetryError) as e:
        await handle_task_acquisition_failure(pool, e)
        return

    await process_task(pool, task_id, workraft)


async def handle_task_acquisition_failure(pool: Pool, error: Exception) -> None:
    if isinstance(error, NoTaskAvailable):
        logger.info("No task available. Returning to IDLE state.")
    elif isinstance(error, RetryError):
        logger.error(
            "Failed to acquire task after 3 attempts. The task queue may be empty or the task may have been taken by another worker."
        )

    WorkerStateSingleton.update(status="IDLE")
    async with pool.acquire() as conn:
        await update_worker_state_async(conn)


async def process_task(pool: Pool, task_id: str, workraft: Workraft) -> None:
    print(task_id, type(task_id))
    WorkerStateSingleton.update(status="WORKING", current_task=task_id)
    async with pool.acquire() as conn:
        await update_worker_state_async(conn)
        task_row = await get_task_row(conn, task_id)

        if task_row is None:
            logger.error(f"Row {task_id} not found!")
            return

        payload = TaskPayload.model_validate(json.loads(task_row["payload"]))
        logger.info(f"Got task: {payload.name} and payload: {payload}")

        task = workraft.tasks.get(payload.name)
        if task is None:
            logger.error(f"Task {payload.name} not found!")
            return

        await execute_task(conn, task_id, task, payload, workraft)


async def get_task_row(conn: Any, task_id: str) -> Optional[Record]:
    return await conn.fetchrow(
        """
        SELECT id, status, payload
        FROM bountyboard
        WHERE id = $1
        FOR UPDATE SKIP LOCKED
        """,
        task_id,
    )


async def execute_task(
    conn: Any, task_id: str, task: Any, payload: TaskPayload, workraft: Workraft
) -> None:
    try:
        await execute_prerun_handler(workraft, payload)
    except Exception as e:
        logger.error(f"Prerun handler failed: {e}, continuing...")

    result = None
    try:
        result = await execute_main_task(task, payload)
        logger.info(f"Task {payload.name} returned: {result}")
        await update_task_status(conn, task_id, "SUCCESS", json.dumps(result))
    except ValidationError as e:
        logger.error(f"Task {payload.name} failed: {e}: Invalid payload")
        await update_task_status(conn, task_id, "FAILURE", str(e))
    except Exception as e:
        logger.error(f"Task {payload.name} failed: {e}")
        await update_task_status(conn, task_id, "FAILURE", str(e))
    finally:
        WorkerStateSingleton.update(status="IDLE", current_task=None)
        await update_worker_state_async(conn)

    try:
        await execute_postrun_handler(workraft, payload, result)
    except Exception as e:
        logger.error(f"Postrun handler failed: {e}")


async def execute_prerun_handler(workraft: Workraft, payload: TaskPayload) -> None:
    if workraft.prerun_handler_fn is not None:
        await execute_handler(
            workraft.prerun_handler_fn,
            payload.prerun_handler_args,
            payload.prerun_handler_kwargs,
        )


async def execute_main_task(task: Any, payload: TaskPayload) -> Any:
    if asyncio.iscoroutinefunction(task):
        return await task(*payload.task_args, **payload.task_kwargs)
    else:
        return task(*payload.task_args, **payload.task_kwargs)


async def execute_postrun_handler(
    workraft: Workraft, payload: TaskPayload, result: Any
) -> None:
    if workraft.postrun_handler_fn is not None:
        await execute_handler(
            workraft.postrun_handler_fn,
            [result] + payload.postrun_handler_args,
            payload.postrun_handler_kwargs,
        )


async def execute_handler(handler: Any, args: list, kwargs: dict) -> None:
    if asyncio.iscoroutinefunction(handler):
        await handler(*args, **kwargs)
    else:
        handler(*args, **kwargs)


async def update_task_status(conn: Any, task_id: str, status: str, result: str) -> None:
    await conn.execute(
        """
        UPDATE bountyboard
        SET status = $1, result = $2
        WHERE id = $3
        """,
        status,
        result,
        task_id,
    )
