"""Allowlist de comandos para execução assistida."""

from __future__ import annotations

ALLOWED_COMMANDS = {"tail", "grep", "cat", "ps"}
BLOCKED_COMMANDS = {
    "rm",
    "mv",
    "dd",
    "chmod",
    "chown",
    "curl",
    "wget",
    "bash",
    "sh",
    "python",
    "python3",
}

_SHELL_METACHARS = set("|&;<>$`\\!{}()*?[]~")


def validate_argv(argv: list[str]) -> tuple[bool, str]:
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        return False, "argv inválido (esperado list[str] não-vazio)"

    command = argv[0]
    if command in BLOCKED_COMMANDS:
        return False, f"comando proibido: {command}"
    if command not in ALLOWED_COMMANDS:
        return False, f"comando fora da allowlist: {command}"

    for token in argv:
        if any(char in _SHELL_METACHARS for char in token):
            return False, "argv contém metacaracter de shell"

    return True, "ok"
