from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"

BASIS_TERMS = [
    "KGAAP",
    "K-GAAP",
    "KIFRS",
    "K-IFRS",
    "IFRS",
    "수익인식",
    "계약부채",
    "선수수익",
    "환불부채",
    "환급부채",
    "해당 매출",
    "이연",
    "현물이연",
    "미공개",
]


def build_shared_ontology_alignment_review(
    *,
    local_semantic_candidates_path: Path,
    domain_source_model_path: Path,
    data_view_projection_path: Path,
) -> dict[str, Any]:
    local_semantic_candidates_path = local_semantic_candidates_path.expanduser().resolve()
    domain_source_model_path = domain_source_model_path.expanduser().resolve()
    data_view_projection_path = data_view_projection_path.expanduser().resolve()

    candidate_package = _read_json(local_semantic_candidates_path)
    domain_model = _read_json(domain_source_model_path)
    data_view_projection = _read_json(data_view_projection_path)

    context = _alignment_context(
        candidate_package=candidate_package,
        domain_model=domain_model,
        data_view_projection=data_view_projection,
    )
    items = [
        _alignment_item(candidate, context=context)
        for candidate in candidate_package.get("local_semantic_candidates", [])
    ]
    review_questions = _review_questions(context=context, items=items)
    shared_ontology_updates: list[dict[str, Any]] = []

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "local_semantic_candidates": str(local_semantic_candidates_path),
            "domain_source_model": str(domain_source_model_path),
            "data_view_projection": str(data_view_projection_path),
        },
        "method": {
            "name": "deterministic_shared_ontology_alignment_review",
            "authority": "review_only_no_shared_promotion",
            "decision_policy": (
                "Evaluate boundary-scoped local semantic candidates against shared ontology "
                "promotion prerequisites. In this sample, do not emit shared ontology updates "
                "unless local boundary, local source evidence, repeated workbook-family evidence, "
                "conflict checks, formula-result authority, and human approval are all satisfied."
            ),
        },
        "alignment_context": context,
        "alignment_items": items,
        "shared_ontology_updates": shared_ontology_updates,
        "review_questions": review_questions,
        "summary": _summary(items, review_questions, shared_ontology_updates),
        "parser_observations": _parser_observations(items, context),
    }


def _alignment_context(
    *,
    candidate_package: dict[str, Any],
    domain_model: dict[str, Any],
    data_view_projection: dict[str, Any],
) -> dict[str, Any]:
    readiness = domain_model.get("semantic_readiness", {})
    layers = domain_model.get("domain_layers", {})
    local_boundary = candidate_package.get("local_boundary") or {}
    local_boundary_confirmed = bool(readiness.get("local_boundary_confirmed"))
    local_domain_source_count = int(readiness.get("local_domain_source_count", 0) or 0)
    projection_summary = data_view_projection.get("summary", {})
    preconditions = [
        _precondition(
            "local_boundary_confirmed",
            local_boundary_confirmed,
            "A declared organization/project/team/tenant/workbook-family boundary is confirmed.",
            "Confirm the local boundary that makes local terminology valid.",
        ),
        _precondition(
            "local_domain_sources_available",
            local_domain_source_count > 0,
            "Local policy, vocabulary, or owner-approved source evidence is available.",
            "Provide local policy/vocabulary evidence before treating local terms as reusable.",
        ),
        _precondition(
            "repeated_workbook_family_evidence_available",
            False,
            "The same candidate meaning appears across workbook pairs or workbook families.",
            "Collect repeated evidence from source/output workbook pairs or adjacent periods.",
        ),
        _precondition(
            "shared_ontology_target_available",
            False,
            "An existing shared ontology target is available for duplicate/conflict checks.",
            "Provide a shared ontology target or mark this review as candidate-only.",
        ),
        _precondition(
            "human_approval_recorded",
            False,
            "A domain owner has approved the promotion scope and label.",
            "Record human approval after reviewing blockers and conflicts.",
        ),
    ]
    return {
        "local_boundary_id": local_boundary.get("id"),
        "local_boundary_status": local_boundary.get("status"),
        "local_boundary_scope": local_boundary.get("scope"),
        "local_boundary_confirmed": local_boundary_confirmed,
        "local_domain_source_count": local_domain_source_count,
        "general_domain_source_count": len(layers.get("general_domain_sources", [])),
        "data_view_projection_count": projection_summary.get("data_view_projection_count", 0),
        "shared_ontology_target_status": "not_provided",
        "alignment_authority": "human_review_packet_only",
        "shared_promotion_preconditions": preconditions,
    }


