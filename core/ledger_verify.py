import json
import hashlib
from pathlib import Path


HISTORY_FILE = Path("ai/history/execution_history.log")


class LedgerIntegrityError(Exception):
    pass


def compute_entry_hash(entry_core: dict) -> str:
    hasher = hashlib.sha256()
    hasher.update(json.dumps(entry_core, sort_keys=True).encode("utf-8"))
    return hasher.hexdigest()


def verify_ledger() -> dict:
    if not HISTORY_FILE.exists():
        return {
            "ok": True,
            "entries": 0,
            "message": "Ledger file not found (treated as empty/OK)."
        }

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if not lines:
        return {"ok": True, "entries": 0, "message": "Ledger empty/OK."}

    previous_entry_hash = None

    for idx, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            raise LedgerIntegrityError(f"Line {idx}: invalid JSON: {e}")

        if "entry_hash" not in entry:
            raise LedgerIntegrityError(f"Line {idx}: missing entry_hash")

        if "previous_hash" not in entry:
            raise LedgerIntegrityError(f"Line {idx}: missing previous_hash")

        # Verificaao do encadeamento
        if entry["previous_hash"] != previous_entry_hash:
            raise LedgerIntegrityError(
                f"Line {idx}: previous_hash mismatch. Expected={previous_entry_hash} Got={entry['previous_hash']}"
            )

        # Recalcular hash (sem entry_hash)
        entry_core = dict(entry)
        entry_hash = entry_core.pop("entry_hash")

        recalculated = compute_entry_hash(entry_core)

        if recalculated != entry_hash:
            raise LedgerIntegrityError(
                f"Line {idx}: entry_hash mismatch. Expected={recalculated} Got={entry_hash}"
            )

        previous_entry_hash = entry_hash

    return {"ok": True, "entries": len(lines), "message": "Ledger integrity OK."}

def recover_ledger() -> dict:
    if not HISTORY_FILE.exists():
        return {"ok": True, "message": "No ledger to recover."}

    # Backup automatico
    backup_path = HISTORY_FILE.with_suffix(".corrupted.bak")
    HISTORY_FILE.rename(backup_path)

    # Criar novo genesis block
    genesis_entry = {
        "timestamp": "GENESIS_RECOVERY",
        "plan_id": "LEDGER_RECOVERY",
        "mode": "recovery",
        "plan_sha256": None,
        "policy_sha256": None,
        "policy_version": None,
        "risk_score": None,
        "previous_hash": None,
    }

    # Calcular hash do genesis
    hasher = hashlib.sha256()
    hasher.update(json.dumps(genesis_entry, sort_keys=True).encode("utf-8"))
    genesis_hash = hasher.hexdigest()

    genesis_entry["entry_hash"] = genesis_hash

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(genesis_entry) + "\n")

    return {
        "ok": True,
        "backup_created": str(backup_path),
        "message": "Ledger recovered with new genesis block."
    }
