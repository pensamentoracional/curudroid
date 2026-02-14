import os
import types
import unittest
from unittest import mock

from ai.plugins.registry import PluginStatus, _validate_module, validate_plugins


class PluginRegistryTests(unittest.TestCase):
    def test_optional_plugin_is_disabled_when_env_missing(self):
        with mock.patch.dict(os.environ, {"AI_PROVIDER": "", "AI_API_KEY": ""}, clear=False):
            report = validate_plugins()

        by_id = {r.plugin_id: r for r in report.results}
        self.assertIn("summarize_logs", by_id)
        self.assertEqual(by_id["summarize_logs"].status, PluginStatus.DISABLED)

    def test_core_like_plugins_are_ok(self):
        report = validate_plugins()
        by_id = {r.plugin_id: r for r in report.results}
        self.assertEqual(by_id["health_check"].status, PluginStatus.OK)
        self.assertEqual(by_id["scan_logs"].status, PluginStatus.OK)

    def test_plugin_without_run_is_error(self):
        fake_module = types.SimpleNamespace(
            plugin_id="fake",
            version="1.0",
            required_env_vars=[],
        )
        with mock.patch("ai.plugins.registry.importlib.import_module", return_value=fake_module):
            result = _validate_module("ai.plugins.fake")
        self.assertEqual(result.status, PluginStatus.ERROR)
        self.assertIn("run() ausente", result.reason)

    def test_plugin_without_required_env_vars_is_disabled(self):
        fake_module = types.SimpleNamespace(
            plugin_id="fake",
            version="1.0",
            run=lambda intent: {
                "success": True,
                "commands": [],
                "risk_estimate": 0.1,
                "assumptions": [],
            },
        )
        with mock.patch("ai.plugins.registry.importlib.import_module", return_value=fake_module):
            result = _validate_module("ai.plugins.fake")
        self.assertEqual(result.status, PluginStatus.DISABLED)
        self.assertIn("required_env_vars ausente", result.reason)


if __name__ == "__main__":
    unittest.main()
