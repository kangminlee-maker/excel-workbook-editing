from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "mcp"))

from sheets_bridge.chatgpt_web_smoke import run_chatgpt_web_smoke  # noqa: E402
from sheets_bridge.http_server import make_http_server  # noqa: E402


class ChatGptWebSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.server = make_http_server(host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def test_chatgpt_web_smoke_writes_credential_free_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_chatgpt_web_smoke(
                endpoint_url=self.base_url,
                package_root=Path(tmpdir),
                timeout_seconds=10,
            )

            manifest_path = Path(result["package"]["manifest_path"])
            smoke_path = Path(result["package"]["smoke_path"])
            plan_path = Path(result["package"]["plan_path"])
            html_path = Path(result["package"]["html_path"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            write_gate = json.loads((manifest_path.parent / "write-gate.json").read_text(encoding="utf-8"))
            rendered = json.dumps(smoke, ensure_ascii=False) + json.dumps(manifest, ensure_ascii=False)
            html_exists = html_path.exists()

        self.assertEqual(result["status"], "passed")
        self.assertEqual(manifest["artifact_kind"], "chatgpt_web_connector_smoke_package")
        self.assertEqual(manifest["source"], "remote_mcp_chatgpt_web_smoke")
        self.assertEqual(plan["plan_kind"], "table_build_plan_v1")
        self.assertEqual(smoke["summary"]["write_gate_status"], "awaiting_user_confirmation")
        self.assertIn("spreadsheet_create_formula_table_from_spec", json.dumps(write_gate))
        self.assertTrue(html_exists)
        self.assertNotIn("Bearer ", rendered)
        self.assertNotIn("access-token-secret", rendered)

    def test_chatgpt_web_endpoint_requires_https_outside_localhost(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                run_chatgpt_web_smoke(
                    endpoint_url="http://example.com",
                    package_root=Path(tmpdir),
                    allow_insecure_localhost=False,
                )


if __name__ == "__main__":
    unittest.main()
