import asyncio
import os
import time

import asyncpg
import psycopg2
from dotenv import load_dotenv
from loguru import logger

from workraft.core import WorkerState, WorkerStateSingleton
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


async def get_task_listener_conenction(db_config: DBConfig) -> asyncpg.Connection:
    try:
        conn = await asyncpg.connect(**db_config.model_dump())
        logger.info("Connected to the Stronghold!")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to the stronghold: {e}")
        raise ValueError("Failed to connect to the stronghold!")


async def get_connection_pool(db_config: DBConfig) -> asyncpg.Pool:
    try:
        pool = await asyncpg.create_pool(**db_config.model_dump())
        if pool is None:
            raise ValueError("Failed to create connection pool.")
        logger.info("Connected to the stronghold!")
        return pool
    except Exception as e:
        logger.error(f"Failed to connect to the stronghold: {e}")
        raise ValueError("Failed to connect to the stronghold!")


async def update_worker_state_async(conn):
    worker_state = WorkerStateSingleton.get()
    await conn.execute(
        """
        INSERT INTO peon (id, status, last_heartbeat, current_task)
        VALUES ($1, $2, NOW(), $3)
        ON CONFLICT (id) DO UPDATE
        SET status = $2, last_heartbeat = NOW(), current_task = $3
    """,
        worker_state.id,
        worker_state.status,
        worker_state.current_task,
    )


async def setup_database(pool: asyncpg.Pool):
    try:
        async with pool.acquire() as conn:
            await conn.execute(SETUP)
    except asyncpg.DuplicateObjectError as e:
        logger.warning(f"Some database objects already exist: {e}")
        # This is not a fatal error, so we can continue
    except Exception as e:
        logger.error(f"Failed to set up database: {e}")
        raise


async def verify_database_setup(pool: asyncpg.Pool):
    try:
        # Check if tables exist
        async with pool.acquire() as conn:
            warband_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_name = 'peon')"
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


def send_heartbeat_sync(db_config: DBConfig, worker_id: str) -> None:
    conn = None
    while True:
        try:
            conn = psycopg2.connect(**db_config.dict())
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE peon SET last_heartbeat = NOW()
                    WHERE id = %s
                """,
                    (worker_id,),
                )
                conn.commit()
            # logger.debug(
            #     f"Drums of war beating... (Heartbeat sent), worker_id: {worker_id}"
            # )
            time.sleep(5)
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
        finally:
            if conn:
                conn.close()


def update_worker_state_sync(db_config: DBConfig):
    worker_state = WorkerStateSingleton.get()
    conn = psycopg2.connect(**db_config.dict())

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO peon (id, status, last_heartbeat, current_task)
            VALUES (%s, %s, NOW(), %s)
            ON CONFLICT (id) DO UPDATE
            SET status = %s, last_heartbeat = NOW(), current_task = %s
        """,
            (
                worker_state.id,
                worker_state.status,
                worker_state.current_task,
                worker_state.status,
                worker_state.current_task,
            ),
        )
        conn.commit()
