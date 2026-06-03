from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_shared_ontology_alignment_review import (  # noqa: E402
    build_shared_ontology_alignment_review,
)


class WorkbookSharedOntologyAlignmentReviewTest(unittest.TestCase):
    def test_generates_review_only_alignment_with_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            local_candidates_path = root / "local-semantic-candidates.json"
            domain_model_path = root / "domain-source-model.json"
            data_view_projection_path = root / "data-view-projection.json"

            local_candidates_path.write_text(
                json.dumps(
                    {
                        "local_boundary": {
                            "id": "local_boundary:sample",
                            "status": "review_required",
                            "scope": "current_workbook_only_until_boundary_confirmed",
                        },
                        "local_semantic_candidates": [
                            {
                                "id": "local_semantic_candidate:revenue",
                                "type": "local_semantic_candidate",
                                "label": "60일 수익인식 배분 스케줄",
                                "candidate_kind": "revenue_recognition_schedule",
                                "source_kind": "accepted_semantic_context",
                                "status": "local_candidate_boundary_pending",
                                "promotion_status": "not_promotable_shared_ontology_boundary_pending",
                                "applicability_scope": "current_workbook_only_until_boundary_confirmed",
                                "confidence": 0.78,
                                "requires_human_review": True,
                                "local_boundary_id": "local_boundary:sample",
                                "general_domain_alignment": {
                                    "status": "aligned",
                                    "accepted_semantic_concept_ids": [
                                        "semantic_concept:revenue"
                                    ],
                                    "accepted_semantic_labels": [
                                        "60일 수익인식 배분 스케줄"
                                    ],
                                    "domain_source_refs": [
                                        "general_domain:accounting-kr/concepts.md"
                                    ],
                                },
                                "local_domain_evidence": {
                                    "local_domain_source_ids": [],
                                    "local_domain_boundary_ids": [
                                        "local_boundary:sample"
                                    ],
                                    "local_domain_source_status": "missing",
                                },
                                "data_view_refs": {
                                    "data_view_ids": ["data_view:revenue"],
                                    "projection_ids": ["projection:data_view:revenue"],
                                    "sheets": ["수익인식60일"],
                                    "ranges": ["A1:Z20"],
                                    "projection_kinds": [
                                        "formula_summary_projection"
                                    ],
                                    "roles": ["summary"],
                                    "sampled_projection_count": 1,
                                    "formula_cell_count": 8,
                                },
                                "observed_terms": [
                                    "수익인식60일",
                                    "해당 매출",
                                    "환불부채",
                                ],
                                "required_actions": [
                                    "confirm_or_define_local_boundary",
                                    "provide_local_policy_or_vocabulary_source",
                                    "validate_formula_results_with_excel_engine_before_numeric_claims",
                                ],
                                "warnings": [
                                    "local_domain_boundary_not_confirmed",
                                    "formula_text_only_not_recalculated_result",
                                ],
                                "evidence_refs": ["data_view:revenue"],
                                "source_artifact_refs": [
                                    "local_semantic_candidates"
                                ],
                            },
                            {
                                "id": "local_semantic_candidate:unmapped",
                                "type": "local_semantic_candidate",
                                "label": "매출 report surface A3:B26",
                                "candidate_kind": "unmapped_pivot_report_surface",
                                "source_kind": "unmapped_data_view_surface",
                                "status": "needs_semantic_interpretation",
                                "promotion_status": "not_promotable_semantic_label_pending",
                                "applicability_scope": "current_workbook_only_until_boundary_confirmed",
                                "confidence": 0.48,
                                "requires_human_review": True,
                                "local_boundary_id": "local_boundary:sample",
                                "general_domain_alignment": {
                                    "status": "unmapped_pending_semantic_interpretation",
                                    "accepted_semantic_concept_ids": [],
                                    "accepted_semantic_labels": [],
                                    "domain_source_refs": [],
                                },
                                "local_domain_evidence": {
                                    "local_domain_source_ids": [],
                                    "local_domain_boundary_ids": [
                                        "local_boundary:sample"
                                    ],
                                    "local_domain_source_status": "missing",
                                },
                                "data_view_refs": {
                                    "data_view_ids": ["data_view:report"],
                                    "projection_ids": ["projection:data_view:report"],
                                    "sheets": ["매출"],
                                    "ranges": ["A3:B26"],
                                    "projection_kinds": ["pivot_view_projection"],
                                    "roles": ["report"],
                                    "sampled_projection_count": 1,
                                    "formula_cell_count": 0,
                                },
                                "observed_terms": [
                                    "*2월 KGAAP기준 매출",
                                    "행 레이블",
                                ],
                                "required_actions": [
                                    "assign_or_confirm_semantic_label"
                                ],
                                "warnings": ["no_accepted_semantic_context"],
                                "evidence_refs": ["data_view:report"],
                                "source_artifact_refs": [
                                    "local_semantic_candidates"
                                ],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            domain_model_path.write_text(
                json.dumps(
                    {
                        "domain_layers": {
                            "general_domain_sources": [{"id": "general:1"}],
                            "local_domain_sources": [],
                            "local_domain_boundaries": [
                                {"id": "local_boundary:sample"}
                            ],
                        },
                        "semantic_readiness": {
                            "local_boundary_confirmed": False,
                            "local_domain_source_count": 0,
                        },
                    }
                ),
                encoding="utf-8",
            )
            data_view_projection_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "data_view_projection_count": 2,
                        }
                    }
                ),
                encoding="utf-8",
            )

            review = build_shared_ontology_alignment_review(
                local_semantic_candidates_path=local_candidates_path,
                domain_source_model_path=domain_model_path,
                data_view_projection_path=data_view_projection_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "workbook-shared-ontology-alignment-review.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(review)

        self.assertEqual(review["summary"]["alignment_item_count"], 2)
        self.assertEqual(review["summary"]["promoted_count"], 0)
        self.assertEqual(review["summary"]["blocked_alignment_count"], 2)
        self.assertEqual(review["summary"]["local_boundary_blocked_count"], 2)
        self.assertEqual(review["summary"]["local_source_blocked_count"], 2)
        self.assertEqual(review["summary"]["semantic_label_pending_count"], 1)
        self.assertEqual(review["summary"]["basis_review_required_count"], 2)
        self.assertEqual(review["summary"]["shared_ontology_update_count"], 0)
        self.assertEqual(
            review["summary"]["alignment_status"],
            "review_only_no_shared_promotion",
        )
        first = review["alignment_items"][0]
        self.assertEqual(first["promotion_decision"], "not_promoted")
        self.assertIn("gaap_ifrs_basis_mapping_required", first["blockers"])
        self.assertIn(
            "official_ifrs_revenue_aggregation_definition",
            first["required_evidence"],
        )
        self.assertTrue(
            any(
                question["topic"] == "gaap_ifrs_basis_separation"
                for question in review["review_questions"]
            )
        )


if __name__ == "__main__":
    unittest.main()