def _alignment_item(candidate: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    has_basis_risk = _has_basis_risk(candidate)
    blockers = _blockers(candidate, context=context, has_basis_risk=has_basis_risk)
    conflict_risks = _conflict_risks(candidate, context=context, has_basis_risk=has_basis_risk)
    required_evidence = _required_evidence(
        candidate, context=context, has_basis_risk=has_basis_risk
    )
    questions = _candidate_questions(candidate, has_basis_risk=has_basis_risk)
    return {
        "id": f"alignment_item:{_stable_hash(candidate.get('id', ''))}",
        "type": "shared_ontology_alignment_item",
        "candidate_id": candidate.get("id"),
        "label": candidate.get("label"),
        "candidate_kind": candidate.get("candidate_kind"),
        "source_kind": candidate.get("source_kind"),
        "alignment_status": _alignment_status(
            candidate, has_basis_risk=has_basis_risk
        ),
        "promotion_decision": "not_promoted",
        "proposed_shared_concept_id": None,
        "existing_shared_concept_refs": [],
        "blockers": blockers,
        "conflict_risks": conflict_risks,
        "required_evidence": required_evidence,
        "human_review_questions": questions,
        "basis_review": {
            "required": has_basis_risk,
            "detected_terms": _detected_basis_terms(candidate),
            "reason": (
                "K-GAAP-labeled output and K-IFRS-relevant revenue recognition surfaces "
                "must be separated before shared promotion."
                if has_basis_risk
                else None
            ),
        },
        "data_view_refs": candidate.get("data_view_refs", {}),
        "observed_terms": candidate.get("observed_terms", []),
        "evidence_refs": candidate.get("evidence_refs", []),
        "source_artifact_refs": _unique(
            candidate.get("source_artifact_refs", [])
            + [
                "local_semantic_candidates",
                "domain_source_model",
                "data_view_projection",
            ]
        ),
    }


def _blockers(
    candidate: dict[str, Any],
    *,
    context: dict[str, Any],
    has_basis_risk: bool,
) -> list[str]:
    blockers = []
    if not context.get("local_boundary_confirmed"):
        blockers.append("local_domain_boundary_not_confirmed")
    if not context.get("local_domain_source_count", 0):
        blockers.append("no_local_domain_sources_available")
    if candidate.get("source_kind") == "unmapped_data_view_surface":
        blockers.append("semantic_label_pending")
    if _requires_formula_result_validation(candidate):
        blockers.append("formula_result_validation_pending")
    if has_basis_risk:
        blockers.append("gaap_ifrs_basis_mapping_required")
    blockers.extend(
        [
            "repeated_workbook_family_evidence_missing",
            "shared_ontology_target_not_provided",
            "human_approval_required",
        ]
    )
    return _unique(blockers)


def _conflict_risks(
    candidate: dict[str, Any],
    *,
    context: dict[str, Any],
    has_basis_risk: bool,
) -> list[str]:
    risks = []
    if has_basis_risk:
        risks.append("dual_basis_revenue_interpretation_risk")
    if not context.get("local_domain_source_count", 0):
        risks.append("local_vocabulary_absent_risk")
    if candidate.get("source_kind") == "unmapped_data_view_surface":
        risks.append("unmapped_semantic_surface_risk")
    if _requires_formula_result_validation(candidate):
        risks.append("formula_result_not_recalculated_risk")
    if not candidate.get("general_domain_alignment", {}).get(
        "accepted_semantic_concept_ids", []
    ):
        risks.append("no_existing_general_domain_alignment_risk")
    return _unique(risks)


def _required_evidence(
    candidate: dict[str, Any],
    *,
    context: dict[str, Any],
    has_basis_risk: bool,
) -> list[str]:
    evidence = [
        "confirmed_organization_or_project_boundary",
        "local_policy_or_vocabulary_source",
        "workbook_family_or_pair_repetition_evidence",
        "shared_ontology_duplicate_and_conflict_check",
        "human_approval_record",
    ]
    if candidate.get("source_kind") == "unmapped_data_view_surface":
        evidence.append("human_confirmed_semantic_label")
    if has_basis_risk:
        evidence.append("k_gaap_vs_k_ifrs_output_definition")
        evidence.append("official_ifrs_revenue_aggregation_definition")
    if _requires_formula_result_validation(candidate):
        evidence.append("excel_engine_recalculation_sample")
    return _unique(evidence)


def _candidate_questions(
    candidate: dict[str, Any],
    *,
    has_basis_risk: bool,
) -> list[str]:
    questions = [
        "이 후보의 의미가 현재 워크북에만 유효한가, 아니면 반복되는 워크북 family에서도 동일하게 쓰이는가?",
        "이 후보명을 승인할 local policy, glossary, 또는 업무 담당자 근거가 있는가?",
    ]
    if candidate.get("source_kind") == "unmapped_data_view_surface":
        questions.append("이 표면의 업무 의미와 canonical label은 무엇인가?")
    if has_basis_risk:
        questions.append(
            "이 표면은 K-GAAP 기준 월 매출 출력인가, K-IFRS 수익인식 계산 보조 표면인가, 또는 둘의 bridge인가?"
        )
    if _requires_formula_result_validation(candidate):
        questions.append("공유 후보 판단 전에 Excel 엔진으로 대표 formula 결과를 재계산했는가?")
    return _unique(questions)


def _review_questions(
    *,
    context: dict[str, Any],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    basis_count = sum(1 for item in items if item.get("basis_review", {}).get("required"))
    formula_pending_count = sum(
        1 for item in items if "formula_result_validation_pending" in item.get("blockers", [])
    )
    semantic_label_pending_count = sum(
        1 for item in items if "semantic_label_pending" in item.get("blockers", [])
    )
    return [
        {
            "id": "review_question:local_boundary",
            "priority": "high",
            "topic": "local_domain_boundary",
            "question": "이 워크북의 local domain boundary는 어느 organization/project/team/tenant/workbook-family까지인가?",
            "blocks": ["shared_ontology_promotion"],
            "required_evidence": ["confirmed_organization_or_project_boundary"],
        },
        {
            "id": "review_question:local_sources",
            "priority": "high",
            "topic": "local_domain_sources",
            "question": "local terminology와 처리 규칙을 승인할 policy, glossary, 또는 담당자 확인 자료가 있는가?",
            "blocks": ["local_semantic_truth_acceptance", "shared_ontology_promotion"],
            "required_evidence": ["local_policy_or_vocabulary_source"],
        },
        {
            "id": "review_question:semantic_labels",
            "priority": "high" if semantic_label_pending_count else "medium",
            "topic": "semantic_label_assignment",
            "question": f"accepted data view 중 의미 label이 없는 {semantic_label_pending_count}개 표면의 canonical label은 무엇인가?",
            "blocks": ["candidate_alignment", "shared_ontology_promotion"],
            "required_evidence": ["human_confirmed_semantic_label"],
        },
        {
            "id": "review_question:gaap_ifrs_basis",
            "priority": "high" if basis_count else "medium",
            "topic": "gaap_ifrs_basis_separation",
            "question": f"K-GAAP 출력명과 K-IFRS 수익인식 관련 표면이 섞일 수 있는 {basis_count}개 후보를 어떻게 분리하거나 연결할 것인가?",
            "blocks": ["revenue_concept_promotion", "official_ifrs_output_claim"],
            "required_evidence": [
                "k_gaap_vs_k_ifrs_output_definition",
                "official_ifrs_revenue_aggregation_definition",
            ],
        },
        {
            "id": "review_question:formula_authority",
            "priority": "high" if formula_pending_count else "medium",
            "topic": "formula_result_authority",
            "question": f"formula text만 확인된 {formula_pending_count}개 후보에 대해 Excel 엔진 재계산 샘플을 어디까지 수행할 것인가?",
            "blocks": ["numeric_revenue_claim", "formula_based_shared_promotion"],
            "required_evidence": ["excel_engine_recalculation_sample"],
        },
        {
            "id": "review_question:workbook_family_repetition",
            "priority": "medium",
            "topic": "shared_promotion_evidence",
            "question": "같은 의미가 다른 월, 원본/output workbook pair, 또는 동일 workbook family에서 반복되는가?",
            "blocks": ["shared_ontology_promotion"],
            "required_evidence": ["workbook_family_or_pair_repetition_evidence"],
        },
    ]


def _summary(
    items: list[dict[str, Any]],
    review_questions: list[dict[str, Any]],
    shared_ontology_updates: list[dict[str, Any]],
) -> dict[str, Any]:
    status_counts = Counter(item.get("alignment_status") for item in items)
    blocker_counts = Counter(
        blocker for item in items for blocker in item.get("blockers", [])
    )
    conflict_counts = Counter(
        risk for item in items for risk in item.get("conflict_risks", [])
    )
    return {
        "alignment_item_count": len(items),
        "promoted_count": sum(
            1 for item in items if item.get("promotion_decision") == "promoted"
        ),
        "blocked_alignment_count": sum(
            1 for item in items if item.get("promotion_decision") != "promoted"
        ),
        "local_boundary_blocked_count": blocker_counts.get(
            "local_domain_boundary_not_confirmed", 0
        ),
        "local_source_blocked_count": blocker_counts.get(
            "no_local_domain_sources_available", 0
        ),
        "semantic_label_pending_count": blocker_counts.get(
            "semantic_label_pending", 0
        ),
        "basis_review_required_count": blocker_counts.get(
            "gaap_ifrs_basis_mapping_required", 0
        ),
        "formula_result_validation_required_count": blocker_counts.get(
            "formula_result_validation_pending", 0
        ),
        "review_question_count": len(review_questions),
        "shared_ontology_update_count": len(shared_ontology_updates),
        "alignment_status_counts": dict(status_counts),
        "blocker_counts": dict(blocker_counts),
        "conflict_risk_counts": dict(conflict_counts),
        "alignment_status": "review_only_no_shared_promotion",
    }


def _parser_observations(
    items: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": f"Prepared {len(items)} shared ontology alignment review items.",
        }
    ]
    if not context.get("local_boundary_confirmed"):
        observations.append(
            {
                "level": "warning",
                "message": "No candidate is promotable because the local domain boundary is not confirmed.",
            }
        )
    if not context.get("local_domain_source_count", 0):
        observations.append(
            {
                "level": "warning",
                "message": "No candidate is promotable because no local policy or vocabulary source is available.",
            }
        )
    basis_count = sum(1 for item in items if item.get("basis_review", {}).get("required"))
    if basis_count:
        observations.append(
            {
                "level": "warning",
                "message": (
                    f"{basis_count} candidates require K-GAAP versus K-IFRS basis separation "
                    "before revenue-related promotion."
                ),
            }
        )
    return observations


def _alignment_status(candidate: dict[str, Any], *, has_basis_risk: bool) -> str:
    if candidate.get("source_kind") == "unmapped_data_view_surface":
        return "blocked_semantic_label_pending"
    if has_basis_risk:
        return "blocked_basis_definition_pending"
    return "blocked_local_boundary_pending"


def _precondition(
    name: str,
    satisfied: bool,
    description: str,
    missing_action: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": "satisfied" if satisfied else "blocked",
        "description": description,
        "missing_action": None if satisfied else missing_action,
    }


def _has_basis_risk(candidate: dict[str, Any]) -> bool:
    return bool(_detected_basis_terms(candidate))


def _detected_basis_terms(candidate: dict[str, Any]) -> list[str]:
    text_parts = [
        str(candidate.get("label") or ""),
        str(candidate.get("candidate_kind") or ""),
    ]
    text_parts.extend(str(term) for term in candidate.get("observed_terms", []))
    joined = "\n".join(text_parts).lower()
    return [
        term
        for term in BASIS_TERMS
        if term.lower() in joined
    ]


def _requires_formula_result_validation(candidate: dict[str, Any]) -> bool:
    refs = candidate.get("data_view_refs", {})
    if refs.get("formula_cell_count", 0):
        return True
    return "validate_formula_results_with_excel_engine_before_numeric_claims" in candidate.get(
        "required_actions", []
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _unique(values: list[Any]) -> list[Any]:
    seen = set()
    out = []
    for value in values:
        marker = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if marker in seen:
            continue
        seen.add(marker)
        out.append(value)
    return out


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build shared ontology alignment review artifact."
    )
    parser.add_argument("--local-semantic-candidates", type=Path, required=True)
    parser.add_argument("--domain-source-model", type=Path, required=True)
    parser.add_argument("--data-view-projection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    package = build_shared_ontology_alignment_review(
        local_semantic_candidates_path=args.local_semantic_candidates,
        domain_source_model_path=args.domain_source_model,
        data_view_projection_path=args.data_view_projection,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
