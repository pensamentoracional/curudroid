from __future__ import annotations


class NullProvider:
    provider_name = "none"
    model_name = "null"

    def recommend(self, plan: dict, context: dict) -> dict | None:
        del plan
        del context
        return None
