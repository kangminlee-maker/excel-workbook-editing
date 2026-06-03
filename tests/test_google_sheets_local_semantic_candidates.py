from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_local_semantic_candidates import (  # noqa: E402
    build_google_sheets_local_semantic_candidates,
)


class GoogleSheetsLocalSemanticCandidatesTest(unittest.TestCase):
    def test_generates_blocked_boundary_scoped_candidates_from_projections(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            projection_path = root / "live-data-view-projection.json"
            validation_path = root / "live-semantic-proposal-validation.json"
            domain_path = root / "live-domain-source-model.json"
            projection_path.write_text(json.dumps(_projection(), ensure_ascii=False), encoding="utf-8")
            validation_path.write_text(json.dumps(_validation(), ensure_ascii=False), encoding="utf-8")
            domain_path.write_text(json.dumps(_domain(), ensure_ascii=False), encoding="utf-8")

            candidates = build_google_sheets_local_semantic_candidates(
                live_data_view_projection_path=projection_path,
                live_semantic_proposal_validation_path=validation_path,
                live_domain_source_model_path=domain_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-local-semantic-candidates.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(candidates)

        self.assertEqual(candidates["summary"]["local_semantic_candidate_count"], 2)
        self.assertEqual(candidates["summary"]["accepted_local_semantic_candidate_count"], 0)
        self.assertEqual(candidates["summary"]["blocked_local_semantic_candidate_count"], 2)
        self.assertEqual(candidates["summary"]["candidate_relation_count"], 1)
        self.assertEqual(candidates["summary"]["shared_ontology_update_count"], 0)
        self.assertFalse(candidates["summary"]["local_boundary_confirmed"])
        self.assertTrue(
            all(item["status"] == "blocked" for item in candidates["local_semantic_candidates"])
        )


def _projection() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "data_view_projections": [
            _pipeline_projection("pipeline_a", "24_0102"),
            _pipeline_projection("pipeline_b", "24_0108"),
            {
                "id": "projection_node_workbook",
                "projection_kind": "document_summary_projection",
            },
        ],
    }


def _pipeline_projection(pipeline_id: str, sheet: str) -> dict:
    return {
        "id": f"projection_{pipeline_id}",
        "projection_kind": "calculation_pipeline_projection",
        "pipeline_id": pipeline_id,
        "label": f"{sheet} formula surface",
        "role": "calculation",
        "sheet": sheet,
        "range": "B8:M56",
        "input_refs": [],
        "output_refs": [],
        "transform_summary": {
            "repeated_formula_family": True,
        },
        "preview": {
            "status": "sampled_from_top_left_window",
            "sampled_formula_cell_count": 2,
        },
        "evidence_refs": [pipeline_id],
    }


def _validation() -> dict:
    return {
        "proposal_results": [
            {
                "target_id": "proposal_period_tab_calculation_surface",
                "target_type": "semantic_concept_proposal",
                "final_status": "blocked",
                "blocking_gates": [
                    "local_boundary_gate",
                    "source_authority_gate",
                    "formula_result_authority_gate",
                ],
            }
        ],
        "review_queue": [
            {
                "target_id": "proposal_period_tab_calculation_surface",
                "status": "blocked",
            }
        ],
    }


def _domain() -> dict:
    return {
        "local_domain_boundary": {
            "boundary_label": "Live Sheet",
            "boundary_status": "review_required",
        },
        "semantic_readiness": {
            "local_boundary_confirmed": False,
            "shared_ontology_promotion_status": "blocked",
        },
    }


if __name__ == "__main__":
    unittest.main()
