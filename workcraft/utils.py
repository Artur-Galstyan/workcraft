import importlib
import os
import signal
import subprocess
import threading


def import_module_attribute(path: str):
    module_path, attr_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


class TerminableThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process: subprocess.Popen | None = None

    def run(self):
        self._target(*self._args, **self._kwargs)  # type: ignore

    def terminate(self):
        if self.process:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)


def run_command(
    command: str, debug: bool = False, background: bool = False
) -> list[str] | TerminableThread:
    def command_thread() -> list[str]:
        if debug:
            print(f"DEBUG: Executing command: {command}")
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            preexec_fn=os.setsid,
        )
        if isinstance(threading.current_thread(), TerminableThread):
            threading.current_thread().process = process  # type: ignore

        output = []
        for line in process.stdout:  # type: ignore
            line = line.strip()
            if debug:
                print(f"DEBUG: {line}")
            output.append(line)
        return_code = process.wait()
        if return_code != 0 and return_code != -signal.SIGTERM:
            error_message = f"Command failed with return code {return_code}: {command}"
            if debug:
                print(f"DEBUG: {error_message}")
            raise Exception(error_message)
        if debug:
            print("DEBUG: Command completed successfully")
        return output

    if background:
        thread = TerminableThread(target=command_thread)
        thread.start()
        return thread
    else:
        return command_thread()
