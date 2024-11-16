import json
from datetime import datetime
from enum import Enum

from beartype.typing import Any, Literal, Protocol
from pydantic import BaseModel, Field


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    INVALID = "INVALID"


class DBConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    use_ssl: bool = False
    ssl_path: str | None = None

    @staticmethod
    def get_uri(db_config: "DBConfig") -> str:
        conn_string = f"mysql+pymysql://{db_config.user}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}"
        if db_config.use_ssl:
            conn_string += "?ssl=true"
            if db_config.ssl_path:
                conn_string += f"&ssl_ca={db_config.ssl_path}"
            else:
                raise ValueError("ssl_path is required when use_ssl is True")

        return conn_string


class TaskPayload(BaseModel):
    task_args: list = Field(default_factory=list)
    task_kwargs: dict = Field(default_factory=dict)
    prerun_handler_args: list = Field(default_factory=list)
    prerun_handler_kwargs: dict = Field(default_factory=dict)
    postrun_handler_args: list = Field(default_factory=list)
    postrun_handler_kwargs: dict = Field(default_factory=dict)


class Task(BaseModel):
    id: str
    task_name: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    worker_id: str | None
    queue: str
    payload: TaskPayload
    result: Any | None
    retry_on_failure: bool
    retry_count: int
    retry_limit: int

    @classmethod
    def from_db_data(cls, data: dict):
        # Parse the payload JSON string
        if isinstance(data["payload"], str):
            data["payload"] = json.loads(data["payload"])

        # Convert retry_on_failure to bool if it's an int
        if isinstance(data["retry_on_failure"], int):
            data["retry_on_failure"] = bool(data["retry_on_failure"])

        # Convert datetime strings to datetime objects if necessary
        for field in ["created_at", "updated_at"]:
            if isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])

        return cls(**data)


class SetupHandlerFn(Protocol):
    def __call__(self): ...


class TaskHandlerFn(Protocol):
    def __call__(
        self,
        task_id: str,
        *args,
        **kwargs,
    ) -> Any: ...


class PostRunHandlerFn(Protocol):
    def __call__(
        self,
        task_id: str,
        task_name: str,
        result: Any,
        status: Literal["FAILURE", "SUCCESS", "RUNNING", "PENDING"],
        *args,
        **kwargs,
    ): ...


class PreRunHandlerFn(Protocol):
    def __call__(
        self,
        task_id: str,
        task_name: str,
        *args,
        **kwargs,
    ): ...


class WorkerState(BaseModel):
    id: str
    status: Literal["IDLE", "PREPARING", "WORKING", "OFFLINE"]
    current_task: str | None = None
    queues: str
