plugin_id = "summarize_logs"
version = "1.1.0"
required_env_vars = ["AI_PROVIDER", "AI_API_KEY"]


def run(intent: dict) -> dict:
    del intent
    return {
        "success": True,
        "commands": [
            {
                "argv": ["tail", "-n", "100", "logs/curudroid.log"],
                "description": "Coletar contexto recente para sumarização",
            },
            {
                "argv": ["python", "-m", "ai.curupira_adapter"],
                "description": "Gerar resumo assistido (dry-run)",
            },
        ],
        "risk_estimate": 0.45,
        "assumptions": [
            "Provider de IA e chave de API configurados",
            "Resumo será revisado manualmente antes de qualquer ação",
        ],
    }
