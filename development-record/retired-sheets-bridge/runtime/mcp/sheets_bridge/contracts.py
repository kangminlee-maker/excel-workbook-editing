from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "1.0"
TABLE_BUILD_INTENT_KIND = "table_build_intent_v1"
TABLE_BUILD_PLAN_KIND = "table_build_plan_v1"
TABLE_BUILDER_SESSION_KIND = "table_builder_session_v1"
HOST_INTENT_SUBMIT_KIND = "table_build_intent_submit_v1"
HOST_INTENT_SAVED_KIND = "table_build_intent_saved_v1"
ARTIFACT_TYPES = {"google_sheets", "excel_workbook"}
CREATION_MODES = {"sheet", "copy"}


def validate_table_build_intent(intent: dict[str, Any]) -> dict[str, Any]:
    _require_object(intent, "TableBuildIntent")
    _require_const(intent, "schema_version", SCHEMA_VERSION)
    _require_const(intent, "intent_kind", TABLE_BUILD_INTENT_KIND)
    _require_non_empty_string(intent, "intent_id")
    _require_non_empty_string(intent, "created_at")
    _require_object_field(intent, "source")
    _require_object_field(intent, "source_package")
    artifact_type = _require_non_empty_string(intent, "artifact_type")
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError("intent.artifact_type must be google_sheets or excel_workbook")
    _require_output_canvas(intent.get("output_canvas"))
    _require_non_empty_string(intent, "llm_prompt")
    output = _require_object_field(intent, "output")
    creation_mode = _require_non_empty_string(output, "creation_mode", prefix="intent.output")
    if creation_mode not in CREATION_MODES:
        raise ValueError("intent.output.creation_mode must be sheet or copy")
    review_state = _require_object_field(intent, "review_state")
    _require_non_empty_string(review_state, "status", prefix="intent.review_state")
    return intent


def validate_table_build_plan(plan: dict[str, Any]) -> dict[str, Any]:
    _require_object(plan, "TableBuildPlan")
    _require_const(plan, "schema_version", SCHEMA_VERSION)
    _require_const(plan, "plan_kind", TABLE_BUILD_PLAN_KIND)
    _require_non_empty_string(plan, "intent_ref")
    for field in (
        "interpreted_output_shape",
        "formula_strategy",
        "target",
        "validation_plan",
        "rollback_plan",
    ):
        _require_object_field(plan, field)
    _require_array_field(plan, "source_evidence_needed")
    _require_array_field(plan, "unresolved_questions")
    target = plan["target"]
    artifact_type = _require_non_empty_string(target, "artifact_type", prefix="plan.target")
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError("plan.target.artifact_type must be google_sheets or excel_workbook")
    creation_mode = _require_non_empty_string(target, "creation_mode", prefix="plan.target")
    if creation_mode not in CREATION_MODES:
        raise ValueError("plan.target.creation_mode must be sheet or copy")
    return plan


def validate_table_builder_session(session: dict[str, Any]) -> dict[str, Any]:
    _require_object(session, "TableBuilderSession")
    _require_const(session, "schema_version", SCHEMA_VERSION)
    _require_const(session, "session_kind", TABLE_BUILDER_SESSION_KIND)
    _require_non_empty_string(session, "session_id")
    _require_non_empty_string(session, "created_at")
    _require_non_empty_string(session, "status")
    validate_table_build_intent(_require_object_field(session, "intent"))
    if session.get("plan") is not None:
        validate_table_build_plan(_require_object_field(session, "plan"))
    _require_object_field(session, "artifacts")
    return session


def validate_host_adapter_message(message: dict[str, Any]) -> dict[str, Any]:
    _require_object(message, "host adapter message")
    _require_const(message, "schema_version", SCHEMA_VERSION)
    message_kind = _require_non_empty_string(message, "message_kind")
    if message_kind == HOST_INTENT_SUBMIT_KIND:
        validate_table_build_intent(_require_object_field(message, "intent"))
        return message
    if message_kind == HOST_INTENT_SAVED_KIND:
        _require_non_empty_string(message, "intent_id")
        _require_non_empty_string(message, "intent_path")
        _require_non_empty_string(message, "next_prompt")
        _require_object_field(message, "package")
        return message
    raise ValueError("message.message_kind must be a supported table-builder host message")


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _require_object_field(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a JSON object")
    return value


def _require_array_field(payload: dict[str, Any], field: str) -> list[Any]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return value


def _require_const(payload: dict[str, Any], field: str, expected: str) -> None:
    if payload.get(field) != expected:
        raise ValueError(f"{field} must be {expected}")


def _require_non_empty_string(payload: dict[str, Any], field: str, *, prefix: str = "") -> str:
    value = str(payload.get(field) or "").strip()
    label = f"{prefix}.{field}" if prefix else field
    if not value:
        raise ValueError(f"{label} is required")
    return value


def _require_output_canvas(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError("intent.output_canvas is required")
    has_value = False
    for row in value:
        if not isinstance(row, list):
            raise ValueError("intent.output_canvas rows must be arrays")
        if any(str(cell or "").strip() for cell in row):
            has_value = True
    if not has_value:
        raise ValueError("intent.output_canvas is required")
