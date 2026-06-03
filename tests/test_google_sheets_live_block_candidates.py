from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_live_block_candidates import build_live_block_candidates  # noqa: E402


class GoogleSheetsLiveBlockCandidatesTest(unittest.TestCase):
    def test_builds_schema_valid_block_candidates(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "sheets-bridge" / "live-inspections" / "test-block-candidates"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        live_manifest_path = fixture_dir / "live-manifest.json"
        top_left_sample_path = fixture_dir / "top-left-sample.json"
        view_formula_path = fixture_dir / "live-view-formula-profile.json"
        smoke_path = fixture_dir / "parser-window-permission-smoke.json"
        live_manifest_path.write_text(json.dumps(_live_manifest(), ensure_ascii=False), encoding="utf-8")
        top_left_sample_path.write_text(json.dumps(_top_left_sample(), ensure_ascii=False), encoding="utf-8")
        view_formula_path.write_text(json.dumps(_view_formula_profile(), ensure_ascii=False), encoding="utf-8")
        smoke_path.write_text(json.dumps(_parser_window_smoke(), ensure_ascii=False), encoding="utf-8")

        candidates = build_live_block_candidates(
            live_manifest_path=live_manifest_path,
            top_left_sample_path=top_left_sample_path,
            live_view_formula_profile_path=view_formula_path,
            parser_window_smoke_path=smoke_path,
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-live-block-candidates.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(candidates)

        self.assertEqual(candidates["summary"]["sheet_count"], 2)
        self.assertGreater(candidates["summary"]["table_candidate_count"], 0)
        self.assertGreater(candidates["summary"]["formula_region_candidate_count"], 0)
        self.assertEqual(
            candidates["authority"]["parser_window_contract_status"],
            "verified_for_current_policy_limits",
        )
        self.assertTrue(
            any(
                relation["type"] == "formula_dependency_candidate"
                for sheet in candidates["sheets"]
                for relation in sheet["relations"]
            )
        )
        self.assertTrue(
            any(
                candidate["range"] == "'FC_DATA'!A1:Z80"
                for sheet in candidates["sheets"]
                for candidate in sheet["read_candidates"]
            )
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
                _sheet("Output", 1, "visible", {"charts": 1, "banded_ranges": 1, "merges_in_profile_window": 0}),
                _sheet("FC_DATA", 2, "hidden", {"charts": 0, "banded_ranges": 0, "merges_in_profile_window": 0}),
            ],
        },
    }


def _sheet(name: str, sheet_id: int, state: str, object_counts: dict) -> dict:
    return {
        "name": name,
        "sheet_id": sheet_id,
        "index": sheet_id - 1,
        "state": state,
        "dimensions": {"row_count": 100, "column_count": 26},
        "profile_window": {"range": "A1:Z80", "grid_data_fetched": True},
        "role_hints": ["styled_document_surface"],
        "object_counts": object_counts,
    }


def _top_left_sample() -> dict:
    return {
        "tabs": [
            {
                "title": "Output",
                "display_rows": [
                    ["A. Overview"],
                    ["Comment"],
                    ["- note"],
                    [],
                    ["", "", "", "", "", "표1 | 주간 결제액", "", "5월"],
                    ["", "", "", "", "", "순매출", "100", "200"],
                ],
            },
            {"title": "FC_DATA", "display_rows": []},
        ]
    }


def _view_formula_profile() -> dict:
    return {
        "view_state_surfaces": [
            {"sheet": "Output", "diagnostic_status": "no_profile_window_view_state_risk"},
            {"sheet": "FC_DATA", "diagnostic_status": "requires_view_state_aware_parsing"},
        ],
        "formula_observations": [
            {
                "sheet": "Output",
                "cell": "Q80",
                "row": 80,
                "column": 17,
                "formula": "={FC_DATA!A61:A69}",
                "classifications": [],
            },
            {
                "sheet": "FC_DATA",
                "cell": "A5",
                "row": 5,
                "column": 1,
                "formula": "=IMPORTRANGE(B1,\"지표!T4:AH175\")",
                "classifications": ["importrange"],
            }
        ],
        "dependency_edges": [
            {
                "id": "edge_output_fc_data",
                "source_sheet": "Output",
                "target_kind": "cross_sheet_range",
                "target_sheet": "FC_DATA",
                "target_status": "known_sheet",
            }
        ],
    }


def _parser_window_smoke() -> dict:
    return {
        "smoke_results": [
            {"operation": "inspect.grid_window", "result": "passed"},
            {"operation": "inspect.values_window", "result": "passed"},
            {"operation": "inspect.formula_window", "result": "passed"},
        ]
    }


if __name__ == "__main__":
    unittest.main()
