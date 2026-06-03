from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema
from openpyxl import Workbook

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_view_state_profile import build_view_state_profile  # noqa: E402


class WorkbookViewStateProfileTest(unittest.TestCase):
    def test_profiles_view_state_without_capture_quality_for_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workbook_path = root / "hidden-rows.xlsx"
            manifest_path = root / "manifest.json"
            _write_workbook(workbook_path)
            manifest_path.write_text(
                json.dumps(_manifest(workbook_path)),
                encoding="utf-8",
            )

            package = build_view_state_profile(manifest_path)

        self.assertEqual(package["summary"]["sheet_count"], 1)
        self.assertEqual(package["summary"]["hidden_row_count"], 4)
        self.assertEqual(package["summary"]["capture_window_analysis_count"], 0)
        self.assertEqual(package["source_artifacts"]["capture_quality_files"], [])

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-view-state-profile.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)

    def test_profiles_hidden_rows_and_explains_capture_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workbook_path = root / "hidden-rows.xlsx"
            manifest_path = root / "manifest.json"
            quality_path = root / "capture-quality.json"

            _write_workbook(workbook_path)
            manifest_path.write_text(
                json.dumps(_manifest(workbook_path)),
                encoding="utf-8",
            )
            quality_path.write_text(
                json.dumps(_capture_quality()),
                encoding="utf-8",
            )

            package = build_view_state_profile(manifest_path, [quality_path])

        self.assertEqual(package["summary"]["sheet_count"], 1)
        self.assertEqual(package["summary"]["hidden_row_count"], 4)
        self.assertEqual(package["summary"]["view_state_explained_count"], 1)
        analysis = package["capture_window_analyses"][0]
        self.assertEqual(analysis["row_state_summary"]["hidden_row_count"], 4)
        self.assertEqual(analysis["row_state_summary"]["visible_row_count"], 1)
        self.assertEqual(
            analysis["classification"],
            "filtered_or_hidden_rows_explain_capture_failure",
        )
        self.assertEqual(
            analysis["authority_decision"],
            "separate_visible_render_authority_from_structural_data_authority",
        )

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-view-state-profile.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)


def _write_workbook(path: Path) -> None:
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Sheet1"
    ws.append(["Header A", "Header B", "Header C"])
    for row in range(2, 11):
        ws.append([row, row * 10, row * 100])
    ws.auto_filter.ref = "A1:C10"
    for row in range(2, 6):
        ws.row_dimensions[row].hidden = True
    workbook.save(path)


def _manifest(workbook_path: Path) -> dict:
    return {
        "source": {
            "path": str(workbook_path),
            "file_name": workbook_path.name,
            "size_bytes": workbook_path.stat().st_size,
            "sha256": "0" * 64,
        },
        "workbook": {
            "sheets": [
                {
                    "name": "Sheet1",
                    "index": 0,
                    "state": "visible",
                    "entry": "xl/worksheets/sheet1.xml",
                    "dimension": "A1:C10",
                    "dimension_bounds": {
                        "min_row": 1,
                        "min_column": 1,
                        "max_row": 10,
                        "max_column": 3,
                    },
                }
            ]
        },
    }


def _capture_quality() -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-06-01T00:00:00Z",
        "source_artifacts": {"render_captures": "/tmp/render.json"},
        "method": {"name": "deterministic_png_capture_quality", "thresholds": {}},
        "quality_results": [
            {
                "id": "quality_capture_hidden",
                "type": "capture_quality_result",
                "status": "recapture_required",
                "capture_id": "capture_hidden",
                "target_id": "target_hidden",
                "sheet": "Sheet1",
                "requested_range": "A1:C5",
                "capture_window_range": "A1:C5",
                "png_path": "/tmp/hidden.png",
                "dimensions": {"width": 300, "height": 20, "size_bytes": 100},
                "range_shape": {
                    "status": "parsed",
                    "min_row": 1,
                    "min_column": 1,
                    "max_row": 5,
                    "max_column": 3,
                    "row_count": 5,
                    "column_count": 3,
                },
                "metrics": {
                    "aspect_ratio": 15,
                    "pixels_per_row": 4,
                    "pixels_per_column": 100,
                    "visible_pixel_ratio": 0.01,
                    "alpha_coverage_ratio": 1,
                },
                "checks": [],
                "recommendations": ["recapture_with_visible_row_context"],
                "evidence_refs": ["capture_hidden"],
                "notes": "thin",
            }
        ],
        "summary": {},
        "parser_observations": [],
    }
