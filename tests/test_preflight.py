import unittest

from ai.config import AppConfig
from ai.preflight import emit_report, run_preflight


class PreflightTests(unittest.TestCase):
    def test_preflight_report_ok_and_exit_code_zero_with_default_config(self):
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
        )
        report = run_preflight(cfg)
        exit_code = emit_report(report, log_func=lambda _: None)
        self.assertEqual(exit_code, 0)
        self.assertTrue(report.ok)

    def test_preflight_exit_code_non_zero_when_blocking_error(self):
        cfg = AppConfig(
            log_level="INVALID",
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
        )
        report = run_preflight(cfg)
        exit_code = emit_report(report, log_func=lambda _: None)
        self.assertNotEqual(exit_code, 0)
        self.assertFalse(report.ok)
        self.assertTrue(any("LOG_LEVEL inválido" in e for e in report.errors))


if __name__ == "__main__":
    unittest.main()
