import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai.executor import execute_plan


class ExecutorApplyTests(unittest.TestCase):
    def _build_plan(self, root: Path) -> Path:
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
            "risk_estimate": 0.2,
            "commands": [
                {
                    "argv": ["tail", "-n", "50", "logs/curudroid.log"],
                    "description": "Inspect recent logs",
                }
            ],
            "assumptions": ["Somente leitura"],
        }

        plan_path = plans / payload["plan_id"]
        plan_path.write_text(json.dumps(payload), encoding="utf-8")
        return plan_path

    def test_apply_requires_confirm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = self._build_plan(root)

            exit_code, payload, message = execute_plan(
                plan_path,
                apply=True,
                input_func=lambda _: "NO",
                run_func=lambda *args, **kwargs: SimpleNamespace(returncode=0),
                repo_root=root,
                results_dir=root / "ai" / "results",
                log_file=root / "logs" / "curudroid.log",
                threshold=0.4,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["status"], "aborted")
            self.assertIn("confirmação", message)

    def test_apply_executes_with_shell_false_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = self._build_plan(root)
            calls = []

            def fake_run(*args, **kwargs):
                calls.append((args, kwargs))
                return SimpleNamespace(returncode=0)

            exit_code, payload, _ = execute_plan(
                plan_path,
                apply=True,
                input_func=lambda _: "CONFIRM",
                run_func=fake_run,
                repo_root=root,
                results_dir=root / "ai" / "results",
                log_file=root / "logs" / "curudroid.log",
                threshold=0.4,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["mode"], "apply")
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(len(calls), 1)
            _, kwargs = calls[0]
            self.assertFalse(kwargs["shell"])

            result_files = list((root / "ai" / "results").glob("*/result.json"))
            self.assertTrue(result_files)


if __name__ == "__main__":
    unittest.main()
