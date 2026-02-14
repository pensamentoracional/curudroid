#!/usr/bin/env python3

import importlib
import json
from datetime import datetime, timezone
from pathlib import Path

from ai.config import CURUPIRA_RISK_THRESHOLD


BASE_DIR = Path(__file__).resolve().parent
APPROVED_DIR = BASE_DIR / "approved"
PLUGINS_DIR = BASE_DIR / "plugins"
PLANS_DIR = BASE_DIR / "plans"

# Compatibilidade legada para testes/chamadores antigos.
INTENTS_DIR = APPROVED_DIR

PLANS_DIR.mkdir(parents=True, exist_ok=True)

_SHELL_METACHARS = set("|&;<>$`\\!{}()*?[]~")


def load_latest_intent():
    intents = sorted(APPROVED_DIR.glob("*.json"))
    if not intents:
        raise RuntimeError("Nenhuma intenção aprovada encontrada em ai/approved/")
    latest = intents[-1]
    with open(latest, "r", encoding="utf-8") as f:
        return json.load(f), latest.name


def load_plugin(intent_name: str):
    plugin_path = PLUGINS_DIR / f"{intent_name}.py"
    if not plugin_path.exists():
        return None
    module_name = f"ai.plugins.{intent_name}"
    return importlib.import_module(module_name)


def now_ts():
    return datetime.now(timezone.utc).isoformat()


def call_curupira(context: dict):
    from ai.curupira_adapter import run_curupira

    return run_curupira(context)


def _command_is_safe(command: dict) -> bool:
    if not isinstance(command, dict):
        return False
    if set(command.keys()) != {"argv", "description"}:
        return False

    argv = command.get("argv")
    description = command.get("description")

    if not isinstance(argv, list) or not argv or not all(isinstance(i, str) and i for i in argv):
        return False
    if not isinstance(description, str):
        return False

    for token in argv:
        if any(char in _SHELL_METACHARS for char in token):
            return False

    return True


def _normalize_commands(commands: list) -> tuple[list[dict], list[str]]:
    normalized: list[dict] = []
    warnings: list[str] = []

    for idx, command in enumerate(commands):
        if not _command_is_safe(command):
            warnings.append(f"Comando {idx} ignorado por formato inválido ou metacaracter de shell")
            continue
        normalized.append(
            {
                "argv": list(command["argv"]),
                "description": command["description"],
            }
        )

    return normalized, warnings


def _write_plan_files(base_name: str, lines: list[str], payload: dict) -> tuple[Path, Path]:
    plan_path = PLANS_DIR / f"{base_name}.plan"
    json_path = PLANS_DIR / f"{base_name}.json"

    with open(plan_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return plan_path, json_path


def generate_plan():
    intent, intent_file = load_latest_intent()
    intent_name = intent.get("intent")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    base_name = f"{timestamp}_{intent_name}"

    plugin = load_plugin(intent_name)

    plan_lines = [
        "# Plano sugerido (DRY-RUN)",
        f"# Gerado em: {now_ts()}",
        f"# Intent file: {intent_file}",
        f"# Intenção: {intent_name}",
    ]

    if plugin is None:
        plan_lines.append("# STATUS: REJEITADO")
        plan_lines.append("# Motivo: Nenhum plugin autorizado para esta intenção")

        json_payload = {
            "plan_id": f"{base_name}.json",
            "version": 1,
            "intent_path": f"ai/approved/{intent_file}",
            "risk_estimate": 0.0,
            "commands": [],
            "assumptions": ["Nenhum plugin autorizado para esta intenção"],
        }

        plan_path, json_path = _write_plan_files(base_name, plan_lines, json_payload)
        print(f"❌ Intenção rejeitada (deny by default): {plan_path}")
        print(f"📦 JSON de plano: {json_path}")
        return

    plugin_result = plugin.run(intent)
    raw_commands = plugin_result.get("commands", [])
    normalized_commands, command_warnings = _normalize_commands(raw_commands)

    risk = float(plugin_result.get("risk_estimate", 0.0))
    assumptions = plugin_result.get("assumptions", [])
    if not isinstance(assumptions, list):
        assumptions = []
    assumptions = [item for item in assumptions if isinstance(item, str)] + command_warnings

    success = bool(plugin_result.get("success", False)) and not command_warnings
    use_curupira = risk >= CURUPIRA_RISK_THRESHOLD

    plan_lines.extend(
        [
            "",
            f"# SUCCESS: {'SIM' if success else 'NÃO'}",
            f"# RISCO ESTIMADO: {risk}",
            f"# LIMIAR CURUPIRA: {CURUPIRA_RISK_THRESHOLD}",
            f"# Curupira acionado: {'SIM' if use_curupira else 'NÃO'}",
            "",
            "# Assumptions:",
        ]
    )
    for assumption in assumptions:
        plan_lines.append(f"# - {assumption}")

    plan_lines.append("")
    plan_lines.append("# Comandos sugeridos (argv):")
    for command in normalized_commands:
        plan_lines.append(f"# {command['description']}")
        plan_lines.append(json.dumps(command["argv"], ensure_ascii=False))

    if use_curupira:
        plan_lines.append("")
        plan_lines.append("# --- Opinião Curupira ---")
        try:
            context = {
                "intent": intent,
                "risk": risk,
                "commands": normalized_commands,
                "assumptions": assumptions,
            }
            curupira_response = call_curupira(context)
            if isinstance(curupira_response, dict):
                plan_lines.append(json.dumps(curupira_response, indent=2, ensure_ascii=False))
            else:
                plan_lines.append(str(curupira_response))
        except Exception as e:
            plan_lines.append(f"# ERRO ao chamar Curupira: {e}")
    else:
        plan_lines.append("")
        plan_lines.append("# Curupira não acionado (risco abaixo do limiar)")

    json_payload = {
        "plan_id": f"{base_name}.json",
        "version": 1,
        "intent_path": f"ai/approved/{intent_file}",
        "risk_estimate": risk,
        "commands": normalized_commands,
        "assumptions": assumptions,
    }

    plan_path, json_path = _write_plan_files(base_name, plan_lines, json_payload)
    print(f"📄 Plano gerado: {plan_path}")
    print(f"📦 JSON de plano: {json_path}")


if __name__ == "__main__":
    generate_plan()
