from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_domain_source_model import build_domain_source_model  # noqa: E402


class WorkbookDomainSourceModelTest(unittest.TestCase):
    def test_separates_general_domain_from_boundary_pending_local_domain(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            domain_root = root / "accounting-kr"
            domain_root.mkdir()
            concept_path = domain_root / "concepts.md"
            concept_path.write_text(
                "# accounting-korea Domain\n\n## 수익 인식\n",
                encoding="utf-8",
            )
            evidence_path = root / "evidence-package.json"
            mapping_path = root / "document-ontology.json"
            action_path = root / "action-contracts.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "source": {
                            "path": str(root / "source.xlsx"),
                            "file_name": "source.xlsx",
                            "sha256": "a" * 64,
                        },
                        "domain_knowledge_refs": [
                            {
                                "id": "general_domain:accounting-kr/concepts.md",
                                "layer": "general_domain",
                                "path": str(concept_path),
                                "scope": "current_sample_workbook",
                                "status": "available",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            mapping_path.write_text(
                json.dumps({"summary": {"review_queue_count": 2}}),
                encoding="utf-8",
            )
            action_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "open_count": 3,
                            "blocked_count": 1,
                            "high_priority_count": 2,
                            "ready_count": 4,
                        }
                    }
                ),
                encoding="utf-8",
            )

            model = build_domain_source_model(
                evidence_package_path=evidence_path,
                document_ontology_mapping_path=mapping_path,
                action_contracts_path=action_path,
            )

        schema = json.loads(
            (
                REPO_ROOT / "schemas" / "workbook-domain-source-model.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(model)

        self.assertEqual(model["summary"]["general_domain_source_count"], 1)
        self.assertEqual(model["summary"]["local_domain_source_count"], 0)
        self.assertEqual(
            model["summary"]["review_required_local_domain_boundary_count"],
            1,
        )
        self.assertEqual(
            model["semantic_readiness"]["status"],
            "proposal_only_local_boundary_pending",
        )
        self.assertIn(
            "local_domain_boundary_not_confirmed",
            model["semantic_readiness"]["blocking_factors"],
        )
        self.assertFalse(model["semantic_readiness"]["shared_ontology_promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
