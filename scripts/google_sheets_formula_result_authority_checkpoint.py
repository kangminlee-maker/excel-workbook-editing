from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openpyxl.utils import range_boundaries

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_formula_result_authority_checkpoint(
    *,
    out_dir: Path,
) -> dict[str, Any]:
    out_dir = out_dir.expanduser().resolve()
    manifest = _read_json(out_dir / "live-manifest.json")
    table_io = _read_json(out_dir / "live-table-io-pipelines.json")
    data_projection = _read_json(out_dir / "live-data-view-projection.json")
    blocker_update = _read_json(out_dir / "live-blocker-resolution-update.json")
    current_grid = _read_json(out_dir / "formula-result-grid-current-probes.json")
    source_grid = _read_json(out_dir / "source-fc-data-grid-formula-window.json")

    current_range_results = _grid_range_results(
        current_grid,
        source_kind="current_workbook",
        requested_ranges=_payload(current_grid).get("requested_ranges", []),
    )
    source_range_results = _grid_range_results(
        source_grid,
        source_kind="fc_data_source_workbook",
        requested_ranges=_payload(source_grid).get("requested_ranges", []),
    )
    all_range_results = current_range_results + source_range_results
    projection_lookup = {
        projection.get("pipeline_id"): projection
        for projection in data_projection.get("data_view_projections", [])
        if projection.get("pipeline_id")
    }
    pipeline_results = [
        _pipeline_result(pipeline, all_range_results, projection_lookup, blocker_update)
        for pipeline in table_io.get("pipelines", [])
    ]
    gate_results = _gate_results(all_range_results, pipeline_results, blocker_update)
    follow_up_actions = _follow_up_actions(all_range_results, pipeline_results)
    accepted_ranges = [item for item in all_range_results if item["status"] == "accepted"]
    blocked_ranges = [item for item in all_range_results if item["status"] == "blocked"]
    accepted_pipelines = [item for item in pipeline_results if item["status"] == "accepted"]
    blocked_pipelines = [item for item in pipeline_results if item["status"] == "blocked"]
    review_pipelines = [item for item in pipeline_results if item["status"] == "review_required"]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": manifest["source"]["spreadsheet_id"],
            "spreadsheet_url": manifest["source"].get("spreadsheet_url"),
            "title": manifest["source"]["title"],
            "source_artifacts": {
                "live_manifest": "live-manifest.json",
                "live_table_io_pipelines": "live-table-io-pipelines.json",
                "live_data_view_projection": "live-data-view-projection.json",
                "live_blocker_resolution_update": "live-blocker-resolution-update.json",
                "formula_result_grid_current_probes": "formula-result-grid-current-probes.json",
                "source_fc_data_grid_formula_window": "source-fc-data-grid-formula-window.json",
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "checkpoint_status": "completed",
            "formula_result_authority_basis": "google_sheets_api_grid_effective_value",
            "shared_ontology_updates": 0,
            "parser_truth": "range_level_authority_only_no_semantic_promotion",
        },
        "method": {
            "name": "connected_sheets_formula_result_authority_checkpoint",
            "authority": "deterministic_grid_effective_value_gate",
            "decision_policy": (
                "Accept formula-result authority only for probed ranges where Google Sheets grid "
                "effective values exist for formula cells and no effective error values are present. "
                "Blocked upstream FC_DATA/source ranges block dependent report pipelines. This stage "
                "does not accept semantic claims or shared ontology updates."
            ),
        },
        "evidence_inputs": {
            "grid_field_mask": "grid_formula_v1",
            "current_workbook_probe_ranges": _payload(current_grid).get("requested_ranges", []),
            "source_workbook_probe_ranges": _payload(source_grid).get("requested_ranges", []),
            "reporting_basis": blocker_update["user_inputs"]["reporting_basis"],
            "local_boundary": blocker_update["user_inputs"]["local_boundary"],
        },
        "range_authority_results": all_range_results,
        "pipeline_authority_results": pipeline_results,
        "gate_results": gate_results,
        "follow_up_actions": follow_up_actions,
        "summary": {
            "range_result_count": len(all_range_results),
            "accepted_range_result_count": len(accepted_ranges),
            "blocked_range_result_count": len(blocked_ranges),
            "pipeline_result_count": len(pipeline_results),
            "accepted_pipeline_result_count": len(accepted_pipelines),
            "review_required_pipeline_result_count": len(review_pipelines),
            "blocked_pipeline_result_count": len(blocked_pipelines),
            "effective_error_range_count": len(
                [item for item in all_range_results if item["metrics"]["effective_error_count"]]
            ),
            "formula_cell_count": sum(item["metrics"]["formula_cell_count"] for item in all_range_results),
            "formula_cell_with_effective_value_count": sum(
                item["metrics"]["formula_cell_with_effective_value_count"]
                for item in all_range_results
            ),
            "formula_error_cell_count": sum(
                item["metrics"]["formula_error_cell_count"] for item in all_range_results
            ),
            "shared_ontology_update_count": 0,
        },
        "parser_observations": _parser_observations(all_range_results, pipeline_results),
    }


