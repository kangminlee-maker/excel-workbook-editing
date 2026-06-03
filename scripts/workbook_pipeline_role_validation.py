from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"


def build_pipeline_role_validation(
    table_io_pipelines_path: Path,
    gate_execution_path: Path,
    boundary_decisions_path: Path,
) -> dict[str, Any]:
    table_io_pipelines_path = table_io_pipelines_path.expanduser().resolve()
    gate_execution_path = gate_execution_path.expanduser().resolve()
    boundary_decisions_path = boundary_decisions_path.expanduser().resolve()
    pipelines_package = _read_json(table_io_pipelines_path)
    gate_execution = _read_json(gate_execution_path)
    boundary_decisions = _read_json(boundary_decisions_path)
    gate_results = gate_execution.get("gate_results", [])
    boundary_index = _boundary_index(boundary_decisions)
    validations = [
        _validate_pipeline_role(
            pipeline,
            linked_gate_results=_linked_gate_results(pipeline, gate_results),
            boundary_constraints=_boundary_constraints(pipeline, boundary_index),
        )
        for pipeline in pipelines_package.get("pipelines", [])
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "table_io_pipelines": str(table_io_pipelines_path),
            "gate_execution": str(gate_execution_path),
            "boundary_decisions": str(boundary_decisions_path),
        },
        "method": {
            "name": "deterministic_pipeline_role_validation",
            "authority": "pipeline_role_decision_not_final_document_graph",
            "decision_policy": (
                "Validate roles from formula signatures, pivot cache definitions, input/output refs, "
                "accepted boundary constraints, and gate contradictions. Missing visual capture is a "
                "review annotation unless it invalidates the role evidence."
            ),
        },
        "role_validations": validations,
        "summary": _summary(validations),
        "parser_observations": _parser_observations(validations),
    }


