import time

import nox
from scripts.start_mysql_docker import start_mysql_docker, stop_mysql_docker
from workcraft.utils import run_command, TerminableThread


@nox.session
def tests(session):
    db_host = "127.0.0.1"
    db_port = 3308
    db_user = "root"
    db_name = "workcraft"
    db_password = "password"
    container_name = "workcraft-mysql-test"

    stop_mysql_docker(container_name=container_name, debug=True)
    start_mysql_docker(
        db_port=db_port,
        db_user=db_user,
        db_name=db_name,
        db_password=db_password,
        container_name=container_name,
        debug=True,
    )
    session.install("-e", ".")
    print("Waiting for MySQL to start...")
    time.sleep(10)  # Increased wait time
    import pymysql

    try:
        connection = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
        )
        print("Successfully connected to the database")
        connection.close()
    except Exception as e:
        print(f"Failed to connect to the database: {str(e)}")
        raise

    cmd = [
        "uv run python3 -m workcraft setup_database_tables --read_from_env=False ",
        f"--db_port={db_port} --db_user={db_user} "
        f"--db_name={db_name} --db_password={db_password} ",
        f"--db_host={db_host} --drop_tables=True ",
    ]
    run_command("".join(cmd), debug=True)

    time.sleep(5)

    cmd = [
        "uv run python3 -m workcraft peon --workcraft_path=tests.test_everything.workcraft ",  # noqa
        "--load_db_config_from_env=False ",
        f"--db_port={db_port} --db_user={db_user} "
        f"--db_name={db_name} --db_password={db_password} ",
        f"--db_host={db_host} ",
    ]

    # start worker
    thread = run_command(
        "".join(cmd),
        debug=True,
        background=True,
    )

    try:
        session.install("pytest")
        session.run("python3", "-m", "pytest", "-s")
    finally:
        assert isinstance(thread, TerminableThread)
        print("Stopping worker thread")
        thread.terminate()
        thread.join(timeout=5)  # Wait up to 5 seconds for the thread to finish
        if thread.is_alive():
            print("Worker thread did not stop gracefully, forcing termination")
        else:
            print("Worker thread stopped")

        stop_mysql_docker(container_name=container_name, debug=True)
