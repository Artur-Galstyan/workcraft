import asyncio
import random
import time

from loguru import logger
from workcraft.core import Workcraft
from workcraft.db import get_db_config
from workcraft.models import TaskPayload


workcraft = Workcraft()

global_counter = 0


@workcraft.setup_handler()
def setup_handler():
    global global_counter
    global_counter = 1000
    logger.info("Setting up the worker!")


@workcraft.task("simple_task")
def simple_task(task_id: str, a: int, b: int, c: int) -> int:
    print(task_id)
    global global_counter
    global_counter += 1
    time.sleep(1)
    logger.info(global_counter)
    # raise ValueError("Random error!")
    return a + b + c


@workcraft.postrun_handler()
def postrun_handler(task_id, task_name, result, status):
    logger.info(
        f"PR called for {task_id} and {task_name}! Got {result} and status {status}"
    )


async def main():
    n_tasks = 1
    for _ in range(n_tasks):
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        c = random.randint(1, 100)

        workcraft.send_task_sync(
            db_config=get_db_config(),
            payload=TaskPayload(
                name="simple_task",
                task_args=[a, b, c],
            ),
        )

    # await asyncio.sleep(5)
    # task_id = "7e1c5c4c-7d8c-4800-9c77-456a4e5fbe39"
    # logger.info(f"getting task for id {task_id}")
    # task = workcraft.get_task_sync(get_db_config(), task_id)
    # assert task is not None
    # assert task.result is not None
    # res = json.loads(task.result)
    # print(res, type(res))
    # _, docs = res
    # print(docs, type(docs))


if __name__ == "__main__":
    asyncio.run(main())
