from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_action_contracts import build_action_contracts  # noqa: E402


class WorkbookActionContractsTest(unittest.TestCase):
    def test_builds_action_contracts_from_document_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            evidence_path = root / "evidence-package.json"
            mapping_path = root / "document-ontology.json"
            evidence_path.write_text(
                json.dumps({"domain_knowledge_refs": [{"id": "general_domain:test"}]}),
                encoding="utf-8",
            )
            mapping_path.write_text(
                json.dumps(
                    {
                        "source_artifacts": {"evidence_package": str(evidence_path)},
                        "data_views": [
                            {
                                "id": "data_view:pipeline_ok",
                                "status": "accepted",
                                "output_node_id": "region:summary",
                                "sheet": "Summary",
                                "range": "A1:B4",
                                "properties": {
                                    "reason": "summary_formula_role_supported",
                                    "confidence": 0.8,
                                },
                                "evidence_refs": ["role_validation_pipeline_ok"],
                                "source_artifact_refs": ["pipeline_role_validation"],
                            },
                            {
                                "id": "data_view:pipeline_review",
                                "status": "review_required",
                                "output_node_id": "region:review",
                                "sheet": "Summary",
                                "range": "D1:E4",
                                "properties": {
                                    "reason": "unresolved_input_region",
                                    "confidence": 0.52,
                                },
                                "evidence_refs": ["role_validation_pipeline_review"],
                                "source_artifact_refs": ["pipeline_role_validation"],
                            },
                        ],
                        "review_queue": [
                            {
                                "id": "gate_capture",
                                "kind": "gate_result",
                                "status": "review_required",
                                "reason": "capture_required",
                                "sheet": "Summary",
                                "range": "A1:B4",
                                "target_node_id": "region:summary",
                                "evidence_refs": ["gate_capture"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            package = build_action_contracts(mapping_path)

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-action-contracts.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        contracts = {item["id"]: item for item in package["action_contracts"]}
        self.assertEqual(
            contracts["action_contract:data_view:pipeline_ok"]["action_status"],
            "ready",
        )
        self.assertEqual(
            contracts["action_contract:data_view:pipeline_review"]["action_type"],
            "resolve_input_region_ownership",
        )
        self.assertEqual(
            contracts["action_contract:data_view:pipeline_review"]["priority"],
            "high",
        )
        self.assertEqual(
            contracts["action_contract:gate_capture"]["action_type"],
            "acquire_render_capture",
        )
        self.assertEqual(package["summary"]["action_contract_count"], 3)
        self.assertEqual(package["summary"]["ready_count"], 1)
        self.assertEqual(package["summary"]["open_count"], 2)


if __name__ == "__main__":
    unittest.main()
