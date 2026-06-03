from __future__ import annotations

import argparse
import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_shared_ontology_alignment_review(
    *,
    live_local_semantic_candidates_path: Path,
    live_data_view_projection_path: Path,
    live_domain_source_model_path: Path,
) -> dict[str, Any]:
    live_local_semantic_candidates_path = live_local_semantic_candidates_path.expanduser().resolve()
    live_data_view_projection_path = live_data_view_projection_path.expanduser().resolve()
    live_domain_source_model_path = live_domain_source_model_path.expanduser().resolve()

    candidates = _read_json(live_local_semantic_candidates_path)
    projection = _read_json(live_data_view_projection_path)
    domain_model = _read_json(live_domain_source_model_path)
    alignment_items = [
        _alignment_item(candidate, domain_model)
        for candidate in candidates["local_semantic_candidates"]
    ]
    review_questions = _review_questions(candidates, projection, domain_model)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": candidates["source"]["spreadsheet_id"],
            "spreadsheet_url": candidates["source"].get("spreadsheet_url"),
            "title": candidates["source"]["title"],
            "source_artifacts": {
                "live_local_semantic_candidates": str(live_local_semantic_candidates_path),
                "live_data_view_projection": str(live_data_view_projection_path),
                "live_domain_source_model": str(live_domain_source_model_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "review_status": "review_only_no_shared_promotion",
            "shared_ontology_updates": 0,
            "formula_result_authority": "not_established",
            "local_boundary_confirmed": domain_model["semantic_readiness"]["local_boundary_confirmed"],
        },
        "method": {
            "name": "connected_sheets_shared_ontology_alignment_review",
            "authority": "human_review_packet_no_ontology_write",
            "decision_policy": (
                "Evaluate local semantic candidates against shared-promotion prerequisites and "
                "emit a blocker-focused human review packet. This stage does not write or update "
                "shared ontology concepts."
            ),
        },
        "alignment_items": alignment_items,
        "review_questions": review_questions,
        "shared_ontology_updates": [],
        "summary": _summary(alignment_items, review_questions),
        "parser_observations": _parser_observations(alignment_items),
    }


def write_google_sheets_shared_ontology_alignment_review_package(
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
    shared_alignment_review: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    review_path = out_dir / "live-shared-ontology-alignment-review.json"
    review_path.write_text(
        json.dumps(shared_alignment_review, ensure_ascii=False, indent=2) + "\n",
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
            live_shared_ontology_alignment_review=shared_alignment_review,
        ),
        encoding="utf-8",
    )


def _alignment_item(candidate: dict[str, Any], domain_model: dict[str, Any]) -> dict[str, Any]:
    preconditions = [
        _precondition(
            "local_boundary_confirmed",
            domain_model["semantic_readiness"]["local_boundary_confirmed"],
            "Local boundary must be explicitly confirmed.",
        ),
        _precondition(
            "source_authority_available",
            domain_model["semantic_readiness"]["unavailable_source_count"] == 0,
            "External source and formula-result authorities must be available.",
        ),
        _precondition(
            "repeated_workbook_family_evidence_available",
            False,
            "Repeated workbook-family evidence is not available in this sample.",
        ),
        _precondition(
            "formula_result_authority_established",
            False,
            "Formula-result authority is not established.",
        ),
        _precondition(
            "human_promotion_approval_recorded",
            False,
            "Human approval for shared ontology promotion is not recorded.",
        ),
    ]
    return {
        "id": f"alignment_{candidate['id']}",
        "type": "shared_ontology_alignment_item",
        "candidate_id": candidate["id"],
        "candidate_label": candidate["label"],
        "status": "blocked",
        "recommended_action": "no_shared_update",
        "preconditions": preconditions,
        "blocking_preconditions": [
            item["id"] for item in preconditions if item["status"] == "blocked"
        ],
        "shared_update": None,
        "evidence_refs": candidate["evidence_refs"],
    }


def _precondition(precondition_id: str, passed: bool, message: str) -> dict[str, Any]:
    return {
        "id": precondition_id,
        "status": "passed" if passed else "blocked",
        "message": message,
    }


