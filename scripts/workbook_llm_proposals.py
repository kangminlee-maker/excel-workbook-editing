from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"


CONCEPT_TEMPLATES = [
    {
        "key": "monthly_kgaap_revenue_summary",
        "sheet_names": ["매출"],
        "label": "월별 K-GAAP 기준 매출 집계",
        "concept_kind": "revenue_summary",
        "scope": "general_domain_aligned_workbook_candidate",
        "description": (
            "월 단위 매출을 강의매출, 교재매출, 현물, 합계 등으로 집계하는 보고 표면 후보입니다."
        ),
        "aliases": ["매출", "KGAAP기준 매출", "강의매출", "교재매출", "현물", "합계"],
        "domain_files": ["concepts.md", "logic_rules.md", "structure_spec.md"],
        "gates": ["source_trace_gate", "general_domain_gate", "formula_consistency_gate"],
    },
    {
        "key": "payment_transaction_detail",
        "sheet_names": ["결제상세"],
        "label": "결제 상세 거래 원장",
        "concept_kind": "transaction_fact_table",
        "scope": "general_domain_aligned_workbook_candidate",
        "description": (
            "PG사, 브랜드, 주문번호, 결제/취소일, 정산액, 강의/교재 금액을 포함하는 거래 단위 원천 표 후보입니다."
        ),
        "aliases": ["결제상세", "PG사", "주문번호", "결제/취소일", "정산액 입금일", "브랜드"],
        "domain_files": ["concepts.md", "dependency_rules.md", "structure_spec.md"],
        "gates": ["source_trace_gate", "table_structure_gate", "formula_consistency_gate"],
    },
    {
        "key": "payment_fee_report",
        "sheet_names": ["결제&수수료"],
        "label": "결제/환불 및 PG 수수료 집계",
        "concept_kind": "payment_fee_report",
        "scope": "general_domain_aligned_workbook_candidate",
        "description": (
            "결제, 환불, PG사별 정산, 카드 과세/면세, 수수료성 금액을 pivot과 수식 표면으로 집계하는 후보입니다."
        ),
        "aliases": ["결제/환불", "결제", "환불", "PG사", "카드과세", "카드면세"],
        "domain_files": ["concepts.md", "dependency_rules.md", "logic_rules.md"],
        "gates": ["source_trace_gate", "pivot_table_gate", "formula_consistency_gate"],
    },
    {
        "key": "revenue_recognition_60_day_schedule",
        "sheet_names": ["수익인식60일"],
        "label": "60일 수익인식 배분 스케줄",
        "concept_kind": "revenue_recognition_schedule",
        "scope": "general_domain_aligned_workbook_candidate",
        "description": (
            "결제 금액을 기간 귀속 및 발생기준 수익 인식 관점에서 해당 일수와 해당 매출로 배분하는 후보입니다."
        ),
        "aliases": ["수익인식60일", "해당 일수", "해당 매출", "환불부채", "환급부채"],
        "domain_files": ["concepts.md", "logic_rules.md", "dependency_rules.md", "competency_qs.md"],
        "gates": ["source_trace_gate", "general_domain_gate", "formula_pattern_gate"],
    },
    {
        "key": "instructor_fee_matching_schedule",
        "sheet_names": ["수익인식60일_강사료"],
        "label": "강사료 기간 대응 스케줄",
        "concept_kind": "expense_matching_schedule",
        "scope": "general_domain_aligned_workbook_candidate",
        "description": (
            "강사료를 수익 인식 기간 또는 관련 매출과 대응시키는 비용 배분 표면 후보입니다."
        ),
        "aliases": ["수익인식60일_강사료", "강사료", "비용 대응", "해당 매출"],
        "domain_files": ["concepts.md", "logic_rules.md", "competency_qs.md"],
        "gates": ["source_trace_gate", "general_domain_gate", "formula_pattern_gate"],
    },
    {
        "key": "cumulative_revenue_surface",
        "sheet_names": ["누적"],
        "label": "누적 집계 및 이월 표면",
        "concept_kind": "cumulative_rollforward_surface",
        "scope": "general_domain_aligned_workbook_candidate",
        "description": (
            "기간 간 누적값, 이월값, 반복 수식 패턴을 통해 월별 산출물을 누적 관리하는 표면 후보입니다."
        ),
        "aliases": ["누적", "이월", "누계", "누적 집계"],
        "domain_files": ["dependency_rules.md", "logic_rules.md", "concepts.md"],
        "gates": ["source_trace_gate", "formula_pattern_gate", "external_reference_gate"],
    },
    {
        "key": "current_month_formula_policy",
        "sheet_names": ["당월산식"],
        "label": "당월 산식 및 계산 규칙 표면",
        "concept_kind": "calculation_policy_surface",
        "scope": "workbook_local_candidate",
        "description": (
            "현재 월 산출 규칙과 계산 기준을 설명하거나 보조하는 workbook-local 계산 정책 표면 후보입니다."
        ),
        "aliases": ["당월산식", "산식", "계산 규칙", "당월"],
        "domain_files": ["logic_rules.md", "dependency_rules.md"],
        "gates": ["source_trace_gate", "formula_consistency_gate", "local_domain_gate"],
    },
    {
        "key": "price_list_reference",
        "sheet_names": ["정가표"],
        "label": "정가 및 가격 참조표",
        "concept_kind": "reference_table",
        "scope": "workbook_local_candidate",
        "description": "상품, 과정, 브랜드별 정가 또는 기준 가격을 참조하는 표면 후보입니다.",
        "aliases": ["정가표", "정가", "가격", "기준가"],
        "domain_files": ["structure_spec.md", "dependency_rules.md"],
        "gates": ["source_trace_gate", "table_structure_gate", "local_domain_gate"],
    },
    {
        "key": "early_bird_adjustment",
        "sheet_names": ["얼리버드"],
        "label": "얼리버드 할인 또는 가격 조정 표면",
        "concept_kind": "pricing_adjustment_surface",
        "scope": "workbook_local_candidate",
        "description": "얼리버드 조건에 따른 가격, 할인, 조정 금액을 산출하거나 참조하는 표면 후보입니다.",
        "aliases": ["얼리버드", "할인", "가격 조정"],
        "domain_files": ["concepts.md", "dependency_rules.md"],
        "gates": ["source_trace_gate", "formula_consistency_gate", "local_domain_gate"],
    },
    {
        "key": "local_brand_revenue_transform",
        "sheet_names": ["유하다요", "유하다요_강사료"],
        "label": "유하다요 boundary-scoped 매출/강사료 변환",
        "concept_kind": "local_brand_transform",
        "scope": "boundary_scoped_local_domain_candidate",
        "description": (
            "특정 boundary 안에서만 의미가 확정될 수 있는 브랜드별 매출 또는 강사료 변환 표면 후보입니다."
        ),
        "aliases": ["유하다요", "유하다요_강사료", "브랜드별 매출", "브랜드별 강사료"],
        "domain_files": ["concepts.md", "conciseness_rules.md"],
        "gates": ["source_trace_gate", "local_domain_gate", "conflict_gate"],
    },
]


