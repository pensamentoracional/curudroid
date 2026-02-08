
#!/usr/bin/env python3
"""
Curupira Adapter — integração segura com Curudroid

Regras:
- Nunca executa ações
- Nunca assume decisão
- Sempre retorna JSON válido
- Silêncio = opinião neutra (confidence 0.0)
- Texto humano = baixa confiança
"""

import json
import subprocess
from datetime import datetime


CURUPIRA_ENTRYPOINT = ["python", "external/curupira/agent.py"]


def run_curupira(context: dict) -> dict:
    """
    Executa o Curupira como subprocesso e normaliza a saída
    para um contrato JSON seguro.
    """
    try:
        result = subprocess.run(
            CURUPIRA_ENTRYPOINT,
            input=json.dumps(context),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as e:
        return {
            "intent": context.get("intent", "unknown"),
            "reason": f"Falha ao executar Curupira: {e}",
            "confidence": 0.0,
            "source": "curupira",
            "status": "execution_error",
            "ts": datetime.utcnow().isoformat(),
        }

    # Caso 1 — erro real de execução
    if result.returncode != 0:
        return {
            "intent": context.get("intent", "unknown"),
            "reason": result.stderr.strip() or "Erro desconhecido no Curupira",
            "confidence": 0.0,
            "source": "curupira",
            "status": "runtime_error",
            "ts": datetime.utcnow().isoformat(),
        }

    stdout = (result.stdout or "").strip()

    # Caso 2 — Curupira deliberadamente silencioso
    if not stdout:
        return {
            "intent": context.get("intent", "unknown"),
            "reason": "Curupira não emitiu resposta explícita",
            "confidence": 0.0,
            "source": "curupira",
            "status": "no_opinion",
            "ts": datetime.utcnow().isoformat(),
        }

    # Caso 3 — Curupira respondeu JSON válido
    try:
        payload = json.loads(stdout)
        payload.setdefault("source", "curupira")
        payload.setdefault("status", "json_response")
        payload.setdefault("ts", datetime.utcnow().isoformat())
        payload.setdefault("confidence", float(payload.get("confidence", 0.0)))
        return payload
    except json.JSONDecodeError:
        # Caso 4 — Curupira respondeu texto humano
        return {
            "intent": context.get("intent", "unknown"),
            "reason": stdout[:800],
            "confidence": 0.2,
            "source": "curupira",
            "status": "text_response",
            "ts": datetime.utcnow().isoformat(),
        }


def main():
    """
    Execução standalone para testes manuais.
    """
    context = {
        "intent": "scan_logs",
        "origin": "manual_test",
        "constraints": {
            "dry_run": True,
            "deny_by_default": True
        }
    }

    result = run_curupira(context)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

