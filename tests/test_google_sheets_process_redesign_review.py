from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_process_redesign_review import build_google_sheets_process_redesign_review  # noqa: E402


class GoogleSheetsProcessRedesignReviewTest(unittest.TestCase):
    def test_reviews_iteration_without_parser_truth_or_shared_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            live_dir = root / "live"
            live_dir.mkdir()
            (live_dir / "live-a.json").write_text("{}", encoding="utf-8")
            (live_dir / "live-b.json").write_text("{}", encoding="utf-8")
            ledger = root / "process-ledger.jsonl"
            ledger.write_text(
                "\n".join(
                    [
                        json.dumps({"stage": "google_sheets_live_manifest_profile"}),
                        json.dumps({"stage": "google_sheets_data_view_projection"}),
                        json.dumps({"stage": "workbook_process_redesign_review"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            tasklist = root / "tasklist.md"
            design = root / "design.md"
            tasklist.write_text("tasklist", encoding="utf-8")
            design.write_text("design", encoding="utf-8")

            review = build_google_sheets_process_redesign_review(
                live_inspection_dir=live_dir,
                process_ledger_path=ledger,
                tasklist_path=tasklist,
                design_path=design,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-process-redesign-review.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(review)

        self.assertEqual(review["authority"]["parser_truth"], "no_new_parser_claims")
        self.assertEqual(review["summary"]["json_artifact_count"], 2)
        self.assertEqual(review["summary"]["google_sheets_ledger_entry_count"], 2)
        self.assertEqual(review["summary"]["shared_ontology_update_count"], 0)
        self.assertGreaterEqual(review["summary"]["redesign_decision_count"], 5)
        self.assertGreaterEqual(review["summary"]["open_evidence_gap_count"], 6)


if __name__ == "__main__":
    unittest.main()
