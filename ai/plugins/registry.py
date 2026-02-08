"""Registry e loader de plugins com validação de contrato."""

from __future__ import annotations

import importlib
import os
import pkgutil
from dataclasses import dataclass
from enum import Enum
from typing import List

from ai.plugins.contracts import PluginSpec


class PluginStatus(str, Enum):
    OK = "OK"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


@dataclass
class PluginValidationResult:
    module_name: str
    status: PluginStatus
    plugin_id: str
    core: bool
    reason: str = ""


@dataclass
class PluginRegistryReport:
    results: List[PluginValidationResult]

    @property
    def has_core_errors(self) -> bool:
        for result in self.results:
            if result.core and result.status in {PluginStatus.ERROR, PluginStatus.DISABLED}:
                return True
        return False


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
                    core=True,
                    reason=f"Falha ao descobrir plugins: {exc}",
                )
            ]
        )

    if not module_names:
        return PluginRegistryReport(results=[])

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
            core=False,
            status=PluginStatus.ERROR,
            reason=f"Falha ao importar: {exc}",
        )

    spec = getattr(module, "PLUGIN_SPEC", None)
    spec_error = _validate_spec(spec)
    if spec_error:
        return PluginValidationResult(
            module_name=module_name,
            plugin_id=module_name,
            core=False,
            status=PluginStatus.ERROR,
            reason=spec_error,
        )

    method_error = _validate_methods(module)
    if method_error:
        return PluginValidationResult(
            module_name=module_name,
            plugin_id=spec.plugin_id,
            core=spec.core,
            status=PluginStatus.ERROR,
            reason=method_error,
        )

    missing_env = [var for var in spec.required_env if not os.getenv(var)]
    if missing_env:
        return PluginValidationResult(
            module_name=module_name,
            plugin_id=spec.plugin_id,
            core=spec.core,
            status=PluginStatus.DISABLED,
            reason=f"faltam env vars: {', '.join(missing_env)}",
        )

    try:
        ok, details = module.healthcheck()
    except Exception as exc:
        return PluginValidationResult(
            module_name=module_name,
            plugin_id=spec.plugin_id,
            core=spec.core,
            status=PluginStatus.ERROR,
            reason=f"healthcheck falhou: {exc}",
        )

    if not isinstance(ok, bool) or not isinstance(details, str):
        return PluginValidationResult(
            module_name=module_name,
            plugin_id=spec.plugin_id,
            core=spec.core,
            status=PluginStatus.ERROR,
            reason="healthcheck deve retornar (bool, str)",
        )

    if not ok:
        return PluginValidationResult(
            module_name=module_name,
            plugin_id=spec.plugin_id,
            core=spec.core,
            status=PluginStatus.ERROR,
            reason=details or "healthcheck retornou falha",
        )

    return PluginValidationResult(
        module_name=module_name,
        plugin_id=spec.plugin_id,
        core=spec.core,
        status=PluginStatus.OK,
        reason=details or "plugin válido",
    )


def _validate_spec(spec) -> str | None:
    if spec is None:
        return "PLUGIN_SPEC ausente"
    if not isinstance(spec, PluginSpec):
        return "PLUGIN_SPEC inválido (esperado PluginSpec)"
    if not isinstance(spec.plugin_id, str) or not spec.plugin_id:
        return "plugin_id inválido"
    if not isinstance(spec.plugin_version, str) or not spec.plugin_version:
        return "plugin_version inválido"
    if not isinstance(spec.required_env, list) or not all(isinstance(i, str) for i in spec.required_env):
        return "required_env inválido (esperado list[str])"
    if not isinstance(spec.capabilities, list) or not all(isinstance(i, str) for i in spec.capabilities):
        return "capabilities inválido (esperado list[str])"
    if not isinstance(spec.core, bool):
        return "core inválido (esperado bool)"
    return None


def _validate_methods(module) -> str | None:
    for method_name in ("init", "healthcheck"):
        method = getattr(module, method_name, None)
        if method is None or not callable(method):
            return f"método obrigatório ausente: {method_name}"
    return None
