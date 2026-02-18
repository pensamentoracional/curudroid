
#!/usr/bin/env python3

import os
import json
import importlib
from datetime import datetime, timezone
from pathlib import Path

from ai.config import CURUPIRA_RISK_THRESHOLD

# Caminhos base
BASE_DIR = Path(__file__).resolve().parent
INTENTS_DIR = BASE_DIR / "intents"
APPROVED_DIR = BASE_DIR / "approved"
PLUGINS_DIR = BASE_DIR / "plugins"
PLANS_DIR = BASE_DIR / "plans"

PLANS_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# Utilidades
# =========================


def load_latest_intent():
    """Carrega a intent mais recente.

    Prioriza `ai/intents` para permitir testes e geração local previsível,
    mantendo fallback para `ai/approved` por compatibilidade com fluxos legados.
    """
    intents = sorted(INTENTS_DIR.glob("*.json"))
    if intents:
        latest = intents[-1]
        with open(latest, "r", encoding="utf-8") as f:
            return json.load(f), latest.name

    approved = sorted(APPROVED_DIR.glob("*.json"))
    if approved:
        latest = approved[-1]
        with open(latest, "r", encoding="utf-8") as f:
            return json.load(f), latest.name

    raise RuntimeError("Nenhuma intenção encontrada em ai/intents/ ou ai/approved/")


def load_plugin(intent_name: str):
    plugin_path = PLUGINS_DIR / f"{intent_name}.py"
    if not plugin_path.exists():
        return None
    module_name = f"ai.plugins.{intent_name}"
    return importlib.import_module(module_name)


def now_ts():
    return datetime.now(timezone.utc).isoformat()


# =========================
# Curupira (condicional)
# =========================

def call_curupira(context: dict) -> str:
    from ai.curupira_adapter import run_curupira
    return run_curupira(context)


# =========================
# Geração de plano
# =========================

def generate_plan():
    intent, intent_file = load_latest_intent()
    intent_name = intent.get("intent")

    plugin = load_plugin(intent_name)

    plan_lines = []
    plan_lines.append("# Plano sugerido (DRY-RUN)")
    plan_lines.append(f"# Gerado em: {now_ts()}")
    plan_lines.append(f"# Intent file: {intent_file}")
    plan_lines.append(f"# Intenao: {intent_name}")

    if plugin is None:
        plan_lines.append("# STATUS: REJEITADO")
        plan_lines.append("# Motivo: Nenhum plugin autorizado para esta intenao")

        plan_path = PLANS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{intent_name}.plan"
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("\n".join(plan_lines))

        print(f" Intenao rejeitada (deny by default): {plan_path}")
        return

    plugin_result = plugin.run(intent)

    raw_commands = plugin_result.get("commands", [])
    risk_float = float(plugin_result.get("risk", 0.0))
    summary = plugin_result.get("summary", "")

    # Converter risco para inteiro compativel com validator
    risk_int = int(round(risk_float))
    if risk_int > 5:
        risk_int = 5
    if risk_int < 0:
        risk_int = 0

    use_curupira = risk_float >= CURUPIRA_RISK_THRESHOLD

    plan_lines.append("")
    plan_lines.append(f"# RISCO ESTIMADO: {risk_float}")
    plan_lines.append(f"# RISCO NORMALIZADO (int): {risk_int}")
    plan_lines.append(f"# LIMIAR CURUPIRA: {CURUPIRA_RISK_THRESHOLD}")
    plan_lines.append(f"# Curupira acionado: {'SIM' if use_curupira else 'NAO'}")

    if summary:
        plan_lines.append(f"# Resumo plugin: {summary}")

    plan_lines.append("")

    # Converter comandos para formato estruturado exigido
    structured_commands = []

    for cmd in raw_commands:
        plan_lines.append(str(cmd))

        structured_commands.append({
            "type": "shell",
            "command": str(cmd),
            "timeout_seconds": 10
        })

    curupira_response_text = None

    if use_curupira:
        plan_lines.append("")
        plan_lines.append("# --- Opiniao Curupira ---")

        try:
            context = {
                "intent": intent,
                "risk": risk_float,
                "commands": raw_commands,
                "summary": summary,
            }

            curupira_response = call_curupira(context)

            if isinstance(curupira_response, dict):
                curupira_response_text = curupira_response
                plan_lines.append(json.dumps(curupira_response, indent=2, ensure_ascii=False))
            else:
                curupira_response_text = str(curupira_response)
                plan_lines.append(str(curupira_response))

        except Exception as e:
            plan_lines.append(f"# ERRO ao chamar Curupira: {e}")
            curupira_response_text = f"ERROR: {e}"

    else:
        plan_lines.append("")
        plan_lines.append("# Curupira nao acionado (risco abaixo do limiar)")

    # =========================
    # Criar JSON estruturado
    # =========================

    plan_json = {
        "schema_version": "0.1",
        "id": f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{intent_name}",
        "created_at": now_ts(),
        "risk_score": risk_int,
        "source": "ai_generate_plan",
        "commands": structured_commands,
        "metadata": {
            "intent_file": intent_file,
            "intent": intent_name,
            "risk_float": risk_float,
            "curupira_used": use_curupira,
            "curupira_response": curupira_response_text,
            "summary": summary
        }
    }

    # =========================
    # Persistencia dual (.plan + .json)
    # =========================

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')

    # 1 Salvar plano textual humano (.plan)
    plan_text_filename = f"{timestamp}_{intent_name}.plan"
    plan_text_path = PLANS_DIR / plan_text_filename

    with open(plan_text_path, "w", encoding="utf-8") as f:
        f.write("\n".join(plan_lines))

    print(f" Plano textual gerado: {plan_text_path}")

    # 2 Salvar plano estruturado JSON (.json)
    plan_json_filename = f"{timestamp}_{intent_name}.json"
    plan_json_path = PLANS_DIR / plan_json_filename

    with open(plan_json_path, "w", encoding="utf-8") as f:
        json.dump(plan_json, f, indent=2, ensure_ascii=False)

    print(f" Plano JSON estruturado gerado: {plan_json_path}")

# =========================
# Entry point
# =========================

if __name__ == "__main__":
    generate_plan()
