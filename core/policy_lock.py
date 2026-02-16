import json
from pathlib import Path
from core.command_policy import load_policy, compute_policy_sha256


POLICY_LOCK_FILE = Path("data/policy_lock.json")


class PolicyLockError(Exception):
    pass


def initialize_policy_lock():
    policy = load_policy()
    lock_data = {
        "locked_policy_sha256": compute_policy_sha256(),
        "locked_version": policy.get("version"),
    }

    POLICY_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    POLICY_LOCK_FILE.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")


def load_policy_lock():
    if not POLICY_LOCK_FILE.exists():
        raise PolicyLockError("Policy lock not initialized.")

    return json.loads(POLICY_LOCK_FILE.read_text(encoding="utf-8"))


def verify_policy_locked():
    lock_data = load_policy_lock()

    current_hash = compute_policy_sha256()
    current_policy = load_policy()

    if current_hash != lock_data["locked_policy_sha256"]:
        raise PolicyLockError("Policy file altered outside maintenance mode.")

    if current_policy.get("version") != lock_data["locked_version"]:
        raise PolicyLockError("Policy version mismatch with locked version.")
