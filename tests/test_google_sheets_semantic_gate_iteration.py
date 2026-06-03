from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_semantic_gate_iteration import build_google_sheets_semantic_gate_iteration  # noqa: E402


class GoogleSheetsSemanticGateIterationTest(unittest.TestCase):
    def test_builds_corrected_domain_candidates_and_metric_review_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_json(root / "live-manifest.json", _manifest())
            _write_json(root / "live-block-candidates.json", _blocks())
            _write_json(root / "live-domain-source-model.json", _domain())
            _write_json(root / "live-document-item-grouping-checkpoint.json", _grouping())
            _write_json(root / "live-version-breakpoint-detection.json", _version())
            _write_json(root / "live-formula-result-authority-checkpoint.json", _formula())
            _write_json(root / "live-blocker-resolution-update.json", _blocker_update())

            iteration = build_google_sheets_semantic_gate_iteration(out_dir=root)

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-semantic-gate-iteration.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(iteration)

        self.assertEqual(iteration["corrected_domain_classification"]["general_domain_source_count"], 0)
        self.assertEqual(iteration["summary"]["accepted_semantic_candidate_count"], 2)
        self.assertEqual(iteration["summary"]["review_required_semantic_candidate_count"], 2)
        self.assertEqual(iteration["summary"]["blocked_semantic_candidate_count"], 1)
        self.assertEqual(iteration["summary"]["metric_equivalence_check_count"], 1)
        self.assertEqual(iteration["summary"]["shared_ontology_update_count"], 0)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _manifest() -> dict:
    return {
        "source": {"spreadsheet_id": "sheet-1", "spreadsheet_url": None, "title": "Live Sheet"}
    }


def _blocks() -> dict:
    return {
        "sheets": [
            {
                "blocks": [
                    {
                        "id": "block_1",
                        "sheet": "25_0101",
                        "type": "table_candidate",
                        "label": "순매출",
                        "bounds": {"a1_range": "A1:B2"},
                    }
                ]
            }
        ]
    }


def _domain() -> dict:
    return {
        "summary": {"general_domain_source_count": 0, "local_boundary_confirmed": True},
        "authority": {"general_domain_authority": "not_selected"},
        "local_domain_boundary": {
            "boundary_label": "전사레벨 현황 보고 문서",
            "boundary_status": "confirmed",
            "reporting_basis": "cash basis; 결제액 기반 운영 현황 보고",
        },
    }


def _grouping() -> dict:
    return {
        "summary": {
            "accepted_document_item_count": 1,
            "review_required_document_item_count": 2,
            "orphan_surface_count": 1,
        }
    }


def _version() -> dict:
    return {
        "summary": {
            "review_required_version_breakpoint_count": 1,
        }
    }


def _formula() -> dict:
    return {
        "summary": {
            "accepted_pipeline_result_count": 1,
            "blocked_pipeline_result_count": 2,
        }
    }


def _blocker_update() -> dict:
    return {
        "user_inputs": {
            "reporting_basis": "cash basis; 결제액 기반 운영 현황 보고",
        }
    }


if __name__ == "__main__":
    unittest.main()
