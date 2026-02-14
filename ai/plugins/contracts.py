"""Contrato mínimo de plugins do Curudroid."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class PluginCommand:
    argv: list[str]
    description: str


@dataclass(frozen=True)
class PluginRunResult:
    success: bool
    commands: list[PluginCommand]
    risk_estimate: float
    assumptions: list[str]


def is_valid_run_result(payload: Any) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "run() deve retornar dict"

    required_keys = {"success", "commands", "risk_estimate", "assumptions"}
    missing = required_keys - set(payload.keys())
    if missing:
        return False, f"run() sem chaves obrigatórias: {', '.join(sorted(missing))}"

    if not isinstance(payload["success"], bool):
        return False, "run().success deve ser bool"

    commands = payload["commands"]
    if not isinstance(commands, list):
        return False, "run().commands deve ser list[dict]"
    for item in commands:
        if not isinstance(item, dict):
            return False, "cada comando deve ser dict"
        if set(item.keys()) != {"argv", "description"}:
            return False, "cada comando deve conter somente argv e description"
        argv = item.get("argv")
        description = item.get("description")
        if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
            return False, "comando.argv deve ser list[str]"
        if not isinstance(description, str):
            return False, "comando.description deve ser str"

    risk_estimate = payload["risk_estimate"]
    if not isinstance(risk_estimate, (int, float)):
        return False, "run().risk_estimate deve ser float"

    assumptions = payload["assumptions"]
    if not isinstance(assumptions, list) or not all(isinstance(a, str) for a in assumptions):
        return False, "run().assumptions deve ser list[str]"

    return True, "ok"


@runtime_checkable
class PluginContract(Protocol):
    plugin_id: str
    version: str
    required_env_vars: list[str]

    def run(self, intent: dict) -> dict:
        ...
