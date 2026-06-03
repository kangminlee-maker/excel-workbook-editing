from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_data_view_projection import build_google_sheets_data_view_projection  # noqa: E402


class GoogleSheetsDataViewProjectionTest(unittest.TestCase):
    def test_projects_pipeline_preview_without_formula_result_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            graph_path = root / "live-validated-document-graph.json"
            evidence_path = root / "live-evidence-package.json"
            sample_path = root / "top-left-sample.json"
            graph_path.write_text(json.dumps(_graph(), ensure_ascii=False), encoding="utf-8")
            evidence_path.write_text(json.dumps(_evidence(), ensure_ascii=False), encoding="utf-8")
            sample_path.write_text(json.dumps(_sample(), ensure_ascii=False), encoding="utf-8")

            projection = build_google_sheets_data_view_projection(
                live_validated_document_graph_path=graph_path,
                live_evidence_package_path=evidence_path,
                top_left_sample_path=sample_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-data-view-projection.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(projection)

        self.assertEqual(projection["summary"]["data_view_projection_count"], 2)
        self.assertEqual(projection["summary"]["calculation_pipeline_projection_count"], 1)
        pipeline_view = next(
            item
            for item in projection["data_view_projections"]
            if item["projection_kind"] == "calculation_pipeline_projection"
        )
        self.assertEqual(pipeline_view["preview"]["status"], "sampled_from_top_left_window")
        self.assertEqual(pipeline_view["preview"]["sampled_formula_cell_count"], 1)
        self.assertEqual(pipeline_view["formula_policy"]["formula_result_authority"], "not_established")
        self.assertIn("formula_text_only_not_recalculated_result", pipeline_view["warnings"])
        self.assertEqual(projection["summary"]["shared_ontology_update_count"], 0)


def _graph() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "graph": {
            "nodes": [
                {
                    "id": "node_workbook",
                    "type": "workbook_document",
                    "label": "Live Sheet",
                    "properties": {},
                    "evidence_refs": ["live-evidence-package.json"],
                },
                {
                    "id": "node_pipeline_ok",
                    "type": "calculation_pipeline",
                    "label": "formula surface",
                    "properties": {"pipeline_id": "pipeline_ok"},
                    "evidence_refs": ["pipeline_ok"],
                },
            ]
        },
        "carry_forward": {
            "document_review_queue": [],
            "semantic_validation_review_queue": [{"id": "review_semantic"}],
        },
    }


def _evidence() -> dict:
    return {
        "accepted_evidence": {
            "pipelines": [
                {
                    "id": "pipeline_ok",
                    "role": "calculation",
                    "input_refs": [
                        {
                            "id": "input_1",
                            "kind": "table_candidate",
                            "role": "input",
                            "sheet": "24_0102",
                            "range": "A1:B2",
                            "label": "Input",
                            "authority": "block_candidate",
                        }
                    ],
                    "output_refs": [
                        {
                            "id": "output_1",
                            "kind": "formula_region_candidate",
                            "role": "output",
                            "sheet": "24_0102",
                            "range": "B2:C3",
                            "bounds": {
                                "start_row": 2,
                                "end_row": 3,
                                "start_column": 2,
                                "end_column": 3,
                            },
                            "label": "Output",
                            "authority": "block_candidate",
                        }
                    ],
                    "transform_refs": [
                        {
                            "kind": "formula_dependency_edge",
                            "formula_count": 2,
                            "signature_group_ids": ["sig_1"],
                            "repeated_formula_family": True,
                        }
                    ],
                    "evidence_refs": ["sig_1"],
                    "review_flags": ["formula_result_not_established"],
                }
            ]
        }
    }


def _sample() -> dict:
    return {
        "tabs": [
            {
                "title": "24_0102",
                "sample_range": "A1:Z80",
                "display_rows": [
                    ["Header", "Old", "New"],
                    ["FC", "119", "126"],
                    ["SB", "29", "29"],
                ],
                "formula_rows": [
                    ["Header", "Old", "New"],
                    ["FC", 119, "=B2+7"],
                    ["SB", 29, 29],
                ],
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
