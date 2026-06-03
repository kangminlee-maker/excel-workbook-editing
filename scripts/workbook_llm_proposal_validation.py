from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"

OUTCOME_ORDER = {
    "accepted": 0,
    "warning": 1,
    "requires_human_review": 2,
    "quarantined": 3,
    "rejected": 4,
}

ALLOWED_PROPOSAL_TYPES = {
    "semantic_concept_candidate",
    "hierarchy_candidate",
    "semantic_relation_candidate",
    "alias_candidate",
    "ambiguity_note",
}

ALLOWED_HIERARCHY_RELATIONS = {"sheet_surface_contains_semantic_concept"}
ALLOWED_SEMANTIC_RELATIONS = {
    "formula_feeds_summary_or_transform",
    "pivot_cache_feeds_report",
}


def build_llm_proposal_validation(
    *,
    llm_proposals_path: Path,
    document_ontology_mapping_path: Path,
    table_io_pipelines_path: Path,
    domain_source_model_path: Path,
) -> dict[str, Any]:
    llm_proposals_path = llm_proposals_path.expanduser().resolve()
    document_ontology_mapping_path = document_ontology_mapping_path.expanduser().resolve()
    table_io_pipelines_path = table_io_pipelines_path.expanduser().resolve()
    domain_source_model_path = domain_source_model_path.expanduser().resolve()

    proposals = _read_json(llm_proposals_path)
    mapping = _read_json(document_ontology_mapping_path)
    table_io = _read_json(table_io_pipelines_path)
    domain_model = _read_json(domain_source_model_path)

    indexes = _build_indexes(mapping, table_io, domain_model)
    concept_lookup = {
        proposal["id"]: proposal
        for proposal in proposals.get("semantic_concept_proposals", [])
    }
    alias_targets = _alias_targets(proposals.get("alias_proposals", []))

    results = []
    for proposal in proposals.get("semantic_concept_proposals", []):
        results.append(_validate_semantic_concept(proposal, indexes))
    concept_outcomes = {result["proposal_id"]: result["final_status"] for result in results}

    for proposal in proposals.get("hierarchy_proposals", []):
        results.append(_validate_hierarchy(proposal, indexes, concept_outcomes))
    for proposal in proposals.get("semantic_relation_proposals", []):
        results.append(
            _validate_semantic_relation(
                proposal,
                indexes,
                concept_lookup,
                concept_outcomes,
            )
        )
    for proposal in proposals.get("alias_proposals", []):
        results.append(
            _validate_alias(
                proposal,
                indexes,
                concept_lookup,
                concept_outcomes,
                alias_targets,
            )
        )
    for note in proposals.get("ambiguity_notes", []):
        results.append(_validate_ambiguity_note(note, indexes))

    review_queue = _review_queue(results)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "llm_proposals": str(llm_proposals_path),
            "document_ontology_mapping": str(document_ontology_mapping_path),
            "table_io_pipelines": str(table_io_pipelines_path),
            "domain_source_model": str(domain_source_model_path),
        },
        "method": {
            "name": "deterministic_llm_proposal_validation",
            "authority": "proposal_gate_outcome_not_final_graph_assembly",
            "decision_policy": (
                "Validate LLM proposal claims using source traces, domain refs, local boundary "
                "status, data-view coordinates, table I/O pipeline evidence, formula/pivot topology, "
                "confidence thresholds, and alias conflicts. This stage does not recalculate Excel "
                "formula results and does not assemble the final document graph."
            ),
        },
        "validation_context": {
            "proposal_summary": proposals.get("summary", {}),
            "semantic_readiness": (
                proposals.get("proposal_context", {}).get("semantic_readiness", {})
            ),
            "known_evidence_ref_count": len(indexes["evidence_refs"]),
            "known_data_view_count": len(indexes["data_views"]),
            "known_pipeline_count": len(indexes["pipelines"]),
            "local_boundary_statuses": indexes["local_boundary_statuses"],
        },
        "proposal_results": sorted(results, key=lambda item: item["proposal_id"]),
        "review_queue": review_queue,
        "summary": _summary(results),
        "gate_summary": _gate_summary(results),
        "parser_observations": _parser_observations(results, review_queue),
    }


