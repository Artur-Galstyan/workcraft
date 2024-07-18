from pydantic import BaseModel


class Settings(BaseModel):
    db_polling_interval: int = 5
    db_refire_interval: int = 10


settings = Settings()
