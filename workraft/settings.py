from pydantic import BaseModel


class Settings(BaseModel):
    """
    Settings for Workraft. The default values are:

        db_polling_interval: 5 seconds
        db_refire_interval: 10 seconds

    """

    db_polling_interval: int = 5
    db_refire_interval: int = 10


settings = Settings()
