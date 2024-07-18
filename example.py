import asyncio
import json
import random
import time
import uuid
from multiprocessing import Pool

from loguru import logger
from workraft.core import Workraft
from workraft.db import get_connection_pool, get_db_config


workraft = Workraft()


@workraft.task("simple_task")
def simple_task(a: int, b: int, c: int) -> int:
    time.sleep(1)
    #    time.sleep(random.randint(10, 20))
    raise ValueError("Random error!")
    return a + b + c


@workraft.postrun_handler()
def postrun_handler(result, status):
    logger.info(f"Postrun handler called! Got result: {result} and status {status}")


def get_random_number():
    logger.info("Getting random number...")
    time.sleep(random.randint(5, 10))
    return random.randint(1, 100)


@workraft.task("complex_task_1")
def parallel_task():
    num_processes = 8
    n_random_numbers = 20
    with Pool(processes=num_processes) as pool:
        all_numbers = pool.starmap(
            get_random_number,
            [() for _ in range(n_random_numbers)],
        )


async def main():
    n_tasks = 1

    for _ in range(n_tasks):
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        c = random.randint(1, 100)

        await workraft.send_task_async(
            "simple_task",
            get_db_config(),
            [a, b],
            task_kwargs={"c": c},
            retry_on_failure=True,
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
