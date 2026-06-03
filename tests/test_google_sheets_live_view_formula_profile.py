from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_live_view_formula_profile import (  # noqa: E402
    build_live_view_formula_profile,
)


class GoogleSheetsLiveViewFormulaProfileTest(unittest.TestCase):
    def test_builds_schema_valid_profile_and_dependency_edges(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "sheets-bridge" / "live-inspections" / "test-view-formula"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        live_manifest_path = fixture_dir / "live-manifest.json"
        top_left_sample_path = fixture_dir / "top-left-sample.json"
        parser_window_smoke_path = fixture_dir / "parser-window-permission-smoke.json"
        live_manifest_path.write_text(
            json.dumps(_live_manifest(), ensure_ascii=False),
            encoding="utf-8",
        )
        top_left_sample_path.write_text(
            json.dumps(_top_left_sample(), ensure_ascii=False),
            encoding="utf-8",
        )
        parser_window_smoke_path.write_text(
            json.dumps(_parser_window_smoke(), ensure_ascii=False),
            encoding="utf-8",
        )

        profile = build_live_view_formula_profile(
            live_manifest_path=live_manifest_path,
            top_left_sample_path=top_left_sample_path,
            parser_window_smoke_path=parser_window_smoke_path,
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-live-view-formula-profile.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(profile)

        self.assertEqual(profile["summary"]["sheet_count"], 2)
        self.assertEqual(profile["summary"]["formula_observation_count"], 3)
        self.assertEqual(profile["summary"]["external_dependency_count"], 1)
        self.assertIn(
            "bounded_grid_formula_value_windows",
            [item["capability"] for item in profile["permission_requirements"]],
        )
        self.assertEqual(
            profile["summary"]["broker_window_contract_status"],
            "verified_for_current_policy_limits",
        )
        self.assertEqual(
            profile["authority"]["expanded_range_authority"],
            "broker_bounded_window_contract_verified",
        )
        self.assertIn(
            "source_spreadsheet_allowlist",
            [item["capability"] for item in profile["permission_requirements"]],
        )
        self.assertTrue(
            any(
                edge["source_sheet"] == "Output"
                and edge["target_sheet"] == "FC_DATA"
                and edge["target_status"] == "known_sheet"
                for edge in profile["dependency_edges"]
            )
        )
        self.assertTrue(
            any(group["formula_count"] == 2 for group in profile["signature_groups"])
        )


def _live_manifest() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "limits": {"profile_range": "A1:Z80"},
        "workbook": {
            "sheet_count": 2,
            "sheets": [
                {
                    "name": "Output",
                    "sheet_id": 1,
                    "index": 0,
                    "state": "visible",
                    "dimensions": {"row_count": 80, "column_count": 26},
                    "profile_window": {"range": "A1:Z80", "grid_data_fetched": True},
                    "view_state_counts": {
                        "hidden_rows_in_profile_window": 0,
                        "filtered_rows_in_profile_window": 0,
                        "hidden_columns_in_profile_window": 0,
                    },
                    "object_counts": {"charts": 0},
                    "style_counts": {"bold_cell_count": 0},
                    "risk_flags": [],
                },
                {
                    "name": "FC_DATA",
                    "sheet_id": 2,
                    "index": 1,
                    "state": "hidden",
                    "dimensions": {"row_count": 80, "column_count": 26},
                    "profile_window": {"range": "A1:Z80", "grid_data_fetched": True},
                    "view_state_counts": {
                        "hidden_rows_in_profile_window": 2,
                        "filtered_rows_in_profile_window": 0,
                        "hidden_columns_in_profile_window": 0,
                    },
                    "object_counts": {"charts": 0},
                    "style_counts": {"bold_cell_count": 0},
                    "risk_flags": ["hidden_sheet"],
                },
            ],
        },
    }


def _top_left_sample() -> dict:
    return {
        "formula_samples": [
            {
                "sheet_id": 1,
                "sheet_title": "Output",
                "cell": "Q80",
                "formula": "={FC_DATA!A61:A69}",
                "classifications": [],
            },
            {
                "sheet_id": 1,
                "sheet_title": "Output",
                "cell": "Q81",
                "formula": "={FC_DATA!A62:A70}",
                "classifications": [],
            },
            {
                "sheet_id": 2,
                "sheet_title": "FC_DATA",
                "cell": "A5",
                "formula": "=IMPORTRANGE(B1,\"지표!T4:AH175\")",
                "classifications": ["importrange"],
            },
        ]
    }


def _parser_window_smoke() -> dict:
    return {
        "smoke_results": [
            {"operation": "inspect.metadata", "result": "passed"},
            {"operation": "inspect.grid_window", "result": "passed"},
            {"operation": "inspect.values_window", "result": "passed"},
            {"operation": "inspect.formula_window", "result": "passed"},
            {"operation": "inspect.values_window", "result": "denied"},
        ]
    }


if __name__ == "__main__":
    unittest.main()
