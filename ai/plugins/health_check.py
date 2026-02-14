import os
from pathlib import Path

from ai.plugins.contracts import PluginSpec

PLUGIN_SPEC = PluginSpec(
    plugin_id="health_check",
    plugin_version="1.0.0",
    required_env=[],
    capabilities=["logs.read", "health.basic"],
    core=True,
)

RISK_BASE = 0.30
BOOT_LOG = "logs/boot.log"
MAIN_LOG = "logs/curudroid.log"


def init(config, logger) -> None:
    # Contrato mínimo: plugin inicializável sem side effects de rede.
    del config
    del logger


def healthcheck() -> tuple[bool, str]:
    """
    Healthcheck leve.
    Nao deve falhar por estrutura de runtime.
    Apenas valida integridade basica do plugin.
    """
    return True, "plugin carregado corretamente"


def run(intent: dict) -> dict:
    """Verificação de saúde do sistema (boot, heartbeat, uptime lógico)."""
    commands = [
        "# Plano sugerido (DRY-RUN)",
        "# Intenção: health_check",
    ]

    if os.path.exists(BOOT_LOG):
        commands.append(f"cat {BOOT_LOG}")
    else:
        commands.append(f"# boot.log não encontrado ({BOOT_LOG})")

    commands.extend(
        [
            "",
            "# Últimos heartbeats",
            f"grep 'Heartbeat' {MAIN_LOG} | tail -n 10",
            "",
            "# Últimos eventos críticos",
            f"grep -E 'ERROR|WARN' {MAIN_LOG} | tail -n 10",
            "",
            "# Uptime lógico (desde último boot detectado)",
            f"head -n 1 {BOOT_LOG} || true",
        ]
    )

    return {
        "plugin": "health_check",
        "risk": RISK_BASE,
        "summary": "Verificação de saúde do sistema",
        "commands": commands,
    }
