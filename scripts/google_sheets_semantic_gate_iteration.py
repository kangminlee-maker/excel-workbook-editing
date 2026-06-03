from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_semantic_gate_iteration(*, out_dir: Path) -> dict[str, Any]:
    out_dir = out_dir.expanduser().resolve()
    manifest = _read_json(out_dir / "live-manifest.json")
    block_candidates = _read_json(out_dir / "live-block-candidates.json")
    domain_model = _read_json(out_dir / "live-domain-source-model.json")
    grouping = _read_json(out_dir / "live-document-item-grouping-checkpoint.json")
    version_detection = _read_json(out_dir / "live-version-breakpoint-detection.json")
    formula_authority = _read_json(out_dir / "live-formula-result-authority-checkpoint.json")
    blocker_update = _read_json(out_dir / "live-blocker-resolution-update.json")

    metric_surfaces = _metric_surfaces(block_candidates)
    semantic_candidates = _semantic_candidates(
        domain_model=domain_model,
        grouping=grouping,
        version_detection=version_detection,
        formula_authority=formula_authority,
        metric_surfaces=metric_surfaces,
        blocker_update=blocker_update,
    )
    gate_results = _gate_results(domain_model, grouping, version_detection, formula_authority, metric_surfaces)
    metric_checks = _metric_equivalence_checks(metric_surfaces, blocker_update)
    iteration = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": manifest["source"]["spreadsheet_id"],
            "spreadsheet_url": manifest["source"].get("spreadsheet_url"),
            "title": manifest["source"]["title"],
            "source_artifacts": {
                "live_domain_source_model": "live-domain-source-model.json",
                "live_document_item_grouping_checkpoint": "live-document-item-grouping-checkpoint.json",
                "live_version_breakpoint_detection": "live-version-breakpoint-detection.json",
                "live_formula_result_authority_checkpoint": "live-formula-result-authority-checkpoint.json",
                "live_blocker_resolution_update": "live-blocker-resolution-update.json",
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "iteration_status": "completed",
            "semantic_truth": "accepted_local_process_claims_only_metric_equivalence_review_required",
            "shared_ontology_updates": 0,
        },
        "corrected_domain_classification": {
            "general_domain_source_count": domain_model["summary"]["general_domain_source_count"],
            "general_domain_status": domain_model["authority"]["general_domain_authority"],
            "rejected_general_domain_sources": ["accounting-kr"],
            "local_boundary": domain_model["local_domain_boundary"]["boundary_label"],
            "local_boundary_status": domain_model["local_domain_boundary"]["boundary_status"],
            "reporting_basis": domain_model["local_domain_boundary"].get("reporting_basis"),
            "operative_domain": "cash_basis_payment_status_operational_reporting",
        },
        "semantic_candidates": semantic_candidates,
        "semantic_gate_results": gate_results,
        "metric_equivalence_checks": metric_checks,
        "carry_forward_review": _carry_forward_review(grouping, version_detection, formula_authority, metric_surfaces),
        "summary": _summary(semantic_candidates, gate_results, metric_checks),
        "parser_observations": _parser_observations(metric_surfaces, gate_results),
    }
    return iteration


