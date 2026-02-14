"""Rotina de preflight do Curudroid."""

from __future__ import annotations

import importlib
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List

from ai.config import AppConfig, config_summary, load_config, validate_config
from ai.plugins.registry import PluginStatus, validate_plugins


@dataclass
class PreflightReport:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    infos: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def run_preflight(config: AppConfig | None = None) -> PreflightReport:
    cfg = config or load_config()
    report = PreflightReport()

    _check_python(report)
    _check_directories(cfg, report)
    _check_config(cfg, report)
    _check_plugins(report)
    _check_deprecations(report)

    report.infos.append(config_summary(cfg))
    return report


def _check_python(report: PreflightReport) -> None:
    min_v = (3, 10)
    if sys.version_info < min_v:
        report.errors.append(
            f"Python incompatível: encontrado {sys.version.split()[0]}, mínimo 3.10"
        )
    else:
        report.infos.append(f"Python OK: {sys.version.split()[0]}")


def _check_directories(config: AppConfig, report: PreflightReport) -> None:
    for name, raw_path in (("logs", config.log_dir), ("data", config.data_dir)):
        p = Path(raw_path)
        try:
            p.mkdir(parents=True, exist_ok=True)
            test_file = p / ".preflight_write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            report.infos.append(f"Diretório OK: {name} ({p})")
        except Exception as exc:
            report.errors.append(f"Sem acesso ao diretório '{name}' ({p}): {exc}")


def _check_config(config: AppConfig, report: PreflightReport) -> None:
    errors, warns = validate_config(config)
    report.errors.extend(errors)
    report.warnings.extend(warns)


def _check_plugins(report: PreflightReport) -> None:
    registry_report = validate_plugins()
    if not registry_report.results:
        report.warnings.append("Nenhum plugin encontrado em ai/plugins")
        return

    for line in registry_report.summary_lines:
        report.infos.append(f"Plugin {line}")

    for result in registry_report.results:
        if result.status == PluginStatus.DISABLED:
            report.warnings.append(f"Plugin {result.plugin_id}: DISABLED ({result.reason})")
        elif result.status == PluginStatus.ERROR:
            report.errors.append(f"Plugin {result.plugin_id}: ERROR ({result.reason})")


def _check_deprecations(report: PreflightReport) -> None:
    modules_to_probe = [
        "ai.generate_plan",
        "ai.curupira_adapter",
    ]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("default", DeprecationWarning)
        for mod_name in modules_to_probe:
            try:
                importlib.import_module(mod_name)
            except Exception:
                # Erros de import reais já aparecem em outros checks.
                pass

    for warning_item in caught:
        if issubclass(warning_item.category, DeprecationWarning):
            report.warnings.append(
                "DeprecationWarning: "
                f"{warning_item.message} "
                f"({warning_item.filename}:{warning_item.lineno})"
            )


def emit_report(report: PreflightReport, log_func: Callable[[str], None] = print) -> int:
    for info in report.infos:
        log_func(f"INFO {info}")
    for warning in report.warnings:
        log_func(f"WARN {warning}")
    for error in report.errors:
        log_func(f"ERROR {error}")

    if report.ok:
        log_func("INFO Preflight: OK")
        return 0

    log_func("ERROR Preflight: FALHOU")
    return 1


def main() -> int:
    report = run_preflight()
    return emit_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
