from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_llm_proposal_validation import build_llm_proposal_validation  # noqa: E402


class WorkbookLlmProposalValidationTest(unittest.TestCase):
    def test_validates_general_claims_and_quarantines_unconfirmed_local_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            proposals_path = root / "llm-proposals.json"
            mapping_path = root / "document-ontology.json"
            table_io_path = root / "table-io.json"
            domain_path = root / "domain-source-model.json"

            proposals_path.write_text(
                json.dumps(
                    {
                        "summary": {"proposal_result_count": 2},
                        "proposal_context": {
                            "semantic_readiness": {
                                "status": "proposal_only_local_boundary_pending"
                            }
                        },
                        "semantic_concept_proposals": [
                            {
                                "id": "semantic_concept:매출",
                                "proposal_type": "semantic_concept_candidate",
                                "proposal_status": "proposed",
                                "label": "매출",
                                "scope": "general_domain_aligned_workbook_candidate",
                                "data_view_ids": ["data_view:매출"],
                                "domain_source_refs": [
                                    "general_domain:accounting-kr/concepts.md"
                                ],
                                "evidence_refs": ["data_view:매출", "role_validation:매출"],
                                "required_gates": [
                                    "source_trace_gate",
                                    "general_domain_gate",
                                    "formula_consistency_gate",
                                    "conflict_gate",
                                ],
                                "confidence": 0.72,
                                "review_flags": [],
                            },
                            {
                                "id": "semantic_concept:정가표",
                                "proposal_type": "semantic_concept_candidate",
                                "proposal_status": "proposed",
                                "label": "정가표",
                                "scope": "workbook_local_candidate",
                                "data_view_ids": ["data_view:정가표"],
                                "local_boundary_ids": [
                                    "local_boundary:workbook_sample:test"
                                ],
                                "domain_source_refs": [
                                    "general_domain:accounting-kr/concepts.md"
                                ],
                                "evidence_refs": ["data_view:정가표", "role_validation:정가표"],
                                "required_gates": [
                                    "source_trace_gate",
                                    "local_domain_gate",
                                    "formula_consistency_gate",
                                    "conflict_gate",
                                ],
                                "confidence": 0.72,
                                "review_flags": ["local_boundary_pending"],
                            },
                        ],
                        "hierarchy_proposals": [],
                        "semantic_relation_proposals": [],
                        "alias_proposals": [],
                        "ambiguity_notes": [],
                    }
                ),
                encoding="utf-8",
            )
            mapping_path.write_text(
                json.dumps(
                    {
                        "data_views": [
                            {
                                "id": "data_view:매출",
                                "status": "accepted",
                                "view_kind": "formula_summary_view",
                                "sheet": "매출",
                                "range": "A1:B2",
                                "evidence_refs": ["role_validation:매출"],
                            },
                            {
                                "id": "data_view:정가표",
                                "status": "accepted",
                                "view_kind": "formula_summary_view",
                                "sheet": "정가표",
                                "range": "A1:B2",
                                "evidence_refs": ["role_validation:정가표"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            table_io_path.write_text(
                json.dumps(
                    {
                        "summary": {"external_dependency_pipeline_count": 0},
                        "pipelines": [],
                    }
                ),
                encoding="utf-8",
            )
            domain_path.write_text(
                json.dumps(
                    {
                        "domain_layers": {
                            "general_domain_sources": [
                                {
                                    "id": "general_domain:accounting-kr/concepts.md",
                                    "file_name": "concepts.md",
                                }
                            ],
                            "local_domain_boundaries": [
                                {
                                    "id": "local_boundary:workbook_sample:test",
                                    "status": "review_required",
                                    "evidence_refs": ["evidence_package.source"],
                                }
                            ],
                        }
                    }
                ),
                encoding="utf-8",
            )

            validation = build_llm_proposal_validation(
                llm_proposals_path=proposals_path,
                document_ontology_mapping_path=mapping_path,
                table_io_pipelines_path=table_io_path,
                domain_source_model_path=domain_path,
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "workbook-llm-proposal-validation.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(validation)

        results = {item["proposal_id"]: item for item in validation["proposal_results"]}
        self.assertEqual(results["semantic_concept:매출"]["final_status"], "accepted")
        self.assertEqual(
            results["semantic_concept:정가표"]["final_status"],
            "quarantined",
        )
        self.assertEqual(validation["summary"]["proposal_result_count"], 2)
        self.assertEqual(validation["summary"]["accepted_count"], 1)
        self.assertEqual(validation["summary"]["quarantined_count"], 1)


if __name__ == "__main__":
    unittest.main()
