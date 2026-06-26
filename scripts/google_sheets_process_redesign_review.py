from __future__ import annotations

import argparse
import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_process_redesign_review(
    *,
    live_inspection_dir: Path,
    process_ledger_path: Path,
    tasklist_path: Path,
    design_path: Path,
) -> dict[str, Any]:
    live_inspection_dir = live_inspection_dir.expanduser().resolve()
    process_ledger_path = process_ledger_path.expanduser().resolve()
    tasklist_path = tasklist_path.expanduser().resolve()
    design_path = design_path.expanduser().resolve()
    artifacts = sorted(path.name for path in live_inspection_dir.glob("*.json"))
    ledger_entries = _read_ledger(process_ledger_path)
    google_entries = [entry for entry in ledger_entries if str(entry.get("stage", "")).startswith("google_sheets")]
    stage_reviews = _stage_reviews()
    decisions = _redesign_decisions()
    gaps = _open_evidence_gaps()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "live_inspection_dir": str(live_inspection_dir),
            "source_artifacts": {
                "process_ledger": str(process_ledger_path),
                "tasklist": str(tasklist_path),
                "design": str(design_path),
            },
        },
        "authority": {
            "review_status": "process_redesign_review_completed",
            "parser_truth": "no_new_parser_claims",
            "shared_ontology_updates": 0,
        },
        "method": {
            "name": "connected_sheets_process_redesign_review",
            "authority": "process_recommendation_not_parser_truth",
            "decision_policy": (
                "Review generated connected-Sheets artifacts, stage ledger entries, active tasklist, "
                "design baseline, schemas, tests, and viewer behavior to recommend process changes. "
                "Recommendations do not alter parser truth until validated in a later iteration."
            ),
        },
        "stage_reviews": stage_reviews,
        "redesign_decisions": decisions,
        "open_evidence_gaps": gaps,
        "summary": {
            "json_artifact_count": len(artifacts),
            "google_sheets_ledger_entry_count": len(google_entries),
            "stage_review_count": len(stage_reviews),
            "redesign_decision_count": len(decisions),
            "open_evidence_gap_count": len(gaps),
            "shared_ontology_update_count": 0,
            "review_status": "process_redesign_review_completed",
        },
        "parser_observations": [
            {
                "level": "info",
                "message": "Connected-Sheets parser stages now run end-to-end through process redesign review.",
            },
            {
                "level": "warning",
                "message": "Source authority, formula-result authority, local boundary, and repeated workbook-family evidence remain the dominant blockers.",
            },
        ],
    }


def write_google_sheets_process_redesign_review_package(
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
    live_local_semantic_candidates_path: Path,
    live_shared_ontology_alignment_review_path: Path,
    process_redesign_review: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    review_path = out_dir / "live-process-redesign-review.json"
    review_path.write_text(
        json.dumps(process_redesign_review, ensure_ascii=False, indent=2) + "\n",
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
            live_local_semantic_candidates=_read_json(live_local_semantic_candidates_path),
            live_shared_ontology_alignment_review=_read_json(live_shared_ontology_alignment_review_path),
            live_process_redesign_review=process_redesign_review,
        ),
        encoding="utf-8",
    )


def _stage_reviews() -> list[dict[str, Any]]:
    return [
        {
            "stage_group": "access_and_manifest",
            "recommendation": "keep",
            "reason": "Source access identity, metadata, view-state, and permission boundaries must be known before parsing.",
        },
        {
            "stage_group": "bounded_sampling_and_tuning",
            "recommendation": "keep_as_loop",
            "reason": "Bounded read candidates, samples, and tuning should iterate until high-priority coverage is sufficient.",
        },
        {
            "stage_group": "pipeline_and_gate_execution",
            "recommendation": "keep_split",
            "reason": "Plan and execution separation made unauthorized source reads visible before live calls were made.",
        },
        {
            "stage_group": "evidence_to_graph",
            "recommendation": "keep",
            "reason": "Evidence package, document ontology mapping, action contracts, and validated graph assembly prevented semantic over-promotion.",
        },
        {
            "stage_group": "semantic_generation",
            "recommendation": "keep_but_batch_when_no_human_review",
            "reason": "Proposal generation and validation can remain separate artifacts, but may be run as one batch when no human review happens between them.",
        },
        {
            "stage_group": "shared_alignment",
            "recommendation": "review_only_until_authority_resolved",
            "reason": "Shared promotion is blocked until local boundary, source authority, formula-result authority, repeated evidence, and human approval exist.",
        },
    ]


