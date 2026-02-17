from core.intent_queue import IntentQueue
from core.autonomy_supervisor import AutonomySupervisor
from core.plan_validator import load_plan
from core.curupira_evaluator import CurupiraEvaluator
from core.observability import log_decision, increment_metric
from core.ai_advisor import AIAdvisor, build_ai_context

def detect_anomaly(plan: dict, decisions: list[dict]) -> bool:
    try:
        risk = float(plan.get("risk_score", 0))
    except Exception:
        return False

    if risk > 90:
        if any(d.get("allowed") for d in decisions):
            return True

    return False


class ReactiveAutonomy:
    def __init__(self, config):
        self.queue = IntentQueue()

        self.supervisor = (
            AutonomySupervisor(
                risk_threshold=config.curupira_risk_threshold
            )
            if config.supervisor_enabled
            else None
        )

        self.curupira = (
            CurupiraEvaluator(
                threshold=config.curupira_risk_threshold
            )
            if config.curupira_enabled
            else None
        )

        self.ai_advisor = AIAdvisor.from_config(config)

    def process_next_intent(self):
        intents = self.queue.load()

        # Selecionar maior prioridade pendente
        pending = [i for i in intents if i.get("status") == "pending"]

        if not pending:
            increment_metric("reactive_empty")
            log_decision({
                "component": "reactive",
                "event": "queue_empty",
            })
            return {"status": "empty"}

        # Ordenado ja na enqueue, pegar primeiro
        intent = pending[0]
        intent["status"] = "processing"
        self.queue.save(intents)

        plan_path = intent.get("plan_path")

        if not plan_path:
            intent["status"] = "error"
            self.queue.save(intents)

            increment_metric("reactive_invalid_intent")
            log_decision({
                "component": "reactive",
                "event": "invalid_intent",
                "allowed": False,
                "reason": "Missing plan_path",
            })

            return {"status": "invalid_intent"}

        try:
            plan = load_plan(plan_path)
            increment_metric("intents_processed")

            decisions_log = []

            # AI consultiva (não altera decisão oficial)
            self.ai_advisor.analyze(
                plan,
                build_ai_context(
                    plan,
                    {
                        "entrypoint": "autonomy_reactive",
                        "intent_id": intent.get("intent_id"),
                        "plan_path": plan_path,
                    },
                ),
            )

        except Exception as e:
            intent["status"] = "error"
            self.queue.save(intents)

            increment_metric("reactive_invalid_plan")
            log_decision({
                "component": "reactive",
                "event": "invalid_plan",
                "plan_path": plan_path,
                "allowed": False,
                "reason": str(e),
            })

            return {
                "status": "error",
                "reason": f"Invalid plan: {e}"
            }

        # Supervisor (se habilitado)
        supervisor_decision = None

        if self.supervisor:
            supervisor_decision = self.supervisor.evaluate(plan)

            decisions_log.append({
                "component": "supervisor",
                "allowed": supervisor_decision.allowed
            })

        if supervisor_decision and not supervisor_decision.allowed:
            intent["status"] = "blocked"
            self.queue.save(intents)

            increment_metric("intents_blocked")
            increment_metric("reactive_blocked")
            log_decision({
                "component": "reactive",
                "event": "blocked",
                "plan_id": plan.get("id"),
                "plan_path": plan_path,
                "risk_score": plan.get("risk_score"),
                "allowed": False,
                "reason": f"Supervisor: {supervisor_decision.reason}",
            })

            if detect_anomaly(plan, decisions_log):
                log_decision({
                    "component": "anomaly",
                    "plan_id": plan.get("id"),
                    "type": "high_risk_allowed"
                })
                increment_metric("anomaly_detected")

            return {
                "status": "blocked",
                "reason": f"Supervisor: {supervisor_decision.reason}",
            }

        # Curupira (se habilitado)
        curupira_decision = None

        if self.curupira:
            curupira_decision = self.curupira.evaluate(plan)

            decisions_log.append({
                "component": "curupira",
                "allowed": curupira_decision.allowed
            })

        if curupira_decision and not curupira_decision.allowed:
            intent["status"] = "blocked"
            self.queue.save(intents)

            increment_metric("intents_blocked")
            increment_metric("reactive_blocked")
            log_decision({
                "component": "reactive",
                "event": "blocked",
                "plan_id": plan.get("id"),
                "plan_path": plan_path,
                "risk_score": plan.get("risk_score"),
                "allowed": False,
                "reason": f"Curupira: {curupira_decision.reason}",
            })

            if detect_anomaly(plan, decisions_log):
                log_decision({
                    "component": "anomaly",
                    "plan_id": plan.get("id"),
                    "type": "high_risk_allowed"
                })
                increment_metric("anomaly_detected")

            return {
                "status": "blocked",
                "reason": f"Curupira: {curupira_decision.reason}",
            }

        # Se chegou aqui, passou nas duas camadas
        intent["status"] = "approved_for_dry_run"
        self.queue.save(intents)

        increment_metric("intents_dry_run")
        increment_metric("reactive_approved")
        log_decision({
            "component": "reactive",
            "event": "approved_for_dry_run",
            "plan_id": plan.get("id"),
            "plan_path": plan_path,
            "risk_score": plan.get("risk_score"),
            "allowed": True,
            "reason": "Approved for dry-run",
        })

        if detect_anomaly(plan, decisions_log):
            log_decision({
                "component": "anomaly",
                "plan_id": plan.get("id"),
                "type": "high_risk_allowed"
            })
            increment_metric("anomaly_detected")

        return {
            "status": "ready_for_dry_run",
            "plan_path": plan_path,
        }
