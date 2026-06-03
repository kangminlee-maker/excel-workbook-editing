from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_table_io_pipeline import build_table_io_pipelines  # noqa: E402


class WorkbookTableIoPipelineTest(unittest.TestCase):
    def test_projects_formula_and_pivot_relations_to_table_io_pipelines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            candidates_path = Path(tmpdir) / "block-candidates.json"
            candidates_path.write_text(
                json.dumps(_block_candidates()),
                encoding="utf-8",
            )

            package = build_table_io_pipelines(candidates_path)

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-table-io-pipeline.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        self.assertEqual(package["schema_version"], "0.1")
        self.assertEqual(package["summary"]["pipeline_count"], 2)
        self.assertEqual(package["summary"]["formula_pipeline_count"], 1)
        self.assertEqual(package["summary"]["pivot_pipeline_count"], 1)

        formula_pipeline = next(
            pipeline for pipeline in package["pipelines"] if pipeline["role"] == "summary"
        )
        self.assertEqual(formula_pipeline["output_ref"]["region_id"], "summary_region")
        self.assertEqual(formula_pipeline["input_refs"][0]["region_id"], "raw_region")
        self.assertIn("repeated_formula_family", formula_pipeline["review_flags"])

        pivot_pipeline = next(
            pipeline for pipeline in package["pipelines"] if pipeline["role"] == "report"
        )
        self.assertEqual(pivot_pipeline["output_ref"]["block_id"], "pivot_block")
        self.assertEqual(pivot_pipeline["input_refs"][0]["region_id"], "raw_region")
        self.assertIn("pivot_cache_dependency", pivot_pipeline["review_flags"])


def _block_candidates() -> dict:
    return {
        "schema_version": "0.1",
        "sheets": [
            {
                "name": "Raw",
                "blocks": [_row_band("raw_band", "Raw", 1, 1, 100, 2)],
                "cell_regions": [_cell_region("raw_region", "raw_band", "Raw", 1, 1, 100, 2)],
                "relations": [],
                "relation_groups": [],
            },
            {
                "name": "Summary",
                "blocks": [_row_band("summary_band", "Summary", 1, 1, 10, 2)],
                "cell_regions": [
                    _cell_region("summary_region", "summary_band", "Summary", 1, 1, 10, 2)
                ],
                "relations": [],
                "relation_groups": [
                    {
                        "id": "group_summary_raw",
                        "type": "formula_signature_group",
                        "source_block_id": "summary_band",
                        "relation_type": "formula_references",
                        "reference_kind": "workbook_range",
                        "target_workbook": None,
                        "target_sheet": "Raw",
                        "formula_signature": "SUMIFS(Raw!$B:$B,Raw!$A:$A,Summary!R[0]C[-1])",
                        "formula_cell_count": 12,
                        "reference_count": 1,
                        "source_cell_samples": ["B2"],
                        "target_bounds_union": {
                            "min_row": 1,
                            "min_column": 1,
                            "max_row": 100,
                            "max_column": 2,
                        },
                    }
                ],
            },
            {
                "name": "Report",
                "blocks": [_pivot_block()],
                "cell_regions": [],
                "relations": [
                    {
                        "id": "rel_pivot_cache",
                        "type": "derived_from_pivot_cache_source",
                        "from": "pivot_block",
                        "to": "range:Raw!A1:B100",
                    }
                ],
                "relation_groups": [],
            },
        ],
    }


def _row_band(
    block_id: str,
    sheet: str,
    start_row: int,
    start_column: int,
    end_row: int,
    end_column: int,
) -> dict:
    return {
        "id": block_id,
        "type": "row_band",
        "subtype": "table_candidate",
        "label": block_id,
        "source": {"sheet": sheet},
        "bounds": {
            "start_row": start_row,
            "start_column": start_column,
            "end_row": end_row,
            "end_column": end_column,
            "start_cell": f"A{start_row}",
            "end_cell": f"B{end_row}",
        },
    }


def _cell_region(
    region_id: str,
    parent_id: str,
    sheet: str,
    start_row: int,
    start_column: int,
    end_row: int,
    end_column: int,
) -> dict:
    return {
        "id": region_id,
        "type": "cell_region",
        "subtype": "table_candidate",
        "parent_seed_block_id": parent_id,
        "label": region_id,
        "source": {"sheet": sheet},
        "bounds": {
            "start_row": start_row,
            "start_column": start_column,
            "end_row": end_row,
            "end_column": end_column,
            "start_cell": f"A{start_row}",
            "end_cell": f"B{end_row}",
        },
    }


def _pivot_block() -> dict:
    return {
        "id": "pivot_block",
        "type": "pivot_table",
        "subtype": "pivot_table",
        "label": "Pivot Report",
        "source": {"sheet": "Report"},
        "bounds": {
            "start_row": 1,
            "start_column": 1,
            "end_row": 5,
            "end_column": 4,
            "start_cell": "A1",
            "end_cell": "D5",
        },
    }


if __name__ == "__main__":
    unittest.main()
