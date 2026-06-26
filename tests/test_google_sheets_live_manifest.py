from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_live_manifest import build_live_manifest  # noqa: E402


class GoogleSheetsLiveManifestTest(unittest.TestCase):
    def test_builds_schema_valid_live_manifest_from_preflight_and_sample(self) -> None:
        manifest = build_live_manifest(
            access_preflight=_access_preflight(),
            top_left_sample=_top_left_sample(),
            grid_profiles={
                "26_0601": {
                    "grid_counts": {
                        "non_empty_cell_count": 8,
                        "string_cell_count": 4,
                        "number_cell_count": 2,
                        "bool_cell_count": 0,
                        "error_cell_count": 1,
                        "pivot_table_cell_count": 1,
                    },
                    "style_counts": {
                        "bold_cell_count": 3,
                        "filled_cell_count": 2,
                        "bordered_cell_count": 4,
                        "data_validation_cell_count": 1,
                        "note_cell_count": 1,
                    },
                    "hidden_row_count": 2,
                    "filtered_row_count": 1,
                    "hidden_column_count": 1,
                    "merge_count": 2,
                }
            },
        )

        schema = json.loads(
            (REPO_ROOT / "schemas" / "google-sheets-live-manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(manifest)

        self.assertEqual(manifest["summary"]["sheet_count"], 2)
        self.assertEqual(manifest["summary"]["hidden_sheet_count"], 1)
        self.assertEqual(manifest["summary"]["sample_formula_count"], 3)
        self.assertEqual(manifest["summary"]["hidden_rows_in_profile_windows"], 2)
        self.assertEqual(manifest["summary"]["pivot_table_cell_count_in_profile_windows"], 1)
        self.assertEqual(
            manifest["formula_profile"]["classification_counts"]["importrange"],
            1,
        )
        self.assertIn(
            "dynamic_formula_dependency",
            manifest["workbook"]["sheets"][0]["risk_flags"],
        )
        self.assertIn(
            "hidden_support_surface",
            manifest["workbook"]["sheets"][1]["role_hints"],
        )
        self.assertEqual(manifest["authority"]["write_operation"], "not_performed")
        self.assertEqual(manifest["permission_gaps"][0]["status"], "not_requested")


def _access_preflight() -> dict:
    return {
        "spreadsheet_id": "spreadsheet-1",
        "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
        "title": "Live Sheet",
        "locale": "ko_KR",
        "time_zone": "Asia/Seoul",
        "authority": {
            "source_document": "live_google_sheet",
            "access_mode": "sheets_api_readonly_with_domain_wide_delegation",
            "service_account_email": "approved-access@example.invalid",
            "impersonated_subject": "pilot.user@day1company.co.kr",
            "xlsx_round_trip": "not_used",
            "write_operation": "not_performed",
        },
        "tabs": [
            {
                "sheet_id": 10,
                "title": "26_0601",
                "index": 0,
                "hidden": False,
                "row_count": 100,
                "column_count": 20,
                "frozen_row_count": 1,
                "frozen_column_count": 0,
                "chart_count": 51,
                "banded_range_count": 3,
                "protected_range_count": 0,
                "filter_view_count": 0,
                "has_basic_filter": False,
            },
            {
                "sheet_id": 20,
                "title": "hidden",
                "index": 1,
                "hidden": True,
                "row_count": 10,
                "column_count": 5,
                "frozen_row_count": 0,
                "frozen_column_count": 0,
                "chart_count": 0,
                "banded_range_count": 0,
                "protected_range_count": 0,
                "filter_view_count": 0,
                "has_basic_filter": False,
            },
        ],
    }


def _top_left_sample() -> dict:
    return {
        "tabs": [
            {
                "title": "26_0601",
                "sample_range": "A1:Z80",
                "summary": {
                    "non_empty_cell_count_in_sample": 12,
                    "formula_cell_count_in_sample": 3,
                },
                "formula_rows": [
                    ["=IMPORTRANGE(\"id\",\"A1:B2\")", "=SUM('hidden'!A:A)"],
                    ["=QUERY(A1:B10,\"select A\")"],
                ],
            },
            {
                "title": "hidden",
                "sample_range": "A1:Z80",
                "summary": {
                    "non_empty_cell_count_in_sample": 0,
                    "formula_cell_count_in_sample": 0,
                },
                "formula_rows": [],
            },
        ]
    }


if __name__ == "__main__":
    unittest.main()
