import json
import time

from beartype.typing import Any, Literal
from loguru import logger
from workcraft.core import Workcraft
from workcraft.models import DBConfig, TaskPayload, TaskStatus


workcraft = Workcraft()

counter = 0


@workcraft.setup_handler()
def setup_handler():
    global counter
    counter = 10


@workcraft.prerun_handler()
def prerun_handler(task_id: str, task_name: str):
    global counter
    logger.info("prerun_handler")
    counter += 1
    logger.info(f"{counter=}")


@workcraft.postrun_handler()
def postrun_handler(
    task_id: str,
    task_name: str,
    result: Any,
    status: Literal["FAILURE", "SUCCESS", "RUNNING", "PENDING"],
):
    global counter
    logger.info("postrun_handler")
    counter = 1000
    logger.info(f"{counter=}")


@workcraft.task("add")
def add(task_id: str, a: int, b: int) -> int:
    global counter
    return a + b + counter


def test_everything():
    global counter
    db_host = "127.0.0.1"
    db_port = 3308
    db_user = "root"
    db_name = "workcraft"
    db_password = "password"
    db_config = DBConfig(
        port=db_port, user=db_user, database=db_name, password=db_password, host=db_host
    )
    task_id = workcraft.send_task_sync(
        db_config=db_config, payload=TaskPayload(task_args=[1, 2]), task_name="add"
    )

    time.sleep(10)
    task = Workcraft.get_task_sync(db_config=db_config, task_id=task_id)
    assert task is not None, f"Task with id {task_id} is None"
    result = task.result
    assert result is not None, f"Task with id {task_id} has no result"

    assert task.status == TaskStatus.SUCCESS, f"Task id {task_id} is {task.status}"

    result = json.loads(result)
    assert result == 14, f"Result is {result}"  # it's 14 because of the counter
    # the counter is 0 at the beginning, then incremented by 10 in the setup_handler
    # then incremented by 1 in the prerun_handler, making it 11

    assert counter == 0, f"Counter is {counter}"
    # the counter is 0, because the pytest python process and the workcraft python
    # process are different, so the counter in the workcraft process is not the same
    # as the counter in the pytest process