def _redesign_decisions() -> list[dict[str, Any]]:
    return [
        {
            "id": "decision_source_authority_earlier",
            "decision": "Move external source authority resolution earlier when IMPORTRANGE blockers appear.",
            "effect": "Avoid spending later semantic stages on candidates that are predictably blocked by the same source gap.",
        },
        {
            "id": "decision_formula_result_authority_gate",
            "decision": "Add a dedicated formula-result authority checkpoint before semantic acceptance.",
            "effect": "Formula text can still drive structural dataflow, but semantic acceptance waits for result authority.",
        },
        {
            "id": "decision_projection_before_human_review",
            "decision": "Keep data view projection before shared alignment review.",
            "effect": "Reviewers can see concrete projected surfaces before answering boundary and promotion questions.",
        },
        {
            "id": "decision_permission_contract_as_stage",
            "decision": "Treat source access policy and Google ACL requirements as process inputs, not incidental failures.",
            "effect": "Missing operations stop the process explicitly instead of encouraging workaround extraction paths.",
        },
        {
            "id": "decision_html_layout_gate",
            "decision": "Run HTML layout/overflow checks for dense review sections before reviewer handoff.",
            "effect": "Schema-valid sections remain human-readable.",
        },
    ]


def _open_evidence_gaps() -> list[dict[str, Any]]:
    return [
        {"id": "gap_external_source_authority", "priority": "high", "description": "FC_DATA IMPORTRANGE source ACL and source access evidence are still needed."},
        {"id": "gap_formula_result_authority", "priority": "high", "description": "Formula-result authority is not established for projected calculation surfaces."},
        {"id": "gap_local_boundary", "priority": "high", "description": "Organization/project/team/workbook-family boundary is not confirmed."},
        {"id": "gap_repeated_workbook_family", "priority": "medium", "description": "Repeated workbook-family evidence is not yet available for shared promotion."},
        {"id": "gap_reporting_basis", "priority": "medium", "description": "Revenue/profit reporting basis and aggregation rule require human decision."},
        {"id": "gap_remaining_bounded_reads", "priority": "medium", "description": "Remaining bounded read candidates still limit full coverage."},
    ]


def _read_ledger(path: Path) -> list[dict[str, Any]]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def render_google_sheets_process_redesign_review_section(review: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in review["summary"].items()
    )
    stage_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['stage_group'])}</td>"
        f"<td>{_esc(item['recommendation'])}</td>"
        f"<td>{_esc(item['reason'])}</td>"
        "</tr>"
        for item in review["stage_reviews"]
    )
    decision_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['decision'])}</td>"
        f"<td>{_esc(item['effect'])}</td>"
        "</tr>"
        for item in review["redesign_decisions"]
    )
    gap_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['priority'])}</td>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['description'])}</td>"
        "</tr>"
        for item in review["open_evidence_gaps"]
    )
    return f"""
  <h2>Live Process Redesign Review</h2>
  <section class="grid">{metrics}</section>
  <h2>Stage Redesign Review</h2>
  <section class="panel"><table><thead><tr><th>Stage Group</th><th>Recommendation</th><th>Reason</th></tr></thead><tbody>{stage_rows}</tbody></table></section>
  <h2>Redesign Decisions</h2>
  <section class="panel"><table><thead><tr><th>ID</th><th>Decision</th><th>Effect</th></tr></thead><tbody>{decision_rows}</tbody></table></section>
  <h2>Open Evidence Gaps</h2>
  <section class="panel"><table><thead><tr><th>Priority</th><th>ID</th><th>Description</th></tr></thead><tbody>{gap_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review connected Google Sheets parser iteration for process redesign."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--process-ledger", type=Path, required=True)
    parser.add_argument("--tasklist", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
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
    parser.add_argument("--live-local-semantic-candidates", type=Path, required=True)
    parser.add_argument("--live-shared-ontology-alignment-review", type=Path, required=True)
    args = parser.parse_args()

    review = build_google_sheets_process_redesign_review(
        live_inspection_dir=args.out_dir,
        process_ledger_path=args.process_ledger,
        tasklist_path=args.tasklist,
        design_path=args.design,
    )
    write_google_sheets_process_redesign_review_package(
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
        live_local_semantic_candidates_path=args.live_local_semantic_candidates,
        live_shared_ontology_alignment_review_path=args.live_shared_ontology_alignment_review,
        process_redesign_review=review,
    )


if __name__ == "__main__":
    main()
