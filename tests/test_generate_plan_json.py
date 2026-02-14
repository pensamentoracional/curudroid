import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import io
from contextlib import redirect_stdout

import ai.generate_plan as generate_plan


class GeneratePlanJsonTests(unittest.TestCase):
    def test_generated_plan_json_has_required_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            approved_dir = base / "approved"
            plans_dir = base / "plans"
            approved_dir.mkdir(parents=True, exist_ok=True)
            plans_dir.mkdir(parents=True, exist_ok=True)

            intent_payload = {"intent": "scan_logs"}
            (approved_dir / "20260101T000000.json").write_text(
                json.dumps(intent_payload), encoding="utf-8"
            )

            with mock.patch.object(generate_plan, "APPROVED_DIR", approved_dir), mock.patch.object(
                generate_plan, "INTENTS_DIR", approved_dir
            ), mock.patch.object(generate_plan, "PLANS_DIR", plans_dir):
                with redirect_stdout(io.StringIO()):
                    generate_plan.generate_plan()

            json_files = sorted(plans_dir.glob("*.json"))
            self.assertTrue(json_files, "Deve gerar ao menos um plan.json")

            payload = json.loads(json_files[-1].read_text(encoding="utf-8"))
            self.assertIsInstance(payload, dict)
            self.assertIn("risk_estimate", payload)
            self.assertIsInstance(payload["risk_estimate"], (int, float))
            self.assertIn("commands", payload)
            self.assertIsInstance(payload["commands"], list)

            for command in payload["commands"]:
                self.assertIsInstance(command, dict)
                self.assertIn("argv", command)
                self.assertIn("description", command)
                self.assertIsInstance(command["argv"], list)
                self.assertTrue(all(isinstance(i, str) for i in command["argv"]))
                self.assertIsInstance(command["description"], str)


if __name__ == "__main__":
    unittest.main()
