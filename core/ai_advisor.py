from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from ai.config import AppConfig
from core.ai_providers import NullProvider, OpenAIProvider
from core.observability import load_last_decisions, load_metrics, log_decision

_ALLOWED_ACTIONS = {"dry_run", "block", "review", "proceed"}
_ALLOWED_RISK_LEVELS = {"low", "medium", "high"}


@dataclass(frozen=True)
class AIRecommendation:
    suggested_action: str
    risk_assessment: dict
    confidence: float
    explanation: str
    provider: str
    model: str
    timestamp: str


class AIAdvisor:
    def __init__(self, provider) -> None:
        self.provider = provider

    @classmethod
    def from_config(cls, config: AppConfig) -> "AIAdvisor":
        provider_name = (config.ai_provider or "none").strip().lower()

        if provider_name == "openai":
            model = (os.getenv("AI_MODEL") or "gpt-4o-mini").strip()
            timeout = _read_timeout_seconds()
            return cls(
                OpenAIProvider(
                    api_key=config.ai_api_key,
                    model=model,
                    timeout_seconds=timeout,
                )
            )

        elif provider_name == "openclaw":
            from core.ai_providers.openclaw_provider import OpenClawProvider
            return cls(OpenClawProvider(config))
        elif provider_name == "none":
            return cls(NullProvider())


    def analyze(self, plan: dict, context: dict) -> dict | None:
        started = time.perf_counter()

        if self.provider.provider_name == "none":
            return None

        try:
            sanitized_plan = _sanitize_plan(plan)
            sanitized_context = _sanitize_context(context)
            raw = self.provider.recommend(sanitized_plan, sanitized_context)

            if raw is None:
                self._log("no_recommendation", plan, started)
                return None

            recommendation = _normalize(raw, self.provider.provider_name, self.provider.model_name)
            payload = asdict(recommendation)

            self._log(
                "success",
                plan,
                started,
                payload,
                input_hash=_stable_hash({"plan": sanitized_plan, "context": sanitized_context}),
                output_hash=_stable_hash(payload),
            )

            return payload
        except Exception as exc:
            self._log("error", plan, started, error=str(exc))
            return None

    def _log(self, status: str, plan: dict, started: float, recommendation: dict | None = None, **extra) -> None:
        event = {
            "component": "ai_advisor",
            "status": status,
            "provider": self.provider.provider_name,
            "model": self.provider.model_name,
            "plan_id": plan.get("id"),
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }

        if recommendation is not None:
            event["ai_recommendation"] = recommendation

        event.update(extra)
        log_decision(event)


def build_ai_context(plan: dict, extra_context: dict | None = None) -> dict:
    context = {
        "plan_id": plan.get("id"),
        "risk_score": plan.get("risk_score"),
        "source": plan.get("source"),
        "commands_count": len(plan.get("commands", [])) if isinstance(plan.get("commands"), list) else 0,
        "last_decisions": load_last_decisions(3),
        "metrics": load_metrics(),
    }

    if extra_context:
        context["extra"] = extra_context

    return context


def _sanitize_plan(plan: dict) -> dict:
    return {
        "id": plan.get("id"),
        "schema_version": plan.get("schema_version"),
        "risk_score": plan.get("risk_score"),
        "source": plan.get("source"),
        "created_at": plan.get("created_at"),
        "commands_count": len(plan.get("commands", [])) if isinstance(plan.get("commands"), list) else 0,
    }


def _sanitize_context(context: dict) -> dict:
    safe = dict(context)
    if isinstance(safe.get("last_decisions"), list):
        safe["last_decisions"] = [
            {
                "component": item.get("component"),
                "allowed": item.get("allowed"),
                "reason": item.get("reason"),
            }
            for item in safe["last_decisions"]
        ]
    return safe


def _normalize(raw: dict, provider: str, model: str) -> AIRecommendation:
    action = str(raw.get("suggested_action") or "review").strip().lower()
    if action not in _ALLOWED_ACTIONS:
        action = "review"

    risk_raw = raw.get("risk_assessment")

    if not isinstance(risk_raw, dict):
        risk_raw = {}

    level = str(risk_raw.get("level") or "medium").strip().lower()
    if level not in _ALLOWED_RISK_LEVELS:
        level = "medium"

    score = _clamp_float(
        risk_raw.get("score"),
        0.0,
        1.0,
        0.5,
    )


    confidence = _clamp_float(raw.get("confidence"), 0.0, 1.0, 0.0)
    explanation = str(raw.get("explanation") or "Sem explicação").strip()

    return AIRecommendation(
        suggested_action=action,
        risk_assessment={"level": level, "score": score},
        confidence=confidence,
        explanation=explanation,
        provider=provider,
        model=model,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )


def _clamp_float(value, minimum: float, maximum: float, fallback: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return fallback
    return max(minimum, min(maximum, parsed))


def _stable_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_timeout_seconds() -> float:
    raw = (os.getenv("AI_TIMEOUT_SECONDS") or "5").strip()
    try:
        timeout = float(raw)
    except ValueError:
        return 5.0
    return max(0.5, min(30.0, timeout))
