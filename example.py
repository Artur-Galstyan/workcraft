import asyncio
import json
import uuid

from workraft.db import get_connection, get_db_config
from workraft.tasks import register_task


def simple_task(a: int, b):
    return a + b


register_task("simple_task", simple_task)


async def main():
    connection = await get_connection(db_config=get_db_config())
    await connection.execute(
        """
            INSERT INTO bountyboard (id, status, priority, payload)
            VALUES ($1, 'pending', 'normal', $2)
            """,
        uuid.uuid4(),
        json.dumps({"name": "simple_task", "args": [1, 2]}),
    )


if __name__ == "__main__":
    asyncio.run(main())
