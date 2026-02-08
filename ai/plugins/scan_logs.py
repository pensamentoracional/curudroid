RISK_BASE = 0.20

def run(intent: dict) -> dict:
    """
    Analisa logs básicos do Curudroid.
    Retorna instruções sugeridas (dry-run).
    """

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
