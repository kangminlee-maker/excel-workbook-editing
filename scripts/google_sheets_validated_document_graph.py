from __future__ import annotations

import argparse
import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_validated_document_graph(
    *,
    live_document_ontology_mapping_path: Path,
    live_evidence_package_path: Path,
    live_action_contracts_path: Path,
    live_semantic_proposal_validation_path: Path,
) -> dict[str, Any]:
    live_document_ontology_mapping_path = live_document_ontology_mapping_path.expanduser().resolve()
    live_evidence_package_path = live_evidence_package_path.expanduser().resolve()
    live_action_contracts_path = live_action_contracts_path.expanduser().resolve()
    live_semantic_proposal_validation_path = live_semantic_proposal_validation_path.expanduser().resolve()

    mapping = _read_json(live_document_ontology_mapping_path)
    evidence = _read_json(live_evidence_package_path)
    actions = _read_json(live_action_contracts_path)
    semantic_validation = _read_json(live_semantic_proposal_validation_path)

    accepted_nodes = [
        _graph_node(node)
        for node in mapping["ontology"]["nodes"]
        if node.get("status") == "accepted"
    ]
    accepted_node_ids = {node["id"] for node in accepted_nodes}
    accepted_relations = [
        _graph_relation(relation)
        for relation in mapping["ontology"].get("relations", [])
        if relation.get("status") == "accepted"
        and relation.get("from") in accepted_node_ids
        and relation.get("to") in accepted_node_ids
    ]
    semantic_results = semantic_validation["proposal_results"]
    accepted_semantic_results = [
        item for item in semantic_results if item["final_status"] == "accepted"
    ]
    carry_forward = _carry_forward(mapping, actions, semantic_validation)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": mapping["source"]["spreadsheet_id"],
            "spreadsheet_url": mapping["source"].get("spreadsheet_url"),
            "title": mapping["source"]["title"],
            "source_artifacts": {
                "live_document_ontology_mapping": str(live_document_ontology_mapping_path),
                "live_evidence_package": str(live_evidence_package_path),
                "live_action_contracts": str(live_action_contracts_path),
                "live_semantic_proposal_validation": str(live_semantic_proposal_validation_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "graph_status": "accepted_document_structure_only",
            "semantic_graph_promotion": "not_performed",
            "accepted_semantic_concepts": 0,
            "shared_ontology_updates": 0,
            "formula_result_authority": "not_established",
        },
        "method": {
            "name": "connected_sheets_validated_graph_assembly",
            "authority": "accepted_graph_projection_with_carry_forward_review_queue",
            "decision_policy": (
                "Assemble only accepted document-structure ontology nodes, accepted document "
                "relations, and accepted deterministic evidence into the graph body. Blocked "
                "semantic proposal validation results remain carry-forward review items."
            ),
        },
        "graph": {
            "nodes": accepted_nodes,
            "relations": accepted_relations,
            "semantic_nodes": [],
            "semantic_relations": [],
            "data_views": [],
        },
        "carry_forward": carry_forward,
        "summary": _summary(
            accepted_nodes=accepted_nodes,
            accepted_relations=accepted_relations,
            accepted_semantic_results=accepted_semantic_results,
            carry_forward=carry_forward,
            evidence=evidence,
            semantic_validation=semantic_validation,
        ),
        "parser_observations": _parser_observations(carry_forward, semantic_validation),
    }


def write_google_sheets_validated_document_graph_package(
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
    live_semantic_proposal_validation_path: Path,
    validated_graph: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    graph_path = out_dir / "live-validated-document-graph.json"
    graph_path.write_text(
        json.dumps(validated_graph, ensure_ascii=False, indent=2) + "\n",
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
            live_semantic_proposal_validation=_read_json(live_semantic_proposal_validation_path),
            live_validated_document_graph=validated_graph,
        ),
        encoding="utf-8",
    )


def _graph_node(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node["id"],
        "type": node["type"],
        "ontology_class": _ontology_class(node["type"]),
        "status": "accepted",
        "label": node.get("label"),
        "properties": node.get("properties", {}),
        "evidence_refs": node.get("evidence_refs", []),
        "source_artifact_refs": ["live-document-ontology-mapping", "live-evidence-package"],
    }


def _graph_relation(relation: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": relation["id"],
        "type": relation["type"],
        "from": relation["from"],
        "to": relation["to"],
        "status": "accepted",
        "properties": {},
        "evidence_refs": relation.get("evidence_refs", []),
        "source_artifact_refs": ["live-document-ontology-mapping"],
    }


