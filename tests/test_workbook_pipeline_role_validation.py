from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_pipeline_role_validation import build_pipeline_role_validation  # noqa: E402


class WorkbookPipelineRoleValidationTest(unittest.TestCase):
    def test_validates_pivot_and_formula_roles_while_retaining_unresolved_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pipelines_path = root / "pipelines.json"
            gates_path = root / "gate-execution.json"
            boundaries_path = root / "boundary-decisions.json"
            pipelines_path.write_text(json.dumps(_pipelines()), encoding="utf-8")
            gates_path.write_text(json.dumps(_gate_execution()), encoding="utf-8")
            boundaries_path.write_text(
                json.dumps(_boundary_decisions()),
                encoding="utf-8",
            )

            package = build_pipeline_role_validation(
                pipelines_path,
                gates_path,
                boundaries_path,
            )

        validations = {
            item["pipeline_id"]: item
            for item in package["role_validations"]
        }
        self.assertEqual(validations["pipeline_pivot"]["status"], "accepted")
        self.assertEqual(validations["pipeline_pivot"]["validated_role"], "report")
        self.assertIn("pivot_cache_transform", validations["pipeline_pivot"]["role_evidence"])
        self.assertEqual(validations["pipeline_summary"]["status"], "accepted")
        self.assertEqual(validations["pipeline_unresolved"]["status"], "review_required")
        self.assertEqual(validations["pipeline_unresolved"]["reason"], "unresolved_input_region")
        self.assertEqual(package["summary"]["accepted_count"], 2)
        self.assertEqual(package["summary"]["review_required_count"], 1)

        schema = json.loads(
            (
                REPO_ROOT / "schemas" / "workbook-pipeline-role-validation.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(package)


def _pipelines() -> dict:
    return {
        "pipelines": [
            {
                "id": "pipeline_pivot",
                "role": "report",
                "output_ref": _ref("pivot_out", "pivot_table", "Report", "A1:B5", None, "pivot_block"),
                "input_refs": [_ref("raw_region", "cell_region", "Raw", "A1:D20", "raw_region", "raw_band")],
                "transform_refs": [
                    {
                        "id": "pivot_transform",
                        "kind": "pivot_cache",
                        "formula_signature": None,
                        "formula_cell_count": 0,
                    }
                ],
                "review_flags": ["pivot_cache_dependency"],
                "evidence_refs": ["pivot_relation"],
            },
            {
                "id": "pipeline_summary",
                "role": "summary",
                "output_ref": _ref("summary_region", "cell_region", "Summary", "A1:C4", "summary_region", "summary_band"),
                "input_refs": [_ref("raw_region", "cell_region", "Raw", "A1:D20", "raw_region", "raw_band")],
                "transform_refs": [
                    {
                        "id": "formula_transform",
                        "kind": "formula_signature_group",
                        "formula_signature": "SUMIFS(Raw!C:C,Raw!A:A,A2)",
                        "formula_cell_count": 12,
                    }
                ],
                "review_flags": ["repeated_formula_family"],
                "evidence_refs": ["formula_group"],
            },
            {
                "id": "pipeline_unresolved",
                "role": "transform",
                "output_ref": _ref("calc_region", "cell_region", "Calc", "A1:C4", "calc_region", "calc_band"),
                "input_refs": [_ref("range_raw", "workbook_range", "Raw", "Z1:Z5", None, None)],
                "transform_refs": [
                    {
                        "id": "calc_transform",
                        "kind": "formula_signature_group",
                        "formula_signature": "A1+1",
                        "formula_cell_count": 2,
                    }
                ],
                "review_flags": ["unresolved_input_region"],
                "evidence_refs": ["calc_group"],
            },
        ]
    }


def _ref(
    ref_id: str,
    kind: str,
    sheet: str,
    range_text: str,
    region_id: str | None,
    block_id: str | None,
) -> dict:
    return {
        "id": ref_id,
        "kind": kind,
        "sheet": sheet,
        "range": range_text,
        "region_id": region_id,
        "block_id": block_id,
    }


def _gate_execution() -> dict:
    return {
        "gate_results": [
            _gate_result("gate_pivot", "pipeline_pivot", "pivot_cache_visual_alignment", "review_required"),
            _gate_result("gate_summary", "pipeline_summary", "formula_summary_visual_alignment", "accepted"),
        ]
    }


def _gate_result(
    result_id: str,
    pipeline_id: str,
    gate_type: str,
    status: str,
) -> dict:
    return {
        "id": result_id,
        "gate_check_id": f"check_{result_id}",
        "target_id": f"target_{result_id}",
        "gate_type": gate_type,
        "status": status,
        "reason": (
            "deterministic_visual_evidence_available"
            if status == "accepted"
            else "capture_required"
        ),
        "confidence": 0.82 if status == "accepted" else 0.25,
        "deterministic_inputs": [pipeline_id],
        "evidence_refs": [pipeline_id],
    }


def _boundary_decisions() -> dict:
    return {
        "boundary_decisions": [
            {
                "id": "boundary_decision_raw",
                "status": "accepted",
                "related_region_ids": ["raw_region"],
            },
            {
                "id": "boundary_decision_summary",
                "status": "review_required",
                "related_region_ids": ["summary_region"],
            },
        ]
    }


if __name__ == "__main__":
    unittest.main()
