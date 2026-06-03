from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"

OUTCOME_ORDER = {
    "accepted": 0,
    "warning": 1,
    "requires_human_review": 2,
    "blocked": 3,
    "rejected": 4,
}

ALLOWED_DOMAIN_LAYERS = {
    "general_domain_reference",
    "local_domain",
    "process_semantic",
}


def build_google_sheets_semantic_proposal_validation(
    *,
    live_semantic_proposals_path: Path,
    live_domain_source_model_path: Path,
    live_evidence_package_path: Path,
    live_document_ontology_mapping_path: Path,
) -> dict[str, Any]:
    live_semantic_proposals_path = live_semantic_proposals_path.expanduser().resolve()
    live_domain_source_model_path = live_domain_source_model_path.expanduser().resolve()
    live_evidence_package_path = live_evidence_package_path.expanduser().resolve()
    live_document_ontology_mapping_path = live_document_ontology_mapping_path.expanduser().resolve()

    proposals = _read_json(live_semantic_proposals_path)
    domain_model = _read_json(live_domain_source_model_path)
    evidence = _read_json(live_evidence_package_path)
    mapping = _read_json(live_document_ontology_mapping_path)
    indexes = _build_indexes(proposals, domain_model, evidence, mapping)

    concept_results = [
        _validate_concept(proposal, domain_model, indexes)
        for proposal in proposals["semantic_concept_proposals"]
    ]
    concept_statuses = {item["target_id"]: item["final_status"] for item in concept_results}
    relation_results = [
        _validate_relation(proposal, domain_model, indexes, concept_statuses)
        for proposal in proposals["semantic_relation_proposals"]
    ]
    promotion_results = [_validate_shared_promotion(domain_model)]
    proposal_results = sorted(
        [*concept_results, *relation_results],
        key=lambda item: (item["target_type"], item["target_id"]),
    )
    review_queue = _review_queue(proposal_results, promotion_results)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": proposals["source"]["spreadsheet_id"],
            "spreadsheet_url": proposals["source"].get("spreadsheet_url"),
            "title": proposals["source"]["title"],
            "source_artifacts": {
                "live_semantic_proposals": str(live_semantic_proposals_path),
                "live_domain_source_model": str(live_domain_source_model_path),
                "live_evidence_package": str(live_evidence_package_path),
                "live_document_ontology_mapping": str(live_document_ontology_mapping_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "validation_status": "deterministic_validation_only",
            "graph_assembly": "not_performed",
            "accepted_semantic_concepts": 0,
            "shared_ontology_updates": 0,
            "formula_result_authority": "not_established",
        },
        "method": {
            "name": "connected_sheets_semantic_proposal_validation",
            "authority": "proposal_gate_outcome_not_final_graph_assembly",
            "decision_policy": (
                "Validate proposal-only semantic concepts and relations with source-trace, "
                "domain-layer, domain-source, local-boundary, source-authority, formula-result, "
                "relation-endpoint, blocker-consistency, and shared-promotion gates. This stage "
                "does not accept graph claims and does not emit shared ontology updates."
            ),
        },
        "validation_context": {
            "proposal_summary": proposals["summary"],
            "semantic_readiness": domain_model["semantic_readiness"],
            "known_evidence_ref_count": len(indexes["evidence_refs"]),
            "known_domain_source_count": len(indexes["domain_source_refs"]),
            "known_concept_proposal_count": len(indexes["concept_ids"]),
        },
        "proposal_results": proposal_results,
        "promotion_gate_results": promotion_results,
        "review_queue": review_queue,
        "summary": _summary(proposal_results, promotion_results),
        "gate_summary": _gate_summary(proposal_results, promotion_results),
        "parser_observations": _parser_observations(proposal_results, promotion_results),
    }


