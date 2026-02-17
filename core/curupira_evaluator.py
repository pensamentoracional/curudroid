from dataclasses import dataclass
from core.observability import log_decision, increment_metric


@dataclass
class CurupiraDecision:
    allowed: bool
    reason: str


class CurupiraEvaluator:
    """
    Segunda camada de avaliaao de risco.
    Atua como avaliador independente.
    """

    def __init__(self, threshold: float):
        self.threshold = threshold

    def evaluate(self, plan: dict) -> CurupiraDecision:
        if "risk_score" not in plan:
            decision = CurupiraDecision(
                allowed=False,
                reason="Missing risk_score field",
            )
            log_decision({
                "component": "curupira",
                "plan_id": plan.get("id"),
                "risk_score": plan.get("risk_score"),
                "allowed": decision.allowed,
                "reason": decision.reason,
            })
            increment_metric("curupira_blocked")
            return decision

        try:
            risk_value = float(plan["risk_score"]) / 10.0
        except Exception:
            decision = CurupiraDecision(
                allowed=False,
                reason="Invalid risk score format"
            )
            log_decision({
                "component": "curupira",
                "plan_id": plan.get("id"),
                "risk_score": plan.get("risk_score"),
                "allowed": decision.allowed,
                "reason": decision.reason,
            })
            increment_metric("curupira_blocked")
            return decision

        adjusted_threshold = self.threshold * 0.8

        if risk_value > adjusted_threshold:
            decision = CurupiraDecision(
                allowed=False,
                reason="Curupira flagged elevated risk"
            )
            log_decision({
                "component": "curupira",
                "plan_id": plan.get("id"),
                "risk_score": plan.get("risk_score"),
                "allowed": decision.allowed,
                "reason": decision.reason,
            })
            increment_metric("curupira_blocked")
            return decision

        decision = CurupiraDecision(
            allowed=True,
            reason="Curupira cleared plan"
        )

        increment_metric("curupira_allowed")
        log_decision({
            "component": "curupira",
            "plan_id": plan.get("id"),
            "risk_score": plan.get("risk_score"),
            "allowed": decision.allowed,
            "reason": decision.reason,
        })

        return decision