def write_google_sheets_formula_result_authority_checkpoint_package(
    *,
    out_dir: Path,
    checkpoint: dict[str, Any],
) -> None:
    out_dir = out_dir.expanduser().resolve()
    checkpoint_path = out_dir / "live-formula-result-authority-checkpoint.json"
    checkpoint_path.write_text(
        json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n",
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
            live_formula_result_authority_checkpoint=checkpoint,
        ),
        encoding="utf-8",
    )


def _grid_range_results(
    response: dict[str, Any],
    *,
    source_kind: str,
    requested_ranges: list[str],
) -> list[dict[str, Any]]:
    payload = _payload(response)
    policy = _policy_summary(payload)
    request_range_by_sheet = {
        _sheet_name(range_text): range_text for range_text in requested_ranges
    }
    results = []
    for sheet in payload.get("windows", []):
        title = sheet.get("title", "")
        range_text = request_range_by_sheet.get(title, title)
        for window in sheet.get("windows", []):
            metrics, samples = _cell_metrics(window.get("rows", []))
            status, blockers, message = _range_status(metrics)
            results.append(
                {
                    "id": f"range_authority_{_slug(source_kind)}_{_slug(title)}_{_slug(range_text)}",
                    "type": "formula_result_range_authority",
                    "source_kind": source_kind,
                    "sheet": title,
                    "range": range_text,
                    "status": status,
                    "authority_basis": "google_sheets_api_grid_effective_value",
                    "metrics": metrics,
                    "error_samples": samples["errors"],
                    "formula_samples": samples["formulas"],
                    "blockers": blockers,
                    "message": message,
                    "evidence_refs": [
                        f"grid_formula_v1:{source_kind}:{range_text}",
                        policy.get("decision_id", ""),
                    ],
                }
            )
    return results


def _cell_metrics(rows: list[list[dict[str, Any]]]) -> tuple[dict[str, int], dict[str, list[dict[str, Any]]]]:
    metrics = Counter()
    error_samples = []
    formula_samples = []
    for row in rows:
        for cell in row:
            if not cell:
                continue
            metrics["cell_count"] += 1
            if cell.get("formatted_value") not in (None, ""):
                metrics["formatted_value_count"] += 1
            user_value = cell.get("user_entered_value", {})
            effective_value = cell.get("effective_value", {})
            is_formula = "formulaValue" in user_value
            has_effective = bool(effective_value)
            has_error = "errorValue" in effective_value
            if is_formula:
                metrics["formula_cell_count"] += 1
                if has_effective:
                    metrics["formula_cell_with_effective_value_count"] += 1
                if has_error:
                    metrics["formula_error_cell_count"] += 1
                if len(formula_samples) < 8:
                    formula_samples.append(
                        {
                            "formula": user_value.get("formulaValue", ""),
                            "formatted_value": cell.get("formatted_value", ""),
                            "effective_value_type": _effective_type(effective_value),
                        }
                    )
            if has_effective:
                metrics["effective_value_count"] += 1
            if has_error:
                metrics["effective_error_count"] += 1
                if len(error_samples) < 12:
                    error_samples.append(
                        {
                            "formatted_value": cell.get("formatted_value", ""),
                            "error": effective_value.get("errorValue", {}),
                            "formula": user_value.get("formulaValue", ""),
                        }
                    )
    for key in [
        "cell_count",
        "formatted_value_count",
        "formula_cell_count",
        "formula_cell_with_effective_value_count",
        "formula_error_cell_count",
        "effective_value_count",
        "effective_error_count",
    ]:
        metrics.setdefault(key, 0)
    return dict(metrics), {"errors": error_samples, "formulas": formula_samples}


