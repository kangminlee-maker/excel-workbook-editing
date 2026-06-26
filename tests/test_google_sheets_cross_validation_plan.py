from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_cross_validation_plan import build_google_sheets_cross_validation_plan  # noqa: E402


class GoogleSheetsCrossValidationPlanTest(unittest.TestCase):
    def test_builds_schema_valid_validation_plan_without_live_reads(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "spreadsheet-processing" / "live-inspections" / "test-cross-validation-plan"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        table_io_path = fixture_dir / "live-table-io-pipelines.json"
        tuning_path = fixture_dir / "live-block-candidate-tuning.json"
        table_io_path.write_text(json.dumps(_table_io(), ensure_ascii=False), encoding="utf-8")
        tuning_path.write_text(json.dumps(_tuning(), ensure_ascii=False), encoding="utf-8")

        plan = build_google_sheets_cross_validation_plan(
            live_table_io_pipelines_path=table_io_path,
            live_block_candidate_tuning_path=tuning_path,
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-cross-validation-plan.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(plan)

        self.assertEqual(plan["summary"]["unauthorized_source_read_count"], 0)
        self.assertEqual(plan["summary"]["external_source_target_count"], 1)
        self.assertEqual(plan["summary"]["formula_error_target_count"], 1)
        self.assertGreater(plan["summary"]["blocked_gate_count"], 0)
        self.assertGreater(plan["summary"]["planned_bounded_read_range_count"], 0)

        gate_types = {gate["gate_type"] for gate in plan["deterministic_gates"]}
        self.assertIn("external_source_authority", gate_types)
        self.assertIn("formula_error_reconciliation", gate_types)
        self.assertIn("bounded_read_policy_check", gate_types)


def _table_io() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "pipelines": [
            {
                "id": "pipeline_fc_data_external",
                "role": "source_ingestion",
                "input_refs": [
                    {
                        "id": "source_url_fc_data",
                        "label": "source-sheet-id",
                        "sheet": None,
                        "range": "지표!T4:AH175",
                    }
                ],
                "output_refs": [
                    {
                        "id": "sampled_region_fc_data_formula",
                        "label": "FC_DATA formula surface",
                        "sheet": "FC_DATA",
                        "range": "A1:Z80",
                    }
                ],
                "evidence_refs": ["edge_fc_data_external"],
                "review_flags": [
                    "external_source_dependency",
                    "source_allowlist_required",
                    "formula_error_observed",
                    "formula_result_not_established",
                ],
            },
            {
                "id": "pipeline_output_fc",
                "role": "report",
                "input_refs": [
                    {
                        "id": "sampled_region_fc_data",
                        "label": "FC_DATA",
                        "sheet": "FC_DATA",
                        "range": "A1:Z80",
                    }
                ],
                "output_refs": [
                    {
                        "id": "block_output_formula",
                        "label": "Output formula surface",
                        "sheet": "Output",
                        "range": "A1:Z80",
                    }
                ],
                "evidence_refs": ["edge_output_fc"],
                "review_flags": [
                    "cross_sheet_dataflow",
                    "sampled_input_confirmed",
                    "formula_result_not_established",
                ],
            },
        ],
        "external_sources": [
            {
                "id": "external_dep_fc_data_A5",
                "formula_sheet": "FC_DATA",
                "formula_cell": "A5",
                "candidate_source_spreadsheet_id": "source-sheet-id",
                "evidence_refs": ["external_dep_fc_data_A5"],
            }
        ],
        "review_queue": [
            {
                "id": "review_formula_error_surfaces",
                "type": "formula_result_authority_gap",
                "evidence_refs": ["action_error_fc_data"],
            }
        ],
    }


def _tuning() -> dict:
    return {
        "remaining_read_queue": [
            {
                "id": "read_output_next_window",
                "sheet": "Output",
                "operation": "inspect.values_window",
                "range": "'Output'!A81:Z160",
                "reason": "sheet extends",
                "status": "pending_bounded_sampling",
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
