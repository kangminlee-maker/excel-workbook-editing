from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sheets_client import (
    build_grid_window_url,
    build_metadata_url,
    build_values_window_url,
    fetch_grid_window,
    fetch_metadata,
    fetch_values_window,
    normalize_grid_window,
    normalize_metadata,
    normalize_values_window,
)


class SheetsClientTests(unittest.TestCase):
    def test_build_metadata_url_uses_read_only_metadata_shape(self) -> None:
        url = build_metadata_url("spreadsheet 1")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "sheets.googleapis.com")
        self.assertEqual(parsed.path, "/v4/spreadsheets/spreadsheet%201")
        self.assertEqual(query["includeGridData"], ["false"])
        self.assertIn("properties(title,locale,timeZone)", query["fields"][0])
        self.assertIn("gridProperties(rowCount,columnCount)", query["fields"][0])

    def test_fetch_metadata_delegates_to_transport_with_access_token(self) -> None:
        calls = []

        def transport(url: str, access_token: str) -> dict:
            calls.append((url, access_token))
            return {
                "spreadsheetId": "spreadsheet-1",
                "properties": {"title": "Ops Sheet"},
                "sheets": [],
            }

        metadata, elapsed_ms = fetch_metadata(
            spreadsheet_id="spreadsheet-1",
            access_token="token-1",
            transport=transport,
        )

        self.assertEqual(metadata["spreadsheetId"], "spreadsheet-1")
        self.assertGreaterEqual(elapsed_ms, 0)
        self.assertEqual(calls[0][1], "token-1")
        self.assertIn("includeGridData=false", calls[0][0])

    def test_fetch_metadata_requires_access_token(self) -> None:
        with self.assertRaisesRegex(ValueError, "access_token"):
            fetch_metadata(
                spreadsheet_id="spreadsheet-1",
                access_token="",
                transport=lambda _url, _token: {},
            )

    def test_build_grid_window_url_uses_bounded_ranges_and_field_mask(self) -> None:
        url = build_grid_window_url(
            spreadsheet_id="spreadsheet 1",
            ranges=["'26_0601'!A1:Z80"],
            field_mask="grid_basic_v1",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(query["includeGridData"], ["true"])
        self.assertEqual(query["ranges"], ["'26_0601'!A1:Z80"])
        self.assertIn("rowData(values(formattedValue", query["fields"][0])

    def test_build_values_window_url_uses_values_batch_get(self) -> None:
        url = build_values_window_url(
            spreadsheet_id="spreadsheet 1",
            ranges=["'26_0601'!A1:B2"],
            value_render_option="FORMULA",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/v4/spreadsheets/spreadsheet%201/values:batchGet")
        self.assertEqual(query["ranges"], ["'26_0601'!A1:B2"])
        self.assertEqual(query["valueRenderOption"], ["FORMULA"])

    def test_fetch_grid_and_values_window_delegate_to_transport(self) -> None:
        calls = []

        grid, _elapsed = fetch_grid_window(
            spreadsheet_id="spreadsheet-1",
            ranges=["Input!A1:B2"],
            field_mask="grid_basic_v1",
            access_token="token-1",
            transport=lambda url, token: calls.append((url, token)) or {"spreadsheetId": "spreadsheet-1"},
        )
        values, _elapsed = fetch_values_window(
            spreadsheet_id="spreadsheet-1",
            ranges=["Input!A1:B2"],
            value_render_option="FORMULA",
            access_token="token-1",
            transport=lambda url, token: calls.append((url, token))
            or {"spreadsheetId": "spreadsheet-1", "valueRanges": []},
        )

        self.assertEqual(grid["spreadsheetId"], "spreadsheet-1")
        self.assertEqual(values["spreadsheetId"], "spreadsheet-1")
        self.assertEqual(calls[0][1], "token-1")
        self.assertIn("includeGridData=true", calls[0][0])
        self.assertIn("valueRenderOption=FORMULA", calls[1][0])

    def test_normalize_metadata_returns_sanitized_inspection_shape(self) -> None:
        snapshot = normalize_metadata(
            {
                "spreadsheetId": "spreadsheet-1",
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
                        },
                        "protectedRanges": [
                            {
                                "protectedRangeId": 3,
                                "warningOnly": True,
                                "range": {
                                    "sheetId": 10,
                                    "startRowIndex": 0,
                                    "endRowIndex": 1,
                                    "startColumnIndex": 0,
                                    "endColumnIndex": 2,
                                },
                            }
                        ],
                    }
                ],
                "namedRanges": [
                    {
                        "name": "Inputs",
                        "range": {
                            "sheetId": 10,
                            "startRowIndex": 0,
                            "endRowIndex": 10,
                            "startColumnIndex": 0,
                            "endColumnIndex": 2,
                        },
                    }
                ],
            },
            snapshot_id="snapshot-1",
            captured_at="2026-06-01T00:00:00+00:00",
            elapsed_ms=42,
            policy_summary={"allowed": True},
            auth_summary={
                "principal": "pilot.user@day1company.co.kr",
                "impersonated_subject": "pilot.user@day1company.co.kr",
            },
        )

        self.assertEqual(snapshot["schema_version"], "1.0")
        self.assertEqual(snapshot["spreadsheet_id"], "spreadsheet-1")
        self.assertEqual(snapshot["title"], "Ops Sheet")
        self.assertEqual(snapshot["tabs"][0]["sheet_id"], 10)
        self.assertEqual(snapshot["tabs"][0]["row_count"], 100)
        self.assertEqual(snapshot["named_ranges"][0]["range"]["range"], "A1:B10")
        self.assertEqual(snapshot["protected_ranges"][0]["range"]["range"], "A1:B1")
        self.assertEqual(snapshot["artifacts"][0]["kind"], "broker_policy")
        self.assertEqual(snapshot["artifacts"][1]["kind"], "broker_auth")

    def test_normalize_grid_window_returns_sanitized_window_shape(self) -> None:
        snapshot = normalize_grid_window(
            {
                "spreadsheetId": "spreadsheet-1",
                "sheets": [
                    {
                        "properties": {
                            "sheetId": 10,
                            "title": "Input",
                            "index": 0,
                            "gridProperties": {"rowCount": 100, "columnCount": 20},
                        },
                        "data": [
                            {
                                "startRow": 0,
                                "startColumn": 0,
                                "rowData": [
                                    {
                                        "values": [
                                            {
                                                "formattedValue": "42",
                                                "userEnteredValue": {"numberValue": 42},
                                                "effectiveValue": {"numberValue": 42},
                                                "dataValidation": {},
                                            }
                                        ]
                                    }
                                ],
                                "rowMetadata": [{"hiddenByFilter": True}],
                                "columnMetadata": [{"pixelSize": 80}],
                            }
                        ],
                        "charts": [{"chartId": 1}],
                    }
                ],
            },
            snapshot_id="snapshot-1",
            captured_at="2026-06-01T00:00:00+00:00",
            operation="inspect.grid_window",
            ranges=["Input!A1:A1"],
            field_mask="grid_basic_v1",
            elapsed_ms=12,
            policy_summary={"allowed": True},
            auth_summary={"principal": "pilot.user@day1company.co.kr"},
        )

        self.assertEqual(snapshot["operation"], "inspect.grid_window")
        self.assertEqual(snapshot["windows"][0]["title"], "Input")
        self.assertEqual(
            snapshot["windows"][0]["windows"][0]["rows"][0][0]["formatted_value"],
            "42",
        )
        self.assertTrue(
            snapshot["windows"][0]["windows"][0]["row_metadata"][0]["hidden_by_filter"]
        )
        self.assertEqual(snapshot["windows"][0]["object_counts"]["charts"], 1)

    def test_normalize_values_window_returns_values_window_shape(self) -> None:
        snapshot = normalize_values_window(
            {
                "spreadsheetId": "spreadsheet-1",
                "valueRanges": [
                    {
                        "range": "Input!A1:B2",
                        "majorDimension": "ROWS",
                        "values": [["=A2", "Value"], ["1", "2"]],
                    }
                ],
            },
            snapshot_id="snapshot-1",
            captured_at="2026-06-01T00:00:00+00:00",
            operation="inspect.formula_window",
            ranges=["Input!A1:B2"],
            value_render_option="FORMULA",
            elapsed_ms=12,
            policy_summary={"allowed": True},
            auth_summary={"principal": "pilot.user@day1company.co.kr"},
        )

        self.assertEqual(snapshot["operation"], "inspect.formula_window")
        self.assertEqual(snapshot["value_render_option"], "FORMULA")
        self.assertEqual(snapshot["windows"][0]["row_count"], 2)
        self.assertEqual(snapshot["windows"][0]["column_count"], 2)


if __name__ == "__main__":
    unittest.main()
