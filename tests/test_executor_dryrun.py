import json
import tempfile
import unittest
from pathlib import Path

from ai.executor import execute_plan


class ExecutorDryRunTests(unittest.TestCase):
    def _build_plan(self, root: Path, *, risk: float = 0.2, command: list[str] | None = None) -> Path:
        approved = root / "ai" / "approved"
        plans = root / "ai" / "plans"
        approved.mkdir(parents=True, exist_ok=True)
        plans.mkdir(parents=True, exist_ok=True)

        intent_file = approved / "20260214T000000.json"
        intent_file.write_text(json.dumps({"intent": "scan_logs"}), encoding="utf-8")

        payload = {
            "plan_id": "20260214T000000_scan_logs.json",
            "version": 1,
            "intent_path": "ai/approved/20260214T000000.json",
            "risk_estimate": risk,
            "commands": [
                {
                    "argv": command or ["tail", "-n", "50", "logs/curudroid.log"],
                    "description": "Inspect recent logs",
                }
            ],
            "assumptions": ["Somente leitura"],
        }

        plan_path = plans / payload["plan_id"]
        plan_path.write_text(json.dumps(payload), encoding="utf-8")
        return plan_path

    def test_dry_run_writes_result_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = self._build_plan(root)

            exit_code, payload, _ = execute_plan(
                plan_path,
                apply=False,
                repo_root=root,
                results_dir=root / "ai" / "results",
                log_file=root / "logs" / "curudroid.log",
                threshold=0.4,
            )

            self.assertEqual(exit_code, 0)
            self.assertIsNotNone(payload)
            self.assertEqual(payload["mode"], "dry-run")
            self.assertEqual(payload["status"], "simulated")

            result_files = list((root / "ai" / "results").glob("*/result.json"))
            self.assertTrue(result_files)

    def test_abort_when_risk_above_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = self._build_plan(root, risk=0.9)

            exit_code, payload, message = execute_plan(
                plan_path,
                apply=False,
                repo_root=root,
                results_dir=root / "ai" / "results",
                log_file=root / "logs" / "curudroid.log",
                threshold=0.4,
            )

            self.assertEqual(exit_code, 1)
            self.assertIsNone(payload)
            self.assertIn("acima do limiar", message)

    def test_abort_when_command_outside_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = self._build_plan(root, command=["rm", "-rf", "/tmp/a"])

            exit_code, payload, message = execute_plan(
                plan_path,
                apply=False,
                repo_root=root,
                results_dir=root / "ai" / "results",
                log_file=root / "logs" / "curudroid.log",
                threshold=0.4,
            )

            self.assertEqual(exit_code, 1)
            self.assertIsNone(payload)
            self.assertIn("comando proibido", message)


if __name__ == "__main__":
    unittest.main()
