import os
import pathlib


def read_file_from_sqls(file_name: str) -> str:
    file_path = pathlib.Path(__file__).parent / "sqls" / file_name
    with open(file_path, "r") as f:
        return f.read()


def get_setup_enum_types():
    file_name = "create_enum_types.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_create_tables():
    file_name = "create_tables.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_create_indexes():
    file_name = "create_indexes.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_create_functions():
    file_name = "create_notify_new_task_function.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_create_trigger_on_bountyboard():
    file_name = "create_trigger_on_bountyboard.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_create_trigger_task_updated_to_pending():
    file_name = "create_trigger_task_updated_to_pending.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_create_get_next_task_function():
    file_name = "create_get_next_task_function.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_create_heartbeat_function():
    file_name = "create_heartbeat_function.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_refire_pending_tasks_for_all_function():
    file_name = "create_refire_pending_tasks_for_all_function.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_create_check_dead_workers_function():
    file_name = "create_check_dead_workers_function.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_create_self_correct_tasks_function():
    file_name = "create_self_correct_tasks_function.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_setup_cron_jobs():
    file_name = "create_setup_cron_jobs.sql"
    return read_file_from_sqls(file_name), file_name


def get_setup_db_create_send_refire_signal_function():
    file_name = "create_send_refire_signal_function.sql"
    return read_file_from_sqls(file_name), file_name


def get_all_sql_commands() -> list[tuple[str, str]]:
    return [
        get_setup_enum_types(),
        get_setup_db_create_tables(),
        get_setup_db_create_indexes(),
        get_setup_db_create_functions(),
        get_setup_db_create_trigger_on_bountyboard(),
        get_setup_db_create_trigger_task_updated_to_pending(),
        get_setup_db_create_get_next_task_function(),
        get_setup_db_create_heartbeat_function(),
        get_setup_db_refire_pending_tasks_for_all_function(),
        get_setup_db_create_check_dead_workers_function(),
        get_setup_db_create_self_correct_tasks_function(),
        get_setup_db_create_send_refire_signal_function(),
        get_setup_db_setup_cron_jobs(),
    ]
