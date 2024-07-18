# Workraft

## Description
Workraft is a lightweight, simple worker library in Python with only a Postgres database
as the single source of truth; no Redis, RabbitMQ, or any other external dependencies.

## Installation

Run the command

```bash
pip install workraft
```

## Usage

First, you need to setup the database. The following environment variables are required:

- WK_DB_HOST - The database host
- WK_DB_PORT - The database port
- WK_DB_USER - The database user
- WK_DB_PASS - The database password
- WK_DB_NAME - The database name

Then, you need to setup the database using the command below:

```bash
python3 -m workraft build_stronghold
```

To create a worker, you need to give it some tasks to perform. For example:

```python
import time

from workraft.core import Workraft


workraft = Workraft()


@workraft.task("simple_task")
def simple_task(a: int, b: int, c: int) -> int:
    time.sleep(1)
    #    time.sleep(random.randint(10, 20))
    raise ValueError("Random error!")
    return a + b + c

```

To run a worker, run the command below:

```bash
python3 -m workraft peon --workraft_path=example.workraft
```

To send a task to the worker, you can use the following example:

```python
async def main():
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    c = random.randint(1, 100)

    await workraft.send_task_async(
        "simple_task",
        get_db_config(),
        [a, b],
        task_kwargs={"c": c},
        retry_on_failure=True,
    )

if __name__ == "__main__":
    asyncio.run(main())
```

And that's it. Use any database viewer to see the tasks and their status.

## License

MIT
