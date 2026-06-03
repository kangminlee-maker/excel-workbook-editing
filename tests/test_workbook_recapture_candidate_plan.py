from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_recapture_candidate_plan import build_recapture_candidate_plan  # noqa: E402


class WorkbookRecaptureCandidatePlanTest(unittest.TestCase):
    def test_builds_candidate_plan_without_treating_candidates_as_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            render_path = root / "render-captures.json"
            quality_path = root / "capture-quality.json"
            render_path.write_text(json.dumps(_render_captures()), encoding="utf-8")
            quality_path.write_text(json.dumps(_capture_quality()), encoding="utf-8")

            package = build_recapture_candidate_plan(render_path, quality_path)

        self.assertEqual(package["method"]["authority"], "candidate_generation_not_final_selection")
        self.assertEqual(package["summary"]["source_capture_count"], 2)
        self.assertEqual(package["summary"]["same_window_control_count"], 1)
        self.assertEqual(package["summary"]["visible_row_context_count"], 1)
        self.assertEqual(package["summary"]["column_tile_count"], 3)
        self.assertEqual(
            len(package["recommended_first_batch_target_ids"]),
            package["summary"]["candidate_target_count"],
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "workbook-recapture-candidate-plan.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(package)


def _render_captures() -> dict:
    return {
        "captures": [
            _capture("capture_thin", "Sheet1", "A1:R22", "A1:Q20"),
            _capture("capture_wide", "Sheet2", "A1:AY22", "A1:AX20"),
        ]
    }


def _capture(capture_id: str, sheet: str, window_range: str, target_range: str) -> dict:
    return {
        "id": capture_id,
        "status": "captured",
        "target_id": f"target_{capture_id}",
        "sheet": sheet,
        "requested_range": target_range,
        "capture_window": {
            "sheet": sheet,
            "range": window_range,
            "bounds": _bounds(window_range),
            "authority": "excel_render_capture",
            "coordinate_systems": ["cell_range", "grid_coordinate", "capture_bbox"],
        },
        "target_ref": {
            "id": f"region_{capture_id}",
            "kind": "cell_region",
            "sheet": sheet,
            "range": target_range,
            "bounds": _bounds(target_range),
        },
    }


def _capture_quality() -> dict:
    return {
        "quality_results": [
            {
                "id": "quality_thin",
                "status": "recapture_required",
                "capture_id": "capture_thin",
                "capture_window_range": "A1:R22",
                "recommendations": [
                    "recapture_with_expanded_window_or_zoom",
                    "recapture_with_visible_row_context",
                ],
            },
            {
                "id": "quality_wide",
                "status": "review_required",
                "capture_id": "capture_wide",
                "capture_window_range": "A1:AY22",
                "recommendations": ["recapture_with_tiling"],
            },
        ]
    }


def _bounds(range_text: str) -> dict:
    from openpyxl.utils import range_boundaries

    min_col, min_row, max_col, max_row = range_boundaries(range_text)
    return {
        "min_row": min_row,
        "min_column": min_col,
        "max_row": max_row,
        "max_column": max_col,
    }


if __name__ == "__main__":
    unittest.main()