def build_llm_proposals(
    *,
    document_ontology_mapping_path: Path,
    action_contracts_path: Path,
    domain_source_model_path: Path,
    readonly_sample_path: Path | None = None,
    table_io_pipelines_path: Path | None = None,
) -> dict[str, Any]:
    document_ontology_mapping_path = document_ontology_mapping_path.expanduser().resolve()
    action_contracts_path = action_contracts_path.expanduser().resolve()
    domain_source_model_path = domain_source_model_path.expanduser().resolve()
    readonly_sample_path = readonly_sample_path.expanduser().resolve() if readonly_sample_path else None
    table_io_pipelines_path = table_io_pipelines_path.expanduser().resolve() if table_io_pipelines_path else None

    mapping = _read_json(document_ontology_mapping_path)
    action_contracts = _read_json(action_contracts_path)
    domain_model = _read_json(domain_source_model_path)
    sample = _read_json(readonly_sample_path) if readonly_sample_path else {}
    table_io = _read_json(table_io_pipelines_path) if table_io_pipelines_path else {}

    domain_refs = _domain_refs_by_file(domain_model)
    local_boundaries = domain_model.get("domain_layers", {}).get("local_domain_boundaries", [])
    local_boundary_ids = [boundary["id"] for boundary in local_boundaries]
    sample_terms = _sheet_terms(sample)
    data_views_by_sheet = _data_views_by_sheet(mapping)

    semantic_concepts = _semantic_concept_proposals(
        data_views_by_sheet=data_views_by_sheet,
        sample_terms=sample_terms,
        domain_refs=domain_refs,
        local_boundary_ids=local_boundary_ids,
        semantic_readiness=domain_model.get("semantic_readiness", {}),
    )
    concept_by_sheet = _concept_ids_by_sheet(semantic_concepts)
    hierarchy_proposals = _hierarchy_proposals(
        data_views_by_sheet=data_views_by_sheet,
        concept_by_sheet=concept_by_sheet,
    )
    relation_proposals = _semantic_relation_proposals(
        table_io=table_io,
        concept_by_sheet=concept_by_sheet,
        domain_refs=domain_refs,
    )
    alias_proposals = _alias_proposals(semantic_concepts, sample_terms)
    ambiguity_notes = _ambiguity_notes(
        action_contracts=action_contracts,
        domain_model=domain_model,
        relation_proposals=relation_proposals,
    )

    proposal_package = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "document_ontology_mapping": str(document_ontology_mapping_path),
            "action_contracts": str(action_contracts_path),
            "domain_source_model": str(domain_source_model_path),
            "readonly_sample": str(readonly_sample_path) if readonly_sample_path else None,
            "table_io_pipelines": str(table_io_pipelines_path) if table_io_pipelines_path else None,
        },
        "method": {
            "name": "bounded_llm_proposal_generation",
            "authority": "proposal_only_not_claim_acceptance",
            "decision_policy": (
                "Generate evidence-bounded semantic and hierarchy proposals that remain "
                "unaccepted until deterministic gates validate source traces, domain constraints, "
                "formula/pivot support, local-boundary scope, and conflicts."
            ),
            "llm_boundary": (
                "LLM interpretation is allowed to name candidate meanings and ambiguities, "
                "but every proposal must cite workbook evidence and required gates."
            ),
        },
        "proposal_context": _proposal_context(domain_model, action_contracts),
        "semantic_concept_proposals": semantic_concepts,
        "hierarchy_proposals": hierarchy_proposals,
        "semantic_relation_proposals": relation_proposals,
        "alias_proposals": alias_proposals,
        "ambiguity_notes": ambiguity_notes,
        "validation_plan": _validation_plan(
            semantic_concepts=semantic_concepts,
            hierarchy_proposals=hierarchy_proposals,
            relation_proposals=relation_proposals,
            alias_proposals=alias_proposals,
        ),
        "summary": _summary(
            semantic_concepts=semantic_concepts,
            hierarchy_proposals=hierarchy_proposals,
            relation_proposals=relation_proposals,
            alias_proposals=alias_proposals,
            ambiguity_notes=ambiguity_notes,
        ),
        "parser_observations": _parser_observations(
            semantic_concepts=semantic_concepts,
            relation_proposals=relation_proposals,
            domain_model=domain_model,
        ),
    }
    return proposal_package


