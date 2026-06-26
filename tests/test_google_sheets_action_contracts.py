from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_action_contracts import build_google_sheets_action_contracts  # noqa: E402


class GoogleSheetsActionContractsTest(unittest.TestCase):
    def test_builds_action_contracts_from_review_items(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "spreadsheet-processing" / "live-inspections" / "test-action-contracts"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        mapping_path = fixture_dir / "live-document-ontology-mapping.json"
        mapping_path.write_text(json.dumps(_mapping(), ensure_ascii=False), encoding="utf-8")

        contracts = build_google_sheets_action_contracts(
            live_document_ontology_mapping_path=mapping_path,
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-action-contracts.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(contracts)

        self.assertEqual(contracts["summary"]["action_contract_count"], 2)
        self.assertEqual(contracts["summary"]["high_priority_contract_count"], 2)
        gates = {item["deterministic_gate"] for item in contracts["action_contracts"]}
        self.assertIn("external_source_authority", gates)
        self.assertIn("formula_error_reconciliation", gates)


def _mapping() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "ontology": {
            "review_items": [
                {
                    "id": "review_external",
                    "type": "external_source_authority_blocker",
                    "severity": "high",
                    "status": "blocked",
                    "message": "Source blocked.",
                    "evidence_refs": ["external_dep"],
                },
                {
                    "id": "review_formula",
                    "type": "formula_result_authority_gap",
                    "severity": "high",
                    "status": "requires_formula_result_review",
                    "message": "Formula error.",
                    "evidence_refs": ["action_error"],
                },
            ]
        },
    }


if __name__ == "__main__":
    unittest.main()
