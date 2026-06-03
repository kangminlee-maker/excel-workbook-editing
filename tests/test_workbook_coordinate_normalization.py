from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_coordinate_normalization import build_coordinate_normalization  # noqa: E402


class WorkbookCoordinateNormalizationTest(unittest.TestCase):
    def test_normalizes_usable_capture_and_blocks_hidden_view_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            render_path = root / "render.json"
            quality_path = root / "quality.json"
            view_state_path = root / "view-state.json"
            render_path.write_text(json.dumps(_render_captures()), encoding="utf-8")
            quality_path.write_text(json.dumps(_capture_quality()), encoding="utf-8")
            view_state_path.write_text(json.dumps(_view_state_profile()), encoding="utf-8")

            package = build_coordinate_normalization(
                [(render_path, quality_path)],
                view_state_profile_path=view_state_path,
            )

        statuses = {
            mapping["capture_id"]: mapping["status"]
            for mapping in package["coordinate_mappings"]
        }
        self.assertEqual(statuses["capture_good"], "normalized_visible_range")
        self.assertEqual(statuses["capture_hidden"], "blocked_by_view_state")
        self.assertEqual(package["summary"]["passed_gate_count"], 1)
        self.assertEqual(package["summary"]["blocked_by_view_state_count"], 1)

        schema = json.loads(
            (
                REPO_ROOT / "schemas" / "workbook-coordinate-normalization.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(package)


def _render_captures() -> dict:
    return {
        "captures": [
            _capture("capture_good", "target_good", "A1:C10", 300, 200),
            _capture("capture_hidden", "target_hidden", "A1:C5", 300, 20),
        ]
    }


def _capture(
    capture_id: str,
    target_id: str,
    range_text: str,
    width: int,
    height: int,
) -> dict:
    return {
        "id": capture_id,
        "status": "captured",
        "target_id": target_id,
        "capture_window": {"range": range_text},
        "coordinate_map": {
            "status": "range_image_only",
            "cell_range": range_text,
            "capture_bbox": {"x": 0, "y": 0, "width": width, "height": height},
        },
    }


def _capture_quality() -> dict:
    return {
        "quality_results": [
            _quality("quality_good", "capture_good", "target_good", "usable", "A1:C10"),
            _quality(
                "quality_hidden",
                "capture_hidden",
                "target_hidden",
                "recapture_required",
                "A1:C5",
            ),
        ]
    }


def _quality(
    quality_id: str,
    capture_id: str,
    target_id: str,
    status: str,
    range_text: str,
) -> dict:
    return {
        "id": quality_id,
        "capture_id": capture_id,
        "target_id": target_id,
        "status": status,
        "sheet": "Sheet1",
        "requested_range": range_text,
        "capture_window_range": range_text,
        "dimensions": {"width": 300, "height": 200, "size_bytes": 100},
    }


def _view_state_profile() -> dict:
    return {
        "capture_window_analyses": [
            {
                "id": "view_state_quality_hidden",
                "quality_result_id": "quality_hidden",
                "classification": "filtered_or_hidden_rows_explain_capture_failure",
                "authority_decision": "separate_visible_render_authority_from_structural_data_authority",
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
