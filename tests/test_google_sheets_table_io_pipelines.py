from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_table_io_pipelines import build_google_sheets_table_io_pipelines  # noqa: E402


class GoogleSheetsTableIoPipelinesTest(unittest.TestCase):
    def test_builds_schema_valid_pipeline_candidates(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "sheets-bridge" / "live-inspections" / "test-table-io"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        block_candidates_path = fixture_dir / "live-block-candidates.json"
        formula_profile_path = fixture_dir / "live-view-formula-profile.json"
        tuning_path = fixture_dir / "live-block-candidate-tuning.json"
        block_candidates_path.write_text(json.dumps(_block_candidates(), ensure_ascii=False), encoding="utf-8")
        formula_profile_path.write_text(json.dumps(_formula_profile(), ensure_ascii=False), encoding="utf-8")
        tuning_path.write_text(json.dumps(_tuning(), ensure_ascii=False), encoding="utf-8")

        table_io = build_google_sheets_table_io_pipelines(
            live_block_candidates_path=block_candidates_path,
            live_view_formula_profile_path=formula_profile_path,
            live_block_candidate_tuning_path=tuning_path,
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-table-io-pipelines.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(table_io)

        self.assertEqual(table_io["summary"]["pipeline_count"], 2)
        self.assertEqual(table_io["summary"]["external_source_pipeline_count"], 1)
        self.assertEqual(table_io["summary"]["formula_error_pipeline_count"], 2)
        self.assertEqual(table_io["summary"]["external_source_count"], 1)
        self.assertIn("flowchart LR", table_io["mermaid"])

        external_pipeline = next(
            pipeline for pipeline in table_io["pipelines"]
            if pipeline["role"] == "source_ingestion"
        )
        self.assertIn("source_allowlist_required", external_pipeline["review_flags"])
        self.assertEqual(
            external_pipeline["input_refs"][0]["source_spreadsheet_id"],
            "source-sheet-id",
        )


def _block_candidates() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "sheets": [
            {
                "name": "Output",
                "blocks": [
                    _block("block_output_formula_surface", "Output", "formula_region_candidate", "A1:Z80"),
                ],
                "cell_regions": [],
            },
            {
                "name": "FC_DATA",
                "blocks": [
                    _block("block_fc_data_support_surface", "FC_DATA", "support_surface", "A1:Z80"),
                    _block("block_fc_data_formula_surface", "FC_DATA", "formula_region_candidate", "A1:Z80"),
                ],
                "cell_regions": [],
            },
        ],
    }


def _block(block_id: str, sheet: str, block_type: str, a1_range: str) -> dict:
    return {
        "id": block_id,
        "type": block_type,
        "subtype": block_type,
        "sheet": sheet,
        "label": block_id,
        "bounds": {
            "start_row": 1,
            "end_row": 80,
            "start_column": 1,
            "end_column": 26,
            "a1_range": a1_range,
        },
        "confidence": 0.7,
    }


def _formula_profile() -> dict:
    return {
        "dependency_edges": [
            {
                "id": "edge_output_fc_data",
                "source_sheet": "Output",
                "target_kind": "cross_sheet_range",
                "target_sheet": "FC_DATA",
                "target_status": "known_sheet",
                "formula_count": 18,
                "sample_formula_cells": ["Q80"],
                "sample_target_ranges": ["A61:A69"],
                "classifications": [],
                "authority": "formula_text_dependency_candidate",
            },
            {
                "id": "edge_fc_data_external",
                "source_sheet": "FC_DATA",
                "target_kind": "external_importrange",
                "target_sheet": None,
                "target_status": "external_source_unresolved",
                "formula_count": 1,
                "sample_formula_cells": ["A5"],
                "sample_target_ranges": ["지표!T4:AH175"],
                "classifications": ["importrange"],
                "authority": "formula_text_dependency_candidate",
            },
        ],
        "signature_groups": [
            {
                "id": "signature_output_fc",
                "formula_count": 18,
                "source_sheets": ["Output"],
                "reference_sheets": ["FC_DATA"],
                "classifications": [],
            },
            {
                "id": "signature_fc_import",
                "formula_count": 1,
                "source_sheets": ["FC_DATA"],
                "reference_sheets": [],
                "classifications": ["importrange"],
            },
        ],
        "external_dependencies": [
            {
                "id": "external_dep_fc_data_A5",
                "formula_sheet": "FC_DATA",
                "formula_cell": "A5",
                "source_argument": "B1",
                "range_argument": "지표!T4:AH175",
                "source_resolution_status": "source_argument_requires_value_lookup",
                "required_evidence": [
                    "source argument value lookup",
                    "source spreadsheet Google ACL check",
                    "broker source spreadsheet allowlist",
                ],
            }
        ],
    }


def _tuning() -> dict:
    return {
        "sampled_regions": [
            {
                "id": "sampled_region_fc_data_external",
                "operation": "inspect.values_window",
                "sheet": "FC_DATA",
                "range": "FC_DATA!A1:Z80",
                "subtype": "sampled_external_source_region",
                "bounds": {
                    "start_row": 1,
                    "end_row": 2,
                    "start_column": 1,
                    "end_column": 18,
                    "a1_range": "A1:R2",
                },
                "metrics": {"formula_cell_count": 0},
                "preview": [
                    "R1: https://docs.google.com/spreadsheets/d/source-sheet-id/edit | Source title"
                ],
            }
        ],
        "tuning_actions": [
            {
                "id": "action_url_fc_data",
                "type": "external_source_url_candidate",
                "sheet": "FC_DATA",
                "target_range": "A1:R2",
                "effect": "use_url_as_candidate_source_id_for_importrange_review",
                "evidence_refs": ["sampled_region_fc_data_external"],
                "status": "requires_source_allowlist_review",
            },
            {
                "id": "action_error_fc_data",
                "type": "formula_error_annotation",
                "sheet": "FC_DATA",
                "target_range": "A5:Z5",
                "effect": "keep_formula_result_authority_unestablished",
                "evidence_refs": ["sampled_region_fc_data_external"],
                "status": "requires_formula_result_review",
            },
        ],
        "remaining_read_queue": [
            {
                "id": "read_output_next_window",
                "sheet": "Output",
                "operation": "inspect.values_window",
                "range": "'Output'!A81:Z160",
                "reason": "sheet extends",
                "status": "pending_bounded_sampling",
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
