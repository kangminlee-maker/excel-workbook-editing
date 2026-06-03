from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_document_ontology_mapping import (  # noqa: E402
    build_google_sheets_document_ontology_mapping,
)


class GoogleSheetsDocumentOntologyMappingTest(unittest.TestCase):
    def test_maps_evidence_package_to_document_structure_only(self) -> None:
        fixture_dir = REPO_ROOT / "review-packages" / "sheets-bridge" / "live-inspections" / "test-document-ontology"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = fixture_dir / "live-evidence-package.json"
        evidence_path.write_text(json.dumps(_evidence_package(), ensure_ascii=False), encoding="utf-8")

        mapping = build_google_sheets_document_ontology_mapping(
            live_evidence_package_path=evidence_path,
        )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-document-ontology-mapping.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(mapping)

        self.assertEqual(mapping["summary"]["semantic_concept_count"], 0)
        self.assertEqual(mapping["summary"]["review_item_count"], 1)
        self.assertGreater(mapping["summary"]["accepted_node_count"], 0)
        self.assertTrue(
            any(node["type"] == "review_queue_item" for node in mapping["ontology"]["nodes"])
        )


def _evidence_package() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "workbook_facts": {"sheet_count": 2},
        "summary": {"accepted_gate_count": 1, "accepted_target_count": 1},
        "accepted_evidence": {
            "pipelines": [
                {
                    "id": "pipeline_ok",
                    "role": "calculation",
                    "confidence": 0.8,
                    "input_refs": [{"label": "Input"}],
                    "output_refs": [{"label": "Output"}],
                }
            ]
        },
        "review_queue": [
            {
                "id": "review_source",
                "type": "external_source_authority_blocker",
                "severity": "high",
                "message": "Source blocked.",
                "evidence_refs": ["external_dep"],
                "status": "blocked",
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