def write_google_sheets_semantic_gate_iteration_package(
    *,
    out_dir: Path,
    iteration: dict[str, Any],
) -> None:
    out_dir = out_dir.expanduser().resolve()
    (out_dir / "live-semantic-gate-iteration.json").write_text(
        json.dumps(iteration, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "index.html").write_text(
        render_live_manifest_html(
            access_preflight=_read_json(out_dir / "access-preflight.json"),
            manifest=_read_json(out_dir / "live-manifest.json"),
            live_view_formula_profile=_optional_json(out_dir / "live-view-formula-profile.json"),
            live_block_candidates=_optional_json(out_dir / "live-block-candidates.json"),
            live_bounded_window_sample=_optional_json(out_dir / "live-bounded-window-sample.json"),
            live_block_candidate_tuning=_optional_json(out_dir / "live-block-candidate-tuning.json"),
            live_table_io_pipelines=_optional_json(out_dir / "live-table-io-pipelines.json"),
            live_cross_validation_plan=_optional_json(out_dir / "live-cross-validation-plan.json"),
            live_validation_batch_execution=_optional_json(out_dir / "live-validation-batch-execution.json"),
            live_gate_execution=_optional_json(out_dir / "live-gate-execution.json"),
            live_evidence_package=_optional_json(out_dir / "live-evidence-package.json"),
            live_document_ontology_mapping=_optional_json(out_dir / "live-document-ontology-mapping.json"),
            live_action_contracts=_optional_json(out_dir / "live-action-contracts.json"),
            live_domain_source_model=_optional_json(out_dir / "live-domain-source-model.json"),
            live_semantic_proposals=_optional_json(out_dir / "live-semantic-proposals.json"),
            live_semantic_proposal_validation=_optional_json(out_dir / "live-semantic-proposal-validation.json"),
            live_validated_document_graph=_optional_json(out_dir / "live-validated-document-graph.json"),
            live_data_view_projection=_optional_json(out_dir / "live-data-view-projection.json"),
            live_local_semantic_candidates=_optional_json(out_dir / "live-local-semantic-candidates.json"),
            live_shared_ontology_alignment_review=_optional_json(out_dir / "live-shared-ontology-alignment-review.json"),
            live_process_redesign_review=_optional_json(out_dir / "live-process-redesign-review.json"),
            live_blocker_resolution_update=_optional_json(out_dir / "live-blocker-resolution-update.json"),
            live_formula_result_authority_checkpoint=_optional_json(out_dir / "live-formula-result-authority-checkpoint.json"),
            live_document_item_grouping_checkpoint=_optional_json(out_dir / "live-document-item-grouping-checkpoint.json"),
            live_version_breakpoint_detection=_optional_json(out_dir / "live-version-breakpoint-detection.json"),
            live_semantic_gate_iteration=iteration,
        ),
        encoding="utf-8",
    )


def _semantic_candidates(
    *,
    domain_model: dict[str, Any],
    grouping: dict[str, Any],
    version_detection: dict[str, Any],
    formula_authority: dict[str, Any],
    metric_surfaces: list[dict[str, Any]],
    blocker_update: dict[str, Any],
) -> list[dict[str, Any]]:
    accepted_groups = grouping["summary"]["accepted_document_item_count"]
    blocked_pipelines = formula_authority["summary"]["blocked_pipeline_result_count"]
    review_breakpoints = version_detection["summary"]["review_required_version_breakpoint_count"]
    return [
        {
            "id": "semantic_cash_basis_operational_report",
            "type": "semantic_candidate",
            "status": "accepted",
            "domain_layer": "local_process_semantic",
            "label": "cash-basis payment/status operational report",
            "description": blocker_update["user_inputs"]["reporting_basis"],
            "gate_outcome": "accepted_process_basis",
            "evidence_refs": ["live-blocker-resolution-update.json", "live-domain-source-model.json"],
            "review_reasons": [],
        },
        {
            "id": "semantic_period_tab_calculation_surface",
            "type": "semantic_candidate",
            "status": "accepted" if accepted_groups else "review_required",
            "domain_layer": "local_document_semantic",
            "label": "period-tab calculation surface",
            "description": f"{accepted_groups} document item groups have formula/dataflow-backed grouping authority.",
            "gate_outcome": "accepted_structural_semantic_seed" if accepted_groups else "review_required",
            "evidence_refs": ["live-document-item-grouping-checkpoint.json", "live-formula-result-authority-checkpoint.json"],
            "review_reasons": [] if accepted_groups else ["no_accepted_grouping_prerequisite"],
        },
        {
            "id": "semantic_revenue_label_as_cash_basis_variant",
            "type": "semantic_candidate",
            "status": "review_required",
            "domain_layer": "local_metric_candidate",
            "label": "visible revenue labels as cash-basis payment metric variants",
            "description": (
                f"{len(metric_surfaces)} visible surfaces contain 결제/매출/순매출 labels. "
                "They must be checked as scoped metric variants before being treated as the same 결제액."
            ),
            "gate_outcome": "metric_equivalence_review_required",
            "evidence_refs": ["live-block-candidates.json", "live-blocker-resolution-update.json"],
            "review_reasons": ["visible_label_differs_from_user_confirmed_basis", "metric_equivalence_gate_required"],
        },
        {
            "id": "semantic_fc_data_dependent_report_pipeline",
            "type": "semantic_candidate",
            "status": "blocked" if blocked_pipelines else "accepted",
            "domain_layer": "local_pipeline_semantic",
            "label": "FC_DATA-dependent report pipeline",
            "description": f"{blocked_pipelines} pipeline outputs remain blocked by formula-result/error authority.",
            "gate_outcome": "blocked_formula_result_authority" if blocked_pipelines else "accepted_formula_result_authority",
            "evidence_refs": ["live-formula-result-authority-checkpoint.json"],
            "review_reasons": ["formula_result_authority_blocked"] if blocked_pipelines else [],
        },
        {
            "id": "semantic_repeated_workbook_family_evidence",
            "type": "semantic_candidate",
            "status": "review_required" if review_breakpoints else "accepted",
            "domain_layer": "process_semantic",
            "label": "repeated workbook-family evidence",
            "description": f"{review_breakpoints} version breakpoints remain review-required before repeated evidence can support shared promotion.",
            "gate_outcome": "version_evidence_review_required" if review_breakpoints else "accepted_version_evidence",
            "evidence_refs": ["live-version-breakpoint-detection.json"],
            "review_reasons": ["review_required_version_breakpoints"] if review_breakpoints else [],
        },
    ]


def _gate_results(
    domain_model: dict[str, Any],
    grouping: dict[str, Any],
    version_detection: dict[str, Any],
    formula_authority: dict[str, Any],
    metric_surfaces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        _gate("gate_general_domain_applicability", "general_domain_applicability_gate", "accepted", "No general-domain pack is selected; accounting-kr is excluded for this document.", ["live-domain-source-model.json"]),
        _gate("gate_local_boundary", "local_boundary_gate", "accepted" if domain_model["summary"]["local_boundary_confirmed"] else "blocked", domain_model["local_domain_boundary"]["boundary_label"], ["live-domain-source-model.json"]),
        _gate("gate_reporting_basis", "reporting_basis_gate", "accepted", domain_model["local_domain_boundary"].get("reporting_basis", ""), ["live-blocker-resolution-update.json"]),
        _gate("gate_grouping_prerequisite", "document_item_grouping_gate", "accepted" if grouping["summary"]["accepted_document_item_count"] else "review_required", f"{grouping['summary']['accepted_document_item_count']} accepted groupings, {grouping['summary']['review_required_document_item_count']} review-required groupings.", ["live-document-item-grouping-checkpoint.json"]),
        _gate("gate_version_evidence", "version_breakpoint_gate", "review_required" if version_detection["summary"]["review_required_version_breakpoint_count"] else "accepted", f"{version_detection['summary']['review_required_version_breakpoint_count']} version breakpoints require review.", ["live-version-breakpoint-detection.json"]),
        _gate("gate_formula_result_authority", "formula_result_authority_gate", "blocked" if formula_authority["summary"]["blocked_pipeline_result_count"] else "accepted", f"{formula_authority['summary']['accepted_pipeline_result_count']} accepted and {formula_authority['summary']['blocked_pipeline_result_count']} blocked pipeline authority results.", ["live-formula-result-authority-checkpoint.json"]),
        _gate("gate_metric_equivalence", "metric_equivalence_gate", "review_required", f"{len(metric_surfaces)} 결제/매출/순매출 surfaces require scoped metric equivalence checks.", ["live-block-candidates.json"]),
        _gate("gate_shared_promotion", "shared_promotion_gate", "blocked", "Shared ontology updates remain 0 until grouping, version, metric-equivalence, lineage, and human approval gates pass.", ["live-semantic-gate-iteration.json"]),
    ]


def _metric_equivalence_checks(
    metric_surfaces: list[dict[str, Any]],
    blocker_update: dict[str, Any],
) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "visible_net_revenue_or_refund_adjusted_label": [],
        "visible_revenue_label": [],
        "visible_payment_label": [],
    }
    for surface in metric_surfaces:
        label = surface["label"]
        if "결제" in label:
            buckets["visible_payment_label"].append(surface)
        elif "순매출" in label or "환불" in label:
            buckets["visible_net_revenue_or_refund_adjusted_label"].append(surface)
        else:
            buckets["visible_revenue_label"].append(surface)
    checks = []
    for bucket, surfaces in buckets.items():
        if not surfaces:
            continue
        checks.append(
            {
                "id": f"metric_check_{bucket}",
                "type": "metric_equivalence_check",
                "status": "review_required",
                "candidate_parent_label": "결제액",
                "visible_label_bucket": bucket,
                "surface_count": len(surfaces),
                "sample_surfaces": surfaces[:12],
                "dimensions_to_verify": [
                    "reporting_basis",
                    "amount_treatment",
                    "time_axis",
                    "filters",
                    "aggregation",
                    "source_lineage",
                    "transformation_role",
                    "formula_result_authority",
                ],
                "current_basis": blocker_update["user_inputs"]["reporting_basis"],
                "decision": "scoped_variant_or_review_required_until_equivalence_is_proven",
                "evidence_refs": ["live-block-candidates.json", "live-blocker-resolution-update.json"],
            }
        )
    return checks


