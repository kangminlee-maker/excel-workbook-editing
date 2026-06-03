from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_validated_document_graph import build_validated_document_graph  # noqa: E402


class WorkbookValidatedDocumentGraphTest(unittest.TestCase):
    def test_assembles_only_accepted_proposals_and_carries_review_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping_path = root / "document-ontology.json"
            proposals_path = root / "llm-proposals.json"
            validation_path = root / "llm-proposal-validation.json"
            action_path = root / "action-contracts.json"

            mapping_path.write_text(
                json.dumps(
                    {
                        "nodes": [
                            {
                                "id": "workbook:source",
                                "type": "workbook",
                                "ontology_class": "WorkbookDocument",
                                "label": "source.xlsx",
                                "status": "accepted",
                                "sheet": None,
                                "range": None,
                                "properties": {},
                                "evidence_refs": ["evidence_package.source"],
                                "source_artifact_refs": ["evidence_package"],
                            },
                            {
                                "id": "sheet:매출",
                                "type": "sheet",
                                "ontology_class": "WorksheetSurface",
                                "label": "매출",
                                "status": "accepted",
                                "sheet": "매출",
                                "range": "A1:B2",
                                "properties": {},
                                "evidence_refs": ["sheet:매출"],
                                "source_artifact_refs": ["evidence_package"],
                            },
                        ],
                        "relations": [
                            {
                                "id": "rel:contains|workbook:source|sheet:매출",
                                "type": "contains",
                                "from": "workbook:source",
                                "to": "sheet:매출",
                                "status": "accepted",
                                "properties": {},
                                "evidence_refs": ["manifest.workbook.sheets"],
                                "source_artifact_refs": ["manifest"],
                            }
                        ],
                        "data_views": [
                            {
                                "id": "data_view:매출",
                                "status": "accepted",
                                "evidence_refs": ["role_validation:매출"],
                                "source_artifact_refs": ["pipeline_role_validation"],
                            }
                        ],
                        "review_queue": [
                            {
                                "id": "review:boundary",
                                "status": "review_required",
                                "reason": "capture_required",
                                "target_node_id": "sheet:매출",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            proposals_path.write_text(
                json.dumps(
                    {
                        "semantic_concept_proposals": [
                            {
                                "id": "semantic_concept:매출",
                                "proposal_type": "semantic_concept_candidate",
                                "label": "매출",
                                "concept_kind": "revenue_summary",
                                "scope": "general_domain_aligned_workbook_candidate",
                                "description": "매출 summary",
                                "matched_terms": ["매출"],
                                "matched_sheets": ["매출"],
                                "data_view_ids": ["data_view:매출"],
                                "domain_source_refs": ["general_domain:concepts"],
                                "evidence_refs": ["data_view:매출"],
                            },
                            {
                                "id": "semantic_concept:정가표",
                                "proposal_type": "semantic_concept_candidate",
                                "label": "정가표",
                                "concept_kind": "reference_table",
                                "scope": "workbook_local_candidate",
                                "description": "local",
                                "matched_terms": ["정가표"],
                                "matched_sheets": ["정가표"],
                                "data_view_ids": [],
                                "domain_source_refs": [],
                                "evidence_refs": ["data_view:정가표"],
                            },
                        ],
                        "hierarchy_proposals": [
                            {
                                "id": "hierarchy:매출",
                                "proposal_type": "hierarchy_candidate",
                                "parent": {"kind": "worksheet_surface", "sheet": "매출"},
                                "child": {
                                    "kind": "semantic_concept",
                                    "id": "semantic_concept:매출",
                                },
                                "data_view_ids": ["data_view:매출"],
                                "evidence_refs": ["data_view:매출"],
                            }
                        ],
                        "semantic_relation_proposals": [],
                        "alias_proposals": [
                            {
                                "id": "alias:매출",
                                "proposal_type": "alias_candidate",
                                "alias": "매출",
                                "canonical_concept_id": "semantic_concept:매출",
                                "alias_scope": "general_domain_aligned_workbook_candidate",
                                "matched_sheets": ["매출"],
                                "confidence": 0.8,
                                "evidence_refs": ["data_view:매출"],
                            }
                        ],
                        "ambiguity_notes": [],
                    }
                ),
                encoding="utf-8",
            )
            validation_path.write_text(
                json.dumps(
                    {
                        "proposal_results": [
                            {
                                "id": "validation_result:semantic_concept:매출",
                                "proposal_id": "semantic_concept:매출",
                                "proposal_type": "semantic_concept_candidate",
                                "final_status": "accepted",
                                "evidence_refs": ["data_view:매출"],
                            },
                            {
                                "id": "validation_result:hierarchy:매출",
                                "proposal_id": "hierarchy:매출",
                                "proposal_type": "hierarchy_candidate",
                                "final_status": "accepted",
                                "evidence_refs": ["data_view:매출"],
                            },
                            {
                                "id": "validation_result:alias:매출",
                                "proposal_id": "alias:매출",
                                "proposal_type": "alias_candidate",
                                "final_status": "accepted",
                                "evidence_refs": ["data_view:매출"],
                            },
                            {
                                "id": "validation_result:semantic_concept:정가표",
                                "proposal_id": "semantic_concept:정가표",
                                "proposal_type": "semantic_concept_candidate",
                                "final_status": "quarantined",
                                "evidence_refs": ["data_view:정가표"],
                            },
                        ],
                        "review_queue": [
                            {
                                "id": "review:semantic_concept:정가표",
                                "status": "quarantined",
                                "proposal_id": "semantic_concept:정가표",
                                "proposal_type": "semantic_concept_candidate",
                                "blocking_gates": ["local_domain_gate"],
                                "required_action": "confirm_local_domain_boundary",
                            }
                        ],
                        "summary": {
                            "accepted_count": 3,
                            "requires_human_review_count": 0,
                            "quarantined_count": 1,
                            "rejected_count": 0,
                        },
                    }
                ),
                encoding="utf-8",
            )
            action_path.write_text(
                json.dumps({"summary": {"open_count": 2, "blocked_count": 1}}),
                encoding="utf-8",
            )

            graph = build_validated_document_graph(
                document_ontology_mapping_path=mapping_path,
                llm_proposals_path=proposals_path,
                llm_proposal_validation_path=validation_path,
                action_contracts_path=action_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "workbook-validated-document-graph.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(graph)

        node_ids = {node["id"] for node in graph["graph"]["nodes"]}
        self.assertIn("semantic_concept:매출", node_ids)
        self.assertNotIn("semantic_concept:정가표", node_ids)
        self.assertEqual(graph["summary"]["semantic_node_count"], 1)
        self.assertEqual(graph["summary"]["semantic_alias_count"], 1)
        self.assertEqual(graph["summary"]["proposal_review_queue_count"], 1)
        self.assertEqual(graph["summary"]["blocked_action_contract_count"], 1)


if __name__ == "__main__":
    unittest.main()
