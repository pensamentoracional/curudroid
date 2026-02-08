import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import io
from contextlib import redirect_stdout

import ai.generate_plan as generate_plan


class GeneratePlanContractTests(unittest.TestCase):
    def test_generated_plan_contains_essential_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            intents_dir = base / "intents"
            plans_dir = base / "plans"
            intents_dir.mkdir(parents=True, exist_ok=True)
            plans_dir.mkdir(parents=True, exist_ok=True)

            intent_payload = {"intent": "scan_logs"}
            (intents_dir / "20260101T000000.json").write_text(
                json.dumps(intent_payload), encoding="utf-8"
            )

            with mock.patch.object(generate_plan, "INTENTS_DIR", intents_dir), mock.patch.object(
                generate_plan, "PLANS_DIR", plans_dir
            ):
                with redirect_stdout(io.StringIO()):
                    generate_plan.generate_plan()

            plan_files = sorted(plans_dir.glob("*.plan"))
            self.assertTrue(plan_files, "Deve gerar ao menos um arquivo de plano")

            content = plan_files[-1].read_text(encoding="utf-8")
            self.assertIn("# RISCO ESTIMADO:", content)
            self.assertIn("# LIMIAR CURUPIRA:", content)
            self.assertIn("# Intenção: scan_logs", content)
            self.assertIn("# Plano sugerido (DRY-RUN)", content)


if __name__ == "__main__":
    unittest.main()
