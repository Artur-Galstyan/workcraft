import fire
from workraft.utils import run_command


def start_mysql_docker(
    db_port: int = 3306,
    db_user: str = "root",
    db_name: str = "workraft",
    db_password: str | None = None,
    container_name: str = "workraft-mysql",
    debug: bool = False,
    start_if_exists: bool = False,
):
    assert db_password is not None, "Please provide a password for the database"

    # check if the container is already running
    if start_if_exists:
        try:
            run_command(f"docker stop {container_name}", debug=debug)
        except Exception as e:
            print("Failed to stop the container, probably it is not running")
            print("Error", e)

        try:
            run_command(f"docker rm {container_name}", debug=debug)
        except Exception as e:
            print("Failed to remove the container, probably it does not exist")
            print("Error", e)

    docker_command = [
        "docker",
        "run",
        "--name",
        container_name,
        "-e",
        f"MYSQL_ROOT_PASSWORD={db_password}",
        "-e",
        f"MYSQL_DATABASE={db_name}",
        "-p",
        f"{db_port}:3306",
        "-d",
        "mysql:latest",
    ]

    run_command(" ".join(docker_command), debug=debug)


if __name__ == "__main__":
    fire.Fire(start_mysql_docker)