def _range_status(metrics: dict[str, int]) -> tuple[str, list[str], str]:
    blockers = []
    if metrics["formula_cell_count"] == 0:
        blockers.append("no_formula_cells_in_probe")
        return "review_required", blockers, "Probe has no formula cells; no formula-result authority decision is needed for formulas."
    if metrics["formula_error_cell_count"] or metrics["effective_error_count"]:
        blockers.append("effective_error_values_present")
        return "blocked", blockers, "Formula/effective error values are present in the probed range."
    if metrics["formula_cell_with_effective_value_count"] < metrics["formula_cell_count"]:
        blockers.append("some_formula_cells_missing_effective_value")
        return "review_required", blockers, "Some formula cells do not expose an effective value in the probe."
    return "accepted", [], "Formula cells expose Google Sheets effective values and no effective errors were observed."


def _pipeline_result(
    pipeline: dict[str, Any],
    range_results: list[dict[str, Any]],
    projection_lookup: dict[str, dict[str, Any]],
    blocker_update: dict[str, Any],
) -> dict[str, Any]:
    output_ref = (pipeline.get("output_refs") or [{}])[0]
    sheet = output_ref.get("sheet", "")
    range_text = output_ref.get("range", "")
    probed = _find_covering_range(range_results, sheet, range_text)
    flags = set(pipeline.get("review_flags", []))
    projection = projection_lookup.get(pipeline.get("id"), {})
    blockers = []
    if "formula_error_observed" in flags:
        blockers.append("formula_error_reconciliation_required")
    if "external_source_dependency" in flags:
        blockers.append("external_source_dependency")
    if "source_allowlist_required" in flags:
        blockers.append("nested_or_external_source_authority_follow_up")
    if "formula_result_not_established" in flags and not probed:
        blockers.append("formula_result_probe_missing")
    if probed and probed["status"] != "accepted":
        blockers.extend(probed["blockers"])

    if probed and probed["status"] == "accepted" and not blockers:
        status = "accepted"
        message = "Pipeline output range has accepted Google Sheets effective-value authority."
    elif "formula_error_reconciliation_required" in blockers or "external_source_dependency" in blockers:
        status = "blocked"
        message = "Pipeline remains blocked by formula errors or external source lineage."
    else:
        status = "review_required"
        message = "Pipeline needs an additional output-specific formula-result probe or review."

    return {
        "id": f"pipeline_authority_{pipeline['id']}",
        "type": "formula_result_pipeline_authority",
        "pipeline_id": pipeline["id"],
        "role": pipeline.get("role", ""),
        "sheet": sheet,
        "range": range_text,
        "status": status,
        "authority_basis": probed["authority_basis"] if probed else "not_probed",
        "probed_range_result_id": probed["id"] if probed else None,
        "review_flags": pipeline.get("review_flags", []),
        "transform_formula_count": _transform_formula_count(pipeline),
        "projection_preview_status": projection.get("preview", {}).get("status"),
        "blockers": sorted(set(blockers)),
        "message": message,
        "evidence_refs": pipeline.get("evidence_refs", []) + ([probed["id"]] if probed else []),
    }


def _find_covering_range(
    range_results: list[dict[str, Any]],
    sheet: str,
    target_range: str,
) -> dict[str, Any] | None:
    ordered = sorted(
        range_results,
        key=lambda item: 0 if item["source_kind"] == "current_workbook" else 1,
    )
    for result in ordered:
        if result["sheet"] == sheet and _range_key(sheet, result["range"]) == _range_key(sheet, target_range):
            return result
    for result in ordered:
        if result["sheet"] == sheet and _contains_range(result["range"], target_range):
            return result
    return None


