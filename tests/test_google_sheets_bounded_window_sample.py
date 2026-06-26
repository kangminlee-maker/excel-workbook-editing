from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_bounded_window_sample import build_bounded_window_sample  # noqa: E402


class GoogleSheetsBoundedWindowSampleTest(unittest.TestCase):
    def test_builds_schema_valid_sample_with_source_evidence_results(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "spreadsheet-processing" / "live-inspections" / "test-bounded-window"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        block_candidates_path = fixture_dir / "live-block-candidates.json"
        block_candidates_path.write_text(
            json.dumps(_block_candidates(), ensure_ascii=False),
            encoding="utf-8",
        )

        sample = build_bounded_window_sample(
            live_block_candidates_path=block_candidates_path,
            spreadsheet_id="spreadsheet-1",
            principal="pilot.user@day1company.co.kr",
            source_evidence_results=[_source_evidence_result("inspect.values_window"), _source_evidence_result("inspect.formula_window")],
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-bounded-window-sample.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(sample)

        self.assertEqual(sample["summary"]["evidence_result_count"], 2)
        self.assertEqual(sample["summary"]["successful_response_count"], 2)
        self.assertGreater(sample["summary"]["non_empty_cell_count"], 0)
        self.assertGreater(sample["summary"]["url_sample_count"], 0)
        self.assertTrue(
            any(
                observation["level"] == "warning"
                for observation in sample["tuning_observations"]
            )
        )


def _block_candidates() -> dict:
    return {
        "source": {"title": "Live Sheet"},
        "sheets": [
            {
                "name": "FC_DATA",
                "index": 10,
                "read_candidates": [
                    {
                        "id": "read_fc_data_profile_values",
                        "operation": "inspect.values_window",
                        "range": "'FC_DATA'!A1:Z80",
                        "reason": "sheet has formula text but no display rows in current sample",
                        "status": "verified_for_current_policy_limits",
                    },
                    {
                        "id": "read_fc_data_profile_formulas",
                        "operation": "inspect.formula_window",
                        "range": "'FC_DATA'!A1:Z80",
                        "reason": "confirm formula-bearing profile window through approved-authority formula read",
                        "status": "verified_for_current_policy_limits",
                    },
                ],
            },
            {
                "name": "26_0601",
                "index": 0,
                "read_candidates": [
                    {
                        "id": "read_26_0601_next_window",
                        "operation": "inspect.values_window",
                        "range": "'26_0601'!A81:Z160",
                        "reason": "sheet extends beyond current profile window",
                        "status": "verified_for_current_policy_limits",
                    }
                ],
            },
        ],
    }


def _source_evidence_result(operation: str) -> dict:
    return {
        "ok": True,
        "payload": {
            "schema_version": "1.0",
            "operation": operation,
            "spreadsheet_id": "spreadsheet-1",
            "requested_ranges": ["'FC_DATA'!A1:Z80"],
            "captured_at": "2026-06-02T00:00:00+00:00",
            "snapshot_id": "snapshot-1",
            "telemetry": {
                "request_count": 1,
                "retry_count": 0,
                "elapsed_ms": 10,
                "timeout_budget": {
                    "read_seconds": 60,
                    "write_seconds": 60,
                    "poll_seconds": 120,
                },
            },
            "artifacts": [],
            "windows": [
                {
                    "range": "FC_DATA!A1:Z80",
                    "row_count": 2,
                    "column_count": 2,
                    "values": [
                        ["https://docs.google.com/spreadsheets/d/source/edit", "Title"],
                        ["#REF!", "=IMPORTRANGE(A1,\"Sheet1!A1:B2\")"],
                    ],
                }
            ],
        },
    }


if __name__ == "__main__":
    unittest.main()
