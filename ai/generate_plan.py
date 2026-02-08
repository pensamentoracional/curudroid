
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
PLUGINS_DIR = BASE_DIR / "plugins"
PLANS_DIR = BASE_DIR / "plans"

PLANS_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# Utilidades
# =========================

def load_latest_intent():
    intents = sorted(INTENTS_DIR.glob("*.json"))
    if not intents:
        raise RuntimeError("Nenhuma intenção encontrada em ai/intents/")
    with open(intents[-1], "r", encoding="utf-8") as f:
        return json.load(f), intents[-1].name


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
    plan_lines.append(f"# Intenção: {intent_name}")

    # -------------------------
    # DENY BY DEFAULT
    # -------------------------
    if plugin is None:
        plan_lines.append("# STATUS: REJEITADO")
        plan_lines.append("# Motivo: Nenhum plugin autorizado para esta intenção")

        plan_path = PLANS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{intent_name}.plan"
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("\n".join(plan_lines))

        print(f"❌ Intenção rejeitada (deny by default): {plan_path}")
        return

    # -------------------------
    # Executar plugin
    # -------------------------
    plugin_result = plugin.run(intent)

    commands = plugin_result.get("commands", [])
    risk = float(plugin_result.get("risk", 0.0))
    summary = plugin_result.get("summary", "")

    use_curupira = risk >= CURUPIRA_RISK_THRESHOLD

    # -------------------------
    # Cabeçalho de risco
    # -------------------------
    plan_lines.append("")
    plan_lines.append(f"# RISCO ESTIMADO: {risk}")
    plan_lines.append(f"# LIMIAR CURUPIRA: {CURUPIRA_RISK_THRESHOLD}")
    plan_lines.append(f"# Curupira acionado: {'SIM' if use_curupira else 'NÃO'}")

    if summary:
        plan_lines.append(f"# Resumo plugin: {summary}")

    plan_lines.append("")

    # -------------------------
    # Comandos sugeridos
    # -------------------------
    for cmd in commands:
        plan_lines.append(cmd)

    # -------------------------
    # Curupira (apenas se risco >= X)
    # -------------------------
    if use_curupira:
        plan_lines.append("")
        plan_lines.append("# --- Opinião Curupira ---")

        try:
            context = {
                "intent": intent,
                "risk": risk,
                "commands": commands,
                "summary": summary,
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

    # -------------------------
    # Persistir plano
    # -------------------------
    plan_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{intent_name}.plan"
    plan_path = PLANS_DIR / plan_filename

    with open(plan_path, "w", encoding="utf-8") as f:
        f.write("\n".join(plan_lines))

    print(f"📄 Plano gerado: {plan_path}")


# =========================
# Entry point
# =========================

if __name__ == "__main__":
    generate_plan()
