from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_llm_proposals import build_llm_proposals  # noqa: E402


class WorkbookLlmProposalsTest(unittest.TestCase):
    def test_generates_proposal_only_semantic_candidates_with_gate_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mapping_path = root / "document-ontology.json"
            actions_path = root / "action-contracts.json"
            domain_path = root / "domain-source-model.json"
            sample_path = root / "readonly-sample.json"
            table_io_path = root / "table-io.json"

            mapping_path.write_text(
                json.dumps(
                    {
                        "data_views": [
                            {
                                "id": "data_view:pipeline_결제상세_cell_region_1",
                                "status": "accepted",
                                "sheet": "결제상세",
                                "range": "A1:AX20",
                                "evidence_refs": ["role_validation_source"],
                            },
                            {
                                "id": "data_view:pipeline_매출_cell_region_1",
                                "status": "accepted",
                                "sheet": "매출",
                                "range": "A1:L58",
                                "evidence_refs": ["role_validation_report"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            actions_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "open_count": 1,
                            "blocked_count": 0,
                            "high_priority_count": 1,
                            "ready_count": 1,
                        }
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
                                },
                                {
                                    "id": "general_domain:accounting-kr/logic_rules.md",
                                    "file_name": "logic_rules.md",
                                },
                                {
                                    "id": "general_domain:accounting-kr/structure_spec.md",
                                    "file_name": "structure_spec.md",
                                },
                                {
                                    "id": "general_domain:accounting-kr/dependency_rules.md",
                                    "file_name": "dependency_rules.md",
                                },
                            ],
                            "local_domain_boundaries": [
                                {"id": "local_boundary:workbook_sample:test"}
                            ],
                        },
                        "semantic_readiness": {
                            "status": "proposal_only_local_boundary_pending",
                            "blocking_factors": ["local_domain_boundary_not_confirmed"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            sample_path.write_text(
                json.dumps(
                    {
                        "sheets": [
                            {
                                "name": "결제상세",
                                "windows": [
                                    {
                                        "rows": [
                                            {
                                                "cells": [
                                                    {
                                                        "value_type": "string",
                                                        "value_preview": "주문번호",
                                                    },
                                                    {
                                                        "value_type": "string",
                                                        "value_preview": "결제/취소일",
                                                    },
                                                ]
                                            }
                                        ]
                                    }
                                ],
                            },
                            {
                                "name": "매출",
                                "windows": [
                                    {
                                        "rows": [
                                            {
                                                "cells": [
                                                    {
                                                        "value_type": "string",
                                                        "value_preview": "강의매출",
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            table_io_path.write_text(
                json.dumps(
                    {
                        "pipelines": [
                            {
                                "id": "pipeline_매출_from_결제상세",
                                "output_ref": {
                                    "sheet": "매출",
                                    "range": "A1:L58",
                                },
                                "input_refs": [
                                    {
                                        "sheet": "결제상세",
                                        "range": "A1:AX20",
                                    }
                                ],
                                "transform_refs": [
                                    {
                                        "kind": "formula_relation_group",
                                    }
                                ],
                                "evidence_refs": ["pipeline_relation"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            package = build_llm_proposals(
                document_ontology_mapping_path=mapping_path,
                action_contracts_path=actions_path,
                domain_source_model_path=domain_path,
                readonly_sample_path=sample_path,
                table_io_pipelines_path=table_io_path,
            )

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-llm-proposals.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        self.assertEqual(
            package["summary"]["proposal_status"],
            "proposal_only_pending_deterministic_validation",
        )
        self.assertGreaterEqual(
            package["summary"]["semantic_concept_proposal_count"],
            2,
        )
        self.assertEqual(package["summary"]["semantic_relation_proposal_count"], 1)
        self.assertTrue(
            all(
                proposal["proposal_status"] == "proposed"
                for proposal in package["semantic_concept_proposals"]
            )
        )
        self.assertIn(
            "source_trace_gate",
            package["validation_plan"]["gate_counts"],
        )


if __name__ == "__main__":
    unittest.main()
