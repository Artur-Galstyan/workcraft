import os

import asyncpg
from dotenv import load_dotenv
from loguru import logger

from workraft.models import DBConfig
from workraft.sql_commands import SETUP


def get_db_config() -> DBConfig:
    load_dotenv()

    host = os.getenv("WK_DB_HOST", None)
    port = os.getenv("WK_DB_PORT", None)
    user = os.getenv("WK_DB_USER", None)
    pswd = os.getenv("WK_DB_PASS", None)
    name = os.getenv("WK_DB_NAME", None)
    assert host, "WK_DB_HOST is not set"
    assert port, "WK_DB_PORT is not set"
    assert user, "WK_DB_USER is not set"
    assert pswd, "WK_DB_PASS is not set"
    assert name, "WK_DB_NAME is not set"
    return DBConfig(host=host, port=int(port), user=user, password=pswd, database=name)


async def get_connection(db_config: DBConfig) -> asyncpg.Connection:
    try:
        conn = await asyncpg.connect(**db_config.model_dump())
        logger.info("Connected to the stronghold!")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to the stronghold: {e}")
        raise ValueError("Failed to connect to the stronghold!")


async def listen_for_tasks(conn: asyncpg.Connection):
    try:
        logger.info("Listening for new tasks...")
    except Exception as e:
        logger.error(f"Failed to listen for tasks: {e}")
        raise ValueError("Failed to listen for tasks!")


async def send_heartbeat(conn: asyncpg.Connection, worker_id: str) -> None:
    try:
        await conn.execute(
            """
            UPDATE warband SET last_heartbeat = NOW()
            WHERE id = $1
        """,
            worker_id,
        )
        logger.debug("Drums of war beating... (Heartbeat sent)")
    except Exception as e:
        logger.error(f"Heartbeat failed: {e}")


async def setup_database(conn: asyncpg.Connection):
    try:
        await conn.execute(SETUP)
    except asyncpg.DuplicateObjectError as e:
        logger.warning(f"Some database objects already exist: {e}")
        # This is not a fatal error, so we can continue
    except Exception as e:
        logger.error(f"Failed to set up database: {e}")
        raise


async def verify_database_setup(conn: asyncpg.Connection):
    try:
        # Check if tables exist
        warband_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'warband')"
        )
        bountyboard_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'bountyboard')"
        )

        if not (warband_exists and bountyboard_exists):
            raise Exception("Required tables do not exist in the database")

        logger.info("Database setup verified successfully.")
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        raise
