from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"


def build_boundary_decisions(
    block_candidates_path: Path,
    gate_execution_path: Path,
) -> dict[str, Any]:
    block_candidates_path = block_candidates_path.expanduser().resolve()
    gate_execution_path = gate_execution_path.expanduser().resolve()
    candidates = _read_json(block_candidates_path)
    gate_execution = _read_json(gate_execution_path)
    split_candidates = _split_candidates_by_id(candidates)
    gate_results = gate_execution.get("gate_results", [])
    decisions = []
    for sheet in candidates.get("sheets", []):
        for boundary_gate in sheet.get("boundary_gate_results", []):
            split_candidate = split_candidates.get(boundary_gate.get("candidate_id"))
            linked_results = _linked_gate_results(boundary_gate, gate_results)
            decisions.append(
                _boundary_decision(
                    boundary_gate,
                    split_candidate=split_candidate,
                    linked_results=linked_results,
                )
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "block_candidates": str(block_candidates_path),
            "gate_execution": str(gate_execution_path),
        },
        "method": {
            "name": "deterministic_boundary_acceptance",
            "authority": "boundary_decision_not_final_document_graph",
            "decision_policy": (
                "Accept only structurally strong split boundaries with no rejected "
                "cross-validation evidence. Retain style-only, merged-title, missing-capture, "
                "and view-state-risk boundaries as review items."
            ),
        },
        "boundary_decisions": decisions,
        "summary": _summary(decisions),
        "parser_observations": _parser_observations(decisions),
    }


