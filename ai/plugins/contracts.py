"""Contrato mínimo de plugins do Curudroid.

Contrato simples para evitar acoplamentos implícitos e quebrar cedo no preflight.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Protocol, runtime_checkable


@dataclass(frozen=True)
class PluginSpec:
    plugin_id: str
    plugin_version: str
    required_env: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    core: bool = False


@runtime_checkable
class PluginContract(Protocol):
    PLUGIN_SPEC: PluginSpec

    def init(self, config, logger: Callable[[str], None]) -> None:
        ...

    def healthcheck(self) -> tuple[bool, str]:
        ...
