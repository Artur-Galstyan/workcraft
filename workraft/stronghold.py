import asyncio

from loguru import logger

from workraft.db import get_connection, setup_database
from workraft.models import DBConfig


async def run_stronghold(db_config: DBConfig):
    conn = await get_connection(db_config)
    await setup_database(conn=conn)
    logger.info("Stronghold is ready!")
    try:
        while True:
            await handle_main_tasks(conn)
            await asyncio.sleep(1)  # Avoid busy-waiting
    except asyncio.CancelledError:
        logger.info("Main loop cancelled. Shutting down...")
    finally:
        await conn.close()
        logger.info("Database connection closed.")


async def handle_main_tasks(conn):
    # Placeholder for main loop logic
    pass
