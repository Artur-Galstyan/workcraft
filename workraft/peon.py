import asyncio

from loguru import logger

from workraft.db import (
    get_connection,
    verify_database_setup,
)
from workraft.models import DBConfig


async def run_peon(db_config: DBConfig):
    conn = await get_connection(db_config)
    await verify_database_setup(conn)
    await conn.add_listener("new_task", notification_handler)
    logger.info("Ready to work!")
    try:
        while True:
            await asyncio.sleep(1)  # Avoid busy-waiting
    except asyncio.CancelledError:
        logger.info("Main loop cancelled. Shutting down...")
    finally:
        await conn.close()
        logger.info("Database connection closed.")


async def notification_handler(conn, pid, channel, payload):
    logger.info(f"Received notification on channel {channel}: {payload}")
    logger.info("Processing task...")
