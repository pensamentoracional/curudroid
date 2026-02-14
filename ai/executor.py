"""Executor assistido para planos JSON do Curudroid."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable

from ai.executor_allowlist import validate_argv

DEFAULT_EXECUTOR_RISK_THRESHOLD = 0.4

MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parent
RESULTS_DIR = MODULE_DIR / "results"
LOG_FILE = REPO_ROOT / "logs" / "curudroid.log"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_threshold() -> float:
    raw = (os.getenv("EXECUTOR_RISK_THRESHOLD") or "").strip()
    if not raw:
        return DEFAULT_EXECUTOR_RISK_THRESHOLD
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_EXECUTOR_RISK_THRESHOLD


def _log_event(log_file: Path, message: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{now_iso()}] {message}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


def _compute_plan_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def _is_approved_intent_path(intent_path: str, repo_root: Path) -> tuple[bool, str]:
    if not isinstance(intent_path, str) or not intent_path:
        return False, "intent_path inválido"

    approved_root = (repo_root / "ai" / "approved").resolve()
    target = (repo_root / intent_path).resolve()

    try:
        target.relative_to(approved_root)
    except ValueError:
        return False, "intent_path fora de ai/approved"

    if not target.exists() or not target.is_file():
        return False, "intent_path não encontrado"

    return True, "ok"


def _validate_commands(commands: Any) -> tuple[bool, str, list[dict[str, Any]]]:
    if not isinstance(commands, list):
        return False, "commands deve ser list", []

    normalized: list[dict[str, Any]] = []
    for idx, command in enumerate(commands):
        if not isinstance(command, dict):
            return False, f"commands[{idx}] deve ser dict", []
        if set(command.keys()) != {"argv", "description"}:
            return False, f"commands[{idx}] deve conter argv e description", []

        argv = command.get("argv")
        description = command.get("description")
        if not isinstance(description, str):
            return False, f"commands[{idx}].description deve ser str", []

        ok, reason = validate_argv(argv)
        if not ok:
            return False, f"commands[{idx}] inválido: {reason}", []

        normalized.append({"argv": list(argv), "description": description})

    return True, "ok", normalized


def validate_plan_payload(payload: dict, threshold: float, repo_root: Path) -> tuple[bool, str, float, list[dict[str, Any]]]:
    required_top = {"plan_id", "version", "intent_path", "risk_estimate", "commands", "assumptions"}
    if not isinstance(payload, dict):
        return False, "plan JSON deve ser objeto", 0.0, []

    missing = required_top - set(payload.keys())
    if missing:
        return False, f"faltam campos no plano: {', '.join(sorted(missing))}", 0.0, []

    risk = payload.get("risk_estimate")
    if not isinstance(risk, (int, float)):
        return False, "risk_estimate inválido", 0.0, []
    effective_risk = float(risk)
    if effective_risk > threshold:
        return False, f"risk_estimate acima do limiar ({effective_risk} > {threshold})", effective_risk, []

    ok, reason = _is_approved_intent_path(payload.get("intent_path"), repo_root)
    if not ok:
        return False, reason, effective_risk, []

    ok, reason, commands = _validate_commands(payload.get("commands"))
    if not ok:
        return False, reason, effective_risk, []

    assumptions = payload.get("assumptions")
    if not isinstance(assumptions, list) or not all(isinstance(item, str) for item in assumptions):
        return False, "assumptions inválido (esperado list[str])", effective_risk, []

    return True, "ok", effective_risk, commands


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def execute_plan(
    plan_path: Path,
    apply: bool = False,
    *,
    input_func: Callable[[str], str] = input,
    run_func: Callable[..., Any] = subprocess.run,
    repo_root: Path = REPO_ROOT,
    results_dir: Path = RESULTS_DIR,
    log_file: Path = LOG_FILE,
    threshold: float | None = None,
) -> tuple[int, dict | None, str]:
    threshold_value = load_threshold() if threshold is None else threshold

    if not plan_path.exists() or not plan_path.is_file():
        return 1, None, "plan.json não encontrado"

    try:
        raw = plan_path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        return 1, None, f"plan.json inválido: {exc}"

    valid, reason, effective_risk, commands = validate_plan_payload(payload, threshold_value, repo_root)
    if not valid:
        _log_event(log_file, f"EXECUTOR ABORT {plan_path.name}: {reason}")
        return 1, None, reason

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    run_root = results_dir / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    timestamp_start = now_iso()
    plan_hash = _compute_plan_hash(raw)

    result_payload: dict[str, Any] = {
        "run_id": run_id,
        "timestamp_start": timestamp_start,
        "timestamp_end": timestamp_start,
        "mode": "apply" if apply else "dry-run",
        "status": "simulated" if not apply else "running",
        "effective_risk": effective_risk,
        "threshold": threshold_value,
        "plan_hash": plan_hash,
        "commands": [command["argv"] for command in commands],
    }

    if not apply:
        result_payload["timestamp_end"] = now_iso()
        result_payload["status"] = "simulated"
        _write_json(run_root / "result.json", result_payload)
        _log_event(log_file, f"EXECUTOR DRY-RUN {run_id} plano={plan_path.name} cmds={len(commands)}")
        return 0, result_payload, "simulado"

    confirmation = input_func("Digite CONFIRM para aplicar o plano: ")
    if confirmation != "CONFIRM":
        result_payload["status"] = "aborted"
        result_payload["timestamp_end"] = now_iso()
        _write_json(run_root / "result.json", result_payload)
        _log_event(log_file, f"EXECUTOR APPLY ABORT {run_id}: confirmação inválida")
        return 1, result_payload, "confirmação inválida"

    command_results: list[dict[str, Any]] = []
    overall_ok = True

    for idx, command in enumerate(commands):
        stdout_path = run_root / f"command_{idx:02d}.stdout.txt"
        stderr_path = run_root / f"command_{idx:02d}.stderr.txt"

        with open(stdout_path, "w", encoding="utf-8") as stdout_file, open(
            stderr_path, "w", encoding="utf-8"
        ) as stderr_file:
            completed = run_func(
                command["argv"],
                shell=False,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
            )

        returncode = int(getattr(completed, "returncode", 1))
        status = "OK" if returncode == 0 else "FAIL"
        if returncode != 0:
            overall_ok = False

        command_results.append(
            {
                "argv": command["argv"],
                "description": command["description"],
                "status": status,
                "returncode": returncode,
                "stdout_file": stdout_path.name,
                "stderr_file": stderr_path.name,
            }
        )

    result_payload["status"] = "ok" if overall_ok else "fail"
    result_payload["timestamp_end"] = now_iso()
    result_payload["command_results"] = command_results
    _write_json(run_root / "result.json", result_payload)

    _log_event(
        log_file,
        f"EXECUTOR APPLY {run_id} plano={plan_path.name} status={result_payload['status']} cmds={len(commands)}",
    )

    return (0 if overall_ok else 1), result_payload, result_payload["status"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Executor assistido de planos JSON")
    parser.add_argument("plan_json", help="Caminho para ai/plans/<timestamp>_<intent>.json")
    parser.add_argument("--apply", action="store_true", help="Executa comandos de fato (requer confirmação)")
    args = parser.parse_args()

    exit_code, payload, message = execute_plan(Path(args.plan_json), apply=args.apply)
    if payload is not None:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(message)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
