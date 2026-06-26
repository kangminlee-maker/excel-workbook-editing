from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_domain_source_model import build_google_sheets_domain_source_model  # noqa: E402


class GoogleSheetsDomainSourceModelTest(unittest.TestCase):
    def test_defaults_to_no_general_domain_sources(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "spreadsheet-processing" / "live-inspections" / "test-domain-source-model"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        contracts_path = fixture_dir / "live-action-contracts.json"
        evidence_path = fixture_dir / "live-evidence-package.json"
        contracts_path.write_text(json.dumps(_contracts(), ensure_ascii=False), encoding="utf-8")
        evidence_path.write_text(json.dumps(_evidence(), ensure_ascii=False), encoding="utf-8")

        model = build_google_sheets_domain_source_model(
            live_action_contracts_path=contracts_path,
            live_evidence_package_path=evidence_path,
        )

        self.assertEqual(model["summary"]["general_domain_source_count"], 0)
        self.assertFalse(model["semantic_readiness"]["general_domain_available"])
        self.assertEqual(model["general_domain_sources"], [])

    def test_separates_general_local_and_unavailable_sources(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "spreadsheet-processing" / "live-inspections" / "test-domain-source-model"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        contracts_path = fixture_dir / "live-action-contracts.json"
        evidence_path = fixture_dir / "live-evidence-package.json"
        contracts_path.write_text(json.dumps(_contracts(), ensure_ascii=False), encoding="utf-8")
        evidence_path.write_text(json.dumps(_evidence(), ensure_ascii=False), encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmpdir:
            domain_dir = Path(tmpdir)
            (domain_dir / "domain_scope.md").write_text("K-IFRS revenue", encoding="utf-8")
            (domain_dir / "concepts.md").write_text("concepts", encoding="utf-8")

            model = build_google_sheets_domain_source_model(
                live_action_contracts_path=contracts_path,
                live_evidence_package_path=evidence_path,
                general_domain_dir=domain_dir,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-domain-source-model.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(model)

        self.assertEqual(model["summary"]["general_domain_source_count"], 2)
        self.assertEqual(model["summary"]["unavailable_source_count"], 2)
        self.assertFalse(model["summary"]["local_boundary_confirmed"])
        self.assertEqual(model["semantic_readiness"]["shared_ontology_promotion_status"], "blocked")


def _contracts() -> dict:
    return {
        "action_contracts": [
            {"id": "contract_source", "deterministic_gate": "external_source_authority"},
            {"id": "contract_formula", "deterministic_gate": "formula_error_reconciliation"},
        ]
    }


def _evidence() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "summary": {"source_spreadsheet_read_count": 0},
        "authority": {"formula_result_authority": "not_established"},
    }


if __name__ == "__main__":
    unittest.main()
