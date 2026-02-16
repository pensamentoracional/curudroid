import subprocess
from datetime import datetime


class CommandExecutionError(Exception):
    pass


def run_command(command: str, timeout_seconds: int) -> dict:
    """
    Executa um comando de forma controlada.
    Retorna resultado estruturado.
    """

    start_time = datetime.utcnow().isoformat() + "Z"

    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False
        )

        end_time = datetime.utcnow().isoformat() + "Z"

        return {
            "command": command,
            "started_at": start_time,
            "finished_at": end_time,
            "return_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "timeout": False
        }

    except subprocess.TimeoutExpired as e:
        return {
            "command": command,
            "started_at": start_time,
            "finished_at": datetime.utcnow().isoformat() + "Z",
            "return_code": None,
            "stdout": "",
            "stderr": "Execution timed out",
            "timeout": True
        }

    except Exception as e:
        raise CommandExecutionError(str(e))
