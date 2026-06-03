from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_validated_document_graph import (  # noqa: E402
    build_google_sheets_validated_document_graph,
)


class GoogleSheetsValidatedDocumentGraphTest(unittest.TestCase):
    def test_assembles_accepted_document_nodes_and_carries_blocked_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping_path = root / "live-document-ontology-mapping.json"
            evidence_path = root / "live-evidence-package.json"
            actions_path = root / "live-action-contracts.json"
            validation_path = root / "live-semantic-proposal-validation.json"
            mapping_path.write_text(json.dumps(_mapping(), ensure_ascii=False), encoding="utf-8")
            evidence_path.write_text(json.dumps(_evidence(), ensure_ascii=False), encoding="utf-8")
            actions_path.write_text(json.dumps(_actions(), ensure_ascii=False), encoding="utf-8")
            validation_path.write_text(json.dumps(_semantic_validation(), ensure_ascii=False), encoding="utf-8")

            graph = build_google_sheets_validated_document_graph(
                live_document_ontology_mapping_path=mapping_path,
                live_evidence_package_path=evidence_path,
                live_action_contracts_path=actions_path,
                live_semantic_proposal_validation_path=validation_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-validated-document-graph.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(graph)

        node_ids = {item["id"] for item in graph["graph"]["nodes"]}
        self.assertIn("node_workbook", node_ids)
        self.assertIn("node_pipeline_ok", node_ids)
        self.assertNotIn("node_review_blocker", node_ids)
        self.assertEqual(graph["summary"]["semantic_node_count"], 0)
        self.assertEqual(graph["summary"]["accepted_semantic_proposal_result_count"], 0)
        self.assertEqual(graph["summary"]["blocked_semantic_proposal_result_count"], 1)
        self.assertEqual(graph["summary"]["shared_ontology_update_count"], 0)
        self.assertEqual(len(graph["carry_forward"]["semantic_validation_review_queue"]), 1)


def _mapping() -> dict:
    return {
        "source": {
            "spreadsheet_id": "spreadsheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/spreadsheet-1/edit",
            "title": "Live Sheet",
        },
        "ontology": {
            "nodes": [
                {
                    "id": "node_workbook",
                    "type": "workbook_document",
                    "status": "accepted",
                    "label": "Live Sheet",
                    "properties": {},
                    "evidence_refs": ["live-evidence-package.json"],
                },
                {
                    "id": "node_pipeline_ok",
                    "type": "calculation_pipeline",
                    "status": "accepted",
                    "label": "formula surface",
                    "properties": {},
                    "evidence_refs": ["pipeline_ok"],
                },
                {
                    "id": "node_review_blocker",
                    "type": "review_queue_item",
                    "status": "review_required",
                    "label": "source blocker",
                    "properties": {},
                    "evidence_refs": ["review_source"],
                },
            ],
            "relations": [
                {
                    "id": "rel_workbook_pipeline",
                    "type": "contains_accepted_pipeline",
                    "from": "node_workbook",
                    "to": "node_pipeline_ok",
                    "status": "accepted",
                    "evidence_refs": ["pipeline_ok"],
                },
                {
                    "id": "rel_workbook_review",
                    "type": "has_review_item",
                    "from": "node_workbook",
                    "to": "node_review_blocker",
                    "status": "review_required",
                    "evidence_refs": ["review_source"],
                },
            ],
            "review_items": [
                {
                    "id": "review_source",
                    "status": "review_required",
                    "target_node_id": "node_review_blocker",
                    "reason": "source_authority_blocked",
                    "evidence_refs": ["review_source"],
                }
            ],
        },
    }


def _evidence() -> dict:
    return {
        "summary": {
            "accepted_gate_count": 2,
            "accepted_pipeline_count": 1,
        }
    }


def _actions() -> dict:
    return {
        "summary": {
            "open_contract_count": 1,
            "high_priority_contract_count": 1,
        }
    }


def _semantic_validation() -> dict:
    return {
        "proposal_results": [
            {
                "id": "validation_semantic",
                "target_id": "proposal_semantic",
                "target_type": "semantic_concept_proposal",
                "final_status": "blocked",
                "blocking_gates": ["source_authority_gate"],
            }
        ],
        "promotion_gate_results": [
            {
                "id": "validation_promotion",
                "target_id": "shared_ontology_promotion",
                "target_type": "promotion_gate",
                "final_status": "blocked",
                "blocking_gates": ["human_review_gate"],
            }
        ],
        "review_queue": [
            {
                "id": "review_semantic",
                "target_id": "proposal_semantic",
                "target_type": "semantic_concept_proposal",
                "severity": "high",
                "status": "blocked",
                "blocking_gates": ["source_authority_gate"],
                "required_action": "Resolve blockers.",
            }
        ],
        "summary": {
            "blocked_count": 1,
        },
    }


if __name__ == "__main__":
    unittest.main()
