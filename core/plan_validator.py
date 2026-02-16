import json
from pathlib import Path
from datetime import datetime


EXECUTION_RISK_THRESHOLD = 5
MAX_TIMEOUT_SECONDS = 30

FORBIDDEN_PATTERNS = [
    "rm ",
    "rm-",
    "sudo",
    "reboot",
    "shutdown",
    "dd ",
    "|",
    "&&",
    "||",
    ";",
    ">",
    "<"
]


class PlanValidationError(Exception):
    pass


def load_plan(path: str) -> dict:
    plan_path = Path(path)

    if not plan_path.exists():
        raise PlanValidationError(f"Plan file not found: {path}")

    with open(plan_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            raise PlanValidationError(f"Invalid JSON format: {e}")


def validate_plan_structure(plan: dict) -> None:
    required_fields = [
        "schema_version",
        "id",
        "created_at",
        "risk_score",
        "source",
        "commands",
    ]

    for field in required_fields:
        if field not in plan:
            raise PlanValidationError(f"Missing required field: {field}")

    if plan["schema_version"] != "0.1":
        raise PlanValidationError("Unsupported schema_version")

    if not isinstance(plan["risk_score"], int):
        raise PlanValidationError("risk_score must be integer")

    if plan["risk_score"] > EXECUTION_RISK_THRESHOLD:
        raise PlanValidationError("risk_score exceeds execution threshold")

    try:
        datetime.fromisoformat(plan["created_at"].replace("Z", "+00:00"))
    except Exception:
        raise PlanValidationError("created_at must be valid ISO 8601 timestamp")

    if not isinstance(plan["commands"], list) or len(plan["commands"]) == 0:
        raise PlanValidationError("commands must be non-empty list")

    for command in plan["commands"]:
        validate_command(command)


def validate_command(command: dict) -> None:
    if "type" not in command or "command" not in command or "timeout_seconds" not in command:
        raise PlanValidationError("Command object missing required fields")

    if command["type"] not in ["shell", "python"]:
        raise PlanValidationError("Unsupported command type")

    if not isinstance(command["timeout_seconds"], int):
        raise PlanValidationError("timeout_seconds must be integer")

    if command["timeout_seconds"] > MAX_TIMEOUT_SECONDS:
        raise PlanValidationError("timeout_seconds exceeds maximum allowed")

    raw_command = command["command"]

    for pattern in FORBIDDEN_PATTERNS:
        if pattern in raw_command:
            raise PlanValidationError(f"Forbidden pattern detected in command: {pattern}")


def validate_plan(path: str) -> dict:
    plan = load_plan(path)
    validate_plan_structure(plan)
    return plan