def _review_questions(
    candidates: dict[str, Any],
    projection: dict[str, Any],
    domain_model: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "question_local_boundary",
            "priority": "high",
            "question": "이 Google Sheet가 어떤 organization/project/team/workbook-family boundary 안에서 의미가 유효한가?",
            "required_for": ["local_candidate_acceptance", "shared_promotion"],
        },
        {
            "id": "question_source_authority",
            "priority": "high",
            "question": "FC_DATA의 IMPORTRANGE 원본 spreadsheet ACL과 broker allowlist를 확보해 원본 source authority를 검증할 수 있는가?",
            "required_for": ["pipeline_acceptance", "semantic_acceptance"],
        },
        {
            "id": "question_formula_result_authority",
            "priority": "high",
            "question": "표시값과 formula 결과를 어떤 authority로 검산할 것인가?",
            "required_for": ["formula_result_validation", "candidate_acceptance"],
        },
        {
            "id": "question_workbook_family_repetition",
            "priority": "medium",
            "question": "동일 workbook family의 반복 문서에서 같은 period-tab calculation surface가 반복되는가?",
            "required_for": ["shared_promotion"],
        },
        {
            "id": "question_reporting_basis",
            "priority": "medium",
            "question": "이 문서의 revenue/profit 관련 표는 어떤 reporting basis와 aggregation rule로 해석해야 하는가?",
            "required_for": ["general_domain_alignment", "human_review"],
        },
    ]


def _summary(alignment_items: list[dict[str, Any]], review_questions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "alignment_item_count": len(alignment_items),
        "blocked_alignment_count": len([item for item in alignment_items if item["status"] == "blocked"]),
        "promoted_alignment_count": 0,
        "review_question_count": len(review_questions),
        "high_priority_question_count": len([item for item in review_questions if item["priority"] == "high"]),
        "shared_ontology_update_count": 0,
        "alignment_status": "review_only_no_shared_promotion",
    }


def _parser_observations(alignment_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "level": "info",
            "message": "Shared ontology alignment review emits a human review packet only.",
        },
        {
            "level": "warning",
            "message": f"{len(alignment_items)} alignment items are blocked from shared promotion.",
        },
        {
            "level": "warning",
            "message": "No shared ontology updates were emitted.",
        },
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def render_google_sheets_shared_ontology_alignment_review_section(review: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in review["summary"].items()
    )
    alignment_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['candidate_label'])}</td>"
        f"<td>{_esc(item['recommended_action'])}</td>"
        f"<td>{_esc(', '.join(item['blocking_preconditions']))}</td>"
        "</tr>"
        for item in review["alignment_items"]
    )
    question_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['priority'])}</td>"
        f"<td>{_esc(item['question'])}</td>"
        f"<td>{_esc(', '.join(item['required_for']))}</td>"
        "</tr>"
        for item in review["review_questions"]
    )
    return f"""
  <h2>Live Shared Ontology Alignment Review</h2>
  <section class="grid">{metrics}</section>
  <h2>Shared Alignment Items</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Candidate</th><th>Action</th><th>Blocking Preconditions</th></tr></thead><tbody>{alignment_rows}</tbody></table></section>
  <h2>Shared Alignment Review Questions</h2>
  <section class="panel"><table><thead><tr><th>Priority</th><th>Question</th><th>Required For</th></tr></thead><tbody>{question_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a review-only shared ontology alignment packet for connected Google Sheets."
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
    parser.add_argument("--live-local-semantic-candidates", type=Path, required=True)
    args = parser.parse_args()

    review = build_google_sheets_shared_ontology_alignment_review(
        live_local_semantic_candidates_path=args.live_local_semantic_candidates,
        live_data_view_projection_path=args.live_data_view_projection,
        live_domain_source_model_path=args.live_domain_source_model,
    )
    write_google_sheets_shared_ontology_alignment_review_package(
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
        shared_alignment_review=review,
    )


if __name__ == "__main__":
    main()
