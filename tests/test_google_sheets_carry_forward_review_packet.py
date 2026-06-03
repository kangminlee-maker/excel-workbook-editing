from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_carry_forward_review_packet import (  # noqa: E402
    build_google_sheets_carry_forward_review_packet,
)


class GoogleSheetsCarryForwardReviewPacketTest(unittest.TestCase):
    def test_builds_review_lanes_without_parser_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_json(root / "live-manifest.json", _manifest())
            _write_json(root / "live-document-item-grouping-checkpoint.json", _grouping())
            _write_json(root / "live-version-breakpoint-detection.json", _version())
            _write_json(root / "live-formula-result-authority-checkpoint.json", _formula())
            _write_json(root / "live-semantic-gate-iteration.json", _semantic_gate())

            packet = build_google_sheets_carry_forward_review_packet(out_dir=root)

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-carry-forward-review-packet.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(packet)

        self.assertEqual(packet["authority"]["parser_truth"], "no_new_parser_claims")
        self.assertEqual(packet["authority"]["shared_ontology_updates"], 0)
        self.assertEqual(packet["summary"]["review_lane_count"], 4)
        self.assertGreaterEqual(packet["summary"]["decision_item_count"], 8)
        self.assertGreater(packet["summary"]["high_priority_decision_item_count"], 0)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _manifest() -> dict:
    return {
        "source": {"spreadsheet_id": "sheet-1", "spreadsheet_url": None, "title": "Live Sheet"}
    }


def _grouping() -> dict:
    return {
        "document_items": [
            {
                "id": "doc_item_1",
                "status": "review_required",
                "item_kind": "section_with_child_blocks",
                "sheet": "25_0101",
                "bounds": {"a1_range": "A1:B2"},
                "label": "Overview",
                "review_reasons": ["ordering_only"],
            },
            {
                "id": "doc_item_2",
                "status": "review_required",
                "item_kind": "formula_dataflow_pipeline_group",
                "sheet": "25_0101",
                "bounds": {"a1_range": "A1:R80"},
                "label": "Report",
                "review_reasons": ["formula_result_probe_missing"],
            },
        ],
        "orphan_surfaces": [
            {
                "id": "orphan_1",
                "sheet": "25_0101",
                "bounds": {"a1_range": "A1:Z80"},
                "label": "object surface",
                "reason": "coarse object anchor",
            }
        ],
    }


def _version() -> dict:
    return {
        "version_groups": [
            {
                "id": "group_1",
                "status": "review_required",
                "newest_tab": "25_0101",
                "oldest_tab": "25_0101",
                "member_tabs": ["25_0101"],
                "review_reasons": ["drift"],
                "evidence": {},
            }
        ],
        "version_breakpoints": [
            {
                "id": "break_1",
                "status": "review_required",
                "newer_tab": "25_0101",
                "older_tab": "24_1225",
                "drift": {"column_count_delta": 1},
                "review_reasons": ["weak"],
            }
        ],
    }


def _formula() -> dict:
    return {
        "range_authority_results": [
            {
                "id": "range_1",
                "status": "blocked",
                "source_kind": "current_workbook",
                "sheet": "FC_DATA",
                "range": "A1:Z80",
                "blockers": ["effective_error_values_present"],
                "error_samples": [],
            }
        ],
        "pipeline_authority_results": [
            {
                "pipeline_id": "pipeline_1",
                "status": "blocked",
                "role": "report",
                "sheet": "25_0101",
                "range": "Q80:R80",
                "authority_basis": "not_probed",
                "blockers": ["formula_result_probe_missing"],
            }
        ],
    }


def _semantic_gate() -> dict:
    return {
        "metric_equivalence_checks": [
            {
                "visible_label_bucket": "visible_revenue_label",
                "status": "review_required",
                "surface_count": 2,
                "sample_surfaces": [{"sheet": "25_0101", "label": "매출"}],
                "evidence_refs": ["live-block-candidates.json"],
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
