from __future__ import annotations

import json
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]

from spreadsheet_processing.table_build_contracts import (
    TABLE_BUILD_INTENT_KIND,
    TABLE_BUILD_PLAN_KIND,
    validate_table_build_intent,
    validate_table_build_plan,
)


class TableBuilderContractsTest(unittest.TestCase):
    def test_table_build_intent_schema_validates_fixture(self) -> None:
        intent = _intent()

        _validate_schema("table-build-intent.schema.json", intent)
        self.assertIs(validate_table_build_intent(intent), intent)

    def test_table_build_plan_schema_validates_fixture(self) -> None:
        plan = _plan()

        _validate_schema("table-build-plan.schema.json", plan)
        self.assertIs(validate_table_build_plan(plan), plan)

    def test_intent_contract_rejects_missing_prompt(self) -> None:
        intent = _intent()
        intent["llm_prompt"] = ""

        with self.assertRaisesRegex(ValueError, "llm_prompt"):
            validate_table_build_intent(intent)

    def test_intent_contract_rejects_missing_review_next_action(self) -> None:
        intent = _intent()
        intent["review_state"]["next_action"] = ""

        with self.assertRaisesRegex(ValueError, "review_state.next_action"):
            validate_table_build_intent(intent)

    def test_plan_contract_rejects_incomplete_source_evidence_request(self) -> None:
        plan = _plan()
        plan["source_evidence_needed"][0]["range"] = ""

        with self.assertRaisesRegex(ValueError, r"source_evidence_needed\[0\]\.range"):
            validate_table_build_plan(plan)

    def test_plan_contract_rejects_missing_formula_strategy_summary(self) -> None:
        plan = _plan()
        plan["formula_strategy"]["summary"] = ""

        with self.assertRaisesRegex(ValueError, "formula_strategy.summary"):
            validate_table_build_plan(plan)


def _validate_schema(filename: str, payload: dict) -> None:
    schema = json.loads((REPO_ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def _intent() -> dict:
    return {
        "schema_version": "1.0",
        "intent_kind": TABLE_BUILD_INTENT_KIND,
        "intent_id": "intent-1",
        "created_at": "2026-06-08T00:00:00+00:00",
        "source": {
            "artifact_type": "google_sheets",
            "spreadsheet_id": "spreadsheet-1",
            "sheet_title": "Raw",
            "qualified_range": "'Raw'!A1:C4",
        },
        "source_package": {
            "manifest_path": "review-packages/spreadsheet-processing/table-builder-fixtures/intent-1/manifest.json",
            "source_path": "review-packages/spreadsheet-processing/table-builder-fixtures/intent-1/builder-source.json",
        },
        "artifact_type": "google_sheets",
        "output_canvas": [["", "Jan"], ["Team A", ""]],
        "llm_prompt": "원본 데이터 안에서 팀별 월별 매출 합계를 수식으로 계산하는 새 표를 만들어줘.",
        "source_hints": {"selected_ranges": ["'Raw'!A1:C4"]},
        "fields": {},
        "formula": {},
        "output": {"creation_mode": "sheet", "preferred_title": "FORMULA_TABLE_RESULT"},
        "review_state": {
            "status": "submitted",
            "next_action": "Generate a TableBuildPlan from this intent and ask the user to confirm the interpreted table shape.",
        },
    }


def _plan() -> dict:
    return {
        "schema_version": "1.0",
        "plan_kind": TABLE_BUILD_PLAN_KIND,
        "intent_ref": "review-packages/spreadsheet-processing/table-builder-fixtures/intents/intent-1/intent.json",
        "interpreted_output_shape": {
            "rows": ["Team A"],
            "columns": ["Jan"],
            "measure": "매출 합계",
        },
        "source_evidence_needed": [{"range": "'Raw'!A1:C4", "purpose": "팀, 월, 매출 후보 열 확인"}],
        "formula_strategy": {
            "summary": "팀과 월 조건으로 원본 매출 열을 집계하는 source-referencing formulas",
            "risk_annotations": [],
        },
        "target": {
            "artifact_type": "google_sheets",
            "creation_mode": "sheet",
            "sheet_title": "FORMULA_TABLE_RESULT",
        },
        "validation_plan": {"readback": "created sheet formatted values and formulas"},
        "rollback_plan": {"kind": "delete_created_sheet"},
        "unresolved_questions": [],
    }


if __name__ == "__main__":
    unittest.main()