def _semantic_concept_proposals(
    *,
    data_views_by_sheet: dict[str, list[dict[str, Any]]],
    sample_terms: dict[str, list[str]],
    domain_refs: dict[str, str],
    local_boundary_ids: list[str],
    semantic_readiness: dict[str, Any],
) -> list[dict[str, Any]]:
    proposals = []
    for template in CONCEPT_TEMPLATES:
        matched_sheets = [
            sheet
            for sheet in template["sheet_names"]
            if sheet in data_views_by_sheet or sheet in sample_terms
        ]
        if not matched_sheets:
            continue
        evidence_refs = _data_view_evidence_refs(
            data_views_by_sheet,
            matched_sheets,
        )
        data_view_ids = [
            view["id"]
            for sheet in matched_sheets
            for view in data_views_by_sheet.get(sheet, [])
        ]
        domain_source_refs = [
            domain_refs[file_name]
            for file_name in template["domain_files"]
            if file_name in domain_refs
        ]
        review_flags = []
        if template["scope"] in {"workbook_local_candidate", "boundary_scoped_local_domain_candidate"}:
            review_flags.extend(["local_boundary_pending", "local_domain_source_missing"])
        if semantic_readiness.get("status") != "ready_for_semantic_proposals":
            review_flags.append(str(semantic_readiness.get("status")))
        confidence = _concept_confidence(template["scope"], data_view_ids, review_flags)
        proposals.append(
            {
                "id": _stable_id("semantic_concept", template["key"], ",".join(matched_sheets)),
                "proposal_type": "semantic_concept_candidate",
                "proposal_status": "proposed",
                "label": template["label"],
                "concept_kind": template["concept_kind"],
                "scope": template["scope"],
                "description": template["description"],
                "matched_sheets": matched_sheets,
                "matched_terms": _matched_terms(sample_terms, matched_sheets, template["aliases"]),
                "data_view_ids": data_view_ids,
                "local_boundary_ids": local_boundary_ids if "local" in template["scope"] else [],
                "domain_source_refs": domain_source_refs,
                "evidence_refs": evidence_refs,
                "required_gates": sorted(set(template["gates"] + ["source_trace_gate", "conflict_gate"])),
                "confidence": confidence,
                "review_flags": sorted(set(review_flags)),
            }
        )
    return sorted(proposals, key=lambda item: item["id"])


