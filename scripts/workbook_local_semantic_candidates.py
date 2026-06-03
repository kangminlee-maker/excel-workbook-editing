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


def build_local_semantic_candidates(
    *,
    data_view_projection_path: Path,
    domain_source_model_path: Path,
    validated_document_graph_path: Path,
) -> dict[str, Any]:
    data_view_projection_path = data_view_projection_path.expanduser().resolve()
    domain_source_model_path = domain_source_model_path.expanduser().resolve()
    validated_document_graph_path = validated_document_graph_path.expanduser().resolve()

    projection_package = _read_json(data_view_projection_path)
    domain_model = _read_json(domain_source_model_path)
    graph_package = _read_json(validated_document_graph_path)

    local_boundary = _local_boundary(domain_model)
    concept_index = _semantic_concept_index(graph_package)
    candidates = _local_candidates(
        projection_package=projection_package,
        domain_model=domain_model,
        concept_index=concept_index,
        local_boundary=local_boundary,
    )
    relations = _candidate_relations(candidates)
    review_queue = _review_queue(candidates, domain_model)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "data_view_projection": str(data_view_projection_path),
            "domain_source_model": str(domain_source_model_path),
            "validated_document_graph": str(validated_document_graph_path),
        },
        "method": {
            "name": "deterministic_local_semantic_candidate_generation",
            "authority": "candidate_projection_not_shared_ontology_promotion",
            "decision_policy": (
                "Project accepted data-view surfaces into boundary-scoped local semantic "
                "ontology candidates. Accepted semantic context may seed candidate labels, "
                "but unconfirmed local boundaries and missing local vocabulary sources block "
                "shared ontology promotion."
            ),
        },
        "local_boundary": local_boundary,
        "semantic_readiness": domain_model.get("semantic_readiness", {}),
        "local_semantic_candidates": candidates,
        "candidate_relations": relations,
        "review_queue": review_queue,
        "summary": _summary(candidates, relations, review_queue, domain_model),
        "parser_observations": _parser_observations(candidates, domain_model),
    }


