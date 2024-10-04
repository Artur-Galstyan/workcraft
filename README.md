# Workraft

## A simple, lightweight, database-only, worker library in Python

Workraft is a simple, lightweight, database-only worker library in Python with a MySQL database as the single source of truth.

Workraft adresses some of the pain points of using Celery, namely its incapability to handle long-running tasks and the fact that you need a message broker and that also that sometimes the workers aren't doing the tasks as you would expect them to.

All Workraft needs is a running MySQL database, which means you could in theory scale Workraft both vertically (get more database resources) and horizontally (get more databases). But so far, I've not tried scaling it that way.

Workraft is **not** the best in sitations where you need extreme precision and sub-second latency/wait times before a task is fetched and processed.

But if it's OK for you that your workers take at least 1 second to fetch your task AND you want a clear overview of your tasks and workers (using a database GUI for example), then Workraft is ideal for you.


## Installation

Run

```
pip install workraft
```

## Getting started

First, you need a running MySQL database. Then, for one time, you need to setup all the tables and events. For that, first you need to create a `.env` file and add some variables in there:

```
WK_DB_HOST="127.0.0.1"
WK_DB_PORT=3306
WK_DB_USER="root"
WK_DB_PASS="workraft"
WK_DB_NAME="workraft"
```

(Adjust to your settings of course)

Then, run:

```
python3 -m workraft setup_database_tables
```

This command will take the connection parameters from your `.env` file - but it's not strictly required. You can also pass it those as parameters. Here are the args of the `setup_database_tables` function:

```python
def setup_database_tables(
    db_host: str = "127.0.0.1",
    db_port: int = 3306,
    db_user: str = "root",
    db_name: str = "workraft",
    db_password: str | None = None,
    read_from_env: bool = True,
    drop_tables: bool = False,
):
...
```

E.g.:
```
python3 -m workraft setup_database_tables --read_from_env=False --db_password=test --drop_tables=True
```

Then, to use workers, implement your worker code:

```python

import asyncio
import random
import time
from multiprocessing import Pool

from loguru import logger
from workraft.core import Workraft
from workraft.db import get_db_config


workraft = Workraft()

global_counter = 0


@workraft.setup_handler()
def setup_handler():
    global global_counter
    global_counter = 1000
    logger.info("Setting up the worker!")


@workraft.task("simple_task")
def simple_task(a: int, b: int, c: int) -> int:
    global global_counter
    global_counter += 1
    time.sleep(1)
    logger.info(global_counter)
    # raise ValueError("Random error!")
    return a + b + c


@workraft.postrun_handler()
def postrun_handler(task_id, task_name, result, status):
    logger.info(
        f"Postrun handler called for {task_id} and {task_name}! Got result: {result} and status {status}"
    )


def get_random_number():
    logger.info("Getting random number...")
    time.sleep(random.randint(5, 10))
    return random.randint(1, 100)


@workraft.task("complex_task_1")
def parallel_task():
    num_processes = 8
    n_random_numbers = 20
    with Pool(processes=num_processes) as pool:
        pool.starmap(
            get_random_number,
            [() for _ in range(n_random_numbers)],
        )


async def main():
    n_tasks = 1

    for _ in range(n_tasks):
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        c = random.randint(1, 100)

        workraft.send_task_sync(
            "simple_task",
            [a, b],
            task_kwargs={"c": c},
            retry_on_failure=True,
            db_config=get_db_config(),
        )
        # But you could also just directly input the data into the database


if __name__ == "__main__":
    asyncio.run(main())

```

To run a worker then, you would run:

```
python3 -m workraft peon --workraft_path=example.workraft --worker-id=test1
```

If you then execute `example.py`, you will add a task into the queue and then see as the worker processes that task.

## Configuration

If you have a `workraft.config.json` file, those settings will be used when setting up the tables as well as other, worker-related settings:

```json

{
  "DB_PEON_HEARTBEAT_INTERVAL": 5,
  "DB_POLLING_INTERVAL": 5,
  "DB_SETUP_BACKOFF_MULTIPLIER_SECONDS": 30,
  "DB_SETUP_BACKOFF_MAX_SECONDS": 3600,
  "DB_SETUP_RUN_SELF_CORRECT_TASK_INTERVAL": 10,
  "DB_SETUP_RUN_REOPEN_FAILED_TASK_INTERVAL": 10,
  "DB_SETUP_WAIT_TIME_BEFORE_WORKER_DECLARED_DEAD": 60,
  "DB_SETUP_CHECK_DEAD_WORKER_INTERVAL": 10
}
```


DB_PEON_HEARTBEAT_INTERVAL: This is the interval at which the peon sends a heartbeat to the database.
DB_POLLING_INTERVAL: This is the interval at which the peon polls the database for new tasks.
DB_SETUP_BACKOFF_MULTIPLIER_SECONDS: This is the multiplier for the exponential backoff algorithm.
DB_SETUP_BACKOFF_MAX_SECONDS: This is the maximum backoff time for the exponential backoff algorithm.
DB_SETUP_RUN_SELF_CORRECT_TASK_INTERVAL: This is the interval at which the database runs the self-correct task.
DB_SETUP_RUN_REOPEN_FAILED_TASK_INTERVAL: This is the interval at which the database reopens failed tasks.
DB_SETUP_WAIT_TIME_BEFORE_WORKER_DECLARED_DEAD: This is the time the database waits before declaring a worker dead.
DB_SETUP_CHECK_DEAD_WORKER_INTERVAL: This is the interval at which the database checks for dead workers.

The configs with `DB_SETUP_` in the beginning are only used during the setup of the database. In other words, they are only used once. The first two are using during runtime.
