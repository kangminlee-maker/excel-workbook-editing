from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"
ACCEPTABLE_VISUAL_GATE_TYPES = {
    "boundary_confirmation",
    "formula_region_coherence",
    "formula_summary_visual_alignment",
    "pipeline_input_output_alignment",
    "pivot_cache_visual_alignment",
}


def build_cross_validation_gate_execution(
    cross_validation_plan_path: Path,
    visual_features_path: Path,
) -> dict[str, Any]:
    cross_validation_plan_path = cross_validation_plan_path.expanduser().resolve()
    visual_features_path = visual_features_path.expanduser().resolve()
    plan = _read_json(cross_validation_plan_path)
    visual_features = _read_json(visual_features_path)
    target_by_id = {
        target.get("id"): target
        for target in plan.get("capture_targets", [])
    }
    feature_by_target_id = {
        result.get("target_id"): result
        for result in visual_features.get("feature_results", [])
        if result.get("target_id")
    }
    gate_results = [
        _execute_gate(gate, target_by_id.get(gate.get("target_id")), feature_by_target_id)
        for gate in plan.get("gate_checks", [])
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "cross_validation_plan": str(cross_validation_plan_path),
            "visual_features": str(visual_features_path),
        },
        "method": {
            "name": "deterministic_cross_validation_gate_execution",
            "authority": "evidence_gate_status_not_final_document_graph_truth",
            "decision_policy": (
                "Accept only gates with sufficient deterministic visual evidence and no "
                "view-state or quality blockers. Otherwise retain review_required."
            ),
        },
        "gate_results": gate_results,
        "summary": _summary(gate_results),
        "parser_observations": _parser_observations(gate_results),
    }


def _execute_gate(
    gate: dict[str, Any],
    target: dict[str, Any] | None,
    feature_by_target_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    feature = feature_by_target_id.get(gate.get("target_id"))
    status, reason, confidence, signals = _decision(gate, target, feature)
    return {
        "id": f"result_{gate.get('id')}",
        "type": "cross_validation_gate_result",
        "gate_check_id": gate.get("id"),
        "target_id": gate.get("target_id"),
        "gate_type": gate.get("gate_type"),
        "status": status,
        "reason": reason,
        "confidence": confidence,
        "target_type": (target or {}).get("target_type"),
        "sheet": (target or {}).get("sheet"),
        "range": (target or {}).get("range"),
        "feature_result_id": (feature or {}).get("id"),
        "feature_status": (feature or {}).get("status"),
        "layout_signals": (feature or {}).get("layout_signals", []),
        "deterministic_inputs": gate.get("deterministic_inputs", []),
        "evidence_refs": _evidence_refs(gate, target, feature),
        "notes": _notes(gate, status, reason, signals),
    }


def _decision(
    gate: dict[str, Any],
    target: dict[str, Any] | None,
    feature: dict[str, Any] | None,
) -> tuple[str, str, float, list[str]]:
    if target is None:
        return "review_required", "target_missing", 0.1, []
    if feature is None:
        return "review_required", "capture_required", 0.25, []
    feature_status = feature.get("status")
    if feature_status == "skipped_view_state_blocked":
        return "review_required", "view_state_blocked", 0.45, feature.get("layout_signals", [])
    if feature_status == "skipped_quality_review":
        return "review_required", "capture_quality_review_required", 0.45, feature.get("layout_signals", [])
    if feature_status in {"skipped_unusable", "not_available"}:
        return "review_required", "visual_evidence_unavailable", 0.2, feature.get("layout_signals", [])
    if feature_status == "no_visible_content_detected":
        return "rejected", "no_visible_content_detected", 0.75, feature.get("layout_signals", [])
    if feature_status == "detected_with_view_state_warning":
        return "review_required", "view_state_warning", 0.62, feature.get("layout_signals", [])

    signals = feature.get("layout_signals", [])
    gate_type = gate.get("gate_type")
    if gate_type == "image_table_hierarchy_confirmation":
        return "review_required", "object_hierarchy_features_not_implemented", 0.5, signals
    if gate_type not in ACCEPTABLE_VISUAL_GATE_TYPES:
        return "review_required", "gate_type_not_deterministically_supported", 0.4, signals
    if "visible_content_bbox" not in signals:
        return "review_required", "visible_content_bbox_missing", 0.45, signals
    if gate_type in {
        "boundary_confirmation",
        "formula_region_coherence",
        "formula_summary_visual_alignment",
        "pivot_cache_visual_alignment",
    } and "grid_or_table_line_structure" not in signals:
        return "review_required", "grid_or_table_signal_missing", 0.55, signals
    return "accepted", "deterministic_visual_evidence_available", 0.82, signals


def _evidence_refs(
    gate: dict[str, Any],
    target: dict[str, Any] | None,
    feature: dict[str, Any] | None,
) -> list[str]:
    refs = []
    for item in [
        gate.get("id"),
        *gate.get("deterministic_inputs", []),
        *((target or {}).get("evidence_refs", [])),
        *((feature or {}).get("evidence_refs", [])),
        (feature or {}).get("id"),
    ]:
        if item and item not in refs:
            refs.append(item)
    return refs


def _notes(
    gate: dict[str, Any],
    status: str,
    reason: str,
    signals: list[str],
) -> str:
    if status == "accepted":
        return (
            f"{gate.get('gate_type')} accepted from deterministic visual evidence: "
            f"{', '.join(signals)}."
        )
    if status == "rejected":
        return f"{gate.get('gate_type')} rejected: {reason}."
    return f"{gate.get('gate_type')} requires review: {reason}."


def _summary(gate_results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "gate_result_count": len(gate_results),
        "accepted_count": _count_status(gate_results, "accepted"),
        "rejected_count": _count_status(gate_results, "rejected"),
        "review_required_count": _count_status(gate_results, "review_required"),
        "capture_required_count": _count_reason(gate_results, "capture_required"),
        "view_state_blocked_count": _count_reason(gate_results, "view_state_blocked"),
        "quality_review_required_count": _count_reason(
            gate_results,
            "capture_quality_review_required",
        ),
        "object_hierarchy_review_count": _count_reason(
            gate_results,
            "object_hierarchy_features_not_implemented",
        ),
    }


def _count_status(gate_results: list[dict[str, Any]], status: str) -> int:
    return sum(1 for result in gate_results if result["status"] == status)


def _count_reason(gate_results: list[dict[str, Any]], reason: str) -> int:
    return sum(1 for result in gate_results if result["reason"] == reason)


def _parser_observations(gate_results: list[dict[str, Any]]) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": "Cross-validation gate execution produces evidence status only; accepted gates are not yet a final document graph.",
        }
    ]
    review_required = _count_status(gate_results, "review_required")
    if review_required:
        observations.append(
            {
                "level": "warning",
                "message": f"{review_required} gates still require capture, view-state, quality, object hierarchy, or human review.",
            }
        )
    return observations


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute deterministic cross-validation gates from visual feature evidence."
    )
    parser.add_argument("cross_validation_plan", type=Path)
    parser.add_argument("visual_features", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = build_cross_validation_gate_execution(
        args.cross_validation_plan,
        args.visual_features,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(package, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(package["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