def _contains_range(container: str, target: str) -> bool:
    try:
        _, container_ref = _split_sheet_range(container)
        _, target_ref = _split_sheet_range(target)
        c_min_col, c_min_row, c_max_col, c_max_row = range_boundaries(container_ref)
        t_min_col, t_min_row, t_max_col, t_max_row = range_boundaries(target_ref)
    except ValueError:
        return False
    return (
        c_min_col <= t_min_col
        and c_min_row <= t_min_row
        and c_max_col >= t_max_col
        and c_max_row >= t_max_row
    )


def _gate_results(
    range_results: list[dict[str, Any]],
    pipeline_results: list[dict[str, Any]],
    blocker_update: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "gate_reporting_basis_resolved",
            "status": "accepted",
            "message": blocker_update["user_inputs"]["reporting_basis"],
            "evidence_refs": ["live-blocker-resolution-update.json"],
        },
        {
            "id": "gate_effective_value_probe_available",
            "status": "accepted" if range_results else "blocked",
            "message": f"{len(range_results)} grid_formula_v1 range probes were summarized.",
            "evidence_refs": [
                "formula-result-grid-current-probes.json",
                "source-fc-data-grid-formula-window.json",
            ],
        },
        {
            "id": "gate_no_effective_errors_in_all_formula_ranges",
            "status": "accepted"
            if not any(item["metrics"]["effective_error_count"] for item in range_results)
            else "blocked",
            "message": "Effective error values must be absent before range-level result authority can be accepted.",
            "evidence_refs": [item["id"] for item in range_results if item["metrics"]["effective_error_count"]],
        },
        {
            "id": "gate_pipeline_authority_coverage",
            "status": "accepted"
            if all(item["status"] == "accepted" for item in pipeline_results)
            else "review_required",
            "message": "All pipelines require accepted output probes and clean upstream dependencies for full coverage.",
            "evidence_refs": [item["id"] for item in pipeline_results if item["status"] != "accepted"],
        },
    ]


def _follow_up_actions(
    range_results: list[dict[str, Any]],
    pipeline_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "id": "reconcile_fc_data_error_surfaces",
            "priority": "high",
            "action": "Investigate current/source FC_DATA effective errors before accepting FC_DATA-dependent report pipelines.",
            "done_when": "FC_DATA probed ranges have 0 effective error values or each remaining error is documented as intentionally non-authoritative.",
        },
        {
            "id": "probe_uncovered_report_outputs",
            "priority": "medium",
            "action": "Run grid_formula_v1 probes for blocked or review-required report output ranges after FC_DATA errors are reconciled.",
            "done_when": "Each report pipeline output has accepted range-level effective-value authority or a specific blocker.",
        },
        {
            "id": "rerun_semantic_authority_stages",
            "priority": "medium",
            "action": "Regenerate domain/source, semantic proposal, validation, local candidate, and shared alignment artifacts using accepted formula-result checkpoint outcomes.",
            "done_when": "Semantic blockers reflect accepted cash-basis and range-level authority outcomes.",
        },
    ]


