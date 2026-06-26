from __future__ import annotations

import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth import AuthConfig
from broker import READONLY_SHEETS_SCOPE, WRITE_SHEETS_SCOPE, handle_inspect_request
from token_provider import TokenProviderError


PILOT = "pilot.user@day1company.co.kr"
SPREADSHEET_ID = "spreadsheet-1"


class BrokerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth_config = AuthConfig(
            accepted_issuers=("https://accounts.google.com",),
            audience="broker-client-id",
            hosted_domain="day1company.co.kr",
        )
        self.identity_claims = {
            "iss": "https://accounts.google.com",
            "aud": "broker-client-id",
            "exp": 1_900_000_000,
            "sub": "google-subject-1",
            "email": PILOT,
            "email_verified": True,
            "hd": "day1company.co.kr",
        }
        self.policy = {
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
        self.request = {
            "request_id": "request-1",
            "operation": "inspect.metadata",
            "spreadsheet_id": SPREADSHEET_ID,
            "sheet_ids": [10],
            "ranges": ["Input!A1:B10"],
            "risk_level": "low",
        }

    def test_handle_inspect_request_uses_dwd_subject_and_returns_sanitized_snapshot(self) -> None:
        observed_subjects = []
        observed_urls = []

        def access_token_provider(context):
            observed_subjects.append(context.subject)
            self.assertEqual(context.scopes, (READONLY_SHEETS_SCOPE,))
            return "broker-access-token"

        def metadata_transport(url: str, access_token: str) -> dict:
            observed_urls.append(url)
            self.assertEqual(access_token, "broker-access-token")
            return {
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
            }

        response = handle_inspect_request(
            request=self.request,
            identity_claims=self.identity_claims,
            policy=self.policy,
            auth_config=self.auth_config,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            access_token_provider=access_token_provider,
            metadata_transport=metadata_transport,
        )

        self.assertTrue(response["ok"])
        self.assertEqual(observed_subjects, [PILOT])
        self.assertIn("includeGridData=false", observed_urls[0])
        self.assertEqual(response["payload"]["spreadsheet_id"], SPREADSHEET_ID)
        self.assertEqual(response["payload"]["tabs"][0]["title"], "Input")
        self.assertEqual(
            response["payload"]["artifacts"][1]["summary"]["impersonated_subject"],
            PILOT,
        )

    def test_policy_denial_returns_structured_error_before_token_provider(self) -> None:
        def access_token_provider(_context):
            raise AssertionError("policy denial must not request a DWD token")

        response = handle_inspect_request(
            request={**self.request, "spreadsheet_id": "spreadsheet-2"},
            identity_claims=self.identity_claims,
            policy=self.policy,
            auth_config=self.auth_config,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            access_token_provider=access_token_provider,
            metadata_transport=lambda _url, _token: {},
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "policy_denied")
        self.assertEqual(response["policy"]["reason"], "spreadsheet_not_allowed")

    def test_verified_identity_overrides_client_supplied_identity_fields(self) -> None:
        observed_subjects = []

        response = handle_inspect_request(
            request={
                **self.request,
                "verified_identity": {"principal": "unknown@day1company.co.kr"},
                "identity_hint": {"principal": "unknown@day1company.co.kr"},
            },
            identity_claims=self.identity_claims,
            policy=self.policy,
            auth_config=self.auth_config,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            access_token_provider=lambda context: observed_subjects.append(context.subject)
            or "broker-access-token",
            metadata_transport=lambda _url, _token: {
                "spreadsheetId": SPREADSHEET_ID,
                "properties": {},
                "sheets": [],
            },
        )

        self.assertTrue(response["ok"])
        self.assertEqual(observed_subjects, [PILOT])
        self.assertEqual(
            response["payload"]["artifacts"][0]["summary"]["principal"],
            PILOT,
        )

    def test_handle_grid_window_request_returns_bounded_grid_snapshot(self) -> None:
        observed_urls = []
        window_policy = {
            "version": "phase1-test",
            "principals": {
                PILOT: {
                    "spreadsheets": {
                        SPREADSHEET_ID: {
                            "operations": ["inspect.grid_window"],
                            "sheet_ids": [10],
                            "ranges": ["Input!A1:B2"],
                            "max_risk": "low",
                            "max_cells_per_request": 10,
                            "allowed_field_masks": ["grid_basic_v1"],
                        }
                    }
                }
            },
        }

        response = handle_inspect_request(
            request={
                **self.request,
                "operation": "inspect.grid_window",
                "ranges": ["Input!A1:B2"],
                "field_mask": "grid_basic_v1",
            },
            identity_claims=self.identity_claims,
            policy=window_policy,
            auth_config=self.auth_config,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            access_token_provider=lambda _context: "broker-access-token",
            metadata_transport=lambda url, _token: observed_urls.append(url)
            or {
                "spreadsheetId": SPREADSHEET_ID,
                "sheets": [
                    {
                        "properties": {
                            "sheetId": 10,
                            "title": "Input",
                            "index": 0,
                            "gridProperties": {"rowCount": 100, "columnCount": 20},
                        },
                        "data": [{"rowData": []}],
                    }
                ],
            },
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["payload"]["operation"], "inspect.grid_window")
        self.assertEqual(response["payload"]["field_mask"], "grid_basic_v1")
        self.assertIn("includeGridData=true", observed_urls[0])

    def test_handle_values_and_formula_window_requests_use_values_batch_get(self) -> None:
        window_policy = {
            "version": "phase1-test",
            "principals": {
                PILOT: {
                    "spreadsheets": {
                        SPREADSHEET_ID: {
                            "operations": ["inspect.values_window", "inspect.formula_window"],
                            "sheet_ids": [10],
                            "ranges": ["Input!A1:B2"],
                            "max_risk": "low",
                            "max_cells_per_request": 10,
                        }
                    }
                }
            },
        }

        def run(operation: str) -> dict:
            observed_urls = []
            response = handle_inspect_request(
                request={**self.request, "operation": operation, "ranges": ["Input!A1:B2"]},
                identity_claims=self.identity_claims,
                policy=window_policy,
                auth_config=self.auth_config,
                service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
                access_token_provider=lambda _context: "broker-access-token",
                metadata_transport=lambda url, _token: observed_urls.append(url)
                or {
                    "spreadsheetId": SPREADSHEET_ID,
                    "valueRanges": [
                        {
                            "range": "Input!A1:B2",
                            "majorDimension": "ROWS",
                            "values": [["1", "2"]],
                        }
                    ],
                },
            )
            response["observed_url"] = observed_urls[0]
            return response

        values = run("inspect.values_window")
        formulas = run("inspect.formula_window")

        self.assertTrue(values["ok"])
        self.assertIn("valueRenderOption=FORMATTED_VALUE", values["observed_url"])
        self.assertTrue(formulas["ok"])
        self.assertIn("valueRenderOption=FORMULA", formulas["observed_url"])

    def test_handle_values_apply_request_captures_rollback_and_readback(self) -> None:
        observed_scopes = []
        read_urls = []
        write_calls = []
        responses = [
            {
                "spreadsheetId": SPREADSHEET_ID,
                "valueRanges": [
                    {
                        "range": "Input!A1:B1",
                        "majorDimension": "ROWS",
                        "values": [["old", "=A2"]],
                    }
                ],
            },
            {
                "spreadsheetId": SPREADSHEET_ID,
                "valueRanges": [
                    {
                        "range": "Input!A1:B1",
                        "majorDimension": "ROWS",
                        "values": [["new", "=A1"]],
                    }
                ],
            },
        ]
        apply_policy = {
            "version": "phase2-apply-test",
            "principals": {
                PILOT: {
                    "spreadsheets": {
                        SPREADSHEET_ID: {
                            "operations": ["apply.values_update"],
                            "sheet_ids": [10],
                            "ranges": ["Input!A1:B1"],
                            "max_risk": "medium",
                            "max_write_cells_per_request": 2,
                            "max_write_ranges_per_request": 1,
                        }
                    }
                }
            },
        }

        response = handle_inspect_request(
            request={
                **self.request,
                "operation": "apply.values_update",
                "ranges": ["Input!A1:B1"],
                "risk_level": "medium",
                "rollback_required": True,
                "write_requests": [{"range": "Input!A1:B1", "values": [["new", "=A1"]]}],
                "total_cell_count": 2,
            },
            identity_claims=self.identity_claims,
            policy=apply_policy,
            auth_config=self.auth_config,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            access_token_provider=lambda context: observed_scopes.append(context.scopes)
            or "broker-access-token",
            metadata_transport=lambda url, _token: read_urls.append(url) or responses.pop(0),
            write_transport=lambda url, token, body: write_calls.append((url, token, body))
            or {
                "spreadsheetId": SPREADSHEET_ID,
                "totalUpdatedCells": 2,
                "totalUpdatedRows": 1,
                "totalUpdatedColumns": 2,
            },
        )

        self.assertTrue(response["ok"])
        self.assertEqual(observed_scopes, [(WRITE_SHEETS_SCOPE,)])
        self.assertEqual(len(read_urls), 2)
        self.assertIn("valueRenderOption=FORMULA", read_urls[0])
        self.assertEqual(write_calls[0][2]["data"][0]["values"], [["new", "=A1"]])
        payload = response["payload"]
        self.assertEqual(payload["operation"], "apply.values_update")
        self.assertEqual(payload["before"][0]["values"], [["old", "=A2"]])
        self.assertEqual(payload["after"][0]["values"], [["new", "=A1"]])
        self.assertEqual(
            payload["rollback"]["write_requests"],
            [{"range": "Input!A1:B1", "values": [["old", "=A2"]]}],
        )
        self.assertEqual(payload["rollback"]["rollback_of_request_id"], "request-1")

    def test_invalid_identity_returns_structured_error(self) -> None:
        response = handle_inspect_request(
            request=self.request,
            identity_claims={**self.identity_claims, "aud": "wrong-audience"},
            policy=self.policy,
            auth_config=self.auth_config,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            access_token_provider=lambda _context: "broker-access-token",
            metadata_transport=lambda _url, _token: {},
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "auth_failed")
        self.assertIn("audience", response["error"]["message"])

    def test_credential_failure_returns_structured_error(self) -> None:
        response = handle_inspect_request(
            request=self.request,
            identity_claims=self.identity_claims,
            policy=self.policy,
            auth_config=self.auth_config,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            access_token_provider=lambda _context: (_ for _ in ()).throw(RuntimeError("secret")),
            metadata_transport=lambda _url, _token: {},
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "credential_failed")
        self.assertNotIn("secret", response["error"]["message"])
        self.assertEqual(response["policy"]["principal"], PILOT)
        self.assertEqual(response["auth"]["impersonated_subject"], PILOT)

    def test_token_provider_failure_includes_sanitized_diagnostic(self) -> None:
        response = handle_inspect_request(
            request=self.request,
            identity_claims=self.identity_claims,
            policy=self.policy,
            auth_config=self.auth_config,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            access_token_provider=lambda _context: (_ for _ in ()).throw(
                TokenProviderError("token provider HTTP error 403: PERMISSION_DENIED")
            ),
            metadata_transport=lambda _url, _token: {},
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "credential_failed")
        self.assertIn("PERMISSION_DENIED", response["error"]["message"])
        self.assertEqual(response["policy"]["principal"], PILOT)
        self.assertEqual(response["auth"]["impersonated_subject"], PILOT)

    def test_inaccessible_spreadsheet_returns_structured_error(self) -> None:
        response = handle_inspect_request(
            request=self.request,
            identity_claims=self.identity_claims,
            policy=self.policy,
            auth_config=self.auth_config,
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            access_token_provider=lambda _context: "broker-access-token",
            metadata_transport=lambda _url, _token: (_ for _ in ()).throw(PermissionError("forbidden")),
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "sheets_metadata_failed")
        self.assertNotIn("forbidden", response["error"]["message"])


if __name__ == "__main__":
    unittest.main()
