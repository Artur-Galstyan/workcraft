import importlib
import subprocess


def import_module_attribute(path: str):
    module_path, attr_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


def run_command(command: str, debug: bool = False) -> list[str]:
    if debug:
        print(f"DEBUG: Executing command: {command}")

    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    output = []
    for line in process.stdout:  # type: ignore
        line = line.strip()
        if debug:
            print(f"DEBUG: {line}")
        output.append(line)

    return_code = process.wait()

    if return_code != 0:
        error_message = f"Command failed with return code {return_code}: {command}"
        if debug:
            print(f"DEBUG: {error_message}")
        raise Exception(error_message)

    if debug:
        print("DEBUG: Command completed successfully")
    return output