def _metric_surfaces(block_candidates: dict[str, Any]) -> list[dict[str, Any]]:
    surfaces = []
    for sheet in block_candidates.get("sheets", []):
        for block in sheet.get("blocks", []):
            label = block.get("label") or ""
            if not re.search(r"결제|매출", label):
                continue
            surfaces.append(
                {
                    "id": block["id"],
                    "sheet": block["sheet"],
                    "range": block.get("bounds", {}).get("a1_range"),
                    "surface_type": block.get("type"),
                    "label": label,
                }
            )
    return surfaces


def _carry_forward_review(
    grouping: dict[str, Any],
    version_detection: dict[str, Any],
    formula_authority: dict[str, Any],
    metric_surfaces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "review_document_item_grouping",
            "severity": "high",
            "message": f"{grouping['summary']['review_required_document_item_count']} document item groups and {grouping['summary']['orphan_surface_count']} object surfaces need review.",
        },
        {
            "id": "review_version_breakpoints",
            "severity": "medium",
            "message": f"{version_detection['summary']['review_required_version_breakpoint_count']} version breakpoints need review before repeated-family promotion.",
        },
        {
            "id": "review_formula_result_authority",
            "severity": "high",
            "message": f"{formula_authority['summary']['blocked_pipeline_result_count']} pipeline outputs remain blocked.",
        },
        {
            "id": "review_metric_equivalence",
            "severity": "high",
            "message": f"{len(metric_surfaces)} visible metric-label surfaces need scoped equivalence review.",
        },
    ]


