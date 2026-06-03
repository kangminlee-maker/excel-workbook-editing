from __future__ import annotations

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import sys
from pathlib import Path
from threading import Thread
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth import AuthConfig
from server import dispatch_inspect, identity_authorization, load_runtime_config, make_handler


PILOT = "pilot.user@day1company.co.kr"
SPREADSHEET_ID = "spreadsheet-1"


class ServerTests(unittest.TestCase):
    def test_health_returns_public_json_readiness_signal(self) -> None:
        status, body = _local_http_request("GET", "/v1/health")

        self.assertEqual(status, 200)
        self.assertEqual(
            body,
            {
                "ok": True,
                "service": "cloud-run-sheets-broker",
            },
        )

    def test_unknown_get_path_returns_json_404(self) -> None:
        status, body = _local_http_request("GET", "/v1/inspect")

        self.assertEqual(status, 404)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "not_found")

    def test_load_runtime_config_requires_audience_and_service_account(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "BROKER_AUDIENCE"):
            load_runtime_config({})
        with self.assertRaisesRegex(RuntimeError, "BROKER_SERVICE_ACCOUNT_EMAIL"):
            load_runtime_config({"BROKER_AUDIENCE": "broker-client-id"})

    def test_load_runtime_config_builds_auth_policy_and_service_account(self) -> None:
        config = load_runtime_config(
            {
                "BROKER_AUDIENCE": "broker-client-id",
                "BROKER_ADDITIONAL_AUDIENCES": "cli-client-id, broker-client-id",
                "BROKER_SERVICE_ACCOUNT_EMAIL": "day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
                "BROKER_HOSTED_DOMAIN": "day1company.co.kr",
                "BROKER_POLICY_JSON": '{"version":"test","principals":{}}',
            }
        )

        self.assertEqual(config["auth_config"].audience, "broker-client-id")
        self.assertEqual(
            config["auth_config"].accepted_audiences,
            ("broker-client-id", "cli-client-id"),
        )
        self.assertEqual(config["auth_config"].hosted_domain, "day1company.co.kr")
        self.assertEqual(config["policy"]["version"], "test")
        self.assertEqual(
            config["service_account_email"],
            "day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
        )

    def test_dispatch_inspect_runs_identity_policy_dwd_and_metadata(self) -> None:
        policy = {
            "version": "phase1-test",
            "principals": {
                PILOT: {
                    "spreadsheets": {
                        SPREADSHEET_ID: {
                            "operations": ["inspect.metadata"],
                            "sheet_ids": [10],
                            "ranges": ["Input!A1:B10"],
                            "max_risk": "low",
                        }
                    }
                }
            },
        }

        status, body = dispatch_inspect(
            authorization="Bearer identity-evidence",
            request={
                "request_id": "request-1",
                "operation": "inspect.metadata",
                "spreadsheet_id": SPREADSHEET_ID,
                "sheet_ids": [10],
                "ranges": ["Input!A1:B10"],
                "risk_level": "low",
            },
            auth_config=AuthConfig(
                accepted_issuers=("https://accounts.google.com",),
                audience="broker-client-id",
                hosted_domain="day1company.co.kr",
            ),
            policy=policy,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            identity_transport=lambda _token: {
                "iss": "https://accounts.google.com",
                "aud": "broker-client-id",
                "exp": 1_900_000_000,
                "sub": "google-subject-1",
                "email": PILOT,
                "email_verified": True,
                "hd": "day1company.co.kr",
            },
            access_token_provider=lambda _context: "broker-access-token",
            metadata_transport=lambda _url, _token: {
                "spreadsheetId": SPREADSHEET_ID,
                "properties": {
                    "title": "Ops Sheet",
                    "locale": "ko_KR",
                    "timeZone": "Asia/Seoul",
                },
                "sheets": [
                    {
                        "properties": {
                            "sheetId": 10,
                            "title": "Input",
                            "index": 0,
                            "hidden": False,
                            "gridProperties": {"rowCount": 100, "columnCount": 20},
                        }
                    }
                ],
            },
        )

        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["payload"]["title"], "Ops Sheet")

    def test_dispatch_inspect_emits_sanitized_audit_event(self) -> None:
        events = []
        policy = {
            "version": "phase1-test",
            "principals": {
                PILOT: {
                    "spreadsheets": {
                        SPREADSHEET_ID: {
                            "operations": ["inspect.metadata"],
                            "sheet_ids": [10],
                            "ranges": ["Input!A1:B10"],
                            "max_risk": "low",
                        }
                    }
                }
            },
        }

        status, body = dispatch_inspect(
            authorization="Bearer identity-evidence",
            request={
                "request_id": "request-1",
                "operation": "inspect.metadata",
                "spreadsheet_id": SPREADSHEET_ID,
                "sheet_ids": [10],
                "ranges": ["Input!A1:B10"],
                "risk_level": "low",
            },
            auth_config=AuthConfig(
                accepted_issuers=("https://accounts.google.com",),
                audience="broker-client-id",
                hosted_domain="day1company.co.kr",
            ),
            policy=policy,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            identity_transport=lambda _token: {
                "iss": "https://accounts.google.com",
                "aud": "broker-client-id",
                "exp": 1_900_000_000,
                "sub": "google-subject-1",
                "email": PILOT,
                "email_verified": True,
                "hd": "day1company.co.kr",
            },
            access_token_provider=lambda _context: "broker-access-token",
            metadata_transport=lambda _url, _token: {
                "spreadsheetId": SPREADSHEET_ID,
                "properties": {"title": "Ops Sheet"},
                "sheets": [],
            },
            audit_sink=events.append,
        )

        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "sheets_broker.inspect")
        self.assertEqual(events[0]["request_id"], "request-1")
        self.assertEqual(events[0]["operation"], "inspect.metadata")
        self.assertEqual(events[0]["spreadsheet_id"], SPREADSHEET_ID)
        self.assertEqual(events[0]["http_status"], 200)
        self.assertTrue(events[0]["ok"])
        self.assertEqual(events[0]["principal"], PILOT)
        self.assertEqual(events[0]["impersonated_subject"], PILOT)
        self.assertEqual(
            events[0]["policy_decision_id"],
            f"phase1-test:{PILOT}:{SPREADSHEET_ID}:inspect.metadata",
        )
        self.assertEqual(events[0]["policy_version"], "phase1-test")
        self.assertTrue(events[0]["policy_allowed"])
        self.assertNotIn("identity-evidence", json.dumps(events[0]))
        self.assertNotIn("broker-access-token", json.dumps(events[0]))

    def test_dispatch_inspect_returns_401_for_missing_identity(self) -> None:
        events = []
        status, body = dispatch_inspect(
            authorization=None,
            request={"request_id": "request-unauth", "operation": "inspect.metadata"},
            auth_config=AuthConfig(
                accepted_issuers=("https://accounts.google.com",),
                audience="broker-client-id",
            ),
            policy={},
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            identity_transport=lambda _token: {},
            audit_sink=events.append,
        )

        self.assertEqual(status, 401)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "identity_evidence_failed")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["request_id"], "request-unauth")
        self.assertEqual(events[0]["http_status"], 401)
        self.assertEqual(events[0]["error_code"], "identity_evidence_failed")
        self.assertEqual(events[0]["principal"], "")

    def test_identity_authorization_prefers_broker_header(self) -> None:
        self.assertEqual(
            identity_authorization(
                {
                    "Authorization": "Bearer cloud-run-layer-token",
                    "X-Broker-Authorization": "Bearer user-identity-evidence",
                }
            ),
            "Bearer user-identity-evidence",
        )
        self.assertEqual(
            identity_authorization({"Authorization": "Bearer legacy-token"}),
            "Bearer legacy-token",
        )

    def test_inspect_malformed_json_emits_sanitized_audit_event(self) -> None:
        events = []
        status, body = _local_http_request(
            "POST",
            "/v1/inspect",
            body="{not-json",
            runtime_config_overrides={"audit_sink": events.append},
        )

        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "bad_request")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "sheets_broker.inspect")
        self.assertEqual(events[0]["http_status"], 400)
        self.assertFalse(events[0]["ok"])
        self.assertEqual(events[0]["error_code"], "bad_request")
        self.assertEqual(events[0]["request_id"], "")
        self.assertEqual(events[0]["operation"], "")
        self.assertEqual(events[0]["spreadsheet_id"], "")
        self.assertNotIn("not-json", json.dumps(events[0]))

    def test_inspect_non_object_json_emits_sanitized_audit_event(self) -> None:
        events = []
        status, body = _local_http_request(
            "POST",
            "/v1/inspect",
            body='["not", "object"]',
            runtime_config_overrides={"audit_sink": events.append},
        )

        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["code"], "bad_request")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "sheets_broker.inspect")
        self.assertEqual(events[0]["http_status"], 400)
        self.assertFalse(events[0]["ok"])
        self.assertEqual(events[0]["error_code"], "bad_request")
        self.assertEqual(events[0]["request_id"], "")
        self.assertEqual(events[0]["operation"], "")
        self.assertEqual(events[0]["spreadsheet_id"], "")
        self.assertNotIn("not", json.dumps(events[0]))


def _local_http_request(
    method: str,
    path: str,
    *,
    body: str | None = None,
    runtime_config_overrides: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    runtime_config = load_runtime_config(
        {
            "BROKER_AUDIENCE": "broker-client-id",
            "BROKER_SERVICE_ACCOUNT_EMAIL": "day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            "BROKER_POLICY_JSON": '{"version":"test","principals":{}}',
        }
    )
    if runtime_config_overrides:
        runtime_config.update(runtime_config_overrides)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(runtime_config))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request(
            method,
            path,
            body=body,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        response = connection.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        return response.status, body
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
