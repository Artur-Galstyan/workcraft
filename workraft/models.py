from pydantic import BaseModel


class DBConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
