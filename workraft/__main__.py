import asyncio
import functools
import importlib
import os
import signal
import sys
import threading
import uuid

import fire
from beartype.typing import Optional
from loguru import logger

from workraft import peon
from workraft.core import WorkerStateSingleton
from workraft.db import (
    get_connection_pool,
    get_db_config,
    send_heartbeat_sync,
    setup_database,
    update_worker_state_sync,
)


db_config = get_db_config()


def signal_handler(signum, frame):
    global shutdown_flag, db_config
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    WorkerStateSingleton.update(status="offline")
    update_worker_state_sync(db_config)
    sys.exit(0)


def heartbeat_wrapper(db_config, worker_id):
    while True:
        send_heartbeat_sync(db_config, worker_id)


def import_workraft(path: str):
    module_path, attr_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


class CLI:
    @staticmethod
    async def peon(workraft_path: str, worker_id: Optional[str] = None):
        global db_config, shutdown_flag
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler)

        logger.info(f"Getting Workraft object at {workraft_path}")
        workraft_instance = import_workraft(workraft_path)
        worker_id = worker_id if worker_id is not None else str(uuid.uuid4())

        WorkerStateSingleton.update(id=worker_id)
        logger.info(f"Worker State: {WorkerStateSingleton.get()}")
        peon_task = asyncio.create_task(peon.run_peon(db_config, workraft_instance))
        heartbeat_task = threading.Thread(
            target=heartbeat_wrapper,
            args=(db_config, WorkerStateSingleton.get().id),
            daemon=True,
        )
        heartbeat_task.start()

        await peon_task

    @staticmethod
    async def stronghold():
        pool = await get_connection_pool(db_config)
        await setup_database(pool)
        logger.info("Stronghold is ready!")


if __name__ == "__main__":
    fire.Fire(CLI)
