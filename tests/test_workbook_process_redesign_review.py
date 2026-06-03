from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_process_redesign_review import build_process_redesign_review  # noqa: E402


class WorkbookProcessRedesignReviewTest(unittest.TestCase):
    def test_builds_process_redesign_review_from_ledger_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_dir = root / "artifacts"
            artifact_dir.mkdir()
            ledger_path = artifact_dir / "process-ledger.jsonl"
            tasklist_path = root / "tasklist.md"
            design_path = root / "design.md"
            agents_path = root / "AGENTS.md"
            map_path = root / "IMPLEMENTATION_MAP.html"

            ledger_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "sequence": 1,
                                "stage": "view_state_preflight_reorder",
                                "result_summary": {
                                    "view_state_preflight": "moved_early"
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "sequence": 2,
                                "stage": "shared_ontology_alignment_human_review",
                                "result_summary": {
                                    "alignment_status": "review_only_no_shared_promotion"
                                },
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            tasklist_path.write_text(
                "\n".join(
                    [
                        "| # | Stage | Status | Current output / done when |",
                        "|---:|---|---|---|",
                        "| 0 | Fast ZIP/XML manifest | Done | Manifest exists. |",
                        "| 1 | Workbook view-state preflight | Done | View state first. |",
                        "| 4 | Initial document block candidate generation | Done | Seeds exist. |",
                        "| 5 | 2D cell region segmentation | Done | Regions exist. |",
                        "| 29 | Shared ontology alignment / human review | Done | Review only. |",
                        "| 30 | Process redesign review | Continuous | Ledger is used. |",
                    ]
                ),
                encoding="utf-8",
            )
            for path in [design_path, agents_path, map_path]:
                path.write_text("process redesign source\n", encoding="utf-8")
            _write_summary(
                artifact_dir / "mbp-2026-02-gate-execution.json",
                {"accepted_count": 1, "review_required_count": 2},
            )
            _write_summary(
                artifact_dir / "mbp-2026-02-pipeline-role-validation.json",
                {"accepted_count": 3},
            )
            _write_summary(
                artifact_dir / "mbp-2026-02-action-contracts.json",
                {"open_count": 4, "blocked_count": 1},
            )
            _write_summary(
                artifact_dir / "mbp-2026-02-llm-proposal-validation.json",
                {
                    "accepted_count": 5,
                    "requires_human_review_count": 6,
                    "quarantined_count": 7,
                },
            )
            _write_summary(
                artifact_dir / "mbp-2026-02-validated-document-graph.json",
                {"graph_node_count": 8, "graph_relation_count": 9},
            )
            _write_summary(
                artifact_dir / "mbp-2026-02-data-view-projection.json",
                {"data_view_projection_count": 10},
            )
            _write_summary(
                artifact_dir / "mbp-2026-02-local-semantic-candidates.json",
                {"local_semantic_candidate_count": 11},
            )
            _write_summary(
                artifact_dir / "mbp-2026-02-shared-ontology-alignment-review.json",
                {
                    "promoted_count": 0,
                    "blocked_alignment_count": 11,
                    "basis_review_required_count": 2,
                    "formula_result_validation_required_count": 3,
                    "semantic_label_pending_count": 4,
                },
            )
            _write_summary(
                artifact_dir / "mbp-2026-02-view-state-profile.json",
                {
                    "view_state_explained_failure_count": 2,
                    "view_state_warning_count": 1,
                },
            )

            review = build_process_redesign_review(
                process_ledger_path=ledger_path,
                tasklist_path=tasklist_path,
                design_doc_path=design_path,
                agents_path=agents_path,
                implementation_map_path=map_path,
                artifact_dir=artifact_dir,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "workbook-process-redesign-review.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(review)

        self.assertEqual(review["summary"]["review_status"], "process_redesign_review_completed")
        self.assertEqual(review["summary"]["ledger_entry_count"], 2)
        self.assertEqual(review["summary"]["tasklist_stage_count"], 6)
        self.assertEqual(review["summary"]["stage_review_count"], 6)
        self.assertEqual(review["final_assessment"]["status"], "structural_understanding_ready_but_semantic_promotion_blocked")
        by_stage = {
            item["current_stage_number"]: item for item in review["stage_reviews"]
        }
        self.assertEqual(by_stage[1]["recommendation"], "keep_reordered_early")
        self.assertEqual(
            by_stage[4]["recommendation"],
            "merge_as_region_candidate_generation",
        )
        self.assertTrue(
            any(
                decision["id"] == "decision:formula_results_need_excel_engine"
                for decision in review["redesign_decisions"]
            )
        )
        self.assertTrue(
            any(gap["id"] == "gap:gaap_ifrs_basis" for gap in review["open_evidence_gaps"])
        )


def _write_summary(path: Path, summary: dict) -> None:
    path.write_text(
        json.dumps(
            {
                "method": {"name": path.stem},
                "summary": summary,
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
