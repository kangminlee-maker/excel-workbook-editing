from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema
from PIL import Image
from PIL import ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_visual_feature_detection import build_visual_feature_detection  # noqa: E402


class WorkbookVisualFeatureDetectionTest(unittest.TestCase):
    def test_detects_grid_features_and_skips_view_state_blocked_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            png_path = root / "grid.png"
            render_path = root / "render.json"
            coordinate_path = root / "coordinate.json"
            _write_grid_image(png_path)
            render_path.write_text(
                json.dumps(_render_captures(png_path)),
                encoding="utf-8",
            )
            coordinate_path.write_text(
                json.dumps(_coordinate_normalization(render_path)),
                encoding="utf-8",
            )

            package = build_visual_feature_detection(coordinate_path)

        statuses = {
            result["capture_id"]: result["status"]
            for result in package["feature_results"]
        }
        self.assertEqual(statuses["capture_grid"], "detected")
        self.assertEqual(statuses["capture_hidden"], "skipped_view_state_blocked")
        detected = next(
            result
            for result in package["feature_results"]
            if result["capture_id"] == "capture_grid"
        )
        self.assertIn("visible_content_bbox", detected["layout_signals"])
        self.assertGreaterEqual(detected["line_features"]["horizontal_line_count"], 2)
        self.assertGreaterEqual(detected["line_features"]["vertical_line_count"], 2)

        schema = json.loads(
            (
                REPO_ROOT / "schemas" / "workbook-visual-feature-detection.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(package)


def _write_grid_image(path: Path) -> None:
    image = Image.new("RGBA", (120, 80), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    for y in (10, 40, 70):
        draw.line((5, y, 115, y), fill=(20, 20, 20, 255), width=2)
    for x in (5, 60, 115):
        draw.line((x, 10, x, 70), fill=(20, 20, 20, 255), width=2)
    draw.rectangle((20, 20, 50, 32), fill=(80, 120, 160, 255))
    image.save(path)


def _render_captures(png_path: Path) -> dict:
    return {
        "captures": [
            {
                "id": "capture_grid",
                "status": "captured",
                "target_id": "target_grid",
                "output": {"png_path": str(png_path)},
            },
            {
                "id": "capture_hidden",
                "status": "captured",
                "target_id": "target_hidden",
                "output": {"png_path": str(png_path)},
            },
        ]
    }


def _coordinate_normalization(render_path: Path) -> dict:
    return {
        "source_artifacts": {
            "render_capture_files": [str(render_path)],
        },
        "coordinate_mappings": [
            _mapping(
                "coord_grid",
                "normalized_visible_range",
                "capture_grid",
                "target_grid",
            ),
            _mapping(
                "coord_hidden",
                "blocked_by_view_state",
                "capture_hidden",
                "target_hidden",
            ),
        ],
    }


def _mapping(
    mapping_id: str,
    status: str,
    capture_id: str,
    target_id: str,
) -> dict:
    return {
        "id": mapping_id,
        "status": status,
        "capture_id": capture_id,
        "target_id": target_id,
        "sheet": "Sheet1",
        "cell_range": "A1:C5",
        "range_bounds": {
            "min_row": 1,
            "min_column": 1,
            "max_row": 5,
            "max_column": 3,
        },
        "quality_status": "usable",
        "view_state_classification": (
            "filtered_or_hidden_rows_explain_capture_failure"
            if status == "blocked_by_view_state"
            else "no_material_view_state_signal"
        ),
    }


if __name__ == "__main__":
    unittest.main()
