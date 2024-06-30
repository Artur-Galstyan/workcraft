import asyncio
import json
import uuid

from workraft.core import Workraft
from workraft.db import get_connection, get_db_config


workraft = Workraft()


@workraft.task("simple_task")
def simple_task(a: int, b: int) -> int:
    return a + b


async def main():
    connection = await get_connection(db_config=get_db_config())
    await connection.execute(
        """
            INSERT INTO bountyboard (id, status, payload)
            VALUES ($1, 'pending', $2)
            """,
        uuid.uuid4(),
        json.dumps({"name": "simple_task", "args": [1, 2]}),
    )


if __name__ == "__main__":
    asyncio.run(main())
