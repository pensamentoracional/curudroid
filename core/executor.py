import hashlib
import json
from pathlib import Path
from datetime import datetime
from core.plan_validator import validate_plan, PlanValidationError
from core.safe_runner import run_command, CommandExecutionError
from core.command_policy import is_command_allowed, compute_policy_sha256, load_policy
from core.observability import log_decision, increment_metric


RESULTS_DIR = Path("ai/results")
APPROVALS_DIR = Path("ai/approvals")
HISTORY_FILE = Path("ai/history/execution_history.log")


def is_plan_approved(plan_id: str) -> bool:
    approval_file = APPROVALS_DIR / f"{plan_id}.approved"
    return approval_file.exists()


def load_previous_report(plan_id: str):
    report_path = RESULTS_DIR / f"{plan_id}_result.json"
    if not report_path.exists():
        return None

    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)

def compute_file_sha256(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


class PlanExecutionError(Exception):
    pass

def append_history(report: dict) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    previous_hash = get_last_history_hash()

    entry_core = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "plan_id": report["plan_id"],
        "mode": report.get("mode"),
        "plan_sha256": report.get("plan_sha256"),
        "policy_sha256": report.get("policy_sha256"),
        "policy_version": report.get("policy_version"),
        "risk_score": report.get("risk_score"),
        "previous_hash": previous_hash,
    }

    # Calcular hash da entrada
    hasher = hashlib.sha256()
    hasher.update(json.dumps(entry_core, sort_keys=True).encode("utf-8"))
    entry_hash = hasher.hexdigest()

    entry_core["entry_hash"] = entry_hash

    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry_core) + "\n")

def get_last_history_hash() -> str | None:
    if not HISTORY_FILE.exists():
        return None

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return None

    last_entry = json.loads(lines[-1])
    return last_entry.get("entry_hash")

def execute_plan(plan_path: str, apply: bool = False) -> dict:
    """
    Executa um plano previamente validado.
    Se apply=False  apenas dry-run.
    """

    try:
        plan = validate_plan(plan_path)
        plan_hash = compute_file_sha256(plan_path)
        policy_hash = compute_policy_sha256()
        policy = load_policy()
        policy_version = policy.get("version")
        previous_report = load_previous_report(plan["id"])

        if apply:
            if previous_report is None:
                log_decision({
                    "component": "executor",
                    "plan_id": plan["id"],
                    "allowed": False,
                    "reason": "Apply blocked: no prior dry-run report found."
                })
                increment_metric("executor_blocked")
                raise PlanExecutionError(
                    "Apply blocked: no prior dry-run report found."
                )


            previous_policy_hash = previous_report.get("policy_sha256")
            previous_policy_version = previous_report.get("policy_version")

            current_policy_hash = policy_hash
            current_policy_version = policy_version

            # Se a policy mudou
            if previous_policy_hash != current_policy_hash:

                # Mudou sem version bump  erro estrutural
                if previous_policy_version == current_policy_version:
                    log_decision({
                        "component": "executor",
                        "plan_id": plan["id"],
                        "allowed": False,
                        "reason": "Apply blocked: policy changed without version bump."
                    })
                    increment_metric("executor_blocked")
                    raise PlanExecutionError(
                        "Apply blocked: policy changed without version bump."
                    )


                # Mudou com version bump  fluxo normal exige novo dry-run
                log_decision({
                    "component": "executor",
                    "plan_id": plan["id"],
                    "allowed": False,
                    "reason": "Apply blocked: allowlist policy changed since last dry-run bump."
                })
                increment_metric("executor_blocked")
                raise PlanExecutionError(
                    "Apply blocked: allowlist policy changed since last dry-run bump."
                )

            # Verifica approval explicito
            if not is_plan_approved(plan["id"]):
                log_decision({
                    "component": "executor",
                    "plan_id": plan["id"],
                    "allowed": False,
                    "reason": "No approval file found."
                })
                increment_metric("executor_blocked")
                raise PlanExecutionError(
                    "No approval file found."
                )


    except PlanValidationError as e:
        log_decision({
            "component": "executor",
            "plan_path": plan_path,
            "allowed": False,
            "reason": f"Validation failed: {str(e)}"
        })
        increment_metric("executor_validation_failed")

        raise PlanExecutionError(f"Validation failed: {str(e)}")


    execution_results = []

    for command in plan["commands"]:
        if not is_command_allowed(command["command"]):
            log_decision({
                "component": "executor",
                "plan_id": plan["id"],
                "allowed": False,
                "reason": f"Command not allowed: {command['command']}"
            })
            increment_metric("executor_blocked")
            raise PlanExecutionError(
                f"Command not allowed by policy: {command['command']}"
            )

        if not apply:
            execution_results.append({
                "command": command["command"],
                "dry_run": True,
                "timeout_seconds": command["timeout_seconds"]
            })
        else:
            try:
                result = run_command(
                    command["command"],
                    command["timeout_seconds"]
                )
                result["dry_run"] = False
                execution_results.append(result)
            except CommandExecutionError as e:
                log_decision({
                    "component": "executor",
                    "plan_id": plan["id"],
                    "allowed": False,
                    "reason": f"Command execution error: {str(e)}"
                })
                increment_metric("executor_failed")
                raise PlanExecutionError(f"Execution error: {str(e)}")

    return build_execution_report(plan, execution_results, plan_hash, policy_hash, policy_version)


def build_execution_report(plan, results, plan_hash, policy_hash, policy_version):
    report = {
        "plan_id": plan["id"],
        "schema_version": plan["schema_version"],
        "plan_sha256": plan_hash,
        "policy_sha256": policy_hash,
        "policy_version": policy_version,
        "executed_at": datetime.utcnow().isoformat() + "Z",
        "risk_score": plan["risk_score"],
        "source": plan["source"],
        "mode": "apply" if any(not r.get("dry_run", False) for r in results) else "dry-run",
        "results": results
    }

    save_execution_report(report)
    append_history(report)

    log_decision({
        "component": "executor",
        "plan_id": report["plan_id"],
        "mode": report["mode"],
        "risk_score": report.get("risk_score"),
        "allowed": True,
        "reason": "Execution completed"
    })

    increment_metric("executor_executed")

    return report


def save_execution_report(report: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{report['plan_id']}_result.json"
    output_path = RESULTS_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