def write_google_sheets_semantic_proposal_validation_package(
    *,
    out_dir: Path,
    access_preflight_path: Path,
    live_manifest_path: Path,
    live_view_formula_profile_path: Path,
    live_block_candidates_path: Path,
    bounded_window_sample_path: Path,
    live_block_candidate_tuning_path: Path,
    live_table_io_pipelines_path: Path,
    live_cross_validation_plan_path: Path,
    live_validation_batch_execution_path: Path,
    live_gate_execution_path: Path,
    live_evidence_package_path: Path,
    live_document_ontology_mapping_path: Path,
    live_action_contracts_path: Path,
    live_domain_source_model_path: Path,
    live_semantic_proposals_path: Path,
    semantic_proposal_validation: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    validation_path = out_dir / "live-semantic-proposal-validation.json"
    validation_path.write_text(
        json.dumps(semantic_proposal_validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "index.html").write_text(
        render_live_manifest_html(
            access_preflight=_read_json(access_preflight_path),
            manifest=_read_json(live_manifest_path),
            live_view_formula_profile=_read_json(live_view_formula_profile_path),
            live_block_candidates=_read_json(live_block_candidates_path),
            live_bounded_window_sample=_read_json(bounded_window_sample_path),
            live_block_candidate_tuning=_read_json(live_block_candidate_tuning_path),
            live_table_io_pipelines=_read_json(live_table_io_pipelines_path),
            live_cross_validation_plan=_read_json(live_cross_validation_plan_path),
            live_validation_batch_execution=_read_json(live_validation_batch_execution_path),
            live_gate_execution=_read_json(live_gate_execution_path),
            live_evidence_package=_read_json(live_evidence_package_path),
            live_document_ontology_mapping=_read_json(live_document_ontology_mapping_path),
            live_action_contracts=_read_json(live_action_contracts_path),
            live_domain_source_model=_read_json(live_domain_source_model_path),
            live_semantic_proposals=_read_json(live_semantic_proposals_path),
            live_semantic_proposal_validation=semantic_proposal_validation,
        ),
        encoding="utf-8",
    )


def _validate_concept(
    proposal: dict[str, Any],
    domain_model: dict[str, Any],
    indexes: dict[str, set[str]],
) -> dict[str, Any]:
    gates = [
        _schema_gate(proposal, "semantic_concept_proposal"),
        _source_trace_gate(proposal.get("source_evidence_refs", []), indexes),
        _domain_layer_gate(proposal),
        _domain_source_gate(proposal, indexes),
        _local_boundary_gate(proposal, domain_model),
        _source_authority_gate(proposal, domain_model),
        _formula_result_authority_gate(proposal, domain_model),
        _shared_promotion_blocker_gate(proposal, domain_model),
    ]
    return _result(
        target_id=proposal["id"],
        target_type="semantic_concept_proposal",
        label=proposal.get("label"),
        gates=gates,
        evidence_refs=proposal.get("source_evidence_refs", []),
        domain_source_refs=proposal.get("domain_source_refs", []),
    )


def _validate_relation(
    relation: dict[str, Any],
    domain_model: dict[str, Any],
    indexes: dict[str, set[str]],
    concept_statuses: dict[str, str],
) -> dict[str, Any]:
    gates = [
        _schema_gate(relation, "semantic_relation_proposal"),
        _source_trace_gate(relation.get("source_evidence_refs", []), indexes),
        _relation_endpoint_gate(relation, indexes),
        _endpoint_status_gate(relation, concept_statuses),
        _relation_blocker_consistency_gate(relation),
        _shared_promotion_relation_gate(domain_model),
    ]
    return _result(
        target_id=relation["id"],
        target_type="semantic_relation_proposal",
        label=relation.get("relation_type"),
        gates=gates,
        evidence_refs=relation.get("source_evidence_refs", []),
        domain_source_refs=[],
    )


def _validate_shared_promotion(domain_model: dict[str, Any]) -> dict[str, Any]:
    readiness = domain_model["semantic_readiness"]
    gates = [
        _gate(
            "local_boundary_gate",
            "accepted" if readiness["local_boundary_confirmed"] else "blocked",
            "Local boundary is confirmed." if readiness["local_boundary_confirmed"] else "Local boundary is not confirmed.",
            [],
        ),
        _gate(
            "source_authority_gate",
            "accepted" if readiness["unavailable_source_count"] == 0 else "blocked",
            "All source authorities are available." if readiness["unavailable_source_count"] == 0 else "Source or formula-result authorities remain unavailable.",
            [item["id"] for item in domain_model.get("unavailable_sources", [])],
        ),
        _gate(
            "human_review_gate",
            "blocked",
            "Human approval for shared ontology promotion is not recorded.",
            [],
        ),
    ]
    return _result(
        target_id="shared_ontology_promotion",
        target_type="promotion_gate",
        label="Shared ontology promotion",
        gates=gates,
        evidence_refs=[],
        domain_source_refs=[],
    )


def _schema_gate(target: dict[str, Any], expected_type: str) -> dict[str, Any]:
    if target.get("type") != expected_type:
        return _gate(
            "schema_gate",
            "rejected",
            f"Expected type {expected_type}, got {target.get('type')}.",
            [],
        )
    if not target.get("id"):
        return _gate("schema_gate", "rejected", "Target id is missing.", [])
    return _gate("schema_gate", "accepted", "Target has the expected proposal shape.", [])


def _source_trace_gate(refs: list[str], indexes: dict[str, set[str]]) -> dict[str, Any]:
    if not refs:
        return _gate("source_trace_gate", "rejected", "No source evidence refs were provided.", [])
    unknown = [ref for ref in refs if ref not in indexes["evidence_refs"]]
    if unknown:
        return _gate(
            "source_trace_gate",
            "requires_human_review",
            f"{len(unknown)} evidence refs are not known in the current evidence index.",
            unknown[:12],
        )
    return _gate(
        "source_trace_gate",
        "accepted",
        f"{len(refs)} source evidence refs resolved.",
        refs[:12],
    )


def _domain_layer_gate(proposal: dict[str, Any]) -> dict[str, Any]:
    layer = proposal.get("domain_layer")
    if layer not in ALLOWED_DOMAIN_LAYERS:
        return _gate(
            "domain_layer_gate",
            "rejected",
            f"Unsupported domain layer: {layer}",
            [],
        )
    return _gate("domain_layer_gate", "accepted", f"Domain layer {layer} is allowed.", [])


def _domain_source_gate(proposal: dict[str, Any], indexes: dict[str, set[str]]) -> dict[str, Any]:
    refs = proposal.get("domain_source_refs", [])
    if proposal.get("domain_layer") != "general_domain_reference":
        return _gate("domain_source_gate", "accepted", "No general-domain source is required for this layer.", [])
    if not refs:
        return _gate("domain_source_gate", "rejected", "General-domain reference proposal has no domain source refs.", [])
    unknown = [ref for ref in refs if ref not in indexes["domain_source_refs"]]
    if unknown:
        return _gate(
            "domain_source_gate",
            "requires_human_review",
            f"{len(unknown)} domain source refs are not available.",
            unknown[:12],
        )
    return _gate("domain_source_gate", "accepted", f"{len(refs)} general-domain refs are available.", refs[:12])


def _local_boundary_gate(proposal: dict[str, Any], domain_model: dict[str, Any]) -> dict[str, Any]:
    if proposal.get("domain_layer") != "local_domain" and "local_boundary_not_confirmed" not in proposal.get("blockers", []):
        return _gate("local_boundary_gate", "accepted", "No local-boundary claim requires confirmation.", [])
    if domain_model["semantic_readiness"]["local_boundary_confirmed"]:
        return _gate("local_boundary_gate", "accepted", "Local boundary is confirmed.", [])
    return _gate("local_boundary_gate", "blocked", "Local boundary is not confirmed.", [])


def _source_authority_gate(proposal: dict[str, Any], domain_model: dict[str, Any]) -> dict[str, Any]:
    unavailable = [
        item["id"]
        for item in domain_model.get("unavailable_sources", [])
        if item.get("status") == "blocked"
    ]
    if "source_authority_unavailable" not in proposal.get("blockers", []) and not unavailable:
        return _gate("source_authority_gate", "accepted", "No source authority blocker applies.", [])
    if unavailable:
        return _gate("source_authority_gate", "blocked", "One or more source authorities remain unavailable.", unavailable)
    return _gate("source_authority_gate", "accepted", "Source authority blockers are resolved.", [])


def _formula_result_authority_gate(proposal: dict[str, Any], domain_model: dict[str, Any]) -> dict[str, Any]:
    formula_blockers = [
        item["id"]
        for item in domain_model.get("unavailable_sources", [])
        if item.get("type") == "formula_result" and item.get("status") == "blocked"
    ]
    if formula_blockers:
        return _gate(
            "formula_result_authority_gate",
            "blocked",
            "Formula-result authority is not established.",
            formula_blockers,
        )
    return _gate("formula_result_authority_gate", "accepted", "Formula-result authority is available.", [])


def _shared_promotion_blocker_gate(
    proposal: dict[str, Any],
    domain_model: dict[str, Any],
) -> dict[str, Any]:
    expected_blocked = domain_model["semantic_readiness"]["shared_ontology_promotion_status"] == "blocked"
    if expected_blocked and proposal.get("shared_promotion_status") == "blocked":
        return _gate(
            "shared_promotion_blocker_gate",
            "accepted",
            "Proposal correctly keeps shared promotion blocked.",
            proposal.get("blockers", []),
        )
    if expected_blocked:
        return _gate(
            "shared_promotion_blocker_gate",
            "rejected",
            "Shared promotion should be blocked but the proposal did not mark it as blocked.",
            [],
        )
    return _gate("shared_promotion_blocker_gate", "accepted", "Shared promotion readiness is consistent.", [])


def _relation_endpoint_gate(relation: dict[str, Any], indexes: dict[str, set[str]]) -> dict[str, Any]:
    endpoints = [relation.get("from"), relation.get("to")]
    missing = [endpoint for endpoint in endpoints if endpoint not in indexes["concept_ids"]]
    if missing:
        return _gate("relation_endpoint_gate", "rejected", "Relation endpoint proposal ids are missing.", missing)
    return _gate("relation_endpoint_gate", "accepted", "Relation endpoints resolve to semantic concept proposals.", endpoints)


def _endpoint_status_gate(relation: dict[str, Any], concept_statuses: dict[str, str]) -> dict[str, Any]:
    statuses = {
        relation.get("from"): concept_statuses.get(relation.get("from")),
        relation.get("to"): concept_statuses.get(relation.get("to")),
    }
    if any(status == "rejected" for status in statuses.values()):
        return _gate("endpoint_status_gate", "rejected", "One or more endpoint concepts were rejected.", list(statuses))
    if any(status == "blocked" for status in statuses.values()):
        return _gate("endpoint_status_gate", "blocked", "One or more endpoint concepts remain blocked.", list(statuses))
    if any(status == "requires_human_review" for status in statuses.values()):
        return _gate("endpoint_status_gate", "requires_human_review", "One or more endpoint concepts require review.", list(statuses))
    return _gate("endpoint_status_gate", "accepted", "Endpoint concepts are validation-accepted.", list(statuses))


def _relation_blocker_consistency_gate(relation: dict[str, Any]) -> dict[str, Any]:
    blockers = relation.get("blockers", [])
    if not blockers:
        return _gate("blocker_consistency_gate", "requires_human_review", "Relation has no explicit blocker context.", [])
    return _gate("blocker_consistency_gate", "accepted", "Relation blocker context is explicit.", blockers)


def _shared_promotion_relation_gate(domain_model: dict[str, Any]) -> dict[str, Any]:
    if domain_model["semantic_readiness"]["shared_ontology_promotion_status"] == "blocked":
        return _gate("shared_promotion_blocker_gate", "blocked", "Shared ontology promotion remains blocked.", [])
    return _gate("shared_promotion_blocker_gate", "accepted", "Shared ontology promotion is not blocked.", [])


def _result(
    *,
    target_id: str,
    target_type: str,
    label: str | None,
    gates: list[dict[str, Any]],
    evidence_refs: list[str],
    domain_source_refs: list[str],
) -> dict[str, Any]:
    final_status = max((gate["status"] for gate in gates), key=lambda status: OUTCOME_ORDER[status])
    return {
        "id": f"validation_{target_id}",
        "target_id": target_id,
        "target_type": target_type,
        "label": label,
        "final_status": final_status,
        "gate_results": gates,
        "blocking_gates": [
            gate["gate"]
            for gate in gates
            if gate["status"] in {"blocked", "rejected"}
        ],
        "warning_gates": [
            gate["gate"]
            for gate in gates
            if gate["status"] in {"warning", "requires_human_review"}
        ],
        "evidence_refs": evidence_refs,
        "domain_source_refs": domain_source_refs,
    }


def _gate(gate: str, status: str, reason: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "gate": gate,
        "status": status,
        "reason": reason,
        "evidence_refs": [str(ref) for ref in evidence_refs],
    }


def _build_indexes(
    proposals: dict[str, Any],
    domain_model: dict[str, Any],
    evidence: dict[str, Any],
    mapping: dict[str, Any],
) -> dict[str, set[str]]:
    evidence_refs = {
        "live-semantic-proposals.json",
        "live-domain-source-model.json",
        "live-evidence-package.json",
        "live-document-ontology-mapping.json",
    }
    for node in mapping["ontology"]["nodes"]:
        evidence_refs.add(node["id"])
        evidence_refs.update(node.get("evidence_refs", []))
    for relation in mapping["ontology"].get("relations", []):
        evidence_refs.add(relation["id"])
        evidence_refs.update(relation.get("evidence_refs", []))
    for pipeline in evidence["accepted_evidence"].get("pipelines", []):
        evidence_refs.add(pipeline["id"])
    for item in evidence.get("review_queue", []):
        evidence_refs.add(item["id"])
        evidence_refs.update(item.get("evidence_refs", []))
    domain_refs = {item["id"] for item in domain_model.get("general_domain_sources", [])}
    concept_ids = {item["id"] for item in proposals["semantic_concept_proposals"]}
    return {
        "evidence_refs": evidence_refs,
        "domain_source_refs": domain_refs,
        "concept_ids": concept_ids,
    }


def _review_queue(
    proposal_results: list[dict[str, Any]],
    promotion_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    review_items = []
    for result in [*proposal_results, *promotion_results]:
        if result["final_status"] == "accepted":
            continue
        review_items.append(
            {
                "id": f"review_{result['target_id']}",
                "target_id": result["target_id"],
                "target_type": result["target_type"],
                "severity": "high" if result["final_status"] in {"blocked", "rejected"} else "medium",
                "status": result["final_status"],
                "blocking_gates": result["blocking_gates"],
                "required_action": "Resolve listed gate blockers before promotion or graph assembly.",
            }
        )
    return review_items


def _summary(
    proposal_results: list[dict[str, Any]],
    promotion_results: list[dict[str, Any]],
) -> dict[str, Any]:
    counts = Counter(item["final_status"] for item in proposal_results)
    target_counts = Counter(item["target_type"] for item in proposal_results)
    return {
        "proposal_result_count": len(proposal_results),
        "semantic_concept_result_count": target_counts["semantic_concept_proposal"],
        "semantic_relation_result_count": target_counts["semantic_relation_proposal"],
        "accepted_count": counts["accepted"],
        "warning_count": counts["warning"],
        "requires_human_review_count": counts["requires_human_review"],
        "blocked_count": counts["blocked"],
        "rejected_count": counts["rejected"],
        "promotion_gate_count": len(promotion_results),
        "promotion_blocked_count": sum(1 for item in promotion_results if item["final_status"] == "blocked"),
        "accepted_semantic_concept_count": 0,
        "shared_ontology_update_count": 0,
        "validation_status": "blocked_pending_authority_resolution" if counts["blocked"] else "validated_no_shared_promotion",
    }


def _gate_summary(
    proposal_results: list[dict[str, Any]],
    promotion_results: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    summary: dict[str, Counter] = defaultdict(Counter)
    for result in [*proposal_results, *promotion_results]:
        for gate in result["gate_results"]:
            summary[gate["gate"]][gate["status"]] += 1
    return {gate: dict(counts) for gate, counts in sorted(summary.items())}


def _parser_observations(
    proposal_results: list[dict[str, Any]],
    promotion_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blocked_count = sum(1 for item in proposal_results if item["final_status"] == "blocked")
    observations = [
        {
            "level": "info",
            "message": "Semantic proposal validation is deterministic and does not assemble the final graph.",
        }
    ]
    if blocked_count:
        observations.append(
            {
                "level": "warning",
                "message": f"{blocked_count} semantic proposals remain blocked by boundary, source, or formula-result authority gates.",
            }
        )
    if any(item["final_status"] == "blocked" for item in promotion_results):
        observations.append(
            {
                "level": "warning",
                "message": "Shared ontology promotion remains blocked and emits 0 updates.",
            }
        )
    return observations


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def render_google_sheets_semantic_proposal_validation_section(validation: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in validation["summary"].items()
    )
    result_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['target_type'])}</td>"
        f"<td>{_esc(item['final_status'])}</td>"
        f"<td>{_esc(item['label'])}</td>"
        f"<td>{_esc(item['target_id'])}</td>"
        f"<td>{_esc(', '.join(item['blocking_gates']))}</td>"
        "</tr>"
        for item in validation["proposal_results"]
    )
    gate_rows = "".join(
        "<tr>"
        f"<td>{_esc(gate)}</td>"
        f"<td>{_esc(counts)}</td>"
        "</tr>"
        for gate, counts in validation["gate_summary"].items()
    )
    review_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['severity'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['target_id'])}</td>"
        f"<td>{_esc(', '.join(item['blocking_gates']))}</td>"
        "</tr>"
        for item in validation["review_queue"]
    )
    if not review_rows:
        review_rows = '<tr><td colspan="4">No semantic validation review items.</td></tr>'
    return f"""
  <h2>Live Semantic Proposal Validation</h2>
  <section class="grid">{metrics}</section>
  <h2>Semantic Proposal Gate Results</h2>
  <section class="panel"><table><thead><tr><th>Type</th><th>Status</th><th>Label</th><th>Target</th><th>Blocking Gates</th></tr></thead><tbody>{result_rows}</tbody></table></section>
  <h2>Semantic Validation Gate Summary</h2>
  <section class="panel"><table><thead><tr><th>Gate</th><th>Counts</th></tr></thead><tbody>{gate_rows}</tbody></table></section>
  <h2>Semantic Validation Review Queue</h2>
  <section class="panel"><table><thead><tr><th>Severity</th><th>Status</th><th>Target</th><th>Blocking Gates</th></tr></thead><tbody>{review_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministically validate connected Google Sheets semantic proposals."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--access-preflight", type=Path, required=True)
    parser.add_argument("--live-manifest", type=Path, required=True)
    parser.add_argument("--live-view-formula-profile", type=Path, required=True)
    parser.add_argument("--live-block-candidates", type=Path, required=True)
    parser.add_argument("--bounded-window-sample", type=Path, required=True)
    parser.add_argument("--live-block-candidate-tuning", type=Path, required=True)
    parser.add_argument("--live-table-io-pipelines", type=Path, required=True)
    parser.add_argument("--live-cross-validation-plan", type=Path, required=True)
    parser.add_argument("--live-validation-batch-execution", type=Path, required=True)
    parser.add_argument("--live-gate-execution", type=Path, required=True)
    parser.add_argument("--live-evidence-package", type=Path, required=True)
    parser.add_argument("--live-document-ontology-mapping", type=Path, required=True)
    parser.add_argument("--live-action-contracts", type=Path, required=True)
    parser.add_argument("--live-domain-source-model", type=Path, required=True)
    parser.add_argument("--live-semantic-proposals", type=Path, required=True)
    args = parser.parse_args()

    validation = build_google_sheets_semantic_proposal_validation(
        live_semantic_proposals_path=args.live_semantic_proposals,
        live_domain_source_model_path=args.live_domain_source_model,
        live_evidence_package_path=args.live_evidence_package,
        live_document_ontology_mapping_path=args.live_document_ontology_mapping,
    )
    write_google_sheets_semantic_proposal_validation_package(
        out_dir=args.out_dir,
        access_preflight_path=args.access_preflight,
        live_manifest_path=args.live_manifest,
        live_view_formula_profile_path=args.live_view_formula_profile,
        live_block_candidates_path=args.live_block_candidates,
        bounded_window_sample_path=args.bounded_window_sample,
        live_block_candidate_tuning_path=args.live_block_candidate_tuning,
        live_table_io_pipelines_path=args.live_table_io_pipelines,
        live_cross_validation_plan_path=args.live_cross_validation_plan,
        live_validation_batch_execution_path=args.live_validation_batch_execution,
        live_gate_execution_path=args.live_gate_execution,
        live_evidence_package_path=args.live_evidence_package,
        live_document_ontology_mapping_path=args.live_document_ontology_mapping,
        live_action_contracts_path=args.live_action_contracts,
        live_domain_source_model_path=args.live_domain_source_model,
        live_semantic_proposals_path=args.live_semantic_proposals,
        semantic_proposal_validation=validation,
    )


if __name__ == "__main__":
    main()
