from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_cross_validation_plan import build_cross_validation_plan  # noqa: E402


class WorkbookCrossValidationPlanTest(unittest.TestCase):
    def test_prioritizes_unresolved_pivot_boundary_and_image_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            block_candidates_path = Path(tmpdir) / "block-candidates.json"
            table_io_path = Path(tmpdir) / "table-io.json"
            block_candidates_path.write_text(
                json.dumps(_block_candidates()),
                encoding="utf-8",
            )
            table_io_path.write_text(
                json.dumps(_table_io_pipelines()),
                encoding="utf-8",
            )

            package = build_cross_validation_plan(block_candidates_path, table_io_path)

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-cross-validation-plan.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        self.assertEqual(package["schema_version"], "0.1")
        self.assertGreaterEqual(package["summary"]["capture_target_count"], 3)
        self.assertEqual(package["summary"]["unresolved_input_target_count"], 1)
        self.assertEqual(package["summary"]["pivot_report_target_count"], 1)
        self.assertEqual(package["summary"]["image_hierarchy_target_count"], 1)
        self.assertGreaterEqual(package["summary"]["recommended_first_batch_count"], 1)
        self.assertTrue(package["recommended_first_batch_target_ids"])

        gate_types = {check["gate_type"] for check in package["gate_checks"]}
        self.assertIn("unresolved_input_region_resolution", gate_types)
        self.assertIn("pivot_cache_visual_alignment", gate_types)
        self.assertIn("boundary_confirmation", gate_types)
        self.assertIn("image_table_hierarchy_confirmation", gate_types)


def _block_candidates() -> dict:
    return {
        "schema_version": "0.1",
        "sheets": [
            {
                "name": "Summary",
                "blocks": [
                    _row_band("summary_band", "Summary", 1, 1, 10, 2),
                    _image("image_1", "Summary", 1, 4, 5, 6),
                ],
                "cell_regions": [
                    _cell_region("summary_region", "summary_band", "Summary", 1, 1, 10, 2)
                ],
                "relations": [
                    {
                        "id": "rel_image_summary",
                        "type": "adjacent_left_of",
                        "from": "summary_band",
                        "to": "image_1",
                    }
                ],
                "boundary_gate_results": [
                    {
                        "id": "gate_split_summary_c1_c2",
                        "type": "split_candidate_gate",
                        "sheet": "Summary",
                        "candidate_id": "split_summary_c1_c2",
                        "candidate_type": "style_discontinuity_boundary",
                        "related_region_ids": ["summary_region"],
                        "score": 0.62,
                        "status": "review_candidate",
                        "decision": "do_not_auto_split",
                        "evidence": ["style_discontinuity_boundary"],
                        "rationale": "Needs visual confirmation.",
                    }
                ],
            },
            {
                "name": "Report",
                "blocks": [_pivot_block()],
                "cell_regions": [],
                "relations": [],
                "boundary_gate_results": [],
            },
        ],
    }


def _table_io_pipelines() -> dict:
    return {
        "schema_version": "0.1",
        "pipelines": [
            {
                "id": "pipeline_summary",
                "type": "table_io_pipeline",
                "status": "candidate",
                "role": "summary",
                "output_ref": _ref("summary_region", "cell_region", "Summary", "A1:B10"),
                "input_refs": [
                    _ref("range_summary_b20", "workbook_range", "Summary", "B20:B20")
                ],
                "transform_refs": [],
                "evidence_refs": ["group_summary"],
                "confidence": 0.7,
                "review_flags": ["unresolved_input_region", "repeated_formula_family"],
            },
            {
                "id": "pipeline_pivot",
                "type": "table_io_pipeline",
                "status": "candidate",
                "role": "report",
                "output_ref": _ref("pivot_block", "pivot_table", "Report", "A1:D5"),
                "input_refs": [],
                "transform_refs": [],
                "evidence_refs": ["rel_pivot_cache"],
                "confidence": 0.87,
                "review_flags": ["pivot_cache_dependency"],
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
        "bounds": _bounds(start_row, start_column, end_row, end_column),
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
        "bounds": _bounds(start_row, start_column, end_row, end_column),
    }


def _image(
    block_id: str,
    sheet: str,
    start_row: int,
    start_column: int,
    end_row: int,
    end_column: int,
) -> dict:
    return {
        "id": block_id,
        "type": "image",
        "subtype": "image_anchor",
        "label": block_id,
        "source": {"sheet": sheet},
        "bounds": _bounds(start_row, start_column, end_row, end_column),
    }


def _pivot_block() -> dict:
    return {
        "id": "pivot_block",
        "type": "pivot_table",
        "subtype": "pivot_table",
        "label": "Pivot Report",
        "source": {"sheet": "Report"},
        "bounds": _bounds(1, 1, 5, 4),
    }


def _ref(ref_id: str, kind: str, sheet: str, range_text: str) -> dict:
    bounds = {
        "A1:B10": {"min_row": 1, "min_column": 1, "max_row": 10, "max_column": 2},
        "A1:D5": {"min_row": 1, "min_column": 1, "max_row": 5, "max_column": 4},
        "B20:B20": {"min_row": 20, "min_column": 2, "max_row": 20, "max_column": 2},
    }[range_text]
    return {
        "id": ref_id,
        "kind": kind,
        "workbook": None,
        "sheet": sheet,
        "range": range_text,
        "block_id": ref_id if kind == "pivot_table" else "summary_band",
        "region_id": ref_id if kind == "cell_region" else None,
        "bounds": bounds,
        "label": ref_id,
    }


def _bounds(
    start_row: int,
    start_column: int,
    end_row: int,
    end_column: int,
) -> dict:
    return {
        "start_row": start_row,
        "start_column": start_column,
        "end_row": end_row,
        "end_column": end_column,
        "start_cell": f"A{start_row}",
        "end_cell": f"D{end_row}",
    }


if __name__ == "__main__":
    unittest.main()