def _split_candidates_by_id(candidates: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_id = {}
    for sheet in candidates.get("sheets", []):
        for candidate in sheet.get("cell_region_split_candidates", []):
            by_id[candidate["id"]] = candidate
    return by_id


def _linked_gate_results(
    boundary_gate: dict[str, Any],
    gate_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    boundary_id = boundary_gate.get("id")
    candidate_id = boundary_gate.get("candidate_id")
    linked = []
    for result in gate_results:
        if result.get("gate_type") != "boundary_confirmation":
            continue
        deterministic_inputs = set(result.get("deterministic_inputs", []))
        evidence_refs = set(result.get("evidence_refs", []))
        link_type = None
        if boundary_id in deterministic_inputs or (
            candidate_id and candidate_id in deterministic_inputs
        ):
            link_type = "direct"
        elif boundary_id in evidence_refs or (candidate_id and candidate_id in evidence_refs):
            link_type = "associated"
        if not link_type:
            continue
        linked.append(
            {
                "id": result.get("id"),
                "gate_check_id": result.get("gate_check_id"),
                "target_id": result.get("target_id"),
                "status": result.get("status"),
                "reason": result.get("reason"),
                "confidence": result.get("confidence"),
                "link_type": link_type,
            }
        )
    return sorted(
        linked,
        key=lambda item: (
            0 if item["link_type"] == "direct" else 1,
            str(item.get("target_id") or ""),
            str(item.get("id") or ""),
        ),
    )


def _boundary_decision(
    boundary_gate: dict[str, Any],
    *,
    split_candidate: dict[str, Any] | None,
    linked_results: list[dict[str, Any]],
) -> dict[str, Any]:
    status, decision, reason, confidence, graph_effect = _decision(
        boundary_gate,
        linked_results,
    )
    evidence_refs = _evidence_refs(boundary_gate, split_candidate, linked_results)
    return {
        "id": f"boundary_decision_{boundary_gate['id']}",
        "type": "document_boundary_decision",
        "sheet": boundary_gate.get("sheet"),
        "candidate_id": boundary_gate.get("candidate_id"),
        "candidate_type": boundary_gate.get("candidate_type"),
        "boundary_kind": _boundary_kind(boundary_gate),
        "source_boundary_gate_result_id": boundary_gate.get("id"),
        "source_boundary_status": boundary_gate.get("status"),
        "source_boundary_decision": boundary_gate.get("decision"),
        "source_boundary_score": boundary_gate.get("score"),
        "status": status,
        "decision": decision,
        "reason": reason,
        "confidence": confidence,
        "graph_effect": graph_effect,
        "related_region_ids": boundary_gate.get("related_region_ids", []),
        "boundary_location": _boundary_location(split_candidate),
        "linked_gate_results": linked_results,
        "evidence_refs": evidence_refs,
        "notes": _notes(boundary_gate, status, reason, linked_results),
    }


def _decision(
    boundary_gate: dict[str, Any],
    linked_results: list[dict[str, Any]],
) -> tuple[str, str, str, float, str]:
    if any(result.get("status") == "rejected" for result in linked_results):
        return (
            "rejected",
            "reject_boundary",
            "cross_validation_rejected",
            0.78,
            "do_not_create_graph_boundary",
        )

    candidate_type = boundary_gate.get("candidate_type")
    source_status = boundary_gate.get("status")
    evidence = set(boundary_gate.get("evidence", []))
    direct_accepted = any(
        result.get("status") == "accepted" and result.get("link_type") == "direct"
        for result in linked_results
    )
    associated_accepted = any(
        result.get("status") == "accepted" for result in linked_results
    )

    if (
        source_status == "strong_candidate"
        and candidate_type == "blank_column_boundary"
        and "materialized_region_boundary" in evidence
    ):
        confidence = 0.88 if direct_accepted else 0.82
        reason = (
            "strong_blank_column_boundary_with_visual_confirmation"
            if associated_accepted
            else "strong_blank_column_boundary_without_visual_contradiction"
        )
        return (
            "accepted",
            "accept_split_boundary",
            reason,
            confidence,
            "create_validated_split_boundary",
        )

    if (
        source_status == "review_candidate"
        and candidate_type == "repeated_header_touching_boundary"
        and direct_accepted
        and "materialized_region_boundary" in evidence
    ):
        return (
            "accepted",
            "accept_split_boundary",
            "repeated_header_boundary_with_direct_visual_confirmation",
            0.76,
            "create_validated_split_boundary",
        )

    if candidate_type == "style_discontinuity_boundary":
        return (
            "review_required",
            "retain_review_item",
            "style_only_boundary_needs_correlated_evidence",
            0.58 if direct_accepted else 0.48,
            "no_graph_boundary_created",
        )
    if candidate_type == "merged_range_title_boundary":
        return (
            "review_required",
            "retain_review_item",
            "merged_title_boundary_needs_semantic_review",
            0.55,
            "no_graph_boundary_created",
        )
    if not linked_results:
        return (
            "review_required",
            "retain_review_item",
            "boundary_not_in_current_capture_plan",
            0.4,
            "no_graph_boundary_created",
        )
    return (
        "review_required",
        "retain_review_item",
        "boundary_confirmation_needs_review",
        0.5,
        "no_graph_boundary_created",
    )


def _boundary_kind(boundary_gate: dict[str, Any]) -> str:
    if boundary_gate.get("type") == "merged_range_title_gate":
        return "title_or_section_boundary"
    return "split_boundary"


def _boundary_location(split_candidate: dict[str, Any] | None) -> dict[str, Any] | None:
    if not split_candidate:
        return None
    return {
        "parent_seed_block_id": split_candidate.get("parent_seed_block_id"),
        "from_region_id": split_candidate.get("from_region_id"),
        "to_region_id": split_candidate.get("to_region_id"),
        "boundary_within_region_id": split_candidate.get("boundary_within_region_id"),
        "boundary_after_column": split_candidate.get("boundary_after_column"),
        "boundary_before_column": split_candidate.get("boundary_before_column"),
    }


def _evidence_refs(
    boundary_gate: dict[str, Any],
    split_candidate: dict[str, Any] | None,
    linked_results: list[dict[str, Any]],
) -> list[str]:
    refs = []
    for item in [
        boundary_gate.get("id"),
        boundary_gate.get("candidate_id"),
        *(boundary_gate.get("evidence", [])),
        *((split_candidate or {}).get("evidence", [])),
        *(result.get("id") for result in linked_results),
        *(result.get("gate_check_id") for result in linked_results),
    ]:
        if item and item not in refs:
            refs.append(item)
    return refs


def _notes(
    boundary_gate: dict[str, Any],
    status: str,
    reason: str,
    linked_results: list[dict[str, Any]],
) -> str:
    linked_summary = _linked_summary(linked_results)
    if status == "accepted":
        return (
            f"{boundary_gate.get('candidate_type')} accepted as a document graph "
            f"boundary: {reason}. {linked_summary}"
        ).strip()
    if status == "rejected":
        return (
            f"{boundary_gate.get('candidate_type')} rejected by deterministic "
            f"gate evidence: {reason}. {linked_summary}"
        ).strip()
    return (
        f"{boundary_gate.get('candidate_type')} retained for review: {reason}. "
        f"{linked_summary}"
    ).strip()


def _linked_summary(linked_results: list[dict[str, Any]]) -> str:
    if not linked_results:
        return "No linked boundary_confirmation gate result is available yet."
    counts = Counter(
        f"{result.get('link_type')}:{result.get('status')}:{result.get('reason')}"
        for result in linked_results
    )
    return "Linked gates: " + ", ".join(
        f"{key}={value}" for key, value in sorted(counts.items())
    )


def _summary(decisions: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "boundary_decision_count": len(decisions),
        "accepted_count": _count_status(decisions, "accepted"),
        "rejected_count": _count_status(decisions, "rejected"),
        "review_required_count": _count_status(decisions, "review_required"),
        "split_boundary_count": _count_kind(decisions, "split_boundary"),
        "title_or_section_boundary_count": _count_kind(
            decisions,
            "title_or_section_boundary",
        ),
        "accepted_split_boundary_count": sum(
            1
            for decision in decisions
            if decision["status"] == "accepted"
            and decision["boundary_kind"] == "split_boundary"
        ),
        "style_only_review_count": _count_reason(
            decisions,
            "style_only_boundary_needs_correlated_evidence",
        ),
        "missing_capture_review_count": _count_link_reason(
            decisions,
            "capture_required",
        ),
        "view_state_review_count": _count_link_reason(
            decisions,
            "view_state_blocked",
        )
        + _count_link_reason(decisions, "view_state_warning"),
    }


def _count_status(decisions: list[dict[str, Any]], status: str) -> int:
    return sum(1 for decision in decisions if decision["status"] == status)


def _count_kind(decisions: list[dict[str, Any]], kind: str) -> int:
    return sum(1 for decision in decisions if decision["boundary_kind"] == kind)


def _count_reason(decisions: list[dict[str, Any]], reason: str) -> int:
    return sum(1 for decision in decisions if decision["reason"] == reason)


def _count_link_reason(decisions: list[dict[str, Any]], reason: str) -> int:
    return sum(
        1
        for decision in decisions
        if any(result.get("reason") == reason for result in decision["linked_gate_results"])
    )


def _parser_observations(decisions: list[dict[str, Any]]) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": "Boundary decisions are graph-boundary candidates, not the final document graph.",
        }
    ]
    review_required = _count_status(decisions, "review_required")
    if review_required:
        observations.append(
            {
                "level": "warning",
                "message": f"{review_required} boundaries remain review-required because evidence is style-only, title-only, uncaptured, or view-state/quality limited.",
            }
        )
    return observations


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve workbook boundary candidates into accepted, rejected, or review-required decisions."
    )
    parser.add_argument("block_candidates", type=Path)
    parser.add_argument("gate_execution", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = build_boundary_decisions(args.block_candidates, args.gate_execution)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(package, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(package["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
