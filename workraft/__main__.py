import asyncio
import importlib

import fire
from loguru import logger

from workraft import peon
from workraft.db import get_connection, get_db_config, setup_database


db_config = get_db_config()


def import_workraft(path: str):
    module_path, attr_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


class CLI:
    @staticmethod
    def peon(workraft_path: str):
        logger.info(f"Getting Workraft object at {workraft_path}")
        workraft_instance = import_workraft(workraft_path)

        asyncio.run(peon.run_peon(db_config, workraft_instance))

    @staticmethod
    async def stronghold():
        conn = await get_connection(db_config)
        await setup_database(conn=conn)
        logger.info("Stronghold is ready!")


if __name__ == "__main__":
    fire.Fire(CLI)
