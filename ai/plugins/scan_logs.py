from pathlib import Path

from ai.plugins.contracts import PluginSpec

PLUGIN_SPEC = PluginSpec(
    plugin_id="scan_logs",
    plugin_version="1.0.0",
    required_env=[],
    capabilities=["logs.read", "analysis.basic"],
    core=True,
)

RISK_BASE = 0.20


def init(config, logger) -> None:
    del config
    del logger


def healthcheck() -> tuple[bool, str]:
    if not Path("logs").exists():
        return False, "diretório logs ausente"
    return True, "estrutura local válida"


def run(intent: dict) -> dict:
    """Analisa logs básicos do Curudroid e retorna instruções DRY-RUN."""
    return {
        "plugin": "scan_logs",
        "risk": RISK_BASE,
        "summary": "Análise básica de logs solicitada",
        "commands": [
            "# Plano sugerido (DRY-RUN)",
            "# Intenção: scan_logs",
            "cat logs/curudroid.log | tail -n 50",
            "grep ERROR logs/curudroid.log",
            "grep WARN logs/curudroid.log",
        ],
    }
