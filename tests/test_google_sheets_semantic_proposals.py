from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_semantic_proposals import build_google_sheets_semantic_proposals  # noqa: E402


class GoogleSheetsSemanticProposalsTest(unittest.TestCase):
    def test_generates_proposal_only_semantics_from_mapping_and_domain_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            domain_path = root / "live-domain-source-model.json"
            evidence_path = root / "live-evidence-package.json"
            mapping_path = root / "live-document-ontology-mapping.json"
            domain_path.write_text(json.dumps(_domain_model(), ensure_ascii=False), encoding="utf-8")
            evidence_path.write_text(json.dumps(_evidence_package(), ensure_ascii=False), encoding="utf-8")
            mapping_path.write_text(json.dumps(_document_mapping(), ensure_ascii=False), encoding="utf-8")

            package = build_google_sheets_semantic_proposals(
                live_domain_source_model_path=domain_path,
                live_evidence_package_path=evidence_path,
                live_document_ontology_mapping_path=mapping_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-semantic-proposals.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        self.assertEqual(package["summary"]["proposal_status"], "proposal_only_not_accepted")
        self.assertEqual(package["summary"]["accepted_semantic_concept_count"], 0)
        self.assertEqual(package["summary"]["shared_ontology_update_count"], 0)
        self.assertGreaterEqual(package["summary"]["semantic_concept_proposal_count"], 3)
        self.assertGreaterEqual(package["summary"]["semantic_relation_proposal_count"], 2)
        period_surface = next(
            item
            for item in package["semantic_concept_proposals"]
            if item["id"] == "proposal_period_tab_calculation_surface"
        )
        self.assertIn("node_pipeline_ok", period_surface["source_evidence_refs"])
        self.assertIn("pipeline_ok", period_surface["source_evidence_refs"])
        self.assertIn("local_boundary_not_confirmed", period_surface["blockers"])


def _domain_model() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "general_domain_sources": [
            {
                "id": "general_concepts",
                "applicability": ["accounting_principles", "k_ifrs", "revenue_recognition"],
            }
        ],
        "semantic_readiness": {
            "semantic_proposal_scope": "limited_document_evidence_only",
            "local_boundary_confirmed": False,
            "unavailable_source_count": 2,
            "shared_ontology_promotion_status": "blocked",
        },
    }


def _evidence_package() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "accepted_evidence": {
            "pipelines": [
                {
                    "id": "pipeline_ok",
                    "role": "calculation",
                    "output_refs": [{"label": "24_0102 formula surface"}],
                }
            ]
        },
        "review_queue": [
            {
                "id": "review_external_source",
                "type": "external_source_authority_blocker",
            }
        ],
    }


def _document_mapping() -> dict:
    return {
        "ontology": {
            "nodes": [
                {
                    "id": "node_pipeline_ok",
                    "type": "calculation_pipeline",
                    "status": "accepted",
                    "label": "24_0102 formula surface",
                },
                {
                    "id": "node_review_external_source",
                    "type": "review_queue_item",
                    "status": "review_required",
                    "label": "external_source_authority_blocker",
                },
            ]
        }
    }


if __name__ == "__main__":
    unittest.main()
