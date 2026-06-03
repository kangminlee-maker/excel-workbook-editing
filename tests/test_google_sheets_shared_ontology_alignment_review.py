from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_shared_ontology_alignment_review import (  # noqa: E402
    build_google_sheets_shared_ontology_alignment_review,
)


class GoogleSheetsSharedOntologyAlignmentReviewTest(unittest.TestCase):
    def test_blocks_shared_promotion_and_emits_no_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            candidates_path = root / "live-local-semantic-candidates.json"
            projection_path = root / "live-data-view-projection.json"
            domain_path = root / "live-domain-source-model.json"
            candidates_path.write_text(json.dumps(_candidates(), ensure_ascii=False), encoding="utf-8")
            projection_path.write_text(json.dumps(_projection(), ensure_ascii=False), encoding="utf-8")
            domain_path.write_text(json.dumps(_domain(), ensure_ascii=False), encoding="utf-8")

            review = build_google_sheets_shared_ontology_alignment_review(
                live_local_semantic_candidates_path=candidates_path,
                live_data_view_projection_path=projection_path,
                live_domain_source_model_path=domain_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-shared-ontology-alignment-review.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(review)

        self.assertEqual(review["summary"]["alignment_item_count"], 1)
        self.assertEqual(review["summary"]["blocked_alignment_count"], 1)
        self.assertEqual(review["summary"]["promoted_alignment_count"], 0)
        self.assertEqual(review["summary"]["shared_ontology_update_count"], 0)
        self.assertEqual(review["shared_ontology_updates"], [])
        self.assertGreaterEqual(review["summary"]["review_question_count"], 5)
        self.assertEqual(review["alignment_items"][0]["recommended_action"], "no_shared_update")


def _candidates() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "local_semantic_candidates": [
            {
                "id": "local_candidate_pipeline_a",
                "label": "24_0102 formula surface",
                "evidence_refs": ["pipeline_a"],
            }
        ],
    }


def _projection() -> dict:
    return {
        "data_view_projections": [
            {
                "id": "projection_pipeline_a",
                "projection_kind": "calculation_pipeline_projection",
            }
        ]
    }


def _domain() -> dict:
    return {
        "semantic_readiness": {
            "local_boundary_confirmed": False,
            "unavailable_source_count": 2,
        }
    }


if __name__ == "__main__":
    unittest.main()
