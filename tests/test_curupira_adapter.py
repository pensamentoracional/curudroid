import io
import json
import unittest
from unittest import mock

from ai.curupira_adapter import run_curupira


class CurupiraAdapterTests(unittest.TestCase):
    def test_http_mode_without_backend_url_returns_backend_unavailable(self):
        context = {"intent": "scan_logs", "origin": "android"}

        with mock.patch.dict("os.environ", {"CURUPIRA_TRANSPORT": "http"}, clear=True):
            result = run_curupira(context)

        self.assertEqual(result["status"], "backend_unavailable")
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["intent"], "scan_logs")

    def test_http_mode_returns_backend_response(self):
        context = {"intent": "scan_logs", "origin": "android"}
        backend_payload = {"status": "ok", "response": "Tudo certo", "confidence": 0.9}

        mocked_response = io.BytesIO(json.dumps(backend_payload).encode("utf-8"))

        class _Ctx:
            def __enter__(self_inner):
                return mocked_response

            def __exit__(self_inner, exc_type, exc, tb):
                return False

        with (
            mock.patch.dict(
                "os.environ",
                {
                    "CURUPIRA_TRANSPORT": "http",
                    "CURUPIRA_BACKEND_URL": "http://127.0.0.1:8000",
                },
                clear=True,
            ),
            mock.patch("urllib.request.urlopen", return_value=_Ctx()),
        ):
            result = run_curupira(context)

        self.assertEqual(result["status"], "backend_response")
        self.assertEqual(result["reason"], "Tudo certo")
        self.assertEqual(result["confidence"], 0.9)

    def test_auto_mode_falls_back_to_subprocess_when_backend_unavailable(self):
        context = {"intent": "scan_logs", "origin": "android"}

        completed = mock.Mock(returncode=0, stdout="", stderr="")

        with (
            mock.patch.dict("os.environ", {"CURUPIRA_TRANSPORT": "auto"}, clear=True),
            mock.patch("subprocess.run", return_value=completed) as run_mock,
        ):
            result = run_curupira(context)

        self.assertEqual(result["status"], "no_opinion")
        run_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
