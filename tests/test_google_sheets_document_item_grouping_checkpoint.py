from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_document_item_grouping_checkpoint import (  # noqa: E402
    build_google_sheets_document_item_grouping_checkpoint,
)


class GoogleSheetsDocumentItemGroupingCheckpointTest(unittest.TestCase):
    def test_accepts_formula_pipeline_and_keeps_ordering_groups_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_json(root / "live-manifest.json", _manifest())
            _write_json(root / "live-block-candidates.json", _block_candidates())
            _write_json(root / "live-table-io-pipelines.json", _pipelines())
            _write_json(root / "live-formula-result-authority-checkpoint.json", _formula_authority())

            checkpoint = build_google_sheets_document_item_grouping_checkpoint(out_dir=root)

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-document-item-grouping-checkpoint.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(checkpoint)

        self.assertEqual(checkpoint["summary"]["pipeline_group_count"], 1)
        self.assertEqual(checkpoint["summary"]["accepted_document_item_count"], 1)
        self.assertEqual(checkpoint["summary"]["section_group_count"], 1)
        self.assertEqual(checkpoint["summary"]["orphan_surface_count"], 1)
        statuses = {item["item_kind"]: item["status"] for item in checkpoint["document_items"]}
        self.assertEqual(statuses["formula_dataflow_pipeline_group"], "accepted")
        self.assertEqual(statuses["section_with_child_blocks"], "review_required")
        self.assertEqual(checkpoint["summary"]["shared_ontology_update_count"], 0)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _manifest() -> dict:
    return {
        "source": {
            "spreadsheet_id": "sheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/sheet-1/edit",
            "title": "Live Sheet",
        }
    }


def _block_candidates() -> dict:
    heading = {
        "id": "block_sheet_001",
        "type": "section_heading",
        "sheet": "24_0102",
        "label": "A. Overview",
        "bounds": _bounds("A1:A1", 1, 1, 1, 1),
        "evidence": ["sample"],
    }
    table = {
        "id": "block_sheet_002",
        "type": "table_candidate",
        "sheet": "24_0102",
        "label": "Payment Amount",
        "bounds": _bounds("B2:C5", 2, 5, 2, 3),
        "evidence": ["sample"],
    }
    obj = {
        "id": "block_sheet_object",
        "type": "object_surface",
        "sheet": "24_0102",
        "label": "object surface",
        "bounds": _bounds("A1:Z80", 1, 80, 1, 26),
        "evidence": ["grid_profile"],
    }
    return {
        "summary": {
            "block_count": 3,
            "relation_count": 1,
            "object_surface_count": 1,
        },
        "sheets": [
            {
                "name": "24_0102",
                "blocks": [heading, table, obj],
                "relations": [
                    {
                        "id": "rel_heading_contains_table",
                        "type": "section_contains_block_candidate",
                        "from": "block_sheet_001",
                        "to": "block_sheet_002",
                        "confidence": 0.62,
                    }
                ],
            }
        ],
    }


def _pipelines() -> dict:
    return {
        "pipelines": [
            {
                "id": "pipeline_clean",
                "label": "clean formula output",
                "input_refs": [
                    {
                        "id": "input_1",
                        "kind": "table_candidate",
                        "sheet": "24_0102",
                        "range": "A1:B2",
                        "label": "input",
                        "authority": "block_candidate",
                    }
                ],
                "output_refs": [
                    {
                        "id": "output_1",
                        "kind": "formula_region_candidate",
                        "sheet": "24_0102",
                        "range": "B8:C8",
                        "label": "output",
                        "authority": "block_candidate",
                    }
                ],
                "evidence_refs": ["edge_clean"],
            }
        ]
    }


def _formula_authority() -> dict:
    return {
        "pipeline_authority_results": [
            {
                "id": "pipeline_result_clean",
                "pipeline_id": "pipeline_clean",
                "status": "accepted",
                "sheet": "24_0102",
                "range": "B8:C8",
                "blockers": [],
            }
        ]
    }


def _bounds(a1: str, start_row: int, end_row: int, start_column: int, end_column: int) -> dict:
    return {
        "start_row": start_row,
        "end_row": end_row,
        "start_column": start_column,
        "end_column": end_column,
        "a1_range": a1,
    }


if __name__ == "__main__":
    unittest.main()