def _boundary_index(boundary_decisions: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_region: dict[str, list[dict[str, Any]]] = {}
    for decision in boundary_decisions.get("boundary_decisions", []):
        for region_id in decision.get("related_region_ids", []):
            by_region.setdefault(region_id, []).append(decision)
    return by_region


def _linked_gate_results(
    pipeline: dict[str, Any],
    gate_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pipeline_id = pipeline["id"]
    linked = []
    for result in gate_results:
        refs = set(result.get("deterministic_inputs", [])) | set(
            result.get("evidence_refs", [])
        )
        if pipeline_id not in refs:
            continue
        linked.append(
            {
                "id": result.get("id"),
                "gate_check_id": result.get("gate_check_id"),
                "target_id": result.get("target_id"),
                "gate_type": result.get("gate_type"),
                "status": result.get("status"),
                "reason": result.get("reason"),
                "confidence": result.get("confidence"),
            }
        )
    return sorted(
        linked,
        key=lambda item: (
            str(item.get("status") or ""),
            str(item.get("gate_type") or ""),
            str(item.get("id") or ""),
        ),
    )


def _boundary_constraints(
    pipeline: dict[str, Any],
    boundary_index: dict[str, list[dict[str, Any]]],
) -> dict[str, list[str]]:
    region_ids = _pipeline_region_ids(pipeline)
    accepted = []
    review_required = []
    rejected = []
    for region_id in region_ids:
        for decision in boundary_index.get(region_id, []):
            target = {
                "accepted": accepted,
                "review_required": review_required,
                "rejected": rejected,
            }[decision["status"]]
            if decision["id"] not in target:
                target.append(decision["id"])
    return {
        "accepted_boundary_ids": sorted(accepted),
        "review_required_boundary_ids": sorted(review_required),
        "rejected_boundary_ids": sorted(rejected),
    }


def _pipeline_region_ids(pipeline: dict[str, Any]) -> list[str]:
    region_ids = []
    output_region_id = pipeline.get("output_ref", {}).get("region_id")
    if output_region_id:
        region_ids.append(output_region_id)
    for ref in pipeline.get("input_refs", []):
        region_id = ref.get("region_id")
        if region_id and region_id not in region_ids:
            region_ids.append(region_id)
    return region_ids


def _validate_pipeline_role(
    pipeline: dict[str, Any],
    *,
    linked_gate_results: list[dict[str, Any]],
    boundary_constraints: dict[str, list[str]],
) -> dict[str, Any]:
    role_evidence = _role_evidence(pipeline, boundary_constraints)
    status, reason, confidence, blockers = _decision(
        pipeline,
        role_evidence=role_evidence,
        linked_gate_results=linked_gate_results,
        boundary_constraints=boundary_constraints,
    )
    validated_role = pipeline["role"] if status != "rejected" else None
    return {
        "id": f"role_validation_{pipeline['id']}",
        "type": "pipeline_role_validation",
        "pipeline_id": pipeline["id"],
        "status": status,
        "reason": reason,
        "confidence": confidence,
        "asserted_role": pipeline["role"],
        "validated_role": validated_role,
        "output_ref": _compact_ref(pipeline.get("output_ref", {})),
        "input_ref_count": len(pipeline.get("input_refs", [])),
        "transform_ref_count": len(pipeline.get("transform_refs", [])),
        "role_evidence": role_evidence,
        "review_flags": pipeline.get("review_flags", []),
        "blockers": blockers,
        "linked_gate_results": linked_gate_results,
        "boundary_constraints": boundary_constraints,
        "evidence_refs": _evidence_refs(pipeline, linked_gate_results, boundary_constraints),
        "notes": _notes(pipeline, status, reason, blockers, linked_gate_results),
    }


def _role_evidence(
    pipeline: dict[str, Any],
    boundary_constraints: dict[str, list[str]],
) -> list[str]:
    evidence = []
    output_kind = pipeline.get("output_ref", {}).get("kind")
    if output_kind:
        evidence.append(f"output:{output_kind}")
    for transform in pipeline.get("transform_refs", []):
        if transform.get("kind") == "pivot_cache":
            evidence.append("pivot_cache_transform")
        elif transform.get("kind") == "formula_signature_group":
            evidence.append("formula_signature_group")
            signature = transform.get("formula_signature") or ""
            if "SUBTOTAL(" in signature:
                evidence.append("subtotal_formula")
            if "SUMIFS(" in signature:
                evidence.append("sumifs_formula")
            if transform.get("formula_cell_count", 0) >= 10:
                evidence.append("repeated_formula_family")
    input_kinds = sorted({ref.get("kind") for ref in pipeline.get("input_refs", [])})
    for kind in input_kinds:
        evidence.append(f"input:{kind}")
    if boundary_constraints["accepted_boundary_ids"]:
        evidence.append("accepted_boundary_constraint")
    if boundary_constraints["review_required_boundary_ids"]:
        evidence.append("review_required_boundary_constraint")
    return sorted(set(evidence))


def _decision(
    pipeline: dict[str, Any],
    *,
    role_evidence: list[str],
    linked_gate_results: list[dict[str, Any]],
    boundary_constraints: dict[str, list[str]],
) -> tuple[str, str, float, list[str]]:
    blockers = []
    role = pipeline.get("role")
    review_flags = set(pipeline.get("review_flags", []))
    rejected_gates = [
        result for result in linked_gate_results if result.get("status") == "rejected"
    ]
    if rejected_gates:
        blockers.append("rejected_gate_evidence")
    if boundary_constraints["rejected_boundary_ids"]:
        blockers.append("rejected_boundary_constraint")
    if rejected_gates or boundary_constraints["rejected_boundary_ids"]:
        return "rejected", "role_contradicted_by_gate_or_boundary", 0.8, blockers

    if "unresolved_input_region" in review_flags:
        blockers.append("unresolved_input_region")
    if "external_workbook_dependency" in review_flags:
        blockers.append("external_workbook_dependency")
    if role == "unknown":
        blockers.append("unknown_role")
    if blockers:
        return "review_required", blockers[0], 0.52, blockers

    if role == "report" and "pivot_cache_transform" in role_evidence:
        return "accepted", "pivot_cache_report_role_supported", _confidence(0.86, linked_gate_results), []
    if role == "summary" and (
        "subtotal_formula" in role_evidence or "sumifs_formula" in role_evidence
    ):
        return "accepted", "summary_formula_role_supported", _confidence(0.8, linked_gate_results), []
    if role == "bridge" and "formula_signature_group" in role_evidence:
        return "accepted", "cross_sheet_formula_bridge_supported", _confidence(0.74, linked_gate_results), []
    if role == "transform" and "formula_signature_group" in role_evidence:
        return "accepted", "formula_transform_role_supported", _confidence(0.72, linked_gate_results), []
    if role in {"input", "parameter", "audit_check"}:
        return "review_required", "passive_role_needs_explicit_source_policy", 0.5, []
    return "review_required", "role_evidence_incomplete", 0.48, []


def _confidence(base: float, linked_gate_results: list[dict[str, Any]]) -> float:
    confidence = base
    if any(result.get("status") == "accepted" for result in linked_gate_results):
        confidence += 0.03
    if any(result.get("status") == "review_required" for result in linked_gate_results):
        confidence -= 0.02
    return round(max(0.0, min(confidence, 0.92)), 4)


def _compact_ref(ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": ref.get("id"),
        "kind": ref.get("kind"),
        "sheet": ref.get("sheet"),
        "range": ref.get("range"),
        "block_id": ref.get("block_id"),
        "region_id": ref.get("region_id"),
    }


def _evidence_refs(
    pipeline: dict[str, Any],
    linked_gate_results: list[dict[str, Any]],
    boundary_constraints: dict[str, list[str]],
) -> list[str]:
    refs = []
    for item in [
        pipeline.get("id"),
        *(pipeline.get("evidence_refs", [])),
        *(result.get("id") for result in linked_gate_results),
        *(result.get("gate_check_id") for result in linked_gate_results),
        *boundary_constraints["accepted_boundary_ids"],
        *boundary_constraints["review_required_boundary_ids"],
        *boundary_constraints["rejected_boundary_ids"],
    ]:
        if item and item not in refs:
            refs.append(item)
    return refs


def _notes(
    pipeline: dict[str, Any],
    status: str,
    reason: str,
    blockers: list[str],
    linked_gate_results: list[dict[str, Any]],
) -> str:
    role = pipeline.get("role")
    if status == "accepted":
        return f"{role} role accepted: {reason}. {_linked_summary(linked_gate_results)}"
    if status == "rejected":
        return f"{role} role rejected: {reason}; blockers={', '.join(blockers)}."
    return f"{role} role requires review: {reason}; blockers={', '.join(blockers) or 'none'}."


def _linked_summary(linked_gate_results: list[dict[str, Any]]) -> str:
    if not linked_gate_results:
        return "No linked gate result."
    counts = Counter(
        f"{result.get('gate_type')}:{result.get('status')}:{result.get('reason')}"
        for result in linked_gate_results
    )
    return "Linked gates: " + ", ".join(
        f"{key}={value}" for key, value in sorted(counts.items())
    )


def _summary(validations: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "role_validation_count": len(validations),
        "accepted_count": _count_status(validations, "accepted"),
        "rejected_count": _count_status(validations, "rejected"),
        "review_required_count": _count_status(validations, "review_required"),
        "report_role_accepted_count": _count_role_status(validations, "report", "accepted"),
        "summary_role_accepted_count": _count_role_status(validations, "summary", "accepted"),
        "transform_role_accepted_count": _count_role_status(validations, "transform", "accepted"),
        "bridge_role_accepted_count": _count_role_status(validations, "bridge", "accepted"),
        "unresolved_input_review_count": _count_reason(validations, "unresolved_input_region"),
        "external_dependency_review_count": _count_reason(
            validations,
            "external_workbook_dependency",
        ),
        "linked_gate_review_count": sum(
            1
            for validation in validations
            if any(
                result.get("status") == "review_required"
                for result in validation["linked_gate_results"]
            )
        ),
    }


def _count_status(validations: list[dict[str, Any]], status: str) -> int:
    return sum(1 for validation in validations if validation["status"] == status)


def _count_role_status(
    validations: list[dict[str, Any]],
    role: str,
    status: str,
) -> int:
    return sum(
        1
        for validation in validations
        if validation["asserted_role"] == role and validation["status"] == status
    )


def _count_reason(validations: list[dict[str, Any]], reason: str) -> int:
    return sum(1 for validation in validations if validation["reason"] == reason)


def _parser_observations(validations: list[dict[str, Any]]) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": "Pipeline role validation accepts or retains review status for role labels only; it does not assemble the final document graph.",
        }
    ]
    review_required = _count_status(validations, "review_required")
    if review_required:
        observations.append(
            {
                "level": "warning",
                "message": f"{review_required} pipeline roles still require review because an input region, external dependency, passive role, or role evidence is unresolved.",
            }
        )
    return observations


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate workbook table I/O pipeline roles against formula, pivot, gate, and boundary evidence."
    )
    parser.add_argument("table_io_pipelines", type=Path)
    parser.add_argument("gate_execution", type=Path)
    parser.add_argument("boundary_decisions", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = build_pipeline_role_validation(
        args.table_io_pipelines,
        args.gate_execution,
        args.boundary_decisions,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(package, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(package["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
