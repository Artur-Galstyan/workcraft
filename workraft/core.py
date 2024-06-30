from beartype.typing import Callable
from loguru import logger


class Workraft:
    """Workraft: A simple distributed task system."""

    def __init__(self):
        self.tasks: dict[str, Callable] = {}

    def task(self, name: str):
        def decorator(func: Callable):
            self.tasks[name] = func
            logger.info(f"Registered task: {name}")
            logger.debug(f"Function arguments: {func.__code__.co_varnames}")
            logger.debug(f"Function name: {func.__name__}")
            logger.debug(f"Function arg types: {func.__annotations__}")
            return func

        return decorator
