from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_block_candidate_tuning import build_block_candidate_tuning  # noqa: E402


class GoogleSheetsBlockCandidateTuningTest(unittest.TestCase):
    def test_builds_schema_valid_tuning_packet(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "spreadsheet-processing" / "live-inspections" / "test-candidate-tuning"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        block_candidates_path = fixture_dir / "live-block-candidates.json"
        bounded_sample_path = fixture_dir / "live-bounded-window-sample.json"
        block_candidates_path.write_text(json.dumps(_block_candidates(), ensure_ascii=False), encoding="utf-8")
        bounded_sample_path.write_text(json.dumps(_bounded_sample(), ensure_ascii=False), encoding="utf-8")

        tuning = build_block_candidate_tuning(
            live_block_candidates_path=block_candidates_path,
            bounded_window_sample_path=bounded_sample_path,
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-block-candidate-tuning.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(tuning)

        self.assertGreater(tuning["summary"]["sampled_region_count"], 0)
        self.assertGreater(tuning["summary"]["external_source_url_candidate_count"], 0)
        self.assertGreater(tuning["summary"]["formula_error_annotation_count"], 0)
        self.assertEqual(tuning["summary"]["remaining_read_queue_count"], 1)


def _block_candidates() -> dict:
    return {
        "source": {"spreadsheet_id": "spreadsheet-1", "title": "Live Sheet"},
        "sheets": [
            {
                "name": "FC_DATA",
                "read_candidates": [
                    {
                        "id": "read_fc_data_profile_values",
                        "operation": "inspect.values_window",
                        "range": "'FC_DATA'!A1:Z80",
                        "reason": "sheet has formula text",
                    },
                    {
                        "id": "read_fc_data_next_window",
                        "operation": "inspect.values_window",
                        "range": "'FC_DATA'!A81:Z160",
                        "reason": "sheet extends beyond current profile window",
                    },
                ],
            }
        ],
    }


def _bounded_sample() -> dict:
    return {
        "sampling_plan": {
            "planned_requests": [
                {"ranges": ["'FC_DATA'!A1:Z80"]},
            ]
        },
        "source_evidence_results": [
            {
                "operation": "inspect.values_window",
                "payload": {
                    "windows": [
                        {
                            "range": "FC_DATA!A1:Z80",
                            "values": [
                                ["https://docs.google.com/spreadsheets/d/source/edit", "Title"],
                                ["#REF!", "100", "200", "300", "400"],
                            ],
                        }
                    ]
                },
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
