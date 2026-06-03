from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_cross_validation_gate_execution import (  # noqa: E402
    build_cross_validation_gate_execution,
)


class WorkbookCrossValidationGateExecutionTest(unittest.TestCase):
    def test_executes_supported_gates_and_keeps_review_required_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            plan_path = root / "plan.json"
            features_path = root / "features.json"
            plan_path.write_text(json.dumps(_cross_validation_plan()), encoding="utf-8")
            features_path.write_text(json.dumps(_visual_features()), encoding="utf-8")

            package = build_cross_validation_gate_execution(plan_path, features_path)

        statuses = {
            result["gate_check_id"]: result["status"]
            for result in package["gate_results"]
        }
        self.assertEqual(statuses["gate_supported"], "accepted")
        self.assertEqual(statuses["gate_blocked"], "review_required")
        self.assertEqual(statuses["gate_uncaptured"], "review_required")
        self.assertEqual(statuses["gate_image"], "review_required")
        self.assertEqual(package["summary"]["accepted_count"], 1)
        self.assertEqual(package["summary"]["review_required_count"], 3)

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "workbook-cross-validation-gate-execution.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(package)


def _cross_validation_plan() -> dict:
    return {
        "capture_targets": [
            _target("target_supported", "pipeline_output", "Sheet1", "A1:C5"),
            _target("target_blocked", "pipeline_output", "Sheet1", "A7:C12"),
            _target("target_uncaptured", "pipeline_output", "Sheet1", "A14:C18"),
            _target("target_image", "image_hierarchy", "Sheet1", "E1:H8"),
        ],
        "gate_checks": [
            _gate("gate_supported", "target_supported", "formula_region_coherence"),
            _gate("gate_blocked", "target_blocked", "formula_region_coherence"),
            _gate("gate_uncaptured", "target_uncaptured", "formula_region_coherence"),
            _gate("gate_image", "target_image", "image_table_hierarchy_confirmation"),
        ],
    }


def _target(target_id: str, target_type: str, sheet: str, range_text: str) -> dict:
    return {
        "id": target_id,
        "target_type": target_type,
        "sheet": sheet,
        "range": range_text,
        "evidence_refs": [f"evidence_{target_id}"],
    }


def _gate(gate_id: str, target_id: str, gate_type: str) -> dict:
    return {
        "id": gate_id,
        "target_id": target_id,
        "gate_type": gate_type,
        "deterministic_inputs": [f"input_{gate_id}"],
    }


def _visual_features() -> dict:
    return {
        "feature_results": [
            {
                "id": "feature_supported",
                "target_id": "target_supported",
                "status": "detected",
                "layout_signals": [
                    "visible_content_bbox",
                    "grid_or_table_line_structure",
                ],
                "evidence_refs": ["feature_supported"],
            },
            {
                "id": "feature_blocked",
                "target_id": "target_blocked",
                "status": "skipped_view_state_blocked",
                "layout_signals": [],
                "evidence_refs": ["feature_blocked"],
            },
            {
                "id": "feature_image",
                "target_id": "target_image",
                "status": "detected",
                "layout_signals": [
                    "visible_content_bbox",
                    "grid_or_table_line_structure",
                ],
                "evidence_refs": ["feature_image"],
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
