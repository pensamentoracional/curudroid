from dataclasses import dataclass
from core.observability import log_decision, increment_metric

@dataclass
class AutonomyDecision:
    allowed: bool
    reason: str
    max_mode: str  # "none", "dry-run"


class AutonomySupervisor:
    def __init__(self, risk_threshold: float):
        self.risk_threshold = risk_threshold

    def evaluate(self, plan: dict) -> AutonomyDecision:
        if "risk_score" not in plan:
            decision = AutonomyDecision(
                allowed=False,
                reason="Missing risk_score field",
                max_mode="none",
            )
            log_decision({
                "component": "supervisor",
                "plan_id": plan.get("id"),
                "risk_score": plan.get("risk_score"),
                "allowed": decision.allowed,
                "reason": decision.reason
            })
            increment_metric("supervisor_blocked")
            return decision

        try:
            risk_value = float(plan["risk_score"]) / 10.0
        except Exception:
            decision = AutonomyDecision(
                allowed=False,
                reason="Invalid risk_score format",
                max_mode="none",
            )
            log_decision({
                "component": "supervisor",
                "plan_id": plan.get("id"),
                "risk_score": plan.get("risk_score"),
                "allowed": decision.allowed,
                "reason": decision.reason
            })
            increment_metric("supervisor_blocked")
            return decision

        if risk_value > self.risk_threshold:
            decision = AutonomyDecision(
                allowed=False,
                reason="Risk above autonomy threshold",
                max_mode="none",
            )
            log_decision({
                "component": "supervisor",
                "plan_id": plan.get("id"),
                "risk_score": plan.get("risk_score"),
                "allowed": decision.allowed,
                "reason": decision.reason
            })
            increment_metric("supervisor_blocked")
            return decision

        decision = AutonomyDecision(
            allowed=True,
            reason="Risk within autonomy threshold",
            max_mode="dry-run",
        )

        increment_metric("supervisor_allowed")
        log_decision({
            "component": "supervisor",
            "plan_id": plan.get("id"),
            "risk_score": plan.get("risk_score"),
            "allowed": decision.allowed,
            "reason": decision.reason
        })

        return decision
