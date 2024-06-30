# workraft/peon.py
import asyncio
import json

from asyncpg import Record
from loguru import logger

from workraft.db import get_connection, verify_database_setup


async def run_peon(db_config, workraft):
    conn = await get_connection(db_config)
    await verify_database_setup(conn)
    await conn.add_listener(
        "new_task",
        lambda conn, pid, channel, payload: asyncio.create_task(
            notification_handler(conn, pid, channel, payload, workraft)
        ),
    )

    logger.info(f"Got {len(workraft.tasks)} tasks to do!")
    logger.info("Ready to work!")

    try:
        while True:
            await asyncio.sleep(1)  # Avoid busy-waiting
    except asyncio.CancelledError:
        logger.info("Main loop cancelled. Shutting down...")
    finally:
        await conn.close()
        logger.info("Database connection closed.")


async def notification_handler(conn, pid, channel, row_id, workraft):
    logger.info(f"Received notification on channel {channel}: {row_id}")
    logger.info(f"{row_id=}, {pid=}")
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

    if status != "pending":
        logger.warning(f"Task {row_id} is not pending!")
        return

    task_name, args = payload["name"], payload["args"]
    logger.info(f"Got task: {task_name} with args: {args}")

    task = workraft.tasks.get(task_name)
    if task is None:
        logger.warning(f"Task {task_name} not found!")
        return

    try:
        result = task(*args)
        logger.info(f"Task {task_name} returned: {result}")
        await conn.execute(
            """
                UPDATE bountyboard
                SET status = 'done', result = $1
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
                SET status = 'failed', result = $1
                WHERE id = $2
                """,
            str(e),
            row_id,
        )
    else:
        logger.info(f"Task {task_name} done!")