def _hierarchy_proposals(
    *,
    data_views_by_sheet: dict[str, list[dict[str, Any]]],
    concept_by_sheet: dict[str, str],
) -> list[dict[str, Any]]:
    proposals = []
    for sheet, views in sorted(data_views_by_sheet.items()):
        if sheet not in concept_by_sheet:
            continue
        accepted = [view for view in views if view.get("status") == "accepted"]
        review_required = [view for view in views if view.get("status") != "accepted"]
        proposals.append(
            {
                "id": _stable_id("hierarchy", sheet, concept_by_sheet[sheet]),
                "proposal_type": "hierarchy_candidate",
                "proposal_status": "proposed",
                "relation_type": "sheet_surface_contains_semantic_concept",
                "parent": {"kind": "worksheet_surface", "sheet": sheet},
                "child": {"kind": "semantic_concept", "id": concept_by_sheet[sheet]},
                "data_view_ids": [view["id"] for view in views],
                "evidence_refs": sorted(
                    {ref for view in views for ref in view.get("evidence_refs", [])}
                ),
                "required_gates": [
                    "source_trace_gate",
                    "ontology_constraint_gate",
                    "coordinate_gate",
                    "conflict_gate",
                ],
                "confidence": 0.74 if accepted and not review_required else 0.58,
                "review_flags": ["contains_review_required_data_view"] if review_required else [],
            }
        )
    return proposals


