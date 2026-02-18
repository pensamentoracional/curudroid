
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
from datetime import datetime, timezone
from urllib import error, request

from ai.config import load_config



def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_curupira(context: dict) -> dict:
    """
    Executa o Curupira como subprocesso e normaliza a saída
    para um contrato JSON seguro.
    """
    transport = _read_transport_mode()

    if transport == "http":
        return _run_curupira_http(context)

    if transport == "subprocess":
        return _run_curupira_subprocess(context)

    # auto: tenta backend remoto primeiro e cai para subprocesso local.
    http_result = _run_curupira_http(context)
    if http_result.get("status") == "backend_unavailable":
        return _run_curupira_subprocess(context)

    return http_result


def _read_transport_mode() -> str:
    return load_config().curupira_transport


def _run_curupira_http(context: dict) -> dict:
    cfg = load_config()
    backend_url = cfg.curupira_backend_url
    timeout = cfg.curupira_backend_timeout

    if not backend_url:
        return {
            "intent": context.get("intent", "unknown"),
            "reason": "CURUPIRA_BACKEND_URL ausente",
            "confidence": 0.0,
            "source": "curupira",
            "status": "backend_unavailable",
            "ts": _utc_ts(),
        }

    payload = {
        "user_id": str(context.get("origin") or "curudroid"),
        "message": str(context.get("intent") or "unknown"),
        "context": context,
    }

    req = request.Request(
        f"{backend_url}/api/message",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except error.URLError as exc:
        return {
            "intent": context.get("intent", "unknown"),
            "reason": f"Falha ao conectar backend Curupira: {exc}",
            "confidence": 0.0,
            "source": "curupira",
            "status": "backend_unavailable",
            "ts": _utc_ts(),
        }
    except Exception as exc:
        return {
            "intent": context.get("intent", "unknown"),
            "reason": f"Erro HTTP no backend Curupira: {exc}",
            "confidence": 0.0,
            "source": "curupira",
            "status": "backend_error",
            "ts": _utc_ts(),
        }

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {
            "intent": context.get("intent", "unknown"),
            "reason": body[:800],
            "confidence": 0.2,
            "source": "curupira",
            "status": "backend_invalid_json",
            "ts": _utc_ts(),
        }

    return {
        "intent": context.get("intent", "unknown"),
        "reason": str(parsed.get("response") or "Sem resposta do backend"),
        "confidence": float(parsed.get("confidence", 0.6)),
        "source": "curupira",
        "status": "backend_response",
        "ts": _utc_ts(),
    }



def _run_curupira_subprocess(context: dict) -> dict:
    try:
        cfg = load_config()
        entrypoint = cfg.curupira_local_entrypoint
        result = subprocess.run(
            ["python", entrypoint],
            input=json.dumps(context),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as e:
        return {
            "intent": context.get("intent", "unknown"),
            "reason": f"Falha ao executar Curupira local ({load_config().curupira_local_entrypoint}): {e}",
            "confidence": 0.0,
            "source": "curupira",
            "status": "execution_error",
            "ts": _utc_ts(),
        }

    # Caso 1 — erro real de execução
    if result.returncode != 0:
        return {
            "intent": context.get("intent", "unknown"),
            "reason": result.stderr.strip() or "Erro desconhecido no Curupira",
            "confidence": 0.0,
            "source": "curupira",
            "status": "runtime_error",
            "ts": _utc_ts(),
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
            "ts": _utc_ts(),
        }

    # Caso 3 — Curupira respondeu JSON válido
    try:
        payload = json.loads(stdout)
        payload.setdefault("source", "curupira")
        payload.setdefault("status", "json_response")
        payload["ts"] = _utc_ts()
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
            "ts": _utc_ts(),
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