def _summary(
    semantic_candidates: list[dict[str, Any]],
    gate_results: list[dict[str, Any]],
    metric_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_counts = Counter(item["status"] for item in semantic_candidates)
    gate_counts = Counter(item["status"] for item in gate_results)
    return {
        "semantic_candidate_count": len(semantic_candidates),
        "accepted_semantic_candidate_count": candidate_counts["accepted"],
        "review_required_semantic_candidate_count": candidate_counts["review_required"],
        "blocked_semantic_candidate_count": candidate_counts["blocked"],
        "semantic_gate_count": len(gate_results),
        "accepted_semantic_gate_count": gate_counts["accepted"],
        "review_required_semantic_gate_count": gate_counts["review_required"],
        "blocked_semantic_gate_count": gate_counts["blocked"],
        "metric_equivalence_check_count": len(metric_checks),
        "shared_ontology_update_count": 0,
        "iteration_status": "completed_with_review_carry_forward",
    }


def _parser_observations(metric_surfaces: list[dict[str, Any]], gate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocked = sum(1 for item in gate_results if item["status"] == "blocked")
    return [
        {
            "level": "info",
            "message": "Semantic/gate iteration uses corrected domain classification: no accounting-kr general domain for this document.",
        },
        {
            "level": "warning",
            "message": f"{len(metric_surfaces)} visible metric-label surfaces require scoped equivalence checks before 결제액 can be treated as one metric.",
        },
        {
            "level": "warning" if blocked else "info",
            "message": f"{blocked} semantic gates remain blocked.",
        },
    ]


def render_google_sheets_semantic_gate_iteration_section(iteration: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in iteration["summary"].items()
    )
    classification_rows = "".join(
        f"<tr><td>{_esc(key)}</td><td>{_esc(value)}</td></tr>"
        for key, value in iteration["corrected_domain_classification"].items()
    )
    candidate_rows = "".join(
        "<tr>"
        f"<td>{_pill(item['status'], _tone(item['status']))}</td>"
        f"<td>{_esc(item['domain_layer'])}</td>"
        f"<td>{_esc(item['label'])}</td>"
        f"<td>{_esc(item['gate_outcome'])}</td>"
        f"<td>{_esc(', '.join(item['review_reasons']))}</td>"
        "</tr>"
        for item in iteration["semantic_candidates"]
    )
    gate_rows = "".join(
        "<tr>"
        f"<td>{_pill(item['status'], _tone(item['status']))}</td>"
        f"<td>{_esc(item['gate_type'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in iteration["semantic_gate_results"]
    )
    metric_rows = "".join(
        "<tr>"
        f"<td>{_pill(item['status'], _tone(item['status']))}</td>"
        f"<td>{_esc(item['visible_label_bucket'])}</td>"
        f"<td>{_esc(item['surface_count'])}</td>"
        f"<td>{_esc(item['decision'])}</td>"
        f"<td>{_esc('; '.join(surface['label'] for surface in item['sample_surfaces'][:5]))}</td>"
        "</tr>"
        for item in iteration["metric_equivalence_checks"]
    )
    review_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['severity'])}</td>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in iteration["carry_forward_review"]
    )
    return f"""
  <h2>Live Semantic / Gate Iteration</h2>
  <section class="grid">{metrics}</section>
  <h2>Corrected Domain Classification</h2>
  <section class="panel"><table><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>{classification_rows}</tbody></table></section>
  <h2>Semantic Candidates</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Layer</th><th>Label</th><th>Gate Outcome</th><th>Review Reasons</th></tr></thead><tbody>{candidate_rows}</tbody></table></section>
  <h2>Semantic Gates</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Gate</th><th>Message</th></tr></thead><tbody>{gate_rows}</tbody></table></section>
  <h2>Metric Equivalence Checks</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Visible Label Bucket</th><th>Surface Count</th><th>Decision</th><th>Samples</th></tr></thead><tbody>{metric_rows}</tbody></table></section>
  <h2>Carry-forward Review</h2>
  <section class="panel"><table><thead><tr><th>Severity</th><th>ID</th><th>Message</th></tr></thead><tbody>{review_rows}</tbody></table></section>
"""


def _gate(id_: str, gate_type: str, status: str, message: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "id": id_,
        "type": "semantic_gate_result",
        "gate_type": gate_type,
        "status": status,
        "message": message,
        "evidence_refs": evidence_refs,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_json(path: Path) -> dict[str, Any] | None:
    return _read_json(path) if path.exists() else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape("" if value is None else str(value))


def _pill(label: str, tone: str) -> str:
    return f'<span class="pill {tone}">{_esc(label)}</span>'


def _tone(status: str) -> str:
    if status == "accepted":
        return "ok"
    if status == "blocked":
        return "bad"
    return "warn"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run authority-aware semantic/gate iteration for connected Google Sheets."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    iteration = build_google_sheets_semantic_gate_iteration(out_dir=args.out_dir)
    write_google_sheets_semantic_gate_iteration_package(out_dir=args.out_dir, iteration=iteration)


if __name__ == "__main__":
    main()