def _semantic_relation_proposals(
    *,
    table_io: dict[str, Any],
    concept_by_sheet: dict[str, str],
    domain_refs: dict[str, str],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for pipeline in table_io.get("pipelines", []):
        output_ref = pipeline.get("output_ref") or {}
        output_sheet = output_ref.get("sheet")
        if not output_sheet or output_sheet not in concept_by_sheet:
            continue
        for input_ref in pipeline.get("input_refs", []):
            input_sheet = input_ref.get("sheet")
            if not input_sheet or input_sheet == output_sheet or input_sheet not in concept_by_sheet:
                continue
            relation_kind = (
                "pivot_cache_feeds_report"
                if any(t.get("kind") == "pivot_cache" for t in pipeline.get("transform_refs", []))
                else "formula_feeds_summary_or_transform"
            )
            key = (input_sheet, output_sheet, relation_kind)
            bucket = grouped.setdefault(
                key,
                {
                    "pipeline_ids": [],
                    "evidence_refs": [],
                    "input_ranges": set(),
                    "output_ranges": set(),
                },
            )
            bucket["pipeline_ids"].append(pipeline["id"])
            bucket["evidence_refs"].extend(pipeline.get("evidence_refs", []))
            if input_ref.get("range"):
                bucket["input_ranges"].add(f"{input_sheet}!{input_ref['range']}")
            if output_ref.get("range"):
                bucket["output_ranges"].add(f"{output_sheet}!{output_ref['range']}")
    proposals = []
    for (input_sheet, output_sheet, relation_kind), bucket in sorted(grouped.items()):
        domain_files = ["dependency_rules.md", "structure_spec.md"]
        if relation_kind == "pivot_cache_feeds_report":
            domain_files.append("concepts.md")
        proposals.append(
            {
                "id": _stable_id("semantic_relation", input_sheet, output_sheet, relation_kind),
                "proposal_type": "semantic_relation_candidate",
                "proposal_status": "proposed",
                "relation_type": relation_kind,
                "from_concept_id": concept_by_sheet[input_sheet],
                "to_concept_id": concept_by_sheet[output_sheet],
                "from_sheet": input_sheet,
                "to_sheet": output_sheet,
                "pipeline_ids": sorted(bucket["pipeline_ids"]),
                "input_ranges": sorted(bucket["input_ranges"]),
                "output_ranges": sorted(bucket["output_ranges"]),
                "domain_source_refs": [
                    domain_refs[file_name]
                    for file_name in domain_files
                    if file_name in domain_refs
                ],
                "evidence_refs": sorted(set(bucket["evidence_refs"])),
                "required_gates": [
                    "source_trace_gate",
                    "table_io_pipeline_gate",
                    "formula_consistency_gate",
                    "pivot_table_gate" if relation_kind == "pivot_cache_feeds_report" else "formula_pattern_gate",
                    "conflict_gate",
                ],
                "confidence": 0.78 if len(bucket["pipeline_ids"]) > 1 else 0.66,
                "review_flags": [],
            }
        )
    return proposals


def _alias_proposals(
    semantic_concepts: list[dict[str, Any]],
    sample_terms: dict[str, list[str]],
) -> list[dict[str, Any]]:
    proposals = []
    for concept in semantic_concepts:
        aliases = set(concept.get("matched_terms", []))
        for sheet in concept.get("matched_sheets", []):
            aliases.add(sheet)
            for term in sample_terms.get(sheet, [])[:12]:
                if _useful_alias(term):
                    aliases.add(term)
        for alias in sorted(aliases):
            proposals.append(
                {
                    "id": _stable_id("alias", concept["id"], alias),
                    "proposal_type": "alias_candidate",
                    "proposal_status": "proposed",
                    "alias": alias,
                    "canonical_concept_id": concept["id"],
                    "alias_scope": concept["scope"],
                    "matched_sheets": concept["matched_sheets"],
                    "evidence_refs": concept["evidence_refs"][:10],
                    "required_gates": [
                        "source_trace_gate",
                        "general_domain_gate"
                        if "general_domain" in concept["scope"]
                        else "local_domain_gate",
                        "conflict_gate",
                    ],
                    "confidence": max(0.45, concept["confidence"] - 0.08),
                    "review_flags": concept.get("review_flags", []),
                }
            )
    return proposals


def _ambiguity_notes(
    *,
    action_contracts: dict[str, Any],
    domain_model: dict[str, Any],
    relation_proposals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    notes = []
    readiness = domain_model.get("semantic_readiness", {})
    blocking_factors = readiness.get("blocking_factors", [])
    if blocking_factors:
        notes.append(
            {
                "id": _stable_id("ambiguity", "semantic_readiness", ",".join(blocking_factors)),
                "proposal_type": "ambiguity_note",
                "severity": "high" if "local_domain_boundary_not_confirmed" in blocking_factors else "medium",
                "topic": "semantic_readiness",
                "note": (
                    "Semantic proposals can be generated, but local-domain meanings and shared ontology promotion remain blocked by readiness factors."
                ),
                "blocking_factors": blocking_factors,
                "required_resolution": "Confirm local boundary and clear blocked/high-priority structural action contracts before accepting semantic claims.",
                "evidence_refs": ["domain_source_model.semantic_readiness"],
            }
        )
    summary = action_contracts.get("summary", {})
    if summary.get("blocked_count") or summary.get("high_priority_count"):
        notes.append(
            {
                "id": _stable_id("ambiguity", "action_contracts", str(summary)),
                "proposal_type": "ambiguity_note",
                "severity": "medium",
                "topic": "structural_action_contracts",
                "note": "Open structural actions may weaken semantic interpretation for affected ranges.",
                "blocking_factors": [
                    f"blocked_action_contracts:{summary.get('blocked_count', 0)}",
                    f"high_priority_action_contracts:{summary.get('high_priority_count', 0)}",
                ],
                "required_resolution": "Resolve or explicitly quarantine high-priority structural actions before semantic acceptance.",
                "evidence_refs": ["action_contracts.summary"],
            }
        )
    if not relation_proposals:
        notes.append(
            {
                "id": _stable_id("ambiguity", "semantic_relations_missing"),
                "proposal_type": "ambiguity_note",
                "severity": "medium",
                "topic": "semantic_relations",
                "note": "No cross-sheet semantic relation proposal could be materialized from table I/O evidence.",
                "blocking_factors": ["table_io_relation_absent"],
                "required_resolution": "Inspect table I/O pipeline evidence and formula graph before accepting isolated semantic concepts.",
                "evidence_refs": ["table_io_pipelines"],
            }
        )
    return notes


def _proposal_context(
    domain_model: dict[str, Any],
    action_contracts: dict[str, Any],
) -> dict[str, Any]:
    readiness = domain_model.get("semantic_readiness", {})
    return {
        "semantic_readiness": readiness,
        "action_contract_summary": action_contracts.get("summary", {}),
        "proposal_constraints": [
            "No semantic proposal is accepted in this stage.",
            "Every semantic proposal must cite workbook evidence refs.",
            "General-domain sources constrain but do not replace workbook evidence.",
            "Local-domain proposals require a confirmed boundary before acceptance.",
            "Shared ontology promotion is blocked for this single workbook sample.",
        ],
    }


def _validation_plan(
    *,
    semantic_concepts: list[dict[str, Any]],
    hierarchy_proposals: list[dict[str, Any]],
    relation_proposals: list[dict[str, Any]],
    alias_proposals: list[dict[str, Any]],
) -> dict[str, Any]:
    gates = Counter()
    for proposal in semantic_concepts + hierarchy_proposals + relation_proposals + alias_proposals:
        gates.update(proposal.get("required_gates", []))
    return {
        "next_stage": "deterministic_validation_of_llm_proposals",
        "gate_counts": dict(sorted(gates.items())),
        "minimum_acceptance_requirements": [
            "schema_gate_passed",
            "all_proposals_have_evidence_refs",
            "domain_source_refs_exist_for_general_domain_claims",
            "local_boundary_confirmed_or_local_claim_quarantined",
            "formula_or_pivot_relation_supported_for_cross_sheet_semantic_relations",
            "conflict_gate_passed",
        ],
    }


def _summary(
    *,
    semantic_concepts: list[dict[str, Any]],
    hierarchy_proposals: list[dict[str, Any]],
    relation_proposals: list[dict[str, Any]],
    alias_proposals: list[dict[str, Any]],
    ambiguity_notes: list[dict[str, Any]],
) -> dict[str, Any]:
    local_count = sum(
        1
        for proposal in semantic_concepts
        if "local" in proposal.get("scope", "")
    )
    return {
        "semantic_concept_proposal_count": len(semantic_concepts),
        "hierarchy_proposal_count": len(hierarchy_proposals),
        "semantic_relation_proposal_count": len(relation_proposals),
        "alias_proposal_count": len(alias_proposals),
        "ambiguity_note_count": len(ambiguity_notes),
        "local_domain_sensitive_proposal_count": local_count,
        "proposal_status": "proposal_only_pending_deterministic_validation",
    }


def _parser_observations(
    *,
    semantic_concepts: list[dict[str, Any]],
    relation_proposals: list[dict[str, Any]],
    domain_model: dict[str, Any],
) -> list[dict[str, str]]:
    observations = []
    if semantic_concepts:
        observations.append(
            {
                "level": "info",
                "message": f"Generated {len(semantic_concepts)} semantic concept proposals from evidence-backed sheet/data-view surfaces.",
            }
        )
    if relation_proposals:
        observations.append(
            {
                "level": "info",
                "message": f"Generated {len(relation_proposals)} cross-sheet semantic relation proposals from table I/O pipelines.",
            }
        )
    readiness = domain_model.get("semantic_readiness", {})
    if readiness.get("status") != "ready_for_semantic_proposals":
        observations.append(
            {
                "level": "warning",
                "message": f"Semantic readiness is {readiness.get('status')}; proposals must remain unaccepted until deterministic gates run.",
            }
        )
    return observations


def _data_views_by_sheet(mapping: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for view in mapping.get("data_views", []):
        sheet = view.get("sheet")
        if sheet:
            grouped[sheet].append(view)
    return dict(grouped)


def _domain_refs_by_file(domain_model: dict[str, Any]) -> dict[str, str]:
    refs = {}
    for source in domain_model.get("domain_layers", {}).get("general_domain_sources", []):
        if source.get("file_name") and source.get("id"):
            refs[source["file_name"]] = source["id"]
    return refs


def _sheet_terms(sample: dict[str, Any]) -> dict[str, list[str]]:
    terms: dict[str, list[str]] = {}
    for sheet in sample.get("sheets", []):
        sheet_terms = []
        for window in sheet.get("windows", []):
            for row in window.get("rows", []):
                for cell in row.get("cells", []):
                    value = str(cell.get("value_preview") or "").strip()
                    if cell.get("value_type") in {"string", "formula"} and value:
                        if not value.startswith("="):
                            sheet_terms.append(value)
        terms[sheet["name"]] = _unique_preserving_order(sheet_terms)[:80]
    return terms


def _matched_terms(
    sample_terms: dict[str, list[str]],
    sheets: list[str],
    aliases: list[str],
) -> list[str]:
    matched = []
    alias_text = " ".join(aliases)
    for sheet in sheets:
        for term in sample_terms.get(sheet, []):
            if term in aliases or term in alias_text or any(alias in term for alias in aliases):
                matched.append(term)
    return _unique_preserving_order(matched + aliases)


def _data_view_evidence_refs(
    data_views_by_sheet: dict[str, list[dict[str, Any]]],
    sheets: list[str],
) -> list[str]:
    refs = []
    for sheet in sheets:
        for view in data_views_by_sheet.get(sheet, []):
            refs.append(view["id"])
            refs.extend(view.get("evidence_refs", [])[:10])
    return sorted(set(refs))


def _concept_ids_by_sheet(
    semantic_concepts: list[dict[str, Any]],
) -> dict[str, str]:
    out = {}
    for concept in semantic_concepts:
        for sheet in concept.get("matched_sheets", []):
            out[sheet] = concept["id"]
    return out


def _concept_confidence(
    scope: str,
    data_view_ids: list[str],
    review_flags: list[str],
) -> float:
    confidence = 0.68
    if data_view_ids:
        confidence += 0.08
    if "general_domain" in scope:
        confidence += 0.04
    if review_flags:
        confidence -= 0.14
    if "boundary_scoped" in scope:
        confidence -= 0.06
    return round(min(0.86, max(0.42, confidence)), 2)


def _useful_alias(term: str) -> bool:
    if not term or len(term) > 40:
        return False
    if re.fullmatch(r"[-+]?\d+(\.\d+)?", term):
        return False
    if term.startswith("Sum of "):
        return True
    return any(ch.isalpha() for ch in term) or any("\uac00" <= ch <= "\ud7a3" for ch in term)


def _unique_preserving_order(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out


def _stable_id(prefix: str, *parts: str) -> str:
    raw = "|".join(str(part) for part in parts)
    slug = re.sub(r"[^0-9A-Za-z가-힣_]+", "_", raw).strip("_")[:72]
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}:{slug}:{digest}"


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate evidence-bounded LLM proposal candidates for workbook ontology."
    )
    parser.add_argument("--document-ontology-mapping", type=Path, required=True)
    parser.add_argument("--action-contracts", type=Path, required=True)
    parser.add_argument("--domain-source-model", type=Path, required=True)
    parser.add_argument("--readonly-sample", type=Path)
    parser.add_argument("--table-io-pipelines", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    proposals = build_llm_proposals(
        document_ontology_mapping_path=args.document_ontology_mapping,
        action_contracts_path=args.action_contracts,
        domain_source_model_path=args.domain_source_model,
        readonly_sample_path=args.readonly_sample,
        table_io_pipelines_path=args.table_io_pipelines,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(proposals, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
