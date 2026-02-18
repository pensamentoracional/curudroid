import os
import unittest
from unittest import mock

from ai.config import AppConfig, config_summary, load_config, validate_config


class ConfigTests(unittest.TestCase):
    def test_validate_config_returns_stable_tuple_lists(self):
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

        result = validate_config(cfg)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        errors, warnings = result
        self.assertIsInstance(errors, list)
        self.assertIsInstance(warnings, list)
        self.assertEqual(errors, [])
        self.assertTrue(any("Telegram: DESATIVADO" in w for w in warnings))
        self.assertTrue(any("IA: DESATIVADA" in w for w in warnings))

    def test_invalid_log_level_is_blocking_error(self):
        cfg = AppConfig(
            log_level="LOUD",
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
        errors, warnings = validate_config(cfg)
        self.assertTrue(any("LOG_LEVEL inválido" in e for e in errors))
        self.assertIsInstance(warnings, list)

    def test_config_summary_masks_secrets(self):
        cfg = AppConfig(
            log_level="INFO",
            ai_provider="openai",
            ai_api_key="sk-supersecret",
            telegram_token="123456:abcDEF",
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
        summary = config_summary(cfg)
        self.assertNotIn("sk-supersecret", summary)
        self.assertNotIn("123456:abcDEF", summary)
        self.assertIn("AI_API_KEY=sk-***et", summary)

    def test_load_config_defaults(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = load_config()
        self.assertEqual(cfg.log_level, "INFO")
        self.assertEqual(cfg.ai_provider, "none")
        self.assertEqual(cfg.ai_api_key, "")
        self.assertEqual(cfg.telegram_token, "")

    def test_http_transport_without_backend_url_emits_warning(self):
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
            curupira_transport="http",
            curupira_backend_url="",
            curupira_backend_timeout=5.0,
        )

        errors, warnings = validate_config(cfg)
        self.assertEqual(errors, [])
        self.assertTrue(any("CURUPIRA_BACKEND_URL ausente" in w for w in warnings))

    def test_load_config_reads_curupira_transport_fields(self):
        with mock.patch.dict(
            os.environ,
            {
                "CURUPIRA_TRANSPORT": "http",
                "CURUPIRA_BACKEND_URL": "http://192.168.1.10:8000/",
                "CURUPIRA_BACKEND_TIMEOUT": "9",
            },
            clear=True,
        ):
            cfg = load_config()

        self.assertEqual(cfg.curupira_transport, "http")
        self.assertEqual(cfg.curupira_backend_url, "http://192.168.1.10:8000")
        self.assertEqual(cfg.curupira_backend_timeout, 9.0)


if __name__ == "__main__":
    unittest.main()
