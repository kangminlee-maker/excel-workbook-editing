from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_semantic_proposal_validation import (  # noqa: E402
    build_google_sheets_semantic_proposal_validation,
)


class GoogleSheetsSemanticProposalValidationTest(unittest.TestCase):
    def test_blocks_proposals_when_boundary_and_source_authority_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            proposals_path = root / "live-semantic-proposals.json"
            domain_path = root / "live-domain-source-model.json"
            evidence_path = root / "live-evidence-package.json"
            mapping_path = root / "live-document-ontology-mapping.json"
            proposals_path.write_text(json.dumps(_semantic_proposals(), ensure_ascii=False), encoding="utf-8")
            domain_path.write_text(json.dumps(_domain_model(), ensure_ascii=False), encoding="utf-8")
            evidence_path.write_text(json.dumps(_evidence_package(), ensure_ascii=False), encoding="utf-8")
            mapping_path.write_text(json.dumps(_document_mapping(), ensure_ascii=False), encoding="utf-8")

            validation = build_google_sheets_semantic_proposal_validation(
                live_semantic_proposals_path=proposals_path,
                live_domain_source_model_path=domain_path,
                live_evidence_package_path=evidence_path,
                live_document_ontology_mapping_path=mapping_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-semantic-proposal-validation.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(validation)

        self.assertEqual(validation["summary"]["proposal_result_count"], 3)
        self.assertEqual(validation["summary"]["blocked_count"], 3)
        self.assertEqual(validation["summary"]["accepted_count"], 0)
        self.assertEqual(validation["summary"]["accepted_semantic_concept_count"], 0)
        self.assertEqual(validation["summary"]["shared_ontology_update_count"], 0)
        self.assertEqual(validation["summary"]["promotion_blocked_count"], 1)
        self.assertIn("source_trace_gate", validation["gate_summary"])
        self.assertIn("source_authority_gate", validation["gate_summary"])


def _semantic_proposals() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "summary": {
            "semantic_concept_proposal_count": 2,
            "semantic_relation_proposal_count": 1,
            "proposal_status": "proposal_only_not_accepted",
        },
        "semantic_concept_proposals": [
            {
                "id": "proposal_period_tab_calculation_surface",
                "type": "semantic_concept_proposal",
                "status": "proposed",
                "domain_layer": "local_domain",
                "label": "period-tab calculation surface",
                "description": "Accepted calculation node.",
                "source_evidence_refs": ["node_pipeline_ok", "pipeline_ok"],
                "domain_source_refs": [],
                "shared_promotion_status": "blocked",
                "blockers": [
                    "shared_promotion_blocked",
                    "local_boundary_not_confirmed",
                    "source_authority_unavailable",
                ],
            },
            {
                "id": "proposal_revenue_recognition_context_reference",
                "type": "semantic_concept_proposal",
                "status": "proposed",
                "domain_layer": "general_domain_reference",
                "label": "revenue recognition context reference",
                "description": "Reference-only K-IFRS context.",
                "source_evidence_refs": ["live-domain-source-model.json"],
                "domain_source_refs": ["general_concepts"],
                "shared_promotion_status": "blocked",
                "blockers": [
                    "shared_promotion_blocked",
                    "local_boundary_not_confirmed",
                    "source_authority_unavailable",
                ],
            },
        ],
        "semantic_relation_proposals": [
            {
                "id": "rel_period_surface_may_use_revenue_context",
                "type": "semantic_relation_proposal",
                "status": "proposed",
                "relation_type": "may_be_interpreted_with_general_domain_reference",
                "from": "proposal_period_tab_calculation_surface",
                "to": "proposal_revenue_recognition_context_reference",
                "source_evidence_refs": ["live-evidence-package.json", "live-domain-source-model.json"],
                "blockers": ["formula_result_authority_not_established"],
            }
        ],
    }


def _domain_model() -> dict:
    return {
        "general_domain_sources": [
            {
                "id": "general_concepts",
                "status": "available",
                "applicability": ["revenue_recognition"],
            }
        ],
        "unavailable_sources": [
            {
                "id": "unavailable_external_importrange_source",
                "type": "source_spreadsheet",
                "status": "blocked",
            },
            {
                "id": "unavailable_formula_result_authority",
                "type": "formula_result",
                "status": "blocked",
            },
        ],
        "semantic_readiness": {
            "local_boundary_confirmed": False,
            "unavailable_source_count": 2,
            "shared_ontology_promotion_status": "blocked",
        },
    }


def _evidence_package() -> dict:
    return {
        "accepted_evidence": {
            "pipelines": [
                {
                    "id": "pipeline_ok",
                    "role": "calculation",
                }
            ]
        },
        "review_queue": [],
    }


def _document_mapping() -> dict:
    return {
        "ontology": {
            "nodes": [
                {
                    "id": "node_pipeline_ok",
                    "type": "calculation_pipeline",
                    "status": "accepted",
                    "evidence_refs": ["pipeline_ok"],
                }
            ],
            "relations": [],
        }
    }


if __name__ == "__main__":
    unittest.main()
