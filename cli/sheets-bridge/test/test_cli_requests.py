from __future__ import annotations

import contextlib
from io import StringIO
import json
import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sheets_bridge_cli import build_inspect_request, invoke_broker_inspect, main


class CliRequestTests(unittest.TestCase):
    def test_build_inspect_request_matches_extension_broker_contract(self) -> None:
        request = build_inspect_request(
            spreadsheet_id="spreadsheet-1",
            principal="pilot.user@day1company.co.kr",
            sheet_ids=[10],
            ranges=["Input!A1:B10"],
            request_id="request-1",
            created_at="2026-06-01T00:00:00+00:00",
        )

        self.assertEqual(
            request,
            {
                "request_id": "request-1",
                "operation": "inspect.metadata",
                "spreadsheet_id": "spreadsheet-1",
                "sheet_ids": [10],
                "ranges": ["Input!A1:B10"],
                "risk_level": "low",
                "created_at": "2026-06-01T00:00:00+00:00",
                "identity_hint": {"principal": "pilot.user@day1company.co.kr"},
            },
        )

    def test_dry_run_prints_broker_request_json(self) -> None:
        stdout = StringIO()

        with contextlib.redirect_stdout(stdout):
            status = main(
                [
                    "inspect",
                    "--spreadsheet-id",
                    "spreadsheet-1",
                    "--principal",
                    "pilot.user@day1company.co.kr",
                    "--sheet-id",
                    "10",
                    "--range",
                    "Input!A1:B10",
                    "--dry-run",
                ]
            )

        self.assertEqual(status, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["operation"], "inspect.metadata")
        self.assertEqual(payload["spreadsheet_id"], "spreadsheet-1")
        self.assertEqual(payload["sheet_ids"], [10])
        self.assertEqual(payload["ranges"], ["Input!A1:B10"])
        self.assertEqual(
            payload["identity_hint"]["principal"],
            "pilot.user@day1company.co.kr",
        )

    def test_build_window_request_includes_bounded_parser_controls(self) -> None:
        request = build_inspect_request(
            spreadsheet_id="spreadsheet-1",
            principal="pilot.user@day1company.co.kr",
            operation="inspect.grid_window",
            sheet_ids=[10],
            ranges=["Input!A1:B2"],
            field_mask="grid_basic_v1",
            timeout_seconds=30,
            retry_count=1,
            total_cell_count=4,
            request_id="request-1",
            created_at="2026-06-01T00:00:00+00:00",
        )

        self.assertEqual(request["operation"], "inspect.grid_window")
        self.assertEqual(request["field_mask"], "grid_basic_v1")
        self.assertEqual(request["timeout_seconds"], 30)
        self.assertEqual(request["retry_count"], 1)
        self.assertEqual(request["total_cell_count"], 4)

    def test_dry_run_can_print_formula_window_request(self) -> None:
        stdout = StringIO()

        with contextlib.redirect_stdout(stdout):
            status = main(
                [
                    "inspect",
                    "--spreadsheet-id",
                    "spreadsheet-1",
                    "--operation",
                    "inspect.formula_window",
                    "--range",
                    "Input!A1:B2",
                    "--total-cell-count",
                    "4",
                    "--dry-run",
                ]
            )

        self.assertEqual(status, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["operation"], "inspect.formula_window")
        self.assertEqual(payload["ranges"], ["Input!A1:B2"])
        self.assertEqual(payload["total_cell_count"], 4)

    def test_invoke_broker_inspect_posts_to_broker_with_gcloud_identity_token(self) -> None:
        calls = []

        response = invoke_broker_inspect(
            broker_url="https://broker.example.run.app",
            request={"operation": "inspect.metadata", "spreadsheet_id": "spreadsheet-1"},
            identity_token_fetcher=lambda: "local-gcloud-identity-token",
            transport=lambda url, body, token: calls.append((url, body, token)) or {"ok": True},
        )

        self.assertEqual(response, {"ok": True})
        self.assertEqual(
            calls,
            [
                (
                    "https://broker.example.run.app/v1/inspect",
                    {"operation": "inspect.metadata", "spreadsheet_id": "spreadsheet-1"},
                    "local-gcloud-identity-token",
                )
            ],
        )

    def test_non_dry_run_calls_broker_and_prints_sanitized_response(self) -> None:
        stdout = StringIO()
        calls = []

        with contextlib.redirect_stdout(stdout):
            status = main(
                ["inspect", "--spreadsheet-id", "spreadsheet-1"],
                identity_token_fetcher=lambda: "local-gcloud-identity-token",
                transport=lambda url, body, token: calls.append((url, body, token))
                or {
                    "ok": True,
                    "payload": {
                        "spreadsheet_id": body["spreadsheet_id"],
                        "title": "Ops Sheet",
                    },
                },
            )

        self.assertEqual(status, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["payload"]["title"], "Ops Sheet")
        self.assertEqual(
            calls[0][0],
            "https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app/v1/inspect",
        )
        self.assertEqual(calls[0][2], "local-gcloud-identity-token")

    def test_non_dry_run_returns_nonzero_for_broker_denial(self) -> None:
        stdout = StringIO()

        with contextlib.redirect_stdout(stdout):
            status = main(
                ["inspect", "--spreadsheet-id", "spreadsheet-1"],
                identity_token_fetcher=lambda: "local-gcloud-identity-token",
                transport=lambda _url, _body, _token: {
                    "ok": False,
                    "error": {"code": "policy_denied", "message": "principal_not_allowed"},
                },
            )

        self.assertEqual(status, 2)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["error"]["code"], "policy_denied")


if __name__ == "__main__":
    unittest.main()
