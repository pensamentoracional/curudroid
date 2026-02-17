from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    provider_name: str
    model_name: str

    def recommend(self, plan: dict, context: dict) -> dict | None:
        ...
