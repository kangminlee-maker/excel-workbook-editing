from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "mcp"))

from sheets_bridge import auth, remote_auth  # noqa: E402
from sheets_bridge.http_server import make_http_server  # noqa: E402
from sheets_bridge.version import __version__  # noqa: E402


class MemoryRemoteSessionStore(remote_auth.RemoteSessionStore):
    def __init__(self, sessions: dict[str, remote_auth.RemoteSession] | None = None) -> None:
        self.sessions = sessions or {}

    def configured(self) -> bool:
        return True

    def get(self, session_id: str) -> remote_auth.RemoteSession | None:
        return self.sessions.get(session_id)


class SheetsBridgeHttpServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryRemoteSessionStore()
        self.get_calls: list[tuple[str, str]] = []
        self.post_calls: list[tuple[str, str, dict]] = []
        self.server = make_http_server(
            host="127.0.0.1",
            port=0,
            remote_session_store=self.store,
            google_get_transport=self._google_get,
            google_post_transport=self._google_post,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def test_healthz_reports_runtime_and_version(self) -> None:
        status, payload = self._get_json("/healthz")

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "sheets-bridge-http")
        self.assertEqual(payload["serverInfo"]["version"], __version__)

    def test_http_mcp_lists_tools_and_reads_table_builder_resource(self) -> None:
        initialized = self._post_mcp({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        listed = self._post_mcp({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        resource = self._post_mcp(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/read",
                "params": {"uri": "ui://sheets-bridge/table-builder"},
            }
        )

        self.assertIn("resources", initialized["result"]["capabilities"])
        tool_names = {tool["name"] for tool in listed["result"]["tools"]}
        self.assertIn("spreadsheet_table_builder_save_intent", tool_names)
        self.assertIn("spreadsheet_table_builder_ui", tool_names)
        content = resource["result"]["contents"][0]
        self.assertEqual(content["mimeType"], "text/html;profile=mcp-app")
        self.assertIn("SheetsBridgeHostAdapters", content["text"])

    def test_http_mcp_saves_table_build_intent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            response = self._post_mcp(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "spreadsheet_table_builder_save_intent",
                        "arguments": {
                            "package_root": tmpdir,
                            "intent": {
                                "artifact_type": "google_sheets",
                                "source": {
                                    "artifact_type": "google_sheets",
                                    "spreadsheet_id": "spreadsheet-1",
                                    "sheet_title": "Raw",
                                    "qualified_range": "'Raw'!A1:C3",
                                },
                                "output_canvas": [["", "Jan"], ["Team A", ""]],
                                "llm_prompt": "팀별 월별 매출 합계를 수식으로 채워줘.",
                            },
                        },
                    },
                }
            )

            result = response["result"]["structuredContent"]
            intent_path = Path(result["package"]["intent_path"])
            self.assertTrue(intent_path.exists())
            self.assertEqual(json.loads(intent_path.read_text(encoding="utf-8"))["intent_kind"], "table_build_intent_v1")

    def test_http_mcp_builds_table_builder_ui_from_sanitized_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            response = self._post_mcp(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "spreadsheet_table_builder_ui",
                        "arguments": {
                            "package_root": tmpdir,
                            "source_preview": {
                                "artifact_type": "google_sheets",
                                "spreadsheet_id": "spreadsheet-1",
                                "workbook_title": "Sales Ops",
                                "sheet_title": "Raw",
                                "qualified_range": "'Raw'!A1:C3",
                                "values": [
                                    ["Team", "Month", "Revenue"],
                                    ["Team A", "2026-01", "10"],
                                    ["Team B", "2026-01", "20"],
                                ],
                                "formulas": [
                                    ["Team", "Month", "Revenue"],
                                    ["Team A", "2026-01", "=SUM(Input!C2:C4)"],
                                ],
                            },
                        },
                    },
                }
            )

            result = response["result"]["structuredContent"]
            self.assertEqual(result["artifact_type"], "google_sheets")
            self.assertEqual(result["summary"]["source_authority"], "sanitized_preview")
            self.assertEqual(result["source_range"], "'Raw'!A1:C3")
            self.assertTrue(Path(result["package"]["source_path"]).exists())
            self.assertIn("app_source", result)

    def test_http_mcp_returns_boundaries_for_local_runtime_and_requires_remote_auth(self) -> None:
        workbook = self._post_mcp(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "spreadsheet_table_builder_ui",
                    "arguments": {"workbook_path": "/tmp/source.xlsx", "sheet_name": "Raw", "source_range": "A1:C4"},
                },
            }
        )
        sheets = self._post_mcp(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "sheets_bridge_inspect", "arguments": {"spreadsheet_id": "spreadsheet-1"}},
            }
        )
        chrome = self._post_mcp(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "sheets_bridge_current_chrome_sheet", "arguments": {}},
            }
        )

        self.assertEqual(workbook["result"]["structuredContent"]["status"], "local_runtime_required")
        self.assertEqual(sheets["result"]["structuredContent"]["status"], "remote_auth_required")
        self.assertEqual(sheets["result"]["structuredContent"]["required_runtime"], "remote_authorized_google_sheets_session")
        self.assertEqual(chrome["result"]["structuredContent"]["required_runtime"], "desktop_runtime")
        self.assertFalse(sheets["result"]["structuredContent"]["credential_boundary"]["raw_credentials_returned"])

    def test_http_mcp_reports_remote_auth_status_without_credentials(self) -> None:
        self.store.sessions["session-read"] = remote_auth.RemoteSession(
            session_id="session-read",
            access_token="access-token-read",
            scopes=(auth.READONLY_SCOPE,),
            user_email="user@example.com",
        )

        response = self._post_mcp(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "sheets_bridge_auth_status", "arguments": {}},
            },
            headers={"Authorization": "Bearer session-read"},
        )

        status = response["result"]["structuredContent"]
        rendered = json.dumps(status)
        self.assertEqual(status["status"], "authenticated")
        self.assertEqual(status["mode"], "remote_user_session")
        self.assertIn(auth.READONLY_SCOPE, status["scopes"])
        self.assertNotIn("access-token-read", rendered)

    def test_http_mcp_remote_read_session_can_inspect_sheet(self) -> None:
        self.store.sessions["session-read"] = remote_auth.RemoteSession(
            session_id="session-read",
            access_token="access-token-read",
            scopes=(auth.READONLY_SCOPE,),
            user_email="user@example.com",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            response = self._post_mcp(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "sheets_bridge_inspect",
                        "arguments": {"spreadsheet_id": "spreadsheet-1", "package_root": tmpdir},
                    },
                },
                headers={"Authorization": "Bearer session-read"},
            )

            result = response["result"]["structuredContent"]
            snapshot_path = Path(result["package"]["snapshot_path"])
            manifest_path = Path(result["package"]["manifest_path"])
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            rendered = json.dumps(snapshot, ensure_ascii=False)

        self.assertEqual(result["snapshot"]["title"], "Remote Sheet")
        self.assertEqual(manifest["source"], "remote_mcp_user_session")
        self.assertEqual(snapshot["artifacts"][0]["summary"]["mode"], "remote_user_session")
        self.assertEqual(snapshot["artifacts"][0]["summary"]["user_email"], "user@example.com")
        self.assertEqual(self.get_calls[0][1], "access-token-read")
        self.assertNotIn("access-token-read", rendered)

    def test_http_mcp_readonly_session_denies_write(self) -> None:
        self.store.sessions["session-read"] = remote_auth.RemoteSession(
            session_id="session-read",
            access_token="access-token-read",
            scopes=(auth.READONLY_SCOPE,),
        )

        response = self._post_mcp(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "sheets_bridge_apply_values_update",
                    "arguments": {
                        "spreadsheet_id": "spreadsheet-1",
                        "write_requests": [{"range": "A1:A1", "values": [["new"]]}],
                        "rollback_required": True,
                    },
                },
            },
            headers={"Authorization": "Bearer session-read"},
        )

        result = response["result"]["structuredContent"]
        self.assertEqual(result["status"], "remote_permission_denied")
        self.assertIn(auth.READWRITE_SCOPE, result["required_scopes"])
        self.assertEqual(self.post_calls, [])

    def test_http_mcp_readwrite_session_can_apply_values(self) -> None:
        self.store.sessions["session-write"] = remote_auth.RemoteSession(
            session_id="session-write",
            access_token="access-token-write",
            scopes=(auth.READWRITE_SCOPE,),
            user_email="editor@example.com",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            response = self._post_mcp(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "sheets_bridge_apply_values_update",
                        "arguments": {
                            "spreadsheet_id": "spreadsheet-1",
                            "write_requests": [{"range": "A1:A1", "values": [["new"]]}],
                            "rollback_required": True,
                            "package_root": tmpdir,
                        },
                    },
                },
                headers={"Authorization": "Bearer session-write"},
            )

            result = response["result"]["structuredContent"]
            snapshot = json.loads(Path(result["package"]["snapshot_path"]).read_text(encoding="utf-8"))
            rendered = json.dumps(snapshot, ensure_ascii=False)

        self.assertEqual(result["snapshot"]["updated_cells"], 1)
        self.assertEqual(result["rollback"]["write_requests"], [{"range": "'Raw'!A1:A1", "values": [["old"]]}])
        self.assertEqual(snapshot["artifacts"][0]["summary"]["mode"], "remote_user_session")
        self.assertEqual(self.post_calls[0][1], "access-token-write")
        self.assertNotIn("access-token-write", rendered)

    def _get_json(self, path: str) -> tuple[int, dict]:
        with urlopen(f"{self.base_url}{path}", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload

    def _post_mcp(self, payload: dict, *, headers: dict[str, str] | None = None) -> dict:
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        request = Request(
            f"{self.base_url}/mcp",
            data=json.dumps(payload).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def _google_get(self, url: str, token: str) -> dict:
        self.get_calls.append((url, token))
        if "values:batchGet" in url:
            if len([call for call in self.get_calls if "values:batchGet" in call[0]]) == 1:
                return {"spreadsheetId": "spreadsheet-1", "valueRanges": [{"range": "'Raw'!A1:A1", "values": [["old"]]}]}
            return {"spreadsheetId": "spreadsheet-1", "valueRanges": [{"range": "'Raw'!A1:A1", "values": [["new"]]}]}
        return {
            "spreadsheetId": "spreadsheet-1",
            "properties": {"title": "Remote Sheet", "locale": "ko_KR", "timeZone": "Asia/Seoul"},
            "sheets": [
                {
                    "properties": {
                        "sheetId": 1,
                        "title": "Raw",
                        "gridProperties": {"rowCount": 100, "columnCount": 20},
                    }
                }
            ],
        }

    def _google_post(self, url: str, token: str, body: dict) -> dict:
        self.post_calls.append((url, token, body))
        return {"totalUpdatedRows": 1, "totalUpdatedColumns": 1, "totalUpdatedCells": 1}


if __name__ == "__main__":
    unittest.main()
