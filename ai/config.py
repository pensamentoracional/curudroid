"""Configuração central do Curudroid.

Mantém defaults seguros e validações leves para ambiente Termux/Android.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# Fonte canônica de default; valor efetivo vem de AppConfig em runtime.
DEFAULT_CURUPIRA_RISK_THRESHOLD = 0.4
DEFAULT_SUPERVISOR_ENABLED = True
DEFAULT_CURUPIRA_ENABLED = True
DEFAULT_AUTONOMY_REACTIVE_ENABLED = False


@dataclass(frozen=True)
class AppConfig:
    log_level: str
    ai_provider: str
    ai_api_key: str
    telegram_token: str
    curupira_risk_threshold: float
    log_dir: str
    data_dir: str
    supervisor_enabled: bool
    curupira_enabled: bool
    autonomy_reactive_enabled: bool


def _read_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default

def _read_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()

    if not raw:
        return default

    if raw in {"1", "true", "yes", "on"}:
        return True

    if raw in {"0", "false", "no", "off"}:
        return False

    return default

def load_config() -> AppConfig:
    """Lê variáveis de ambiente com defaults conservadores."""
    return AppConfig(
        log_level=(os.getenv("LOG_LEVEL") or "INFO").strip().upper(),
        ai_provider=(os.getenv("AI_PROVIDER") or "none").strip().lower(),
        ai_api_key=(os.getenv("AI_API_KEY") or "").strip(),
        telegram_token=(os.getenv("TELEGRAM_TOKEN") or "").strip(),
        curupira_risk_threshold=_read_float(
            "CURUPIRA_RISK_THRESHOLD", DEFAULT_CURUPIRA_RISK_THRESHOLD
        ),
        log_dir=(os.getenv("LOG_DIR") or "logs").strip(),
        data_dir=(os.getenv("DATA_DIR") or "data").strip(),

        supervisor_enabled=_read_bool(
            "SUPERVISOR_ENABLED",
            DEFAULT_SUPERVISOR_ENABLED
        ),

        curupira_enabled=_read_bool(
            "CURUPIRA_ENABLED",
            DEFAULT_CURUPIRA_ENABLED
        ),

        autonomy_reactive_enabled=_read_bool(
            "AUTONOMY_REACTIVE_ENABLED",
            DEFAULT_AUTONOMY_REACTIVE_ENABLED
        ),
    )


def mask_secret(value: str) -> str:
    if not value:
        return "(ausente)"
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}***{value[-2:]}"


def validate_config(config: AppConfig) -> tuple[List[str], List[str]]:
    """Retorna (erros, avisos).

    Erros: apenas inconsistências que podem quebrar o core.
    Avisos: integrações opcionais ausentes ou parcialmente configuradas.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if config.log_level not in _ALLOWED_LOG_LEVELS:
        errors.append(f"LOG_LEVEL inválido: {config.log_level}")

    if not (0.0 <= config.curupira_risk_threshold <= 1.0):
        errors.append(
            "CURUPIRA_RISK_THRESHOLD inválido: esperado valor entre 0.0 e 1.0"
        )

    if config.ai_provider in {"none", "", "disabled", "off"}:
        warnings.append("IA: DESATIVADA (AI_PROVIDER não configurado)")
    elif not config.ai_api_key:
        warnings.append(
            f"IA: DESATIVADA (AI_API_KEY ausente para provider '{config.ai_provider}')"
        )

    if not config.telegram_token:
        warnings.append("Telegram: DESATIVADO (TELEGRAM_TOKEN ausente)")

    return errors, warnings


def config_summary(config: AppConfig) -> str:
    """Resumo legível e seguro para logs."""
    return (
        "Config: "
        f"LOG_LEVEL={config.log_level}, "
        f"AI_PROVIDER={config.ai_provider}, "
        f"AI_API_KEY={mask_secret(config.ai_api_key)}, "
        f"TELEGRAM_TOKEN={mask_secret(config.telegram_token)}, "
        f"CURUPIRA_RISK_THRESHOLD={config.curupira_risk_threshold}, "
        f"LOG_DIR={config.log_dir}, DATA_DIR={config.data_dir}"
    )


# Compatibilidade legada sem side-effect em import-time.
CURUPIRA_RISK_THRESHOLD = DEFAULT_CURUPIRA_RISK_THRESHOLD
