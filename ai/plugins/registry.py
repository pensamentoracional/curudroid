"""Registry e validação de contrato mínimo de plugins."""

from __future__ import annotations

import importlib
import inspect
import os
import pkgutil
from dataclasses import dataclass
from enum import Enum
from typing import List

from ai.plugins.contracts import is_valid_run_result


class PluginStatus(str, Enum):
    OK = "OK"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


@dataclass
class PluginValidationResult:
    module_name: str
    status: PluginStatus
    plugin_id: str
    reason: str = ""


@dataclass
class PluginRegistryReport:
    results: List[PluginValidationResult]

    @property
    def summary_lines(self) -> list[str]:
        return [f"{r.plugin_id} | {r.status.value} | {r.reason or '-'}" for r in self.results]


def discover_plugin_modules() -> List[str]:
    plugins_pkg = importlib.import_module("ai.plugins")
    skip = {"contracts", "registry"}
    return sorted(
        f"ai.plugins.{m.name}"
        for m in pkgutil.iter_modules(plugins_pkg.__path__)
        if not m.name.startswith("_") and m.name not in skip
    )


def validate_plugins() -> PluginRegistryReport:
    results: List[PluginValidationResult] = []

    try:
        module_names = discover_plugin_modules()
    except Exception as exc:
        return PluginRegistryReport(
            results=[
                PluginValidationResult(
                    module_name="ai.plugins",
                    plugin_id="ai.plugins",
                    status=PluginStatus.ERROR,
                    reason=f"Falha ao descobrir plugins: {exc}",
                )
            ]
        )

    for module_name in module_names:
        results.append(_validate_module(module_name))

    return PluginRegistryReport(results=results)


def _validate_module(module_name: str) -> PluginValidationResult:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return PluginValidationResult(
            module_name=module_name,
            plugin_id=module_name,
            status=PluginStatus.ERROR,
            reason=f"Falha ao importar: {exc}",
        )

    plugin_id = getattr(module, "plugin_id", module_name)
    version = getattr(module, "version", None)

    if not isinstance(plugin_id, str) or not plugin_id:
        return PluginValidationResult(module_name, PluginStatus.ERROR, module_name, "plugin_id inválido")

    if not isinstance(version, str) or not version:
        return PluginValidationResult(module_name, PluginStatus.ERROR, plugin_id, "version inválido")

    if not hasattr(module, "required_env_vars"):
        return PluginValidationResult(
            module_name, PluginStatus.DISABLED, plugin_id, "required_env_vars ausente"
        )

    required_env_vars = getattr(module, "required_env_vars")
    if not isinstance(required_env_vars, list) or not all(
        isinstance(item, str) for item in required_env_vars
    ):
        return PluginValidationResult(
            module_name,
            PluginStatus.ERROR,
            plugin_id,
            "required_env_vars inválido (esperado list[str])",
        )

    run_func = getattr(module, "run", None)
    if run_func is None or not callable(run_func):
        return PluginValidationResult(module_name, PluginStatus.ERROR, plugin_id, "run() ausente")

    sig = inspect.signature(run_func)
    if len(sig.parameters) != 1 or "intent" not in sig.parameters:
        return PluginValidationResult(
            module_name,
            PluginStatus.ERROR,
            plugin_id,
            "assinatura inválida em run(intent: dict)",
        )

    missing_env = [var for var in required_env_vars if not os.getenv(var)]
    if missing_env:
        return PluginValidationResult(
            module_name,
            PluginStatus.DISABLED,
            plugin_id,
            f"faltam env vars: {', '.join(missing_env)}",
        )

    try:
        sample_result = run_func({"intent": plugin_id, "_contract_check": True})
    except Exception as exc:
        return PluginValidationResult(
            module_name,
            PluginStatus.ERROR,
            plugin_id,
            f"run() falhou na validação: {exc}",
        )

    ok, reason = is_valid_run_result(sample_result)
    if not ok:
        return PluginValidationResult(module_name, PluginStatus.ERROR, plugin_id, reason)

    return PluginValidationResult(module_name, PluginStatus.OK, plugin_id, "contrato válido")
