from beartype.typing import Callable


workraft_tasks: list[dict[str, Callable]] = []


def register_task(name: str, function: Callable):
    workraft_tasks.append({name: function})
    print(
        "Function arguments are: ",
        function.__code__.co_varnames,
        "Function name is: ",
        function.__name__,
        " and the function args types are: ",
        function.__annotations__,
    )
