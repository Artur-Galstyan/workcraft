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
def simple_task(a: int, b: int) -> int:
    time.sleep(random.randint(10, 20))
    return a + b


@workraft.postrun_handler()
def postrun_handler():
    logger.info("Postrun handler called!")


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
    pool = await get_connection_pool(db_config=get_db_config())
    async with pool.acquire() as conn:
        await conn.execute(
            """
                INSERT INTO bountyboard (id, status, payload)
                VALUES ($1, 'PENDING', $2)
                """,
            uuid.uuid4(),
            json.dumps({"name": "simple_task", "args": [1, 2]}),
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