def _local_candidates(
    *,
    projection_package: dict[str, Any],
    domain_model: dict[str, Any],
    concept_index: dict[str, dict[str, Any]],
    local_boundary: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    projections = projection_package.get("data_view_projections", [])
    by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unassigned = []
    for projection in projections:
        concept_ids = projection.get("semantic_context", {}).get("semantic_concept_ids", [])
        if concept_ids:
            for concept_id in concept_ids:
                by_concept[concept_id].append(projection)
        else:
            unassigned.append(projection)

    candidates = []
    for concept_id, concept_projections in sorted(by_concept.items()):
        concept = concept_index.get(concept_id, {})
        label = _first_non_empty(
            concept.get("label"),
            _first(concept_projections).get("semantic_context", {}).get("semantic_labels", [None])[0],
            concept_id,
        )
        candidate_id = _candidate_id("accepted_context", concept_id)
        domain_refs = concept.get("properties", {}).get("domain_source_refs", [])
        candidates.append(
            {
                "id": candidate_id,
                "type": "local_semantic_candidate",
                "label": label,
                "candidate_kind": concept.get("properties", {}).get("concept_kind")
                or "general_domain_aligned_surface",
                "source_kind": "accepted_semantic_context",
                "status": _candidate_status(local_boundary),
                "promotion_status": _promotion_status(local_boundary),
                "applicability_scope": _applicability_scope(local_boundary),
                "confidence": 0.78,
                "requires_human_review": True,
                "local_boundary_id": (local_boundary or {}).get("id"),
                "general_domain_alignment": {
                    "status": "aligned",
                    "accepted_semantic_concept_ids": [concept_id],
                    "accepted_semantic_labels": [label],
                    "domain_source_refs": domain_refs,
                },
                "local_domain_evidence": _local_domain_evidence(domain_model),
                "data_view_refs": _data_view_refs(concept_projections),
                "observed_terms": _unique(
                    _first(concept_projections).get("semantic_context", {}).get("accepted_aliases", [])
                    + _observed_terms(concept_projections)
                )[:40],
                "required_actions": _required_actions(
                    assigned=True,
                    formula_cell_count=sum(
                        item.get("metrics", {}).get("formula_cell_count", 0)
                        for item in concept_projections
                    ),
                    local_boundary=local_boundary,
                    domain_model=domain_model,
                ),
                "warnings": _candidate_warnings(
                    assigned=True,
                    projections=concept_projections,
                    local_boundary=local_boundary,
                    domain_model=domain_model,
                ),
                "evidence_refs": _unique(
                    [concept_id]
                    + concept.get("evidence_refs", [])
                    + _projection_evidence_refs(concept_projections)
                ),
                "source_artifact_refs": _unique(
                    concept.get("source_artifact_refs", [])
                    + ["data_view_projection", "domain_source_model", "validated_document_graph"]
                ),
            }
        )

    for projection in sorted(unassigned, key=lambda item: (str(item.get("sheet")), str(item.get("range")))):
        candidate_id = _candidate_id("unmapped_data_view", projection["data_view_id"])
        label = f"{projection.get('sheet')} {projection.get('role')} surface {projection.get('range')}"
        formula_cell_count = projection.get("metrics", {}).get("formula_cell_count", 0)
        candidates.append(
            {
                "id": candidate_id,
                "type": "local_semantic_candidate",
                "label": label,
                "candidate_kind": _candidate_kind_from_projection(projection),
                "source_kind": "unmapped_data_view_surface",
                "status": "needs_semantic_interpretation",
                "promotion_status": "not_promotable_semantic_label_pending",
                "applicability_scope": _applicability_scope(local_boundary),
                "confidence": _unassigned_confidence(projection),
                "requires_human_review": True,
                "local_boundary_id": (local_boundary or {}).get("id"),
                "general_domain_alignment": {
                    "status": "unmapped_pending_semantic_interpretation",
                    "accepted_semantic_concept_ids": [],
                    "accepted_semantic_labels": [],
                    "domain_source_refs": [],
                },
                "local_domain_evidence": _local_domain_evidence(domain_model),
                "data_view_refs": _data_view_refs([projection]),
                "observed_terms": _observed_terms([projection])[:30],
                "required_actions": _required_actions(
                    assigned=False,
                    formula_cell_count=formula_cell_count,
                    local_boundary=local_boundary,
                    domain_model=domain_model,
                ),
                "warnings": _candidate_warnings(
                    assigned=False,
                    projections=[projection],
                    local_boundary=local_boundary,
                    domain_model=domain_model,
                ),
                "evidence_refs": _projection_evidence_refs([projection]),
                "source_artifact_refs": _unique(
                    projection.get("source_artifact_refs", [])
                    + ["data_view_projection", "domain_source_model"]
                ),
            }
        )

    return sorted(candidates, key=lambda item: item["id"])


def _candidate_relations(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relations = []
    for candidate in candidates:
        for data_view_id in candidate.get("data_view_refs", {}).get("data_view_ids", []):
            relations.append(
                {
                    "id": f"candidate_relation:{_stable_hash(candidate['id'] + data_view_id)}",
                    "type": "local_candidate_describes_data_view",
                    "from": candidate["id"],
                    "to": data_view_id,
                    "status": "candidate",
                    "evidence_refs": [data_view_id],
                    "source_artifact_refs": ["local_semantic_candidates", "data_view_projection"],
                }
            )
        for concept_id in candidate.get("general_domain_alignment", {}).get(
            "accepted_semantic_concept_ids", []
        ):
            relations.append(
                {
                    "id": f"candidate_relation:{_stable_hash(candidate['id'] + concept_id)}",
                    "type": "local_candidate_refines_accepted_semantic_context",
                    "from": candidate["id"],
                    "to": concept_id,
                    "status": "candidate",
                    "evidence_refs": [concept_id],
                    "source_artifact_refs": [
                        "local_semantic_candidates",
                        "validated_document_graph",
                    ],
                }
            )
    return sorted(relations, key=lambda item: item["id"])


def _review_queue(
    candidates: list[dict[str, Any]],
    domain_model: dict[str, Any],
) -> list[dict[str, Any]]:
    queue = []
    queue.extend(domain_model.get("review_queue", []))
    for candidate in candidates:
        queue.append(
            {
                "id": f"review:{candidate['id']}:confirm_local_candidate",
                "kind": "local_semantic_candidate",
                "priority": "high"
                if candidate["source_kind"] == "unmapped_data_view_surface"
                else "medium",
                "reason": "semantic_label_pending"
                if candidate["source_kind"] == "unmapped_data_view_surface"
                else "local_boundary_confirmation_pending",
                "target_id": candidate["id"],
                "required_action": "assign_or_confirm_semantic_label"
                if candidate["source_kind"] == "unmapped_data_view_surface"
                else "confirm_local_boundary_and_applicability",
                "evidence_refs": candidate.get("evidence_refs", [])[:20],
            }
        )
    return queue


def _summary(
    candidates: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
    domain_model: dict[str, Any],
) -> dict[str, Any]:
    source_counts = Counter(item["source_kind"] for item in candidates)
    status_counts = Counter(item["status"] for item in candidates)
    promotion_counts = Counter(item["promotion_status"] for item in candidates)
    data_view_ids = {
        data_view_id
        for candidate in candidates
        for data_view_id in candidate.get("data_view_refs", {}).get("data_view_ids", [])
    }
    readiness = domain_model.get("semantic_readiness", {})
    return {
        "local_semantic_candidate_count": len(candidates),
        "accepted_context_candidate_count": source_counts.get("accepted_semantic_context", 0),
        "unmapped_data_view_candidate_count": source_counts.get("unmapped_data_view_surface", 0),
        "boundary_pending_candidate_count": status_counts.get("local_candidate_boundary_pending", 0),
        "needs_semantic_interpretation_count": status_counts.get("needs_semantic_interpretation", 0),
        "shared_promotion_allowed_candidate_count": promotion_counts.get(
            "shared_ontology_promotion_allowed", 0
        ),
        "candidate_relation_count": len(relations),
        "covered_data_view_count": len(data_view_ids),
        "review_queue_count": len(review_queue),
        "local_boundary_confirmed": bool(readiness.get("local_boundary_confirmed")),
        "local_domain_source_count": readiness.get("local_domain_source_count", 0),
        "candidate_status": "generated_boundary_scoped_candidates_with_promotion_blockers",
    }


def _parser_observations(
    candidates: list[dict[str, Any]],
    domain_model: dict[str, Any],
) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": f"Generated {len(candidates)} boundary-scoped local semantic candidates.",
        }
    ]
    readiness = domain_model.get("semantic_readiness", {})
    if not readiness.get("local_boundary_confirmed"):
        observations.append(
            {
                "level": "warning",
                "message": "Local boundary is not confirmed; candidates are not promotable to shared ontology.",
            }
        )
    if not readiness.get("local_domain_source_count", 0):
        observations.append(
            {
                "level": "warning",
                "message": "No local policy or vocabulary source is available; local semantics require human review.",
            }
        )
    unassigned_count = sum(
        1 for candidate in candidates if candidate["source_kind"] == "unmapped_data_view_surface"
    )
    if unassigned_count:
        observations.append(
            {
                "level": "warning",
                "message": f"{unassigned_count} accepted data-view surfaces still need semantic labels.",
            }
        )
    return observations