def _ontology_class(node_type: str) -> str:
    return {
        "workbook_document": "WorkbookDocument",
        "accepted_evidence_body": "EvidenceBody",
        "calculation_pipeline": "CalculationPipeline",
    }.get(node_type, "DocumentNode")


def _carry_forward(
    mapping: dict[str, Any],
    actions: dict[str, Any],
    semantic_validation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "document_review_queue": [
            {
                "id": item.get("id"),
                "status": item.get("status"),
                "target_node_id": item.get("target_node_id"),
                "reason": item.get("reason") or item.get("type"),
                "evidence_refs": item.get("evidence_refs", []),
            }
            for item in mapping["ontology"].get("review_items", [])
        ],
        "semantic_validation_review_queue": semantic_validation.get("review_queue", []),
        "action_contract_summary": actions.get("summary", {}),
        "promotion_gate_results": semantic_validation.get("promotion_gate_results", []),
    }


def _summary(
    *,
    accepted_nodes: list[dict[str, Any]],
    accepted_relations: list[dict[str, Any]],
    accepted_semantic_results: list[dict[str, Any]],
    carry_forward: dict[str, Any],
    evidence: dict[str, Any],
    semantic_validation: dict[str, Any],
) -> dict[str, Any]:
    document_review_queue_count = len(carry_forward["document_review_queue"])
    semantic_review_queue_count = len(carry_forward["semantic_validation_review_queue"])
    return {
        "graph_node_count": len(accepted_nodes),
        "document_node_count": len(accepted_nodes),
        "semantic_node_count": 0,
        "graph_relation_count": len(accepted_relations),
        "document_relation_count": len(accepted_relations),
        "semantic_relation_count": 0,
        "data_view_count": 0,
        "document_review_queue_count": document_review_queue_count,
        "semantic_review_queue_count": semantic_review_queue_count,
        "accepted_semantic_proposal_result_count": len(accepted_semantic_results),
        "blocked_semantic_proposal_result_count": semantic_validation["summary"]["blocked_count"],
        "accepted_gate_count": evidence["summary"]["accepted_gate_count"],
        "accepted_pipeline_count": evidence["summary"]["accepted_pipeline_count"],
        "shared_ontology_update_count": 0,
        "graph_status": "assembled_with_carry_forward_review_queue",
    }


def _parser_observations(
    carry_forward: dict[str, Any],
    semantic_validation: dict[str, Any],
) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Validated graph assembly promotes accepted document-structure evidence only.",
        }
    ]
    if semantic_validation["summary"]["blocked_count"]:
        observations.append(
            {
                "level": "warning",
                "message": "Blocked semantic validation results were carried forward instead of promoted.",
            }
        )
    if carry_forward["document_review_queue"]:
        observations.append(
            {
                "level": "warning",
                "message": f"{len(carry_forward['document_review_queue'])} document review items remain open.",
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


def render_google_sheets_validated_document_graph_section(graph: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in graph["summary"].items()
    )
    node_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['type'])}</td>"
        f"<td>{_esc(item['label'])}</td>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(', '.join(item['evidence_refs']))}</td>"
        "</tr>"
        for item in graph["graph"]["nodes"]
    )
    review_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['target_id'])}</td>"
        f"<td>{_esc(item['target_type'])}</td>"
        f"<td>{_esc(', '.join(item.get('blocking_gates', [])))}</td>"
        "</tr>"
        for item in graph["carry_forward"]["semantic_validation_review_queue"]
    )
    if not review_rows:
        review_rows = '<tr><td colspan="4">No semantic carry-forward review items.</td></tr>'
    return f"""
  <h2>Live Validated Document Graph</h2>
  <section class="grid">{metrics}</section>
  <h2>Accepted Graph Nodes</h2>
  <section class="panel"><table><thead><tr><th>Type</th><th>Label</th><th>ID</th><th>Evidence</th></tr></thead><tbody>{node_rows}</tbody></table></section>
  <h2>Semantic Carry-Forward Queue</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Target</th><th>Type</th><th>Blocking Gates</th></tr></thead><tbody>{review_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble a validated connected Google Sheets document graph."
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
    parser.add_argument("--live-semantic-proposal-validation", type=Path, required=True)
    args = parser.parse_args()

    graph = build_google_sheets_validated_document_graph(
        live_document_ontology_mapping_path=args.live_document_ontology_mapping,
        live_evidence_package_path=args.live_evidence_package,
        live_action_contracts_path=args.live_action_contracts,
        live_semantic_proposal_validation_path=args.live_semantic_proposal_validation,
    )
    write_google_sheets_validated_document_graph_package(
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
        live_semantic_proposal_validation_path=args.live_semantic_proposal_validation,
        validated_graph=graph,
    )


if __name__ == "__main__":
    main()
