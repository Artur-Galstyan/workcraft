import asyncio
import random
import time
from multiprocessing import Pool

from loguru import logger
from workraft.core import Workraft
from workraft.db import get_db_config
from workraft.models import TaskPayload


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
            db_config=get_db_config(),
            payload=TaskPayload(
                name="simple_task",
                task_args=[a, b, c],
            ),
        )

        # await conn.execute(
        #     """
        #         INSERT INTO bountyboard (id, status, payload)
        #         VALUES ($1, 'PENDING', $2)
        #         """,
        #     uuid.uuid4(),
        #     json.dumps({"name": "complex_task_1", "args": []}),
        # )


if __name__ == "__main__":
    asyncio.run(main())
