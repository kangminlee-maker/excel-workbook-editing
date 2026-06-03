from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"


def build_validated_document_graph(
    *,
    document_ontology_mapping_path: Path,
    llm_proposals_path: Path,
    llm_proposal_validation_path: Path,
    action_contracts_path: Path | None = None,
) -> dict[str, Any]:
    document_ontology_mapping_path = document_ontology_mapping_path.expanduser().resolve()
    llm_proposals_path = llm_proposals_path.expanduser().resolve()
    llm_proposal_validation_path = llm_proposal_validation_path.expanduser().resolve()
    action_contracts_path = action_contracts_path.expanduser().resolve() if action_contracts_path else None

    mapping = _read_json(document_ontology_mapping_path)
    proposals = _read_json(llm_proposals_path)
    validation = _read_json(llm_proposal_validation_path)
    action_contracts = _read_json(action_contracts_path) if action_contracts_path else {}

    proposal_lookup = _proposal_lookup(proposals)
    validation_lookup = {
        result["proposal_id"]: result
        for result in validation.get("proposal_results", [])
    }
    accepted_proposal_ids = {
        proposal_id
        for proposal_id, result in validation_lookup.items()
        if result.get("final_status") == "accepted"
    }

    document_nodes = [
        node for node in mapping.get("nodes", []) if node.get("status") == "accepted"
    ]
    accepted_node_ids = {node["id"] for node in document_nodes}
    accepted_document_relations = [
        relation
        for relation in mapping.get("relations", [])
        if relation.get("status") == "accepted"
    ]
    document_relations = [
        relation
        for relation in accepted_document_relations
        if relation.get("from") in accepted_node_ids
        and relation.get("to") in accepted_node_ids
    ]
    filtered_document_relations = [
        relation
        for relation in accepted_document_relations
        if relation.get("from") not in accepted_node_ids
        or relation.get("to") not in accepted_node_ids
    ]
    accepted_data_views = [
        view for view in mapping.get("data_views", []) if view.get("status") == "accepted"
    ]

    semantic_nodes = _semantic_nodes(
        accepted_proposal_ids=accepted_proposal_ids,
        proposal_lookup=proposal_lookup,
        validation_lookup=validation_lookup,
    )
    semantic_node_ids = {node["id"] for node in semantic_nodes}
    semantic_relations = _semantic_relations(
        accepted_proposal_ids=accepted_proposal_ids,
        proposal_lookup=proposal_lookup,
        validation_lookup=validation_lookup,
        document_node_ids=accepted_node_ids,
        semantic_node_ids=semantic_node_ids,
    )
    semantic_aliases = _semantic_aliases(
        accepted_proposal_ids=accepted_proposal_ids,
        proposal_lookup=proposal_lookup,
        validation_lookup=validation_lookup,
        semantic_node_ids=semantic_node_ids,
    )

    all_nodes = sorted(document_nodes + semantic_nodes, key=lambda item: item["id"])
    all_relations = sorted(document_relations + semantic_relations, key=lambda item: item["id"])
    _assert_no_dangling_relations(all_nodes, all_relations)
    carry_forward = _carry_forward(
        mapping,
        validation,
        action_contracts,
        filtered_document_relations=filtered_document_relations,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "document_ontology_mapping": str(document_ontology_mapping_path),
            "llm_proposals": str(llm_proposals_path),
            "llm_proposal_validation": str(llm_proposal_validation_path),
            "action_contracts": str(action_contracts_path) if action_contracts_path else None,
        },
        "method": {
            "name": "deterministic_validated_document_graph_assembly",
            "authority": "accepted_graph_projection_with_carry_forward_review_queue",
            "decision_policy": (
                "Assemble only accepted document ontology artifacts and accepted proposal "
                "validation results into the graph body. Preserve review-required, quarantined, "
                "and rejected items as carry-forward queue entries instead of promoting them."
            ),
        },
        "graph": {
            "nodes": all_nodes,
            "relations": all_relations,
            "data_views": accepted_data_views,
            "semantic_aliases": semantic_aliases,
        },
        "carry_forward": carry_forward,
        "summary": _summary(
            document_nodes=document_nodes,
            document_relations=document_relations,
            semantic_nodes=semantic_nodes,
            semantic_relations=semantic_relations,
            semantic_aliases=semantic_aliases,
            accepted_data_views=accepted_data_views,
            carry_forward=carry_forward,
            validation=validation,
        ),
        "parser_observations": _parser_observations(
            semantic_nodes=semantic_nodes,
            semantic_relations=semantic_relations,
            semantic_aliases=semantic_aliases,
            carry_forward=carry_forward,
            validation=validation,
        ),
    }


