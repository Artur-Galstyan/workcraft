import asyncio
import json

import tenacity
from asyncpg import Record
from beartype.typing import Optional
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from workraft.constants import NEW_TASK_CHANNEL
from workraft.core import WorkerStateSingleton
from workraft.db import (
    get_connection_pool,
    get_task_listener_conenction,
    update_worker_state_async,
    verify_database_setup,
)


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
        return task_id


async def notification_handler(pool, row_id, channel, workraft):
    logger.debug(f"Received notification: {row_id}, channel: {channel}")
    if channel != NEW_TASK_CHANNEL and channel != WorkerStateSingleton.get().id:
        logger.debug(f"Ignoring notification from channel {channel}")
        return
    if WorkerStateSingleton.get().status != "IDLE":
        logger.debug(
            f"Peon status is {WorkerStateSingleton.get().status}, ignoring notification."
        )
        return

    WorkerStateSingleton.update(status="PREPARING")
    async with pool.acquire() as conn:
        await update_worker_state_async(conn)
    logger.debug(f"Received notification: {row_id}")

    try:
        try:
            task_id = await get_next_task_with_retry(
                pool, WorkerStateSingleton.get().id
            )
            logger.info(f"Successfully acquired task: {task_id}")
        except NoTaskAvailable:
            logger.info("No task available. Returning to IDLE state.")
            WorkerStateSingleton.update(status="IDLE")
            async with pool.acquire() as conn:
                await update_worker_state_async(conn)
            return
        except tenacity.RetryError:
            logger.error(
                "Failed to acquire task after 3 attempts. "
                "The task queue may be empty or the task may have been taken by another worker. "
                "Returning to IDLE state."
            )
            WorkerStateSingleton.update(status="IDLE")
            async with pool.acquire() as conn:
                await update_worker_state_async(conn)
            return
        WorkerStateSingleton.update(status="WORKING", current_task=task_id)
        async with pool.acquire() as conn:
            await update_worker_state_async(conn)

        async with pool.acquire() as conn:
            row: Optional[Record] = await conn.fetchrow(
                """
                    SELECT id, status, payload
                    FROM bountyboard
                    WHERE id = $1
                    FOR UPDATE SKIP LOCKED
                    """,
                task_id,
            )
            del row_id
            logger.info(f"Got row: {row}")
            if row is None:
                logger.error(f"Row {task_id} not found!")
                return

            payload = json.loads(row["payload"])
            task_name, args = payload["name"], payload["args"]
            logger.info(f"Got task: {task_name} with args: {args}")

            task = workraft.tasks.get(task_name)
            if task is None:
                logger.error(f"Task {task_name} not found!")
                return
            try:
                result = task(*args)
                logger.info(f"Task {task_name} returned: {result}")
                await conn.execute(
                    """
                        UPDATE bountyboard
                        SET status = 'SUCCESS', result = $1
                        WHERE id = $2
                        """,
                    json.dumps(result),
                    task_id,
                )
            except Exception as e:
                logger.error(f"Task {task_name} failed: {e}")
                await conn.execute(
                    """
                        UPDATE bountyboard
                        SET status = 'FAILURE', result = $1
                        WHERE id = $2
                        """,
                    str(e),
                    task_id,
                )
            else:
                logger.info(f"Task {task_name} done!")
    finally:
        if workraft.postrun_handler is not None:
            workraft.postrun_handler()
        WorkerStateSingleton.update(status="IDLE", current_task=None)
        async with pool.acquire() as conn:
            await update_worker_state_async(conn)
