from __future__ import annotations

import argparse
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_semantic_proposals(
    *,
    live_domain_source_model_path: Path,
    live_evidence_package_path: Path,
    live_document_ontology_mapping_path: Path,
) -> dict[str, Any]:
    live_domain_source_model_path = live_domain_source_model_path.expanduser().resolve()
    live_evidence_package_path = live_evidence_package_path.expanduser().resolve()
    live_document_ontology_mapping_path = live_document_ontology_mapping_path.expanduser().resolve()
    domain_model = _read_json(live_domain_source_model_path)
    evidence = _read_json(live_evidence_package_path)
    mapping = _read_json(live_document_ontology_mapping_path)
    proposals = _concept_proposals(evidence, domain_model, mapping)
    relations = _relation_proposals(proposals)
    validation_plan = _validation_plan(proposals, relations, domain_model)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": evidence["source"]["spreadsheet_id"],
            "spreadsheet_url": evidence["source"].get("spreadsheet_url"),
            "title": evidence["source"]["title"],
            "source_artifacts": {
                "live_domain_source_model": str(live_domain_source_model_path),
                "live_evidence_package": str(live_evidence_package_path),
                "live_document_ontology_mapping": str(live_document_ontology_mapping_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "proposal_status": "proposal_only_not_accepted",
            "shared_ontology_updates": 0,
            "semantic_generation_scope": domain_model["semantic_readiness"]["semantic_proposal_scope"],
            "formula_result_authority": "not_established",
        },
        "semantic_concept_proposals": proposals,
        "semantic_relation_proposals": relations,
        "validation_plan": validation_plan,
        "summary": _summary(proposals, relations, validation_plan),
        "parser_observations": _parser_observations(domain_model, proposals),
    }


