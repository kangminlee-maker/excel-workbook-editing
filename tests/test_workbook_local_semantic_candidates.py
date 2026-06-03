from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_local_semantic_candidates import build_local_semantic_candidates  # noqa: E402


class WorkbookLocalSemanticCandidatesTest(unittest.TestCase):
    def test_generates_boundary_pending_and_unmapped_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            projection_path = root / "data-view-projection.json"
            domain_path = root / "domain-source-model.json"
            graph_path = root / "validated-graph.json"

            projection_path.write_text(
                json.dumps(
                    {
                        "data_view_projections": [
                            {
                                "id": "projection:data_view:매출",
                                "type": "data_view_projection",
                                "projection_kind": "formula_summary_projection",
                                "data_view_id": "data_view:매출",
                                "role": "summary",
                                "sheet": "매출",
                                "range": "A1:B2",
                                "semantic_context": {
                                    "semantic_concept_ids": ["semantic_concept:매출"],
                                    "semantic_labels": ["매출 집계"],
                                    "accepted_aliases": ["Revenue"],
                                },
                                "preview": {
                                    "status": "sampled",
                                    "rows": [
                                        {
                                            "row": 1,
                                            "cells": [
                                                {
                                                    "cell": "A1",
                                                    "column": 1,
                                                    "value_type": "string",
                                                    "value_preview": "매출",
                                                    "formula": None,
                                                }
                                            ],
                                        }
                                    ],
                                    "sampled_row_count": 1,
                                },
                                "metrics": {
                                    "sampled_row_count": 1,
                                    "sampled_cell_count": 1,
                                    "formula_cell_count": 1,
                                    "number_cell_count": 0,
                                    "string_cell_count": 1,
                                    "datetime_cell_count": 0,
                                },
                                "warnings": [
                                    "formula_text_only_not_recalculated_result"
                                ],
                                "evidence_refs": ["role_validation:매출"],
                                "source_artifact_refs": ["data_view_projection"],
                            },
                            {
                                "id": "projection:data_view:미분류",
                                "type": "data_view_projection",
                                "projection_kind": "pivot_view_projection",
                                "data_view_id": "data_view:미분류",
                                "role": "report",
                                "sheet": "미분류",
                                "range": "D1:E4",
                                "semantic_context": {
                                    "semantic_concept_ids": [],
                                    "semantic_labels": [],
                                    "accepted_aliases": [],
                                },
                                "preview": {
                                    "status": "sampled",
                                    "rows": [
                                        {
                                            "row": 1,
                                            "cells": [
                                                {
                                                    "cell": "D1",
                                                    "column": 4,
                                                    "value_type": "string",
                                                    "value_preview": "행 레이블",
                                                    "formula": None,
                                                }
                                            ],
                                        }
                                    ],
                                    "sampled_row_count": 1,
                                },
                                "metrics": {
                                    "sampled_row_count": 1,
                                    "sampled_cell_count": 1,
                                    "formula_cell_count": 0,
                                    "number_cell_count": 0,
                                    "string_cell_count": 1,
                                    "datetime_cell_count": 0,
                                },
                                "warnings": [],
                                "evidence_refs": ["role_validation:미분류"],
                                "source_artifact_refs": ["data_view_projection"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            domain_path.write_text(
                json.dumps(
                    {
                        "domain_layers": {
                            "general_domain_sources": [],
                            "local_domain_sources": [],
                            "local_domain_boundaries": [
                                {
                                    "id": "local_boundary:sample",
                                    "status": "review_required",
                                    "scope": "current_workbook_only_until_boundary_confirmed",
                                }
                            ],
                        },
                        "semantic_readiness": {
                            "local_boundary_confirmed": False,
                            "local_domain_source_count": 0,
                        },
                        "review_queue": [
                            {
                                "id": "review:local_boundary",
                                "kind": "local_domain_boundary",
                                "required_action": "confirm_or_define_local_boundary",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            graph_path.write_text(
                json.dumps(
                    {
                        "graph": {
                            "nodes": [
                                {
                                    "id": "semantic_concept:매출",
                                    "type": "semantic_concept",
                                    "label": "매출 집계",
                                    "properties": {
                                        "concept_kind": "revenue_summary",
                                        "domain_source_refs": [
                                            "general_domain:accounting-kr/concepts.md"
                                        ],
                                    },
                                    "evidence_refs": ["data_view:매출"],
                                    "source_artifact_refs": [
                                        "llm_proposals",
                                        "llm_proposal_validation",
                                    ],
                                }
                            ],
                            "relations": [],
                            "data_views": [],
                            "semantic_aliases": [],
                        }
                    }
                ),
                encoding="utf-8",
            )

            candidates = build_local_semantic_candidates(
                data_view_projection_path=projection_path,
                domain_source_model_path=domain_path,
                validated_document_graph_path=graph_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "workbook-local-semantic-candidates.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(candidates)

        self.assertEqual(candidates["summary"]["local_semantic_candidate_count"], 2)
        self.assertEqual(candidates["summary"]["accepted_context_candidate_count"], 1)
        self.assertEqual(candidates["summary"]["unmapped_data_view_candidate_count"], 1)
        self.assertFalse(candidates["summary"]["local_boundary_confirmed"])
        self.assertEqual(
            candidates["summary"]["shared_promotion_allowed_candidate_count"], 0
        )
        by_source = {
            item["source_kind"]: item for item in candidates["local_semantic_candidates"]
        }
        accepted = by_source["accepted_semantic_context"]
        self.assertEqual(accepted["status"], "local_candidate_boundary_pending")
        self.assertIn("Revenue", accepted["observed_terms"])
        self.assertIn(
            "not_promotable_shared_ontology_boundary_pending",
            accepted["promotion_status"],
        )
        unmapped = by_source["unmapped_data_view_surface"]
        self.assertEqual(unmapped["status"], "needs_semantic_interpretation")
        self.assertIn("assign_or_confirm_semantic_label", unmapped["required_actions"])
        self.assertIn("no_accepted_semantic_context", unmapped["warnings"])
        self.assertEqual(candidates["summary"]["covered_data_view_count"], 2)


if __name__ == "__main__":
    unittest.main()
