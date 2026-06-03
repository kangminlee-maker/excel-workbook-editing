from __future__ import annotations

import argparse
import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_local_semantic_candidates(
    *,
    live_data_view_projection_path: Path,
    live_semantic_proposal_validation_path: Path,
    live_domain_source_model_path: Path,
) -> dict[str, Any]:
    live_data_view_projection_path = live_data_view_projection_path.expanduser().resolve()
    live_semantic_proposal_validation_path = live_semantic_proposal_validation_path.expanduser().resolve()
    live_domain_source_model_path = live_domain_source_model_path.expanduser().resolve()

    projection = _read_json(live_data_view_projection_path)
    validation = _read_json(live_semantic_proposal_validation_path)
    domain_model = _read_json(live_domain_source_model_path)
    concept_validation = {
        item["target_id"]: item
        for item in validation["proposal_results"]
        if item["target_type"] == "semantic_concept_proposal"
    }
    umbrella = concept_validation.get("proposal_period_tab_calculation_surface")
    candidates = [
        _candidate_from_projection(item, umbrella, domain_model)
        for item in projection["data_view_projections"]
        if item["projection_kind"] == "calculation_pipeline_projection"
    ]
    relations = _candidate_relations(candidates)
    review_queue = _review_queue(candidates, validation, domain_model)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": projection["source"]["spreadsheet_id"],
            "spreadsheet_url": projection["source"].get("spreadsheet_url"),
            "title": projection["source"]["title"],
            "source_artifacts": {
                "live_data_view_projection": str(live_data_view_projection_path),
                "live_semantic_proposal_validation": str(live_semantic_proposal_validation_path),
                "live_domain_source_model": str(live_domain_source_model_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "candidate_status": "boundary_scoped_candidates_only",
            "accepted_local_semantic_candidates": 0,
            "shared_ontology_updates": 0,
            "formula_result_authority": "not_established",
            "local_boundary_confirmed": domain_model["semantic_readiness"]["local_boundary_confirmed"],
        },
        "method": {
            "name": "connected_sheets_local_semantic_candidate_generation",
            "authority": "local_candidates_not_accepted_or_shared",
            "decision_policy": (
                "Generate boundary-scoped local semantic candidate records from accepted data-view "
                "projections and semantic validation blockers. Do not accept candidates, resolve "
                "local boundary, recalculate formulas, or promote shared ontology updates."
            ),
        },
        "local_semantic_candidates": candidates,
        "candidate_relations": relations,
        "review_queue": review_queue,
        "summary": _summary(candidates, relations, review_queue, domain_model),
        "parser_observations": _parser_observations(candidates, domain_model),
    }


def write_google_sheets_local_semantic_candidates_package(
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
    live_validated_document_graph_path: Path,
    live_data_view_projection_path: Path,
    local_semantic_candidates: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = out_dir / "live-local-semantic-candidates.json"
    candidates_path.write_text(
        json.dumps(local_semantic_candidates, ensure_ascii=False, indent=2) + "\n",
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
            live_validated_document_graph=_read_json(live_validated_document_graph_path),
            live_data_view_projection=_read_json(live_data_view_projection_path),
            live_local_semantic_candidates=local_semantic_candidates,
        ),
        encoding="utf-8",
    )


def _candidate_from_projection(
    projection: dict[str, Any],
    umbrella_validation: dict[str, Any] | None,
    domain_model: dict[str, Any],
) -> dict[str, Any]:
    blockers = [
        "local_boundary_not_confirmed",
        "source_authority_unavailable",
        "formula_result_authority_not_established",
    ]
    if umbrella_validation:
        blockers.extend(umbrella_validation.get("blocking_gates", []))
    return {
        "id": f"local_candidate_{projection['pipeline_id']}",
        "type": "local_semantic_candidate",
        "status": "blocked",
        "label": projection["label"],
        "candidate_kind": "period_tab_calculation_surface",
        "boundary_scope": domain_model["local_domain_boundary"]["boundary_label"],
        "boundary_status": domain_model["local_domain_boundary"]["boundary_status"],
        "projection_id": projection["id"],
        "pipeline_id": projection["pipeline_id"],
        "sheet": projection["sheet"],
        "range": projection["range"],
        "properties": {
            "role": projection["role"],
            "input_refs": projection["input_refs"],
            "output_refs": projection["output_refs"],
            "transform_summary": projection["transform_summary"],
            "preview_status": projection["preview"]["status"],
            "sampled_formula_cell_count": projection["preview"]["sampled_formula_cell_count"],
        },
        "blockers": _unique(blockers),
        "shared_promotion_status": "blocked",
        "evidence_refs": projection["evidence_refs"],
        "required_evidence": [
            "local_boundary_confirmation",
            "source_spreadsheet_authority",
            "formula_result_authority",
            "repeated_workbook_family_evidence",
            "human_review_approval",
        ],
    }


