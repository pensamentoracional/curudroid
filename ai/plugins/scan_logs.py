plugin_id = "scan_logs"
version = "1.1.0"
required_env_vars: list[str] = []


def run(intent: dict) -> dict:
    del intent
    return {
        "success": True,
        "commands": [
            {
                "argv": ["tail", "-n", "50", "logs/curudroid.log"],
                "description": "Ler últimas 50 linhas do log principal",
            },
            {
                "argv": ["grep", "ERROR", "logs/curudroid.log"],
                "description": "Filtrar erros registrados",
            },
            {
                "argv": ["grep", "WARN", "logs/curudroid.log"],
                "description": "Filtrar avisos registrados",
            },
        ],
        "risk_estimate": 0.2,
        "assumptions": [
            "Arquivo logs/curudroid.log existe",
            "Execução em modo somente leitura",
        ],
    }
