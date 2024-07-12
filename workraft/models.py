from beartype.typing import Literal, Optional
from pydantic import BaseModel


class DBConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str


class WorkerState(BaseModel):
    id: str
    status: Literal["IDLE", "PREPARING" "WORKING", "OFFLINE"]
    current_task: Optional[str] = None
    queues: list[str] = ["DEFAULT"]


class TaskPayload(BaseModel):
    name: str
    task_args: list = []
    task_kwargs: dict = {}
    prerun_handler_args: list = []
    prerun_handler_kwargs: dict = {}
    postrun_handler_args: list = []
    postrun_handler_kwargs: dict = {}