def write_google_sheets_semantic_proposals_package(
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
    semantic_proposals: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    proposals_path = out_dir / "live-semantic-proposals.json"
    proposals_path.write_text(
        json.dumps(semantic_proposals, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    access_preflight = _read_json(access_preflight_path)
    manifest = _read_json(live_manifest_path)
    view_formula_profile = _read_json(live_view_formula_profile_path)
    block_candidates = _read_json(live_block_candidates_path)
    bounded_sample = _read_json(bounded_window_sample_path)
    tuning = _read_json(live_block_candidate_tuning_path)
    table_io = _read_json(live_table_io_pipelines_path)
    cross_validation_plan = _read_json(live_cross_validation_plan_path)
    validation_batch = _read_json(live_validation_batch_execution_path)
    gate_execution = _read_json(live_gate_execution_path)
    evidence_package = _read_json(live_evidence_package_path)
    ontology_mapping = _read_json(live_document_ontology_mapping_path)
    action_contracts = _read_json(live_action_contracts_path)
    domain_model = _read_json(live_domain_source_model_path)
    (out_dir / "index.html").write_text(
        render_live_manifest_html(
            access_preflight=access_preflight,
            manifest=manifest,
            live_view_formula_profile=view_formula_profile,
            live_block_candidates=block_candidates,
            live_bounded_window_sample=bounded_sample,
            live_block_candidate_tuning=tuning,
            live_table_io_pipelines=table_io,
            live_cross_validation_plan=cross_validation_plan,
            live_validation_batch_execution=validation_batch,
            live_gate_execution=gate_execution,
            live_evidence_package=evidence_package,
            live_document_ontology_mapping=ontology_mapping,
            live_action_contracts=action_contracts,
            live_domain_source_model=domain_model,
            live_semantic_proposals=semantic_proposals,
        ),
        encoding="utf-8",
    )


def _concept_proposals(
    evidence: dict[str, Any],
    domain_model: dict[str, Any],
    mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    proposals = []
    accepted_pipelines = evidence["accepted_evidence"]["pipelines"]
    accepted_pipeline_nodes = _accepted_calculation_pipeline_nodes(mapping)
    if accepted_pipelines or accepted_pipeline_nodes:
        proposals.append(
            {
                "id": "proposal_period_tab_calculation_surface",
                "type": "semantic_concept_proposal",
                "status": "proposed",
                "domain_layer": "local_domain",
                "label": "period-tab calculation surface",
                "description": "Accepted document-structure calculation nodes and internal formula surfaces that appear to calculate within period-labeled tabs.",
                "source_evidence_refs": [
                    *[node["id"] for node in accepted_pipeline_nodes],
                    *[pipeline["id"] for pipeline in accepted_pipelines],
                ],
                "domain_source_refs": [],
                "shared_promotion_status": "blocked",
                "blockers": _shared_blockers(domain_model),
            }
        )
    if any("revenue_recognition" in item.get("applicability", []) for item in domain_model["general_domain_sources"]):
        proposals.append(
            {
                "id": "proposal_revenue_recognition_context_reference",
                "type": "semantic_concept_proposal",
                "status": "proposed",
                "domain_layer": "general_domain_reference",
                "label": "revenue recognition context reference",
                "description": "General accounting/K-IFRS revenue recognition references may be relevant to workbook revenue labels, but workbook formula-result authority is not established.",
                "source_evidence_refs": ["live-domain-source-model.json"],
                "domain_source_refs": [
                    item["id"]
                    for item in domain_model["general_domain_sources"]
                    if "revenue_recognition" in item.get("applicability", [])
                ],
                "shared_promotion_status": "blocked",
                "blockers": _shared_blockers(domain_model),
            }
        )
    if evidence["review_queue"]:
        proposals.append(
            {
                "id": "proposal_source_authority_blocker_context",
                "type": "semantic_concept_proposal",
                "status": "proposed",
                "domain_layer": "process_semantic",
                "label": "source authority blocker context",
                "description": "External source and formula-result blockers materially constrain semantic interpretation of FC_DATA-dependent report flows.",
                "source_evidence_refs": [item["id"] for item in evidence["review_queue"]],
                "domain_source_refs": [],
                "shared_promotion_status": "blocked",
                "blockers": _shared_blockers(domain_model),
            }
        )
    return proposals


def _accepted_calculation_pipeline_nodes(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        node
        for node in mapping["ontology"]["nodes"]
        if node.get("status") == "accepted" and node.get("type") == "calculation_pipeline"
    ]


def _relation_proposals(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relations = []
    ids = {proposal["id"] for proposal in proposals}
    if {
        "proposal_period_tab_calculation_surface",
        "proposal_revenue_recognition_context_reference",
    } <= ids:
        relations.append(
            {
                "id": "rel_period_surface_may_use_revenue_context",
                "type": "semantic_relation_proposal",
                "status": "proposed",
                "relation_type": "may_be_interpreted_with_general_domain_reference",
                "from": "proposal_period_tab_calculation_surface",
                "to": "proposal_revenue_recognition_context_reference",
                "source_evidence_refs": ["live-evidence-package.json", "live-domain-source-model.json"],
                "blockers": ["formula_result_authority_not_established"],
            }
        )
    if {
        "proposal_source_authority_blocker_context",
        "proposal_revenue_recognition_context_reference",
    } <= ids:
        relations.append(
            {
                "id": "rel_source_blocker_limits_revenue_context",
                "type": "semantic_relation_proposal",
                "status": "proposed",
                "relation_type": "blocks_confident_domain_interpretation",
                "from": "proposal_source_authority_blocker_context",
                "to": "proposal_revenue_recognition_context_reference",
                "source_evidence_refs": ["live-action-contracts.json"],
                "blockers": ["source_authority_not_established"],
            }
        )
    return relations


def _validation_plan(
    proposals: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    domain_model: dict[str, Any],
) -> list[dict[str, Any]]:
    items = []
    for proposal in proposals:
        items.append(
            {
                "id": f"validate_{proposal['id']}",
                "target_id": proposal["id"],
                "target_type": "semantic_concept_proposal",
                "required_gates": [
                    "source_trace_gate",
                    "local_boundary_gate",
                    "shared_promotion_blocker_gate",
                ],
                "status": "pending_validation",
            }
        )
    for relation in relations:
        items.append(
            {
                "id": f"validate_{relation['id']}",
                "target_id": relation["id"],
                "target_type": "semantic_relation_proposal",
                "required_gates": [
                    "source_trace_gate",
                    "relation_endpoint_gate",
                    "blocker_consistency_gate",
                ],
                "status": "pending_validation",
            }
        )
    if domain_model["semantic_readiness"]["shared_ontology_promotion_status"] == "blocked":
        items.append(
            {
                "id": "validate_shared_promotion_blocked",
                "target_id": "shared_ontology_promotion",
                "target_type": "promotion_gate",
                "required_gates": ["human_review_gate", "local_boundary_gate", "source_authority_gate"],
                "status": "blocked",
            }
        )
    return items


def _shared_blockers(domain_model: dict[str, Any]) -> list[str]:
    blockers = ["shared_promotion_blocked"]
    if not domain_model["semantic_readiness"]["local_boundary_confirmed"]:
        blockers.append("local_boundary_not_confirmed")
    if domain_model["semantic_readiness"]["unavailable_source_count"]:
        blockers.append("source_authority_unavailable")
    return blockers


def _summary(
    proposals: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    validation_plan: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "semantic_concept_proposal_count": len(proposals),
        "semantic_relation_proposal_count": len(relations),
        "validation_plan_count": len(validation_plan),
        "accepted_semantic_concept_count": 0,
        "shared_ontology_update_count": 0,
        "proposal_status": "proposal_only_not_accepted",
    }


def _parser_observations(domain_model: dict[str, Any], proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Semantic candidates are proposal-only and require deterministic validation before acceptance.",
        }
    ]
    if domain_model["semantic_readiness"]["shared_ontology_promotion_status"] == "blocked":
        observations.append(
            {
                "level": "warning",
                "message": "Shared ontology promotion remains blocked by local boundary, source authority, repeated evidence, or formula-result authority gaps.",
            }
        )
    if not proposals:
        observations.append(
            {
                "level": "warning",
                "message": "No semantic proposals were generated from accepted evidence.",
            }
        )
    return observations


def _slug(value: Any) -> str:
    text = str(value or "none")
    text = re.sub(r"[^A-Za-z0-9가-힣]+", "_", text).strip("_").lower()
    return text or "none"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def render_google_sheets_semantic_proposals_section(proposals: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in proposals["summary"].items()
    )
    concept_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['domain_layer'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['label'])}</td>"
        f"<td>{_esc(', '.join(item['blockers']))}</td>"
        "</tr>"
        for item in proposals["semantic_concept_proposals"]
    )
    relation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['relation_type'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['from'])}</td>"
        f"<td>{_esc(item['to'])}</td>"
        "</tr>"
        for item in proposals["semantic_relation_proposals"]
    )
    if not relation_rows:
        relation_rows = '<tr><td colspan="4">No semantic relation proposals.</td></tr>'
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in proposals["parser_observations"]
    )
    return f"""
  <h2>Live Semantic Proposals</h2>
  <section class="grid">{metrics}</section>
  <h2>Semantic Concept Proposals</h2>
  <section class="panel"><table><thead><tr><th>Layer</th><th>Status</th><th>Label</th><th>Blockers</th></tr></thead><tbody>{concept_rows}</tbody></table></section>
  <h2>Semantic Relation Proposals</h2>
  <section class="panel"><table><thead><tr><th>Relation</th><th>Status</th><th>From</th><th>To</th></tr></thead><tbody>{relation_rows}</tbody></table></section>
  <h2>Semantic Proposal Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate proposal-only semantic candidates for connected Google Sheets evidence."
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
    args = parser.parse_args()

    proposals = build_google_sheets_semantic_proposals(
        live_domain_source_model_path=args.live_domain_source_model,
        live_evidence_package_path=args.live_evidence_package,
        live_document_ontology_mapping_path=args.live_document_ontology_mapping,
    )
    write_google_sheets_semantic_proposals_package(
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
        semantic_proposals=proposals,
    )


if __name__ == "__main__":
    main()