def _candidate_relations(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relations = []
    sorted_candidates = sorted(candidates, key=lambda item: item["sheet"] or "")
    for before, after in zip(sorted_candidates, sorted_candidates[1:]):
        relations.append(
            {
                "id": f"rel_{before['id']}_same_family_{after['id']}",
                "type": "local_semantic_candidate_relation",
                "status": "blocked",
                "relation_type": "same_repeated_formula_family_candidate",
                "from": before["id"],
                "to": after["id"],
                "blockers": [
                    "formula_result_authority_not_established",
                    "local_boundary_not_confirmed",
                ],
                "evidence_refs": _unique([*before["evidence_refs"], *after["evidence_refs"]]),
            }
        )
    return relations


def _review_queue(
    candidates: list[dict[str, Any]],
    validation: dict[str, Any],
    domain_model: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "id": f"review_{candidate['id']}",
            "target_id": candidate["id"],
            "severity": "high",
            "status": "blocked",
            "blocking_gates": candidate["blockers"],
            "required_action": "Confirm local boundary, source authority, formula-result authority, repeated evidence, and human review before accepting or promoting.",
        }
        for candidate in candidates
    ] + [
        {
            "id": "review_shared_promotion_blocked",
            "target_id": "shared_ontology_promotion",
            "severity": "high",
            "status": domain_model["semantic_readiness"]["shared_ontology_promotion_status"],
            "blocking_gates": [
                "local_boundary_gate",
                "source_authority_gate",
                "formula_result_authority_gate",
                "human_review_gate",
            ],
            "required_action": "Resolve promotion gates before any shared ontology update.",
        },
        {
            "id": "review_semantic_validation_carry_forward",
            "target_id": "semantic_validation_review_queue",
            "severity": "high",
            "status": "blocked",
            "blocking_gates": [
                item["target_id"]
                for item in validation.get("review_queue", [])
                if item.get("status") == "blocked"
            ],
            "required_action": "Resolve semantic validation review queue before accepting local semantic candidates.",
        },
    ]


def _summary(
    candidates: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
    domain_model: dict[str, Any],
) -> dict[str, Any]:
    return {
        "local_semantic_candidate_count": len(candidates),
        "accepted_local_semantic_candidate_count": 0,
        "blocked_local_semantic_candidate_count": len(candidates),
        "candidate_relation_count": len(relations),
        "blocked_candidate_relation_count": len(relations),
        "review_queue_count": len(review_queue),
        "local_boundary_confirmed": domain_model["semantic_readiness"]["local_boundary_confirmed"],
        "shared_ontology_update_count": 0,
        "candidate_status": "blocked_boundary_scoped_candidates_only",
    }


def _parser_observations(candidates: list[dict[str, Any]], domain_model: dict[str, Any]) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Local semantic candidates are generated as blocked boundary-scoped records only.",
        }
    ]
    if not domain_model["semantic_readiness"]["local_boundary_confirmed"]:
        observations.append(
            {
                "level": "warning",
                "message": "Local boundary is not confirmed; candidates cannot be accepted.",
            }
        )
    if candidates:
        observations.append(
            {
                "level": "warning",
                "message": "Formula-result and source authority blockers still apply to local candidates.",
            }
        )
    return observations


def _unique(values: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def render_google_sheets_local_semantic_candidates_section(candidates: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in candidates["summary"].items()
    )
    rows = "".join(
        "<tr>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['label'])}</td>"
        f"<td>{_esc(item['sheet'])}</td>"
        f"<td>{_esc(item['range'])}</td>"
        f"<td>{_esc(', '.join(item['blockers']))}</td>"
        "</tr>"
        for item in candidates["local_semantic_candidates"]
    )
    review_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['severity'])}</td>"
        f"<td>{_esc(item['target_id'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(', '.join(item['blocking_gates']))}</td>"
        "</tr>"
        for item in candidates["review_queue"]
    )
    return f"""
  <h2>Live Local Semantic Candidates</h2>
  <section class="grid">{metrics}</section>
  <h2>Boundary-Scoped Local Candidates</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Label</th><th>Sheet</th><th>Range</th><th>Blockers</th></tr></thead><tbody>{rows}</tbody></table></section>
  <h2>Local Candidate Review Queue</h2>
  <section class="panel"><table><thead><tr><th>Severity</th><th>Target</th><th>Status</th><th>Blocking Gates</th></tr></thead><tbody>{review_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate blocked boundary-scoped local semantic candidates for connected Google Sheets."
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
    parser.add_argument("--live-validated-document-graph", type=Path, required=True)
    parser.add_argument("--live-data-view-projection", type=Path, required=True)
    args = parser.parse_args()

    candidates = build_google_sheets_local_semantic_candidates(
        live_data_view_projection_path=args.live_data_view_projection,
        live_semantic_proposal_validation_path=args.live_semantic_proposal_validation,
        live_domain_source_model_path=args.live_domain_source_model,
    )
    write_google_sheets_local_semantic_candidates_package(
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
        live_validated_document_graph_path=args.live_validated_document_graph,
        live_data_view_projection_path=args.live_data_view_projection,
        local_semantic_candidates=candidates,
    )


if __name__ == "__main__":
    main()
