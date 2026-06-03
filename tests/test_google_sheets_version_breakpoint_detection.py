from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_version_breakpoint_detection import (  # noqa: E402
    build_google_sheets_version_breakpoint_detection,
)


class GoogleSheetsVersionBreakpointDetectionTest(unittest.TestCase):
    def test_detects_multisignal_breakpoint_and_review_required_group_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_json(root / "live-manifest.json", _manifest())
            _write_json(root / "live-block-candidates.json", _blocks())
            _write_json(root / "live-view-formula-profile.json", _formula_profile())
            _write_json(root / "live-blocker-resolution-update.json", _blocker_update())
            _write_json(root / "live-document-item-grouping-checkpoint.json", _grouping())

            detection = build_google_sheets_version_breakpoint_detection(out_dir=root)

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-version-breakpoint-detection.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(detection)

        self.assertEqual(detection["summary"]["version_group_count"], 1)
        self.assertEqual(detection["summary"]["review_required_version_group_count"], 1)
        self.assertEqual(detection["summary"]["accepted_version_breakpoint_count"], 1)
        self.assertEqual(detection["summary"]["shared_ontology_update_count"], 0)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _manifest() -> dict:
    return {
        "source": {"spreadsheet_id": "sheet-1", "spreadsheet_url": None, "title": "Live Sheet"},
        "workbook": {
            "sheets": [
                _sheet("25_0201", 0, 12),
                _sheet("25_0125", 1, 10),
            ]
        },
    }


def _sheet(name: str, index: int, columns: int) -> dict:
    return {
        "name": name,
        "index": index,
        "state": "visible",
        "dimensions": {"column_count": columns, "row_count": 100},
    }


def _blocks() -> dict:
    return {
        "sheets": [
            {"name": "25_0201", "summary": {"table_candidate_count": 3, "section_heading_count": 2, "formula_region_candidate_count": 1, "object_surface_count": 1}},
            {"name": "25_0125", "summary": {"table_candidate_count": 1, "section_heading_count": 1, "formula_region_candidate_count": 1, "object_surface_count": 1}},
        ]
    }


def _formula_profile() -> dict:
    return {
        "signature_groups": [
            {"id": "sig_a", "source_sheets": ["25_0201", "25_0125"]},
            {"id": "sig_b", "source_sheets": ["25_0201"]},
        ]
    }


def _blocker_update() -> dict:
    return {
        "lineage_observations": {
            "version_group_candidates": [
                {"id": "group_1", "newest_tab": "25_0201", "oldest_tab": "25_0125", "column_count": 12}
            ],
            "version_breakpoint_candidates": [
                {
                    "id": "break_1",
                    "newer_tab": "25_0201",
                    "older_tab": "25_0125",
                    "newer_column_count": 12,
                    "older_column_count": 10,
                    "reason": "column count changed",
                }
            ],
        }
    }


def _grouping() -> dict:
    return {
        "document_items": [
            {"sheet": "25_0201", "status": "accepted", "item_kind": "formula_dataflow_pipeline_group"},
            {"sheet": "25_0201", "status": "review_required", "item_kind": "section_with_child_blocks"},
            {"sheet": "25_0125", "status": "review_required", "item_kind": "section_with_child_blocks"},
        ]
    }


if __name__ == "__main__":
    unittest.main()
