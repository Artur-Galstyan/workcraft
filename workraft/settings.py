import json
import pathlib

from loguru import logger
from pydantic import BaseModel


class Settings(BaseModel):
    """
    Settings for Workraft. The default values are:
        DB_PEON_HEARTBEAT_INTERVAL: 5
            This is the interval at which the peon sends a heartbeat to the database.

        DB_POLLING_INTERVAL: 5
            This is the interval at which the peon polls the database for new tasks.

        DB_SETUP_BACKOFF_MULTIPLIER_SECONDS: 60
            This is the multiplier for the exponential backoff algorithm.

        DB_SETUP_BACKOFF_MAX_SECONDS: 3600
            This is the maximum backoff time for the exponential backoff algorithm.

        DB_SETUP_RUN_SELF_CORRECT_TASK_INTERVAL: 10
            This is the interval at which the database runs the self-correct task.

        DB_SETUP_RUN_REOPEN_FAILED_TASK_INTERVAL: 10
            This is the interval at which the database reopens failed tasks.

        DB_SETUP_WAIT_TIME_BEFORE_WORKER_DECLARED_DEAD: 60
            This is the time the database waits before declaring a worker dead.

        DB_SETUP_CHECK_DEAD_WORKER_INTERVAL: 10
            This is the interval at which the database checks for dead workers.

    These values are read from the workraft.config.json file.
    """

    DB_PEON_HEARTBEAT_INTERVAL: int
    DB_POLLING_INTERVAL: int
    DB_SETUP_BACKOFF_MULTIPLIER_SECONDS: int
    DB_SETUP_BACKOFF_MAX_SECONDS: int
    DB_SETUP_RUN_SELF_CORRECT_TASK_INTERVAL: int
    DB_SETUP_RUN_REOPEN_FAILED_TASK_INTERVAL: int
    DB_SETUP_WAIT_TIME_BEFORE_WORKER_DECLARED_DEAD: int
    DB_SETUP_CHECK_DEAD_WORKER_INTERVAL: int


def load_settings() -> Settings:
    # Start with the current working directory
    current_dir = pathlib.Path.cwd()

    # Look for the config file in the current directory and its parents
    while current_dir != current_dir.parent:
        config_file = current_dir / "workraft.config.json"
        if config_file.exists():
            with open(config_file) as f:
                return Settings(**json.load(f))
        current_dir = current_dir.parent

    raise FileNotFoundError("Could not find workraft.config.json")


settings = load_settings()
if settings is None:
    logger.error("Could not load settings. Couldn't find workraft.config.json")
    exit(1)
