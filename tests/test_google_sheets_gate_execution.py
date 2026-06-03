from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_gate_execution import build_google_sheets_gate_execution  # noqa: E402


class GoogleSheetsGateExecutionTest(unittest.TestCase):
    def test_executes_deterministic_gate_results(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "sheets-bridge" / "live-inspections" / "test-gate-execution"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        plan_path = fixture_dir / "live-cross-validation-plan.json"
        batch_path = fixture_dir / "live-validation-batch-execution.json"
        table_path = fixture_dir / "live-table-io-pipelines.json"
        tuning_path = fixture_dir / "live-block-candidate-tuning.json"
        plan_path.write_text(json.dumps(_plan(), ensure_ascii=False), encoding="utf-8")
        batch_path.write_text(json.dumps(_batch(), ensure_ascii=False), encoding="utf-8")
        table_path.write_text(json.dumps(_table_io(), ensure_ascii=False), encoding="utf-8")
        tuning_path.write_text(json.dumps(_tuning(), ensure_ascii=False), encoding="utf-8")

        execution = build_google_sheets_gate_execution(
            live_cross_validation_plan_path=plan_path,
            live_validation_batch_execution_path=batch_path,
            live_table_io_pipelines_path=table_path,
            live_block_candidate_tuning_path=tuning_path,
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-gate-execution.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(execution)

        self.assertEqual(execution["summary"]["accepted_gate_count"], 3)
        self.assertEqual(execution["summary"]["blocked_gate_count"], 1)
        self.assertEqual(execution["summary"]["review_required_gate_count"], 1)

        statuses = {item["status"] for item in execution["target_results"]}
        self.assertIn("accepted", statuses)
        self.assertIn("blocked", statuses)
        self.assertIn("review_required", statuses)


def _plan() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "authority": {"formula_result_authority": "not_established"},
        "validation_targets": [
            _target("target_pipeline", "pipeline_flow", []),
            _target("target_blocked", "external_source_authority", ["source_spreadsheet_acl_required"]),
            _target("target_review", "pipeline_flow", []),
        ],
        "deterministic_gates": [
            _gate("gate_formula", "target_pipeline", "formula_text_dependency_trace", "planned", ["pipeline_output_fc"]),
            _gate("gate_sample", "target_pipeline", "bounded_sample_surface_trace", "planned", ["sampled_region_fc_data"]),
            _gate("gate_policy", "target_pipeline", "bounded_read_policy_check", "planned", ["inspect.values_window"]),
            _gate("gate_external", "target_blocked", "external_source_authority", "blocked", ["external_dep"]),
            _gate("gate_missing", "target_review", "bounded_sample_surface_trace", "planned", ["missing_sampled_region"]),
        ],
    }


def _target(target_id: str, target_type: str, blockers: list[str]) -> dict:
    return {
        "id": target_id,
        "target_type": target_type,
        "authority_blockers": blockers,
    }


def _gate(
    gate_id: str,
    target_id: str,
    gate_type: str,
    status: str,
    inputs: list[str],
) -> dict:
    return {
        "id": gate_id,
        "target_id": target_id,
        "gate_type": gate_type,
        "status": status,
        "deterministic_inputs": inputs,
    }


def _batch() -> dict:
    return {
        "summary": {
            "source_spreadsheet_read_count": 0,
            "successful_response_count": 1,
            "planned_request_count": 1,
        },
        "evidence_updates": [
            {"id": "evidence_display_output"},
        ],
    }


def _table_io() -> dict:
    return {
        "pipelines": [
            {"id": "pipeline_output_fc"},
        ]
    }


def _tuning() -> dict:
    return {
        "sampled_regions": [
            {"id": "sampled_region_fc_data"},
        ]
    }


if __name__ == "__main__":
    unittest.main()