def _data_view_refs(projections: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "data_view_ids": _unique([item["data_view_id"] for item in projections]),
        "projection_ids": _unique([item["id"] for item in projections]),
        "sheets": _unique([item.get("sheet") for item in projections if item.get("sheet")]),
        "ranges": _unique([item.get("range") for item in projections if item.get("range")]),
        "projection_kinds": _unique([item.get("projection_kind") for item in projections]),
        "roles": _unique([item.get("role") for item in projections]),
        "sampled_projection_count": sum(
            1 for item in projections if item.get("preview", {}).get("status") == "sampled"
        ),
        "formula_cell_count": sum(
            item.get("metrics", {}).get("formula_cell_count", 0) for item in projections
        ),
    }


def _observed_terms(projections: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    for projection in projections:
        if projection.get("sheet"):
            terms.append(projection["sheet"])
        for row in projection.get("preview", {}).get("rows", []):
            for cell in row.get("cells", []):
                if cell.get("value_type") != "string":
                    continue
                value = str(cell.get("value_preview") or "").strip()
                if not value or len(value) > 80:
                    continue
                if re.fullmatch(r"[-_.,:/\\s]+", value):
                    continue
                terms.append(value)
    return _unique(terms)


def _projection_evidence_refs(projections: list[dict[str, Any]]) -> list[str]:
    refs = []
    for projection in projections:
        refs.append(projection.get("data_view_id"))
        refs.extend(projection.get("evidence_refs", []))
    return _unique([ref for ref in refs if ref])


def _candidate_warnings(
    *,
    assigned: bool,
    projections: list[dict[str, Any]],
    local_boundary: dict[str, Any] | None,
    domain_model: dict[str, Any],
) -> list[str]:
    warnings = []
    if not local_boundary or local_boundary.get("status") != "confirmed":
        warnings.append("local_domain_boundary_not_confirmed")
    if not domain_model.get("semantic_readiness", {}).get("local_domain_source_count", 0):
        warnings.append("no_local_domain_sources_available")
    if not assigned:
        warnings.append("no_accepted_semantic_context")
    if any(item.get("metrics", {}).get("formula_cell_count", 0) for item in projections):
        warnings.append("formula_text_only_not_recalculated_result")
    projection_warnings = [
        warning for item in projections for warning in item.get("warnings", [])
    ]
    warnings.extend(projection_warnings)
    return _unique(warnings)


def _required_actions(
    *,
    assigned: bool,
    formula_cell_count: int,
    local_boundary: dict[str, Any] | None,
    domain_model: dict[str, Any],
) -> list[str]:
    actions = []
    if not local_boundary or local_boundary.get("status") != "confirmed":
        actions.append("confirm_or_define_local_boundary")
    if not domain_model.get("semantic_readiness", {}).get("local_domain_source_count", 0):
        actions.append("provide_local_policy_or_vocabulary_source")
    if not assigned:
        actions.append("assign_or_confirm_semantic_label")
    if formula_cell_count:
        actions.append("validate_formula_results_with_excel_engine_before_numeric_claims")
    return _unique(actions)


def _local_domain_evidence(domain_model: dict[str, Any]) -> dict[str, Any]:
    layers = domain_model.get("domain_layers", {})
    return {
        "local_domain_source_ids": [
            item.get("id") for item in layers.get("local_domain_sources", [])
        ],
        "local_domain_boundary_ids": [
            item.get("id") for item in layers.get("local_domain_boundaries", [])
        ],
        "local_domain_source_status": "available"
        if layers.get("local_domain_sources")
        else "missing",
    }


def _semantic_concept_index(graph_package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        node["id"]: node
        for node in graph_package.get("graph", {}).get("nodes", [])
        if node.get("type") == "semantic_concept"
    }


def _local_boundary(domain_model: dict[str, Any]) -> dict[str, Any] | None:
    boundaries = domain_model.get("domain_layers", {}).get("local_domain_boundaries", [])
    return boundaries[0] if boundaries else None


def _candidate_status(local_boundary: dict[str, Any] | None) -> str:
    if local_boundary and local_boundary.get("status") == "confirmed":
        return "local_candidate"
    return "local_candidate_boundary_pending"


def _promotion_status(local_boundary: dict[str, Any] | None) -> str:
    if local_boundary and local_boundary.get("status") == "confirmed":
        return "local_candidate_not_yet_shared"
    return "not_promotable_shared_ontology_boundary_pending"


def _applicability_scope(local_boundary: dict[str, Any] | None) -> str:
    return (local_boundary or {}).get(
        "scope", "current_workbook_only_until_boundary_confirmed"
    )


def _candidate_kind_from_projection(projection: dict[str, Any]) -> str:
    kind = projection.get("projection_kind")
    if kind == "pivot_view_projection":
        return "unmapped_pivot_report_surface"
    if kind == "formula_summary_projection":
        return "unmapped_formula_summary_surface"
    if kind == "formula_transform_projection":
        return "unmapped_formula_transform_surface"
    return "unmapped_table_surface"


def _unassigned_confidence(projection: dict[str, Any]) -> float:
    kind = projection.get("projection_kind")
    if kind == "pivot_view_projection":
        return 0.48
    if kind == "formula_summary_projection":
        return 0.46
    if kind == "formula_transform_projection":
        return 0.42
    return 0.4


def _candidate_id(source_kind: str, seed: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", seed).strip("_")[:80]
    return f"local_semantic_candidate:{source_kind}:{slug}:{_stable_hash(seed)}"


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _first(values: list[Any]) -> Any:
    return values[0] if values else {}


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value:
            return value
    return None


def _unique(values: list[Any]) -> list[Any]:
    seen = set()
    out = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate boundary-scoped local semantic ontology candidates."
    )
    parser.add_argument("--data-view-projection", type=Path, required=True)
    parser.add_argument("--domain-source-model", type=Path, required=True)
    parser.add_argument("--validated-document-graph", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candidates = build_local_semantic_candidates(
        data_view_projection_path=args.data_view_projection,
        domain_source_model_path=args.domain_source_model,
        validated_document_graph_path=args.validated_document_graph,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
