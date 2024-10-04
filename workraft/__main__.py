import asyncio
import functools
import pathlib
import signal
import sys
import threading
import uuid

import fire
from loguru import logger
from sqlalchemy import text

from workraft.core import WorkerStateSingleton, Workraft
from workraft.db import (
    DBConfig,
    DBEngineSingleton,
    get_db_config,
    send_heartbeat_sync,
    update_worker_state_sync,
)
from workraft.peon import run_peon
from workraft.settings import settings
from workraft.utils import import_module_attribute


def signal_handler(signum, frame, db_config):
    global shutdown_flag
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    WorkerStateSingleton.update(status="OFFLINE")
    logger.info(f"Latest worker state: {WorkerStateSingleton.get()}")
    update_worker_state_sync(db_config, WorkerStateSingleton.get())
    sys.exit(0)


class CLI:
    @staticmethod
    async def peon(
        workraft_path: str,
        worker_id: str | None = None,
        queues: list[str] = ["DEFAULT"],
        load_db_config_from_env: bool = True,
        db_host: str = "localhost",
        db_port: int = 3306,
        db_user: str = "root",
        db_password: str | None = None,
        db_name: str = "workraft",
    ):
        global shutdown_flag

        if load_db_config_from_env:
            logger.info("Reading DB config from environment variables")
            db_config = get_db_config()
        else:
            assert (
                db_password
            ), "db_password is required if load_db_config_from_env is False"
            db_config = DBConfig(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
            )
        signal_handler_partial = functools.partial(signal_handler, db_config=db_config)
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler_partial)

        logger.info(f"Getting Workraft object at {workraft_path}")
        workraft_instance: Workraft = import_module_attribute(workraft_path)

        if workraft_instance.setup_handler_fn is not None:
            workraft_instance.setup_handler_fn()

        worker_id = worker_id if worker_id is not None else str(uuid.uuid4())

        WorkerStateSingleton.update(id=worker_id, queues=queues)
        update_worker_state_sync(db_config, WorkerStateSingleton.get())
        logger.info(f"Worker State: {WorkerStateSingleton.get()}")

        heartbeat_task = threading.Thread(
            target=send_heartbeat_sync,
            args=(db_config, WorkerStateSingleton.get().id),
            daemon=True,
        )
        heartbeat_task.start()
        run_peon_task = asyncio.create_task(run_peon(db_config, workraft_instance))
        await asyncio.gather(run_peon_task, return_exceptions=True)

    @staticmethod
    def setup_database_tables(
        db_host: str = "127.0.0.1",
        db_port: int = 3306,
        db_user: str = "root",
        db_name: str = "workraft",
        db_password: str | None = None,
        read_from_env: bool = True,
        drop_tables: bool = False,
    ):
        """
        Sets up the database tables required for Workraft to function properly.
        If `read_from_env` is True, it will read the database configuration from the
        environment variables.
        Otherwise, you can provide the database configuration using the
        `db_host`, `db_port`, `db_user`, `db_name`, and `db_password` arguments.

        If `drop_tables` is True, it will drop the existing tables
        before creating new ones.

        Parameters
        ----------
        db_host : str, optional
            The hostname of the database server, by default "
        db_port : int, optional
            The port number of the database server, by default 3306
        db_user : str, optional
            The username to connect to the database, by default "root"
        db_name : str, optional
            The name of the database, by default "workraft"
        db_password : str, optional
            The password to connect to the database, by default None, meaning you
            have to provide the password
        read_from_env : bool, optional
            Whether to read the database configuration from the environment variables,
            by default True
        drop_tables : bool, optional
            Whether to drop the existing tables before creating new ones,
            by default False
        """

        if read_from_env:
            db_config = get_db_config()
        else:
            assert db_password is not None, "Please provide a password for the database"
            db_config = DBConfig(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
            )
        sqls_dir = pathlib.Path(__file__).parent / "sqls"
        sql_files = sorted(sqls_dir.glob("*.sql"))
        with DBEngineSingleton.get(db_config).connect() as conn:
            conn.execute(text("SET GLOBAL log_bin_trust_function_creators = 1;"))
            conn.execute(text("SET GLOBAL event_scheduler = ON;"))

            if drop_tables:
                drops = [
                    ("PROCEDURE", "self_correct_tasks"),
                    ("PROCEDURE", "reopen_failed_tasks"),
                    ("PROCEDURE", "check_dead_workers"),
                    ("EVENT", "run_reopen_failed_tasks"),
                    ("EVENT", "run_self_correct_tasks"),
                    ("EVENT", "run_check_dead_workers"),
                    ("TABLE", "logs"),
                    ("TABLE", "bountyboard"),
                    ("TABLE", "peon"),
                ]

                for type, name in drops:
                    conn.execute(text(f"DROP {type} IF EXISTS {name};"))

            conn.commit()

            for sql_file in sql_files:
                logger.info(f"Running {sql_file}")
                with open(sql_file) as f:
                    sql = f.read()
                    sql = sql.format_map(settings.model_dump())
                    conn.execute(text(sql))
                    conn.commit()


if __name__ == "__main__":
    fire.Fire(CLI)
