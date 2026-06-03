from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_data_view_projection import build_data_view_projection  # noqa: E402


class WorkbookDataViewProjectionTest(unittest.TestCase):
    def test_projects_accepted_data_views_with_preview_and_semantic_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            graph_path = root / "validated-document-graph.json"
            readonly_path = root / "readonly-sample.json"

            graph_path.write_text(
                json.dumps(
                    {
                        "schema_version": "0.1",
                        "graph": {
                            "nodes": [
                                {
                                    "id": "semantic_concept:매출",
                                    "type": "semantic_concept",
                                    "ontology_class": "SemanticConcept",
                                    "label": "매출 집계",
                                    "status": "accepted",
                                    "sheet": None,
                                    "range": None,
                                    "properties": {
                                        "data_view_ids": ["data_view:매출"]
                                    },
                                    "evidence_refs": ["data_view:매출"],
                                    "source_artifact_refs": ["llm_proposal_validation"],
                                },
                                {
                                    "id": "block:매출_image_1",
                                    "type": "document_block",
                                    "ontology_class": "ImageBlock",
                                    "label": "매출 이미지",
                                    "status": "accepted",
                                    "sheet": "매출",
                                    "range": "A1:B2",
                                    "properties": {"candidate_type": "image"},
                                    "evidence_refs": ["manifest.drawing_objects"],
                                    "source_artifact_refs": ["block_candidates"],
                                },
                            ],
                            "relations": [],
                            "data_views": [
                                {
                                    "id": "data_view:매출",
                                    "type": "data_view",
                                    "view_kind": "formula_summary_view",
                                    "status": "accepted",
                                    "role": "summary",
                                    "sheet": "매출",
                                    "range": "A1:B2",
                                    "properties": {"confidence": 0.9},
                                    "evidence_refs": ["role_validation:매출"],
                                    "source_artifact_refs": ["pipeline_role_validation"],
                                }
                            ],
                            "semantic_aliases": [
                                {
                                    "id": "alias:매출",
                                    "type": "semantic_alias",
                                    "alias": "Revenue",
                                    "canonical_concept_id": "semantic_concept:매출",
                                    "status": "accepted",
                                    "evidence_refs": ["data_view:매출"],
                                }
                            ],
                        },
                        "carry_forward": {
                            "document_review_queue": [{"id": "review:boundary"}],
                            "proposal_review_queue": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            readonly_path.write_text(
                json.dumps(
                    {
                        "schema_version": "0.1",
                        "sheets": [
                            {
                                "name": "매출",
                                "windows": [
                                    {
                                        "rows": [
                                            {
                                                "row": 1,
                                                "cells": [
                                                    {
                                                        "cell": "A1",
                                                        "column": 1,
                                                        "value_type": "string",
                                                        "value_preview": "구분",
                                                        "formula": None,
                                                    },
                                                    {
                                                        "cell": "B1",
                                                        "column": 2,
                                                        "value_type": "string",
                                                        "value_preview": "금액",
                                                        "formula": None,
                                                    },
                                                ],
                                            },
                                            {
                                                "row": 2,
                                                "cells": [
                                                    {
                                                        "cell": "A2",
                                                        "column": 1,
                                                        "value_type": "string",
                                                        "value_preview": "2월",
                                                        "formula": None,
                                                    },
                                                    {
                                                        "cell": "B2",
                                                        "column": 2,
                                                        "value_type": "formula",
                                                        "value_preview": "=SUM(C2:C4)",
                                                        "formula": "=SUM(C2:C4)",
                                                    },
                                                ],
                                            },
                                        ]
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            projection = build_data_view_projection(
                validated_document_graph_path=graph_path,
                readonly_sample_path=readonly_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "workbook-data-view-projection.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(projection)

        self.assertEqual(projection["summary"]["data_view_projection_count"], 1)
        self.assertEqual(projection["summary"]["document_object_projection_count"], 1)
        data_view = projection["data_view_projections"][0]
        self.assertEqual(data_view["projection_kind"], "formula_summary_projection")
        self.assertEqual(data_view["preview"]["status"], "sampled")
        self.assertEqual(data_view["preview"]["sampled_row_count"], 2)
        self.assertEqual(data_view["metrics"]["formula_cell_count"], 1)
        self.assertTrue(
            data_view["formula_policy"][
                "excel_recalculation_required_for_formula_results"
            ]
        )
        self.assertIn("formula_text_only_not_recalculated_result", data_view["warnings"])
        self.assertEqual(data_view["semantic_context"]["semantic_labels"], ["매출 집계"])
        self.assertEqual(data_view["semantic_context"]["accepted_aliases"], ["Revenue"])
        self.assertEqual(data_view["related_object_ids"], ["block:매출_image_1"])


if __name__ == "__main__":
    unittest.main()
