from enum import Enum


NEW_TASK_CHANNEL = "new_task"
TASK_QUEUE_SEPARATOR = "§"


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