def _parser_observations(
    range_results: list[dict[str, Any]],
    pipeline_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    accepted_ranges = len([item for item in range_results if item["status"] == "accepted"])
    blocked_ranges = len([item for item in range_results if item["status"] == "blocked"])
    accepted_pipelines = len([item for item in pipeline_results if item["status"] == "accepted"])
    blocked_pipelines = len([item for item in pipeline_results if item["status"] == "blocked"])
    return [
        {
            "level": "info",
            "message": f"{accepted_ranges} probed ranges have accepted Google Sheets effective-value authority.",
        },
        {
            "level": "warning",
            "message": f"{blocked_ranges} probed ranges contain effective errors and remain blocked.",
        },
        {
            "level": "warning",
            "message": f"{blocked_pipelines} pipeline authority results remain blocked; {accepted_pipelines} are accepted.",
        },
    ]


def render_google_sheets_formula_result_authority_checkpoint_section(
    checkpoint: dict[str, Any]
) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in checkpoint["summary"].items()
    )
    range_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['source_kind'])}</td>"
        f"<td>{_esc(item['sheet'])}</td>"
        f"<td>{_esc(item['range'])}</td>"
        f"<td>{_esc(item['metrics']['formula_cell_count'])}</td>"
        f"<td>{_esc(item['metrics']['formula_error_cell_count'])}</td>"
        f"<td>{_esc(', '.join(item['blockers']))}</td>"
        "</tr>"
        for item in checkpoint["range_authority_results"]
    )
    pipeline_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['role'])}</td>"
        f"<td>{_esc(item['pipeline_id'])}</td>"
        f"<td>{_esc(item['sheet'])}</td>"
        f"<td>{_esc(item['range'])}</td>"
        f"<td>{_esc(item['probed_range_result_id'] or '')}</td>"
        f"<td>{_esc(', '.join(item['blockers']))}</td>"
        "</tr>"
        for item in checkpoint["pipeline_authority_results"]
    )
    gate_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in checkpoint["gate_results"]
    )
    action_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['priority'])}</td>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['action'])}</td>"
        f"<td>{_esc(item['done_when'])}</td>"
        "</tr>"
        for item in checkpoint["follow_up_actions"]
    )
    return f"""
  <h2>Live Formula Result Authority Checkpoint</h2>
  <section class="grid">{metrics}</section>
  <h2>Formula Result Range Authority</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Source</th><th>Sheet</th><th>Range</th><th>Formula Cells</th><th>Formula Errors</th><th>Blockers</th></tr></thead><tbody>{range_rows}</tbody></table></section>
  <h2>Pipeline Formula Result Authority</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Role</th><th>Pipeline</th><th>Sheet</th><th>Range</th><th>Probe</th><th>Blockers</th></tr></thead><tbody>{pipeline_rows}</tbody></table></section>
  <h2>Formula Authority Gates</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Gate</th><th>Message</th></tr></thead><tbody>{gate_rows}</tbody></table></section>
  <h2>Formula Authority Follow-Up</h2>
  <section class="panel"><table><thead><tr><th>Priority</th><th>ID</th><th>Action</th><th>Done When</th></tr></thead><tbody>{action_rows}</tbody></table></section>
"""


def _payload(response: dict[str, Any]) -> dict[str, Any]:
    payload = response.get("payload")
    return payload if isinstance(payload, dict) else response


def _policy_summary(payload: dict[str, Any]) -> dict[str, Any]:
    for artifact in payload.get("artifacts", []):
        if artifact.get("kind") == "source_access_policy_evidence":
            return artifact.get("summary", {})
    return {}


def _sheet_name(range_text: str) -> str:
    sheet, _, _ = range_text.partition("!")
    return sheet.strip("'")


def _range_key(sheet: str, range_text: str) -> str:
    _, ref = _split_sheet_range(range_text)
    return f"{sheet}!{ref}"


def _split_sheet_range(range_text: str) -> tuple[str, str]:
    if "!" in range_text:
        sheet, ref = range_text.split("!", 1)
        return sheet.strip("'"), ref
    return "", range_text


def _transform_formula_count(pipeline: dict[str, Any]) -> int:
    return sum(item.get("formula_count", 0) for item in pipeline.get("transform_refs", []))


def _effective_type(value: dict[str, Any]) -> str:
    for key in ("numberValue", "stringValue", "boolValue", "errorValue"):
        if key in value:
            return key
    return "none"


def _slug(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", str(value).lower()).strip("_") or "item"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _optional_json(path: Path) -> dict[str, Any] | None:
    return _read_json(path) if path.exists() else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify connected Google Sheets formula-result authority from grid effective-value probes."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    checkpoint = build_google_sheets_formula_result_authority_checkpoint(
        out_dir=args.out_dir
    )
    write_google_sheets_formula_result_authority_checkpoint_package(
        out_dir=args.out_dir,
        checkpoint=checkpoint,
    )


if __name__ == "__main__":
    main()