def _validate_semantic_concept(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    gates = [
        _schema_gate(proposal),
        _source_trace_gate(proposal, indexes),
        _domain_gate(proposal, indexes),
        _local_domain_gate(proposal, indexes),
        _data_view_gate(proposal, indexes),
        _formula_or_pivot_gate(proposal, indexes),
        _external_reference_gate(proposal, indexes),
        _confidence_gate(proposal, threshold=0.6),
        _conflict_gate(proposal),
    ]
    return _result(proposal, gates)


def _validate_hierarchy(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
    concept_outcomes: dict[str, str],
) -> dict[str, Any]:
    child_id = (proposal.get("child") or {}).get("id")
    gates = [
        _schema_gate(proposal),
        _source_trace_gate(proposal, indexes),
        _ontology_constraint_gate(
            proposal,
            allowed_relations=ALLOWED_HIERARCHY_RELATIONS,
        ),
        _coordinate_gate(proposal, indexes),
        _dependency_outcome_gate(child_id, concept_outcomes, "child_concept"),
        _confidence_gate(proposal, threshold=0.6),
        _conflict_gate(proposal),
    ]
    return _result(proposal, gates)


def _validate_semantic_relation(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
    concept_lookup: dict[str, dict[str, Any]],
    concept_outcomes: dict[str, str],
) -> dict[str, Any]:
    from_id = proposal.get("from_concept_id")
    to_id = proposal.get("to_concept_id")
    gates = [
        _schema_gate(proposal),
        _source_trace_gate(proposal, indexes),
        _ontology_constraint_gate(
            proposal,
            allowed_relations=ALLOWED_SEMANTIC_RELATIONS,
        ),
        _table_io_pipeline_gate(proposal, indexes),
        _formula_or_pivot_gate(proposal, indexes),
        _domain_gate(proposal, indexes),
        _relation_local_scope_gate(proposal, concept_lookup, indexes),
        _dependency_outcome_gate(from_id, concept_outcomes, "from_concept"),
        _dependency_outcome_gate(to_id, concept_outcomes, "to_concept"),
        _confidence_gate(proposal, threshold=0.6),
        _conflict_gate(proposal),
    ]
    return _result(proposal, gates)


def _validate_alias(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
    concept_lookup: dict[str, dict[str, Any]],
    concept_outcomes: dict[str, str],
    alias_targets: dict[str, set[str]],
) -> dict[str, Any]:
    canonical_id = proposal.get("canonical_concept_id")
    gates = [
        _schema_gate(proposal),
        _source_trace_gate(proposal, indexes),
        _alias_domain_gate(proposal, concept_lookup, indexes),
        _alias_local_scope_gate(proposal, concept_lookup, indexes),
        _dependency_outcome_gate(canonical_id, concept_outcomes, "canonical_concept"),
        _alias_conflict_gate(proposal, alias_targets),
        _confidence_gate(proposal, threshold=0.5),
    ]
    return _result(proposal, gates)


def _validate_ambiguity_note(
    note: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    gates = [
        _schema_gate(note),
        _source_trace_gate(note, indexes),
        _gate(
            "ambiguity_resolution_gate",
            "requires_human_review",
            "Ambiguity notes intentionally remain review items until the stated resolution is completed.",
            note.get("evidence_refs", []),
        ),
    ]
    return _result(note, gates)


def _schema_gate(proposal: dict[str, Any]) -> dict[str, Any]:
    proposal_type = proposal.get("proposal_type")
    if proposal_type not in ALLOWED_PROPOSAL_TYPES:
        return _gate(
            "schema_gate",
            "rejected",
            f"Unsupported proposal_type: {proposal_type}",
            [],
        )
    if not proposal.get("id"):
        return _gate("schema_gate", "rejected", "Proposal id is missing.", [])
    return _gate("schema_gate", "accepted", "Proposal has a supported shape.", [])


def _source_trace_gate(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    refs = [str(ref) for ref in proposal.get("evidence_refs", []) if ref]
    if not refs:
        return _gate("source_trace_gate", "rejected", "Proposal has no evidence refs.", [])
    unknown = [ref for ref in refs if ref not in indexes["evidence_refs"]]
    if unknown:
        return _gate(
            "source_trace_gate",
            "requires_human_review",
            f"{len(unknown)} evidence refs are not in the deterministic evidence index.",
            unknown[:12],
        )
    return _gate(
        "source_trace_gate",
        "accepted",
        f"{len(refs)} evidence refs resolved in the deterministic evidence index.",
        refs[:12],
    )


def _domain_gate(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    refs = [str(ref) for ref in proposal.get("domain_source_refs", []) if ref]
    needs_general = (
        "general_domain_gate" in proposal.get("required_gates", [])
        or "general_domain" in str(proposal.get("scope") or proposal.get("alias_scope") or "")
    )
    if not needs_general:
        return _gate("general_domain_gate", "accepted", "No general-domain claim required.", [])
    if not refs:
        return _gate(
            "general_domain_gate",
            "rejected",
            "General-domain claim has no domain source refs.",
            [],
        )
    missing = [ref for ref in refs if ref not in indexes["general_domain_refs"]]
    if missing:
        return _gate(
            "general_domain_gate",
            "rejected",
            "Domain source refs are missing from the domain source model.",
            missing,
        )
    return _gate(
        "general_domain_gate",
        "accepted",
        f"{len(refs)} general-domain refs resolved.",
        refs,
    )


def _local_domain_gate(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    if "local_domain_gate" not in proposal.get("required_gates", []):
        return _gate("local_domain_gate", "accepted", "No local-domain gate required.", [])
    boundary_ids = proposal.get("local_boundary_ids", [])
    if not boundary_ids:
        return _gate(
            "local_domain_gate",
            "requires_human_review",
            "Local-domain gate is required but no local boundary id is attached.",
            [],
        )
    unconfirmed = [
        boundary_id
        for boundary_id in boundary_ids
        if indexes["local_boundary_statuses"].get(boundary_id) != "available"
    ]
    if unconfirmed:
        return _gate(
            "local_domain_gate",
            "quarantined",
            "Local boundary is not confirmed; local-domain claim cannot be accepted.",
            unconfirmed,
        )
    return _gate("local_domain_gate", "accepted", "Local boundary is confirmed.", boundary_ids)


def _data_view_gate(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    data_view_ids = proposal.get("data_view_ids", [])
    if not data_view_ids:
        return _gate(
            "data_view_evidence_gate",
            "requires_human_review",
            "Semantic concept has no data view refs.",
            [],
        )
    missing = [data_view_id for data_view_id in data_view_ids if data_view_id not in indexes["data_views"]]
    if missing:
        return _gate(
            "data_view_evidence_gate",
            "rejected",
            "Data view refs are missing from document ontology mapping.",
            missing,
        )
    review_required = [
        data_view_id
        for data_view_id in data_view_ids
        if indexes["data_views"][data_view_id].get("status") != "accepted"
    ]
    if review_required:
        return _gate(
            "data_view_evidence_gate",
            "requires_human_review",
            "At least one data view is not accepted.",
            review_required,
        )
    return _gate(
        "data_view_evidence_gate",
        "accepted",
        f"{len(data_view_ids)} accepted data views support the proposal.",
        data_view_ids[:12],
    )


def _coordinate_gate(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    data_view_ids = proposal.get("data_view_ids", [])
    missing_coordinates = []
    for data_view_id in data_view_ids:
        view = indexes["data_views"].get(data_view_id)
        if not view or not view.get("sheet") or not view.get("range"):
            missing_coordinates.append(data_view_id)
    if missing_coordinates:
        return _gate(
            "coordinate_gate",
            "requires_human_review",
            "Some data views lack sheet/range coordinates.",
            missing_coordinates,
        )
    return _gate(
        "coordinate_gate",
        "accepted",
        f"{len(data_view_ids)} data view coordinate refs resolved.",
        data_view_ids[:12],
    )


def _ontology_constraint_gate(
    proposal: dict[str, Any],
    *,
    allowed_relations: set[str],
) -> dict[str, Any]:
    relation_type = proposal.get("relation_type")
    if relation_type not in allowed_relations:
        return _gate(
            "ontology_constraint_gate",
            "rejected",
            f"Relation type is not allowed: {relation_type}",
            [],
        )
    return _gate(
        "ontology_constraint_gate",
        "accepted",
        "Relation type is allowed by the proposal ontology.",
        [],
    )


def _table_io_pipeline_gate(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    pipeline_ids = proposal.get("pipeline_ids", [])
    if not pipeline_ids:
        return _gate(
            "table_io_pipeline_gate",
            "rejected",
            "Relation proposal has no pipeline refs.",
            [],
        )
    missing = [pipeline_id for pipeline_id in pipeline_ids if pipeline_id not in indexes["pipelines"]]
    if missing:
        return _gate(
            "table_io_pipeline_gate",
            "rejected",
            "Pipeline refs are missing from table I/O pipelines.",
            missing,
        )
    return _gate(
        "table_io_pipeline_gate",
        "accepted",
        f"{len(pipeline_ids)} pipeline refs resolved.",
        pipeline_ids[:12],
    )


def _formula_or_pivot_gate(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    required = set(proposal.get("required_gates", []))
    if "pivot_table_gate" in required:
        return _pivot_gate(proposal, indexes)
    if "formula_consistency_gate" in required or "formula_pattern_gate" in required:
        return _formula_gate(proposal, indexes)
    if "external_reference_gate" in required:
        return _external_reference_gate(proposal, indexes)
    return _gate("formula_or_pivot_gate", "accepted", "No formula/pivot gate required.", [])


def _pivot_gate(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    pipeline_ids = proposal.get("pipeline_ids", [])
    if pipeline_ids:
        invalid = [
            pipeline_id
            for pipeline_id in pipeline_ids
            if not _pipeline_has_transform_kind(indexes["pipelines"].get(pipeline_id), "pivot_cache")
        ]
        if invalid:
            return _gate(
                "pivot_table_gate",
                "requires_human_review",
                "Some referenced pipelines are not pivot-cache backed.",
                invalid,
            )
        return _gate(
            "pivot_table_gate",
            "accepted",
            f"{len(pipeline_ids)} pivot-cache backed pipelines resolved.",
            pipeline_ids[:12],
        )
    data_view_ids = proposal.get("data_view_ids", [])
    pivot_views = [
        data_view_id
        for data_view_id in data_view_ids
        if indexes["data_views"].get(data_view_id, {}).get("view_kind") == "pivot_report_view"
    ]
    if not pivot_views:
        return _gate(
            "pivot_table_gate",
            "requires_human_review",
            "No pivot report data view supports a pivot claim.",
            data_view_ids,
        )
    return _gate(
        "pivot_table_gate",
        "accepted",
        f"{len(pivot_views)} pivot report data views support the proposal.",
        pivot_views[:12],
    )


def _formula_gate(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    pipeline_ids = proposal.get("pipeline_ids", [])
    if pipeline_ids:
        missing_formula_or_pivot = [
            pipeline_id
            for pipeline_id in pipeline_ids
            if not indexes["pipelines"].get(pipeline_id, {}).get("transform_refs")
        ]
        if missing_formula_or_pivot:
            return _gate(
                "formula_consistency_gate",
                "requires_human_review",
                "Some referenced pipelines lack transform evidence.",
                missing_formula_or_pivot,
            )
        return _gate(
            "formula_consistency_gate",
            "accepted",
            "Formula/pivot topology is supported by table I/O pipeline transform refs.",
            pipeline_ids[:12],
        )
    data_view_ids = proposal.get("data_view_ids", [])
    formula_views = [
        data_view_id
        for data_view_id in data_view_ids
        if "formula" in str(indexes["data_views"].get(data_view_id, {}).get("view_kind", ""))
    ]
    if not formula_views:
        return _gate(
            "formula_consistency_gate",
            "warning",
            "No formula view was found; proposal may be supported by table/pivot evidence only.",
            data_view_ids[:12],
        )
    return _gate(
        "formula_consistency_gate",
        "accepted",
        "Formula topology is supported by accepted formula data views; formula result recalculation is outside this stage.",
        formula_views[:12],
    )


def _external_reference_gate(
    proposal: dict[str, Any],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    if "external_reference_gate" not in proposal.get("required_gates", []):
        return _gate("external_reference_gate", "accepted", "No external-reference gate required.", [])
    count = int(indexes["table_io_summary"].get("external_dependency_pipeline_count") or 0)
    if count:
        return _gate(
            "external_reference_gate",
            "requires_human_review",
            f"{count} external dependency pipelines exist.",
            [],
        )
    return _gate(
        "external_reference_gate",
        "accepted",
        "No external dependency pipelines were reported in table I/O summary.",
        [],
    )


def _relation_local_scope_gate(
    proposal: dict[str, Any],
    concept_lookup: dict[str, dict[str, Any]],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    concepts = [
        concept_lookup.get(proposal.get("from_concept_id"), {}),
        concept_lookup.get(proposal.get("to_concept_id"), {}),
    ]
    local_concepts = [
        concept.get("id")
        for concept in concepts
        if "local" in str(concept.get("scope", ""))
    ]
    if not local_concepts:
        return _gate("local_domain_gate", "accepted", "Relation does not depend on local-domain concepts.", [])
    if not _all_local_boundaries_available(indexes):
        return _gate(
            "local_domain_gate",
            "quarantined",
            "Relation touches local-domain concepts while the local boundary is not confirmed.",
            local_concepts,
        )
    return _gate("local_domain_gate", "accepted", "Local relation boundary is confirmed.", local_concepts)


def _alias_local_scope_gate(
    proposal: dict[str, Any],
    concept_lookup: dict[str, dict[str, Any]],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    concept = concept_lookup.get(proposal.get("canonical_concept_id"), {})
    local_scope = "local" in str(proposal.get("alias_scope", "")) or "local" in str(concept.get("scope", ""))
    if not local_scope:
        return _gate("local_domain_gate", "accepted", "Alias is not local-domain scoped.", [])
    if not _all_local_boundaries_available(indexes):
        return _gate(
            "local_domain_gate",
            "quarantined",
            "Alias is local-domain scoped while the local boundary is not confirmed.",
            [proposal.get("canonical_concept_id", "")],
        )
    return _gate("local_domain_gate", "accepted", "Local alias boundary is confirmed.", [])


def _alias_domain_gate(
    proposal: dict[str, Any],
    concept_lookup: dict[str, dict[str, Any]],
    indexes: dict[str, Any],
) -> dict[str, Any]:
    concept = concept_lookup.get(proposal.get("canonical_concept_id"), {})
    needs_general = "general_domain" in str(proposal.get("alias_scope", ""))
    if not needs_general:
        return _gate("general_domain_gate", "accepted", "Alias does not require a general-domain gate.", [])
    refs = [str(ref) for ref in concept.get("domain_source_refs", []) if ref]
    if not refs:
        return _gate(
            "general_domain_gate",
            "requires_human_review",
            "General-domain alias has no canonical concept domain refs.",
            [proposal.get("canonical_concept_id", "")],
        )
    missing = [ref for ref in refs if ref not in indexes["general_domain_refs"]]
    if missing:
        return _gate(
            "general_domain_gate",
            "rejected",
            "Canonical concept domain refs are missing from the domain source model.",
            missing,
        )
    return _gate(
        "general_domain_gate",
        "accepted",
        "Alias inherits resolved general-domain refs from the canonical concept proposal.",
        refs,
    )


def _dependency_outcome_gate(
    dependency_id: str | None,
    dependency_outcomes: dict[str, str],
    dependency_kind: str,
) -> dict[str, Any]:
    if not dependency_id:
        return _gate(
            "dependency_outcome_gate",
            "rejected",
            f"{dependency_kind} dependency id is missing.",
            [],
        )
    outcome = dependency_outcomes.get(dependency_id)
    if outcome is None:
        return _gate(
            "dependency_outcome_gate",
            "rejected",
            f"{dependency_kind} dependency was not validated.",
            [dependency_id],
        )
    if outcome in {"rejected", "quarantined"}:
        return _gate(
            "dependency_outcome_gate",
            outcome,
            f"{dependency_kind} dependency outcome is {outcome}.",
            [dependency_id],
        )
    if outcome == "requires_human_review":
        return _gate(
            "dependency_outcome_gate",
            "requires_human_review",
            f"{dependency_kind} dependency requires human review.",
            [dependency_id],
        )
    return _gate(
        "dependency_outcome_gate",
        "accepted" if outcome == "accepted" else "warning",
        f"{dependency_kind} dependency outcome is {outcome}.",
        [dependency_id],
    )


def _alias_conflict_gate(
    proposal: dict[str, Any],
    alias_targets: dict[str, set[str]],
) -> dict[str, Any]:
    alias = _alias_key(proposal.get("alias", ""))
    targets = alias_targets.get(alias, set())
    if len(targets) > 1:
        return _gate(
            "conflict_gate",
            "requires_human_review",
            "Alias maps to multiple canonical concept candidates.",
            sorted(targets),
        )
    return _gate("conflict_gate", "accepted", "Alias has a single canonical target.", sorted(targets))


def _conflict_gate(proposal: dict[str, Any]) -> dict[str, Any]:
    if "conflict_gate" not in proposal.get("required_gates", []):
        return _gate("conflict_gate", "accepted", "No explicit conflict gate required.", [])
    return _gate("conflict_gate", "accepted", "No deterministic conflict found for this proposal.", [])


def _confidence_gate(proposal: dict[str, Any], *, threshold: float) -> dict[str, Any]:
    confidence = float(proposal.get("confidence") or 0)
    if confidence < threshold:
        return _gate(
            "confidence_gate",
            "requires_human_review",
            f"Confidence {confidence:.2f} is below threshold {threshold:.2f}.",
            [],
        )
    return _gate(
        "confidence_gate",
        "accepted",
        f"Confidence {confidence:.2f} meets threshold {threshold:.2f}.",
        [],
    )


def _result(proposal: dict[str, Any], gate_results: list[dict[str, Any]]) -> dict[str, Any]:
    final_status = _combine_gate_statuses(gate["status"] for gate in gate_results)
    return {
        "id": f"validation_result:{proposal['id']}",
        "proposal_id": proposal["id"],
        "proposal_type": proposal.get("proposal_type"),
        "final_status": final_status,
        "label": proposal.get("label") or proposal.get("alias") or proposal.get("topic") or proposal.get("relation_type"),
        "gate_results": gate_results,
        "blocking_gates": [
            gate["gate"]
            for gate in gate_results
            if gate["status"] in {"rejected", "quarantined", "requires_human_review"}
        ],
        "warning_gates": [
            gate["gate"]
            for gate in gate_results
            if gate["status"] == "warning"
        ],
        "evidence_refs": proposal.get("evidence_refs", []),
    }


def _gate(
    gate: str,
    status: str,
    reason: str,
    evidence_refs: list[str],
) -> dict[str, Any]:
    return {
        "gate": gate,
        "status": status,
        "reason": reason,
        "evidence_refs": [str(ref) for ref in evidence_refs if ref],
    }


def _combine_gate_statuses(statuses: Any) -> str:
    return max(statuses, key=lambda status: OUTCOME_ORDER.get(status, 99))


def _build_indexes(
    mapping: dict[str, Any],
    table_io: dict[str, Any],
    domain_model: dict[str, Any],
) -> dict[str, Any]:
    evidence_refs = {
        "domain_source_model.semantic_readiness",
        "action_contracts.summary",
        "table_io_pipelines",
    }
    data_views = {}
    for key in ["nodes", "relations", "data_views", "review_queue"]:
        for item in mapping.get(key, []):
            if item.get("id"):
                evidence_refs.add(item["id"])
            evidence_refs.update(str(ref) for ref in item.get("evidence_refs", []) if ref)
            if key == "data_views" and item.get("id"):
                data_views[item["id"]] = item
    pipelines = {}
    for pipeline in table_io.get("pipelines", []):
        if pipeline.get("id"):
            pipelines[pipeline["id"]] = pipeline
            evidence_refs.add(pipeline["id"])
        evidence_refs.update(str(ref) for ref in pipeline.get("evidence_refs", []) if ref)
        for transform in pipeline.get("transform_refs", []):
            if transform.get("id"):
                evidence_refs.add(transform["id"])
            if transform.get("relation_id"):
                evidence_refs.add(transform["relation_id"])
    general_domain_refs = set()
    for source in domain_model.get("domain_layers", {}).get("general_domain_sources", []):
        if source.get("id"):
            general_domain_refs.add(source["id"])
            evidence_refs.add(source["id"])
    local_boundary_statuses = {}
    for boundary in domain_model.get("domain_layers", {}).get("local_domain_boundaries", []):
        if boundary.get("id"):
            local_boundary_statuses[boundary["id"]] = boundary.get("status")
            evidence_refs.add(boundary["id"])
            evidence_refs.update(str(ref) for ref in boundary.get("evidence_refs", []) if ref)
    return {
        "evidence_refs": evidence_refs,
        "data_views": data_views,
        "pipelines": pipelines,
        "table_io_summary": table_io.get("summary", {}),
        "general_domain_refs": general_domain_refs,
        "local_boundary_statuses": local_boundary_statuses,
    }


def _pipeline_has_transform_kind(pipeline: dict[str, Any] | None, kind: str) -> bool:
    if not pipeline:
        return False
    return any(transform.get("kind") == kind for transform in pipeline.get("transform_refs", []))


def _all_local_boundaries_available(indexes: dict[str, Any]) -> bool:
    statuses = indexes["local_boundary_statuses"].values()
    return bool(statuses) and all(status == "available" for status in statuses)


def _alias_targets(alias_proposals: list[dict[str, Any]]) -> dict[str, set[str]]:
    targets: dict[str, set[str]] = defaultdict(set)
    for proposal in alias_proposals:
        targets[_alias_key(proposal.get("alias", ""))].add(
            proposal.get("canonical_concept_id", "")
        )
    return targets


def _alias_key(alias: str) -> str:
    return " ".join(str(alias).strip().casefold().split())


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(result["final_status"] for result in results)
    type_counts = Counter(result["proposal_type"] for result in results)
    return {
        "proposal_result_count": len(results),
        "accepted_count": status_counts.get("accepted", 0),
        "warning_count": status_counts.get("warning", 0),
        "requires_human_review_count": status_counts.get("requires_human_review", 0),
        "quarantined_count": status_counts.get("quarantined", 0),
        "rejected_count": status_counts.get("rejected", 0),
        "semantic_concept_result_count": type_counts.get("semantic_concept_candidate", 0),
        "hierarchy_result_count": type_counts.get("hierarchy_candidate", 0),
        "semantic_relation_result_count": type_counts.get("semantic_relation_candidate", 0),
        "alias_result_count": type_counts.get("alias_candidate", 0),
        "ambiguity_note_result_count": type_counts.get("ambiguity_note", 0),
        "validation_status": "validated_with_open_review_items"
        if status_counts.get("requires_human_review", 0) or status_counts.get("quarantined", 0)
        else "validated",
    }


def _gate_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for result in results:
        for gate in result.get("gate_results", []):
            counts[gate["gate"]][gate["status"]] += 1
    return {
        gate: dict(sorted(counter.items()))
        for gate, counter in sorted(counts.items())
    }


def _review_queue(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue = []
    for result in results:
        if result["final_status"] not in {"requires_human_review", "quarantined", "rejected"}:
            continue
        queue.append(
            {
                "id": f"review:{result['proposal_id']}",
                "proposal_id": result["proposal_id"],
                "proposal_type": result["proposal_type"],
                "status": result["final_status"],
                "label": result.get("label"),
                "blocking_gates": result.get("blocking_gates", []),
                "required_action": _required_action(result),
            }
        )
    return sorted(queue, key=lambda item: (item["status"], item["proposal_type"], item["proposal_id"]))


def _required_action(result: dict[str, Any]) -> str:
    gates = set(result.get("blocking_gates", []))
    if "local_domain_gate" in gates:
        return "confirm_local_domain_boundary_or_keep_quarantined"
    if "conflict_gate" in gates:
        return "resolve_alias_or_relation_conflict"
    if "source_trace_gate" in gates:
        return "repair_or_explain_missing_evidence_ref"
    if "ambiguity_resolution_gate" in gates:
        return "resolve_recorded_ambiguity"
    if "confidence_gate" in gates:
        return "human_review_low_confidence_claim"
    return "human_review_required"


def _parser_observations(
    results: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
) -> list[dict[str, str]]:
    summary = _summary(results)
    observations = [
        {
            "level": "info",
            "message": (
                f"Validated {summary['proposal_result_count']} LLM proposals with "
                f"{summary['accepted_count']} accepted and {summary['quarantined_count']} quarantined."
            ),
        }
    ]
    if review_queue:
        observations.append(
            {
                "level": "warning",
                "message": f"{len(review_queue)} proposal results still require review, quarantine, or rejection handling.",
            }
        )
    return observations


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministically validate evidence-bounded LLM workbook ontology proposals."
    )
    parser.add_argument("--llm-proposals", type=Path, required=True)
    parser.add_argument("--document-ontology-mapping", type=Path, required=True)
    parser.add_argument("--table-io-pipelines", type=Path, required=True)
    parser.add_argument("--domain-source-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    validation = build_llm_proposal_validation(
        llm_proposals_path=args.llm_proposals,
        document_ontology_mapping_path=args.document_ontology_mapping,
        table_io_pipelines_path=args.table_io_pipelines,
        domain_source_model_path=args.domain_source_model,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
