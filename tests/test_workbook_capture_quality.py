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

from workbook_capture_quality import build_capture_quality  # noqa: E402


class WorkbookCaptureQualityTest(unittest.TestCase):
    def test_builds_quality_package_and_flags_thin_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            good_png = root / "good.png"
            thin_png = root / "thin.png"
            good = Image.new("RGBA", (240, 160), (255, 255, 255, 255))
            good_draw = ImageDraw.Draw(good)
            good_draw.rectangle((20, 20, 220, 130), fill=(32, 64, 96, 255))
            good.save(good_png)
            thin = Image.new("RGBA", (1080, 20), (255, 255, 255, 255))
            thin_draw = ImageDraw.Draw(thin)
            thin_draw.rectangle((0, 0, 1080, 18), fill=(32, 64, 96, 255))
            thin.save(thin_png)
            render_path = root / "render-captures.json"
            render_path.write_text(
                json.dumps(_render_captures(good_png, thin_png)),
                encoding="utf-8",
            )

            package = build_capture_quality(render_path)

        self.assertEqual(package["summary"]["capture_count"], 2)
        self.assertEqual(package["summary"]["recapture_required_count"], 1)
        statuses = {
            result["capture_id"]: result["status"]
            for result in package["quality_results"]
        }
        self.assertEqual(statuses["capture_good"], "usable")
        self.assertEqual(statuses["capture_thin"], "recapture_required")

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-capture-quality.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)


def _render_captures(good_png: Path, thin_png: Path) -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-06-01T00:00:00Z",
        "source_artifacts": {"cross_validation_plan": "/tmp/plan.json"},
        "source_workbook": {
            "path": "/tmp/workbook.xlsx",
            "file_name": "workbook.xlsx",
            "size_bytes": 100,
            "sha256": "0" * 64,
        },
        "method": {
            "engine": "Microsoft Excel",
            "capture_method": "range_copy_picture_png",
            "helper": "/tmp/helper.applescript",
            "sandbox_copy": True,
            "png_export_settings": {"appearance": "screen", "format": "picture"},
        },
        "selected_target_ids": ["target_good", "target_thin"],
        "captures": [
            _capture("capture_good", "target_good", "A1:C8", good_png, 240, 160),
            _capture("capture_thin", "target_thin", "A1:R22", thin_png, 1080, 20),
        ],
        "gate_results": [],
        "summary": {
            "selected_target_count": 2,
            "captured_count": 2,
            "failed_count": 0,
            "png_count": 2,
            "gate_result_count": 0,
            "captured_pending_review_gate_count": 0,
            "capture_failed_gate_count": 0,
        },
        "parser_observations": [],
    }


def _capture(
    capture_id: str,
    target_id: str,
    range_text: str,
    png_path: Path,
    width: int,
    height: int,
) -> dict:
    return {
        "id": capture_id,
        "type": "render_capture",
        "status": "captured",
        "target_id": target_id,
        "sheet": "Sheet1",
        "requested_range": range_text,
        "capture_window": {"sheet": "Sheet1", "range": range_text},
        "target_ref": {"id": target_id},
        "output": {
            "pdf_path": None,
            "png_path": str(png_path),
            "pdf_size_bytes": None,
            "png_size_bytes": png_path.stat().st_size,
            "png_width": width,
            "png_height": height,
        },
        "coordinate_map": {
            "status": "range_image_only",
            "cell_range": range_text,
            "capture_bbox": {"x": 0, "y": 0, "width": width, "height": height},
        },
        "gate_results": [],
        "parser_observations": [],
    }


if __name__ == "__main__":
    unittest.main()
