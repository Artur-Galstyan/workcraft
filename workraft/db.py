import os
import time

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, Engine, text

from workraft.models import DBConfig, WorkerState
from workraft.settings import settings


class DBEngineSingleton:
    _engine: Engine | None = None

    @staticmethod
    def get(db_config: DBConfig) -> Engine:
        if DBEngineSingleton._engine is None:
            _engine = create_engine(DBConfig.get_uri(db_config))
            DBEngineSingleton._engine = _engine
        assert (
            DBEngineSingleton._engine is not None
        ), "DBEngineSingleton._engine is None"
        return DBEngineSingleton._engine


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


def update_worker_state_sync(db_config: DBConfig, worker_state: WorkerState):
    with DBEngineSingleton.get(db_config).connect() as conn:
        statement = text("""
            INSERT INTO peon (id, status, last_heartbeat, current_task, queues)
            VALUES (:id, :status, NOW(), :current_task, :queues)
            ON DUPLICATE KEY UPDATE
            status = :status,
            last_heartbeat = NOW(),
            current_task = :current_task,
            queues = :queues
        """)

        conn.execute(
            statement,
            {
                "id": worker_state.id,
                "status": worker_state.status,
                "current_task": worker_state.current_task,
                "queues": ",".join(worker_state.queues),
            },
        )
        conn.commit()


def send_heartbeat_sync(db_config: DBConfig, worker_id: str) -> None:
    conn = None
    while True:
        try:
            with DBEngineSingleton.get(db_config).connect() as conn:
                update_query = [
                    "UPDATE peon",
                    "SET last_heartbeat = NOW()",
                    f'WHERE id = "{worker_id}"',
                ]
                conn.execute(text(" ".join(update_query)))
                conn.commit()
                time.sleep(settings.DB_PEON_HEARTBEAT_INTERVAL)
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
        finally:
            if conn:
                conn.close()


def verify_database_setup(db_config: DBConfig):
    # TODO: check if the database is setup correctly
    pass
