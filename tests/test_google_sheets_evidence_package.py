from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_evidence_package import build_google_sheets_evidence_package  # noqa: E402


class GoogleSheetsEvidencePackageTest(unittest.TestCase):
    def test_assembles_accepted_body_and_review_queue(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "sheets-bridge" / "live-inspections" / "test-evidence-package"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "manifest": fixture_dir / "live-manifest.json",
            "blocks": fixture_dir / "live-block-candidates.json",
            "table": fixture_dir / "live-table-io-pipelines.json",
            "plan": fixture_dir / "live-cross-validation-plan.json",
            "batch": fixture_dir / "live-validation-batch-execution.json",
            "gate": fixture_dir / "live-gate-execution.json",
        }
        paths["manifest"].write_text(json.dumps(_manifest(), ensure_ascii=False), encoding="utf-8")
        paths["blocks"].write_text(json.dumps(_blocks(), ensure_ascii=False), encoding="utf-8")
        paths["table"].write_text(json.dumps(_table_io(), ensure_ascii=False), encoding="utf-8")
        paths["plan"].write_text(json.dumps(_plan(), ensure_ascii=False), encoding="utf-8")
        paths["batch"].write_text(json.dumps(_batch(), ensure_ascii=False), encoding="utf-8")
        paths["gate"].write_text(json.dumps(_gate_execution(), ensure_ascii=False), encoding="utf-8")

        package = build_google_sheets_evidence_package(
            live_manifest_path=paths["manifest"],
            live_block_candidates_path=paths["blocks"],
            live_table_io_pipelines_path=paths["table"],
            live_cross_validation_plan_path=paths["plan"],
            live_validation_batch_execution_path=paths["batch"],
            live_gate_execution_path=paths["gate"],
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-evidence-package.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        self.assertEqual(package["summary"]["accepted_pipeline_count"], 1)
        self.assertEqual(package["summary"]["accepted_gate_count"], 1)
        self.assertGreater(package["summary"]["review_queue_count"], 0)
        self.assertEqual(package["summary"]["source_spreadsheet_read_count"], 0)


def _manifest() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "summary": {"sheet_count": 2, "hidden_sheet_count": 1},
        "view_state_profile": {"risk_surface_count": 1},
        "formula_profile": {"total_formula_count_in_profile_windows": 3},
    }


def _blocks() -> dict:
    return {
        "summary": {"block_count": 3, "cell_region_count": 3}
    }


def _table_io() -> dict:
    return {
        "pipelines": [
            {"id": "pipeline_ok", "role": "calculation", "output_refs": [{"label": "Output"}], "confidence": 0.8},
            {"id": "pipeline_blocked", "role": "report", "output_refs": [{"label": "Blocked"}], "confidence": 0.5},
        ],
        "external_sources": [
            {
                "id": "external_dep",
                "evidence_refs": ["external_dep"],
                "status": "blocked_until_source_acl_and_broker_allowlist",
            }
        ],
        "review_queue": [
            {
                "id": "review_formula_error",
                "type": "formula_result_authority_gap",
                "severity": "high",
                "message": "Formula error remains.",
                "evidence_refs": ["action_error"],
                "status": "requires_formula_result_review",
            }
        ],
    }


def _plan() -> dict:
    return {
        "validation_targets": [
            {"id": "target_ok", "related_pipeline_ids": ["pipeline_ok"]},
            {"id": "target_blocked", "related_pipeline_ids": ["pipeline_blocked"]},
        ]
    }


def _batch() -> dict:
    return {
        "evidence_updates": [{"id": "evidence_1"}],
        "summary": {"source_spreadsheet_read_count": 0},
    }


def _gate_execution() -> dict:
    return {
        "gate_results": [
            {"id": "gate_result_ok", "status": "accepted"},
            {"id": "gate_result_blocked", "status": "blocked"},
        ],
        "target_results": [
            {
                "id": "target_result_ok",
                "target_id": "target_ok",
                "target_type": "pipeline_flow",
                "status": "accepted",
            },
            {
                "id": "target_result_blocked",
                "target_id": "target_blocked",
                "target_type": "pipeline_flow",
                "status": "blocked",
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
