import os
import unittest
from unittest import mock

from ai.plugins.registry import PluginStatus, validate_plugins


class PluginRegistryTests(unittest.TestCase):
    def test_optional_plugin_is_disabled_when_env_missing(self):
        with mock.patch.dict(os.environ, {"AI_PROVIDER": "", "AI_API_KEY": ""}, clear=False):
            report = validate_plugins()

        by_id = {r.plugin_id: r for r in report.results}
        self.assertIn("summarize_logs", by_id, "summarize_logs deve ser descoberto")
        self.assertEqual(
            by_id["summarize_logs"].status,
            PluginStatus.DISABLED,
            "Plugin opcional deve ficar DISABLED sem env vars",
        )
        self.assertIn("faltam env vars", by_id["summarize_logs"].reason)

    def test_core_plugins_are_ok_in_default_env(self):
        report = validate_plugins()
        by_id = {r.plugin_id: r for r in report.results}
        self.assertEqual(by_id["health_check"].status, PluginStatus.OK)
        self.assertEqual(by_id["scan_logs"].status, PluginStatus.OK)


if __name__ == "__main__":
    unittest.main()