def _semantic_nodes(
    *,
    accepted_proposal_ids: set[str],
    proposal_lookup: dict[str, dict[str, Any]],
    validation_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    nodes = []
    for proposal_id in sorted(accepted_proposal_ids):
        proposal = proposal_lookup.get(proposal_id, {})
        if proposal.get("proposal_type") != "semantic_concept_candidate":
            continue
        validation = validation_lookup[proposal_id]
        nodes.append(
            {
                "id": proposal["id"],
                "type": "semantic_concept",
                "ontology_class": "SemanticConcept",
                "label": proposal.get("label"),
                "status": "accepted",
                "sheet": ",".join(proposal.get("matched_sheets", [])) or None,
                "range": None,
                "properties": {
                    "concept_kind": proposal.get("concept_kind"),
                    "scope": proposal.get("scope"),
                    "description": proposal.get("description"),
                    "matched_terms": proposal.get("matched_terms", []),
                    "data_view_ids": proposal.get("data_view_ids", []),
                    "domain_source_refs": proposal.get("domain_source_refs", []),
                    "source_proposal_id": proposal["id"],
                    "validation_result_id": validation["id"],
                },
                "evidence_refs": proposal.get("evidence_refs", []),
                "source_artifact_refs": [
                    "llm_proposals",
                    "llm_proposal_validation",
                    "document_ontology_mapping",
                ],
            }
        )
    return nodes


def _semantic_relations(
    *,
    accepted_proposal_ids: set[str],
    proposal_lookup: dict[str, dict[str, Any]],
    validation_lookup: dict[str, dict[str, Any]],
    document_node_ids: set[str],
    semantic_node_ids: set[str],
) -> list[dict[str, Any]]:
    relations = []
    for proposal_id in sorted(accepted_proposal_ids):
        proposal = proposal_lookup.get(proposal_id, {})
        proposal_type = proposal.get("proposal_type")
        if proposal_type == "hierarchy_candidate":
            sheet = (proposal.get("parent") or {}).get("sheet")
            parent_id = f"sheet:{sheet}" if sheet else None
            child_id = (proposal.get("child") or {}).get("id")
            if parent_id not in document_node_ids or child_id not in semantic_node_ids:
                continue
            relations.append(
                _graph_relation(
                    relation_id=f"rel:contains_semantic_concept|{parent_id}|{child_id}",
                    relation_type="contains_semantic_concept",
                    from_id=parent_id,
                    to_id=child_id,
                    proposal=proposal,
                    validation=validation_lookup[proposal_id],
                )
            )
        elif proposal_type == "semantic_relation_candidate":
            from_id = proposal.get("from_concept_id")
            to_id = proposal.get("to_concept_id")
            if from_id not in semantic_node_ids or to_id not in semantic_node_ids:
                continue
            relations.append(
                _graph_relation(
                    relation_id=f"rel:{proposal.get('relation_type')}|{from_id}|{to_id}",
                    relation_type=proposal.get("relation_type"),
                    from_id=from_id,
                    to_id=to_id,
                    proposal=proposal,
                    validation=validation_lookup[proposal_id],
                )
            )
    return relations


def _graph_relation(
    *,
    relation_id: str,
    relation_type: str,
    from_id: str,
    to_id: str,
    proposal: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": relation_id,
        "type": relation_type,
        "from": from_id,
        "to": to_id,
        "status": "accepted",
        "properties": {
            "source_proposal_id": proposal["id"],
            "validation_result_id": validation["id"],
            "proposal_type": proposal.get("proposal_type"),
            "pipeline_ids": proposal.get("pipeline_ids", []),
            "data_view_ids": proposal.get("data_view_ids", []),
            "confidence": proposal.get("confidence"),
        },
        "evidence_refs": proposal.get("evidence_refs", []),
        "source_artifact_refs": [
            "llm_proposals",
            "llm_proposal_validation",
            "document_ontology_mapping",
        ],
    }


def _semantic_aliases(
    *,
    accepted_proposal_ids: set[str],
    proposal_lookup: dict[str, dict[str, Any]],
    validation_lookup: dict[str, dict[str, Any]],
    semantic_node_ids: set[str],
) -> list[dict[str, Any]]:
    aliases = []
    for proposal_id in sorted(accepted_proposal_ids):
        proposal = proposal_lookup.get(proposal_id, {})
        if proposal.get("proposal_type") != "alias_candidate":
            continue
        concept_id = proposal.get("canonical_concept_id")
        if concept_id not in semantic_node_ids:
            continue
        aliases.append(
            {
                "id": proposal["id"],
                "alias": proposal.get("alias"),
                "canonical_concept_id": concept_id,
                "status": "accepted",
                "scope": proposal.get("alias_scope"),
                "matched_sheets": proposal.get("matched_sheets", []),
                "confidence": proposal.get("confidence"),
                "evidence_refs": proposal.get("evidence_refs", []),
                "source_artifact_refs": ["llm_proposals", "llm_proposal_validation"],
                "validation_result_id": validation_lookup[proposal_id]["id"],
            }
        )
    return aliases


def _carry_forward(
    mapping: dict[str, Any],
    validation: dict[str, Any],
    action_contracts: dict[str, Any],
    *,
    filtered_document_relations: list[dict[str, Any]],
) -> dict[str, Any]:
    document_review_items = [
        {
            "id": item.get("id"),
            "kind": "document_ontology_review_item",
            "status": item.get("status"),
            "reason": item.get("reason"),
            "target_node_id": item.get("target_node_id"),
            "sheet": item.get("sheet"),
            "range": item.get("range"),
            "evidence_refs": item.get("evidence_refs", []),
        }
        for item in mapping.get("review_queue", [])
    ]
    proposal_review_items = [
        {
            "id": item.get("id"),
            "kind": "proposal_validation_review_item",
            "status": item.get("status"),
            "reason": ",".join(item.get("blocking_gates", [])),
            "proposal_id": item.get("proposal_id"),
            "proposal_type": item.get("proposal_type"),
            "label": item.get("label"),
            "required_action": item.get("required_action"),
        }
        for item in validation.get("review_queue", [])
    ]
    return {
        "document_review_queue": document_review_items,
        "proposal_review_queue": proposal_review_items,
        "filtered_document_relations": [
            {
                "id": relation.get("id"),
                "type": relation.get("type"),
                "from": relation.get("from"),
                "to": relation.get("to"),
                "reason": "accepted_relation_has_non_graph_endpoint",
                "evidence_refs": relation.get("evidence_refs", []),
            }
            for relation in filtered_document_relations
        ],
        "action_contract_summary": action_contracts.get("summary", {}),
    }


def _proposal_lookup(proposals: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup = {}
    for key in [
        "semantic_concept_proposals",
        "hierarchy_proposals",
        "semantic_relation_proposals",
        "alias_proposals",
        "ambiguity_notes",
    ]:
        for proposal in proposals.get(key, []):
            lookup[proposal["id"]] = proposal
    return lookup


def _summary(
    *,
    document_nodes: list[dict[str, Any]],
    document_relations: list[dict[str, Any]],
    semantic_nodes: list[dict[str, Any]],
    semantic_relations: list[dict[str, Any]],
    semantic_aliases: list[dict[str, Any]],
    accepted_data_views: list[dict[str, Any]],
    carry_forward: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    action_summary = carry_forward.get("action_contract_summary", {})
    return {
        "graph_node_count": len(document_nodes) + len(semantic_nodes),
        "document_node_count": len(document_nodes),
        "semantic_node_count": len(semantic_nodes),
        "graph_relation_count": len(document_relations) + len(semantic_relations),
        "document_relation_count": len(document_relations),
        "semantic_relation_count": len(semantic_relations),
        "accepted_data_view_count": len(accepted_data_views),
        "semantic_alias_count": len(semantic_aliases),
        "document_review_queue_count": len(carry_forward.get("document_review_queue", [])),
        "proposal_review_queue_count": len(carry_forward.get("proposal_review_queue", [])),
        "filtered_document_relation_count": len(carry_forward.get("filtered_document_relations", [])),
        "open_action_contract_count": int(action_summary.get("open_count") or 0),
        "blocked_action_contract_count": int(action_summary.get("blocked_count") or 0),
        "accepted_proposal_result_count": int(validation.get("summary", {}).get("accepted_count") or 0),
        "graph_status": "assembled_with_carry_forward_review_queue",
    }


def _parser_observations(
    *,
    semantic_nodes: list[dict[str, Any]],
    semantic_relations: list[dict[str, Any]],
    semantic_aliases: list[dict[str, Any]],
    carry_forward: dict[str, Any],
    validation: dict[str, Any],
) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": (
                f"Assembled {len(semantic_nodes)} semantic concept nodes, "
                f"{len(semantic_relations)} semantic relations, and {len(semantic_aliases)} accepted aliases."
            ),
        }
    ]
    non_accepted = (
        int(validation.get("summary", {}).get("requires_human_review_count") or 0)
        + int(validation.get("summary", {}).get("quarantined_count") or 0)
        + int(validation.get("summary", {}).get("rejected_count") or 0)
    )
    if non_accepted:
        observations.append(
            {
                "level": "warning",
                "message": f"{non_accepted} proposal validation results remain outside the graph body.",
            }
        )
    if carry_forward.get("document_review_queue"):
        observations.append(
            {
                "level": "warning",
                "message": f"{len(carry_forward['document_review_queue'])} document ontology review items were carried forward.",
            }
        )
    if carry_forward.get("filtered_document_relations"):
        observations.append(
            {
                "level": "warning",
                "message": f"{len(carry_forward['filtered_document_relations'])} accepted document relations were carried forward because an endpoint was outside the accepted graph body.",
            }
        )
    return observations


def _assert_no_dangling_relations(
    nodes: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> None:
    node_ids = {node["id"] for node in nodes}
    dangling = [
        relation["id"]
        for relation in relations
        if relation["from"] not in node_ids or relation["to"] not in node_ids
    ]
    if dangling:
        raise ValueError(f"Dangling graph relations: {dangling[:10]}")


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble a validated workbook document graph from accepted ontology and proposal validation artifacts."
    )
    parser.add_argument("--document-ontology-mapping", type=Path, required=True)
    parser.add_argument("--llm-proposals", type=Path, required=True)
    parser.add_argument("--llm-proposal-validation", type=Path, required=True)
    parser.add_argument("--action-contracts", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    graph = build_validated_document_graph(
        document_ontology_mapping_path=args.document_ontology_mapping,
        llm_proposals_path=args.llm_proposals,
        llm_proposal_validation_path=args.llm_proposal_validation,
        action_contracts_path=args.action_contracts,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
