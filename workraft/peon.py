import asyncio
import json

from asyncpg import Record
from loguru import logger

from workraft.core import WorkerStateSingleton
from workraft.db import (
    get_connection_pool,
    get_task_listener_conenction,
    update_worker_state_async,
    verify_database_setup,
)


async def run_peon(db_config, workraft):
    pool = await get_connection_pool(db_config)
    await verify_database_setup(pool)

    listener_connection = await get_task_listener_conenction(db_config)

    async with pool.acquire() as conn:
        WorkerStateSingleton.update(status="idle", current_task=None)
        await update_worker_state_async(conn)
        await listener_connection.add_listener(
            "new_task",
            lambda conn, pid, channel, payload: asyncio.create_task(
                notification_handler(pool, pid, channel, payload, workraft)
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


async def notification_handler(pool, pid, channel, row_id, workraft):
    logger.info(f"Received notification on channel {channel}: {row_id}")
    logger.info(f"{row_id=}, {pid=}")
    async with pool.acquire() as conn:
        row: Record = await conn.fetchrow(
            """
                SELECT id, status, payload
                FROM bountyboard
                WHERE id = $1
                FOR UPDATE SKIP LOCKED
                """,
            row_id,
        )
        logger.info(f"Got row: {row}")
        if row is None:
            logger.warning(f"Row {row_id} not found!")
            return

        status, payload = row["status"], json.loads(row["payload"])
        logger.info(f"Got status: {status}, payload: {payload}")

        if status != "PENDING":
            logger.warning(f"Task {row_id} is not pending!")
            return

        WorkerStateSingleton.update(status="working", current_task=row_id)
        await update_worker_state_async(conn)

        task_name, args = payload["name"], payload["args"]
        logger.info(f"Got task: {task_name} with args: {args}")

        # set status of task to "RUNNING"
        await conn.execute(
            """
                UPDATE bountyboard
                SET status = 'RUNNING'
                WHERE id = $1
                """,
            row_id,
        )

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
                row_id,
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
                row_id,
            )
        else:
            logger.info(f"Task {task_name} done!")
        finally:
            if workraft.postrun_handler is not None:
                workraft.postrun_handler()
            WorkerStateSingleton.update(status="idle", current_task=None)
            await update_worker_state_async(conn)
