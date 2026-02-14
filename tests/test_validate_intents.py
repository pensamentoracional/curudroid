import unittest

from ai.validate_intents import load_schema, validate_intent_payload


class ValidateIntentsTests(unittest.TestCase):
    def test_intent_with_existing_plugin_is_recognized(self):
        schema = load_schema()
        payload = {
            "intent": "scan_logs",
            "reason": "Analisar o log principal",
            "confidence": 0.7,
            "created_at": "2026-02-08T10:00:00+00:00",
        }
        ok, reason = validate_intent_payload(payload, schema, {"scan_logs", "health_check"})
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_intent_without_plugin_is_rejected(self):
        schema = load_schema()
        payload = {
            "intent": "health_check",
            "reason": "Checar sinais básicos",
            "confidence": 0.8,
            "created_at": "2026-02-08T10:00:00+00:00",
        }
        ok, reason = validate_intent_payload(payload, schema, {"scan_logs"})
        self.assertFalse(ok)
        self.assertIn("sem plugin mapeado", reason)


if __name__ == "__main__":
    unittest.main()
