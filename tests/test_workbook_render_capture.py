from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_render_capture import _select_targets  # noqa: E402


class WorkbookRenderCaptureTest(unittest.TestCase):
    def test_selects_recommended_targets_and_validates_schema(self) -> None:
        plan = {
            "recommended_first_batch_target_ids": ["target_a"],
            "capture_targets": [
                {"id": "target_a", "priority": "high"},
                {"id": "target_b", "priority": "medium"},
            ],
        }

        selected = _select_targets(plan, batch="recommended", target_ids=None, limit=None)

        self.assertEqual([target["id"] for target in selected], ["target_a"])

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-render-captures.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(_render_capture_package())


def _render_capture_package() -> dict:
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
            "png_export_settings": {
                "appearance": "screen",
                "format": "picture",
            },
        },
        "selected_target_ids": ["target_a"],
        "captures": [_capture()],
        "gate_results": [_gate_result()],
        "summary": {
            "selected_target_count": 1,
            "captured_count": 1,
            "failed_count": 0,
            "png_count": 1,
            "gate_result_count": 1,
            "captured_pending_review_gate_count": 1,
            "capture_failed_gate_count": 0,
        },
        "parser_observations": [],
    }


def _capture() -> dict:
    return {
        "id": "capture_target_a",
        "type": "render_capture",
        "status": "captured",
        "target_id": "target_a",
        "sheet": "Sheet1",
        "requested_range": "A1:B2",
        "capture_window": {"sheet": "Sheet1", "range": "A1:B2"},
        "target_ref": {"id": "region_a"},
        "output": {
            "pdf_path": None,
            "png_path": "/tmp/capture.png",
            "pdf_size_bytes": None,
            "png_size_bytes": 100,
            "png_width": 200,
            "png_height": 80,
        },
        "coordinate_map": {
            "status": "range_image_only",
            "cell_range": "A1:B2",
            "capture_bbox": {"x": 0, "y": 0, "width": 200, "height": 80},
        },
        "gate_results": [_gate_result()],
        "parser_observations": [{"level": "info", "message": "/tmp/capture.png"}],
    }


def _gate_result() -> dict:
    return {
        "id": "result_gate_a",
        "type": "visual_formula_gate_result",
        "capture_id": "capture_target_a",
        "target_id": "target_a",
        "gate_check_id": "gate_a",
        "gate_type": "boundary_confirmation",
        "status": "captured_pending_review",
        "evidence_refs": ["capture_target_a"],
        "notes": "Captured.",
    }


if __name__ == "__main__":
    unittest.main()
