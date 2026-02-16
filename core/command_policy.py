import json
import hashlib
from pathlib import Path


POLICY_FILE = Path("core/policy/allowlist.json")


class CommandPolicyError(Exception):
    pass


def load_policy() -> dict:
    if not POLICY_FILE.exists():
        raise CommandPolicyError("Allowlist policy file not found")

    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        policy = json.load(f)

    if "version" not in policy:
        raise CommandPolicyError("Policy version field missing")

    if "allowed_commands" not in policy:
        raise CommandPolicyError("allowed_commands missing")

    return policy


def compute_policy_sha256() -> str:
    hasher = hashlib.sha256()
    with open(POLICY_FILE, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_command_allowed(command: str) -> bool:
    policy = load_policy()
    allowed = policy.get("allowed_commands", [])
    command_base = command.split()[0]
    return command_base in allowed
