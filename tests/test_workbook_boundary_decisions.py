from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_boundary_decisions import build_boundary_decisions  # noqa: E402


class WorkbookBoundaryDecisionsTest(unittest.TestCase):
    def test_accepts_strong_blank_boundary_and_keeps_style_boundary_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            candidates_path = root / "block-candidates.json"
            gates_path = root / "gate-execution.json"
            candidates_path.write_text(
                json.dumps(_block_candidates()),
                encoding="utf-8",
            )
            gates_path.write_text(json.dumps(_gate_execution()), encoding="utf-8")

            package = build_boundary_decisions(candidates_path, gates_path)

        decisions = {
            item["source_boundary_gate_result_id"]: item
            for item in package["boundary_decisions"]
        }
        self.assertEqual(decisions["gate_split_blank"]["status"], "accepted")
        self.assertEqual(
            decisions["gate_split_blank"]["graph_effect"],
            "create_validated_split_boundary",
        )
        self.assertEqual(decisions["gate_split_style"]["status"], "review_required")
        self.assertEqual(decisions["gate_split_rejected"]["status"], "rejected")
        self.assertEqual(package["summary"]["accepted_count"], 1)
        self.assertEqual(package["summary"]["review_required_count"], 1)
        self.assertEqual(package["summary"]["rejected_count"], 1)

        schema = json.loads(
            (
                REPO_ROOT / "schemas" / "workbook-boundary-decisions.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(package)


def _block_candidates() -> dict:
    return {
        "sheets": [
            {
                "name": "Sheet1",
                "cell_region_split_candidates": [
                    _split_candidate("split_blank", "blank_column_boundary", 3, 5),
                    _split_candidate("split_style", "style_discontinuity_boundary", 7, 8),
                    _split_candidate(
                        "split_rejected",
                        "repeated_header_touching_boundary",
                        10,
                        11,
                    ),
                ],
                "boundary_gate_results": [
                    _boundary_gate(
                        "gate_split_blank",
                        "split_blank",
                        "blank_column_boundary",
                        "strong_candidate",
                        "accept_as_split_candidate",
                        ["blank_column_boundary", "materialized_region_boundary"],
                    ),
                    _boundary_gate(
                        "gate_split_style",
                        "split_style",
                        "style_discontinuity_boundary",
                        "review_candidate",
                        "do_not_auto_split",
                        ["style_discontinuity_boundary", "within_region_boundary_signal"],
                    ),
                    _boundary_gate(
                        "gate_split_rejected",
                        "split_rejected",
                        "repeated_header_touching_boundary",
                        "review_candidate",
                        "requires_human_or_visual_review",
                        [
                            "repeated_header_touching_boundary",
                            "materialized_region_boundary",
                        ],
                    ),
                ],
            }
        ]
    }


def _split_candidate(
    candidate_id: str,
    candidate_type: str,
    after_column: int,
    before_column: int,
) -> dict:
    return {
        "id": candidate_id,
        "type": candidate_type,
        "parent_seed_block_id": "row_band_1",
        "from_region_id": "region_left",
        "to_region_id": "region_right",
        "boundary_within_region_id": None,
        "boundary_after_column": after_column,
        "boundary_before_column": before_column,
        "evidence": ["readonly_sample.windows", "column_segmentation"],
    }


def _boundary_gate(
    gate_id: str,
    candidate_id: str,
    candidate_type: str,
    status: str,
    decision: str,
    evidence: list[str],
) -> dict:
    return {
        "id": gate_id,
        "type": "split_candidate_gate",
        "sheet": "Sheet1",
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "related_region_ids": ["region_left", "region_right"],
        "score": 0.86 if status == "strong_candidate" else 0.62,
        "status": status,
        "decision": decision,
        "evidence": evidence,
        "rationale": "fixture",
    }


def _gate_execution() -> dict:
    return {
        "gate_results": [
            _gate_result("gate_result_blank", "gate_split_blank", "split_blank", "accepted"),
            _gate_result("gate_result_style", "gate_split_style", "split_style", "accepted"),
            _gate_result(
                "gate_result_rejected",
                "gate_split_rejected",
                "split_rejected",
                "rejected",
            ),
        ]
    }


def _gate_result(
    result_id: str,
    boundary_gate_id: str,
    candidate_id: str,
    status: str,
) -> dict:
    return {
        "id": result_id,
        "gate_check_id": f"check_{result_id}",
        "target_id": f"target_{result_id}",
        "gate_type": "boundary_confirmation",
        "status": status,
        "reason": (
            "deterministic_visual_evidence_available"
            if status == "accepted"
            else "no_visible_content_detected"
        ),
        "confidence": 0.82,
        "deterministic_inputs": [boundary_gate_id, candidate_id],
        "evidence_refs": [boundary_gate_id, candidate_id],
    }


if __name__ == "__main__":
    unittest.main()
