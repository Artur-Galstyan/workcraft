import asyncio
import json
import random
import time
import uuid

from workraft.core import Workraft
from workraft.db import get_connection_pool, get_db_config


workraft = Workraft()


@workraft.task("simple_task")
def simple_task(a: int, b: int) -> int:
    time.sleep(random.randint(3, 5))
    return a + b


async def main():
    pool = await get_connection_pool(db_config=get_db_config())
    async with pool.acquire() as conn:
        await conn.execute(
            """
                INSERT INTO bountyboard (id, status, payload)
                VALUES ($1, 'PENDING', $2)
                """,
            uuid.uuid4(),
            json.dumps({"name": "simple_task", "args": [1, 2]}),
        )


if __name__ == "__main__":
    asyncio.run(main())
