import unittest
from unittest import mock

from ai.config import AppConfig
from core.ai_advisor import AIAdvisor


class _FakeProvider:
    provider_name = "fake"
    model_name = "fake-model"

    def recommend(self, plan: dict, context: dict) -> dict | None:
        del plan
        del context
        return {
            "suggested_action": "INVALID_ACTION",
            "risk_assessment": {"level": "extreme", "score": 99},
            "confidence": 42,
            "explanation": "ok",
        }


class AIAdvisorTests(unittest.TestCase):
    def test_none_provider_returns_none_and_does_not_log(self):
        cfg = AppConfig(
            log_level="INFO",
            ai_provider="none",
            ai_api_key="",
            telegram_token="",
            curupira_risk_threshold=0.4,
            log_dir="logs",
            data_dir="data",
            supervisor_enabled=True,
            curupira_enabled=True,
            autonomy_reactive_enabled=False,
            curupira_transport="subprocess",
            curupira_backend_url="",
            curupira_backend_timeout=5.0,
            curupira_local_entrypoint="external/curupira/agent.py",
        )

        advisor = AIAdvisor.from_config(cfg)

        with mock.patch("core.ai_advisor.log_decision") as log_mock:
            result = advisor.analyze({"id": "p1"}, {})

        self.assertIsNone(result)
        log_mock.assert_not_called()

    def test_output_is_normalized_and_logged(self):
        advisor = AIAdvisor(provider=_FakeProvider())

        with mock.patch("core.ai_advisor.log_decision") as log_mock:
            result = advisor.analyze({"id": "p1", "commands": []}, {})

        self.assertEqual(result["suggested_action"], "review")
        self.assertEqual(result["risk_assessment"]["level"], "medium")
        self.assertEqual(result["risk_assessment"]["score"], 1.0)
        self.assertEqual(result["confidence"], 1.0)
        self.assertEqual(log_mock.call_args[0][0]["component"], "ai_advisor")
        self.assertEqual(log_mock.call_args[0][0]["status"], "success")


if __name__ == "__main__":
    unittest.main()
