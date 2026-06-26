from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_validation_batch_execution import (  # noqa: E402
    build_google_sheets_validation_batch_execution,
)


class GoogleSheetsValidationBatchExecutionTest(unittest.TestCase):
    def test_merges_planned_batches_with_source_evidence_results(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "spreadsheet-processing" / "live-inspections" / "test-validation-batch"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        plan_path = fixture_dir / "live-cross-validation-plan.json"
        plan_path.write_text(json.dumps(_plan(), ensure_ascii=False), encoding="utf-8")

        execution = build_google_sheets_validation_batch_execution(
            live_cross_validation_plan_path=plan_path,
            spreadsheet_id="spreadsheet-1",
            principal="user@example.com",
            source_evidence_results=[_source_evidence_result()],
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-validation-batch-execution.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(execution)

        self.assertEqual(execution["summary"]["evidence_result_count"], 1)
        self.assertEqual(execution["summary"]["successful_response_count"], 1)
        self.assertEqual(execution["summary"]["source_spreadsheet_read_count"], 0)
        self.assertGreater(execution["summary"]["formula_cell_count"], 0)
        self.assertGreater(execution["summary"]["error_display_count"], 0)

        update_types = {item["type"] for item in execution["evidence_updates"]}
        self.assertIn("bounded_window_surface_observed", update_types)
        self.assertIn("bounded_formula_text_observed", update_types)
        self.assertIn("bounded_error_surface_observed", update_types)


def _plan() -> dict:
    return {
        "source": {
            "title": "Live Sheet",
        },
        "source_evidence_read_plan": {
            "status": "planned_not_executed",
            "batches": [
                {
                    "id": "source_evidence_batch_inspect_formula_window",
                    "operation": "inspect.formula_window",
                    "ranges": ["'Output'!A81:Z160"],
                    "read_candidate_ids": ["read_output_formula_next_window"],
                }
            ],
            "blocked_source_reads": [],
        },
    }


def _source_evidence_result() -> dict:
    return {
        "ok": True,
        "payload": {
            "windows": [
                {
                    "range": "'Output'!A81:Z160",
                    "row_count": 2,
                    "column_count": 3,
                    "values": [
                        ["Header", "=SUM(A1:A2)", "#REF!"],
                        ["10", "20", "30"],
                    ],
                }
            ]
        },
    }


if __name__ == "__main__":
    unittest.main()
