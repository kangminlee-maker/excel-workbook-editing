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


def build_google_sheets_cross_validation_plan(
    *,
    live_table_io_pipelines_path: Path,
    live_block_candidate_tuning_path: Path,
    max_remaining_read_ranges: int = 8,
) -> dict[str, Any]:
    live_table_io_pipelines_path = live_table_io_pipelines_path.expanduser().resolve()
    live_block_candidate_tuning_path = live_block_candidate_tuning_path.expanduser().resolve()
    table_io = _read_json(live_table_io_pipelines_path)
    tuning = _read_json(live_block_candidate_tuning_path)
    targets = _pipeline_targets(table_io)
    targets.extend(_external_source_targets(table_io))
    targets.extend(_formula_error_targets(table_io))
    read_plan = _broker_read_plan(
        tuning,
        max_ranges=max_remaining_read_ranges,
    )
    if read_plan["batches"]:
        targets.append(_remaining_read_target(read_plan))
    gates = [
        gate
        for target in targets
        for gate in target["planned_gates"]
    ]
    targets.sort(key=lambda item: (_priority_sort(item["priority"]), item["id"]))
    gates.sort(key=lambda item: (item["status"], item["id"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": table_io["source"]["spreadsheet_id"],
            "spreadsheet_url": table_io["source"].get("spreadsheet_url"),
            "title": table_io["source"]["title"],
            "source_artifacts": {
                "live_table_io_pipelines": str(live_table_io_pipelines_path),
                "live_block_candidate_tuning": str(live_block_candidate_tuning_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "plan_status": "validation_plan_only_no_live_read",
            "formula_result_authority": "not_established",
            "source_spreadsheet_read_authority": "blocked_until_source_acl_and_broker_allowlist",
            "allowed_live_read_scope": "broker_bounded_parser_windows_only",
        },
        "validation_targets": targets,
        "deterministic_gates": gates,
        "broker_read_plan": read_plan,
        "summary": _summary(targets, gates, read_plan),
        "parser_observations": _parser_observations(targets, read_plan),
    }


def write_google_sheets_cross_validation_plan_package(
    *,
    out_dir: Path,
    access_preflight_path: Path,
    live_manifest_path: Path,
    live_view_formula_profile_path: Path,
    live_block_candidates_path: Path,
    bounded_window_sample_path: Path,
    live_block_candidate_tuning_path: Path,
    live_table_io_pipelines_path: Path,
    cross_validation_plan: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "live-cross-validation-plan.json"
    plan_path.write_text(
        json.dumps(cross_validation_plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    access_preflight = _read_json(access_preflight_path)
    manifest = _read_json(live_manifest_path)
    view_formula_profile = _read_json(live_view_formula_profile_path)
    block_candidates = _read_json(live_block_candidates_path)
    bounded_sample = _read_json(bounded_window_sample_path)
    tuning = _read_json(live_block_candidate_tuning_path)
    table_io = _read_json(live_table_io_pipelines_path)
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
        ),
        encoding="utf-8",
    )


def _pipeline_targets(table_io: dict[str, Any]) -> list[dict[str, Any]]:
    targets = []
    for pipeline in table_io.get("pipelines", []):
        flags = set(pipeline.get("review_flags", []))
        priority = "high" if flags & {"formula_error_observed", "source_allowlist_required"} else "medium"
        if pipeline["role"] == "calculation" and not flags & {"sampled_input_confirmed", "formula_error_observed"}:
            priority = "low"
        target = _target_seed(
            target_id=f"target_pipeline_{_slug(pipeline['id'])}",
            target_type="pipeline_flow",
            priority=priority,
            sheet=pipeline["output_refs"][0].get("sheet"),
            range_text=pipeline["output_refs"][0].get("range"),
            related_pipeline_ids=[pipeline["id"]],
            evidence_refs=pipeline.get("evidence_refs", []),
            authority_blockers=_authority_blockers_for_pipeline(pipeline),
        )
        _add_gate(
            target,
            gate_type="formula_text_dependency_trace",
            status="planned",
            deterministic_inputs=[pipeline["id"], *pipeline.get("evidence_refs", [])],
            pass_conditions=[
                "Every input/output edge remains traceable to formula text dependency evidence.",
                "Formula text dependencies are not promoted to formula-result authority.",
            ],
            failure_signals=[
                "Pipeline edge has no dependency evidence.",
                "Pipeline requires calculated values but only formula text is available.",
            ],
        )
        if "sampled_input_confirmed" in flags:
            _add_gate(
                target,
                gate_type="bounded_sample_surface_trace",
                status="planned",
                deterministic_inputs=[pipeline["input_refs"][0]["id"]],
                pass_conditions=[
                    "Sampled input surface range exists in bounded broker sample evidence.",
                    "Sampled input surface is marked as candidate evidence, not final graph truth.",
                ],
                failure_signals=[
                    "Input ref points to a sampled region absent from tuning evidence.",
                    "Sampled range is used as calculated-value authority.",
                ],
            )
        if "formula_error_observed" in flags:
            _add_gate(
                target,
                gate_type="formula_error_reconciliation",
                status="blocked",
                deterministic_inputs=[pipeline["id"], "live-block-candidate-tuning.json"],
                pass_conditions=[
                    "Displayed errors are reconciled with formula text, source authority, and expected output behavior.",
                    "Affected outputs remain review-required until error cause is resolved.",
                ],
                failure_signals=[
                    "Pipeline output is treated as valid calculated data while #REF! evidence remains unresolved.",
                    "Error evidence is dropped from downstream graph assembly.",
                ],
            )
        targets.append(target)
    return targets


def _external_source_targets(table_io: dict[str, Any]) -> list[dict[str, Any]]:
    targets = []
    for source in table_io.get("external_sources", []):
        target = _target_seed(
            target_id=f"target_external_source_{_slug(source['id'])}",
            target_type="external_source_authority",
            priority="high",
            sheet=source["formula_sheet"],
            range_text=source["formula_cell"],
            related_pipeline_ids=[
                pipeline["id"]
                for pipeline in table_io.get("pipelines", [])
                if "external_source_dependency" in pipeline.get("review_flags", [])
            ],
            evidence_refs=source.get("evidence_refs", []),
            authority_blockers=[
                "source_argument_value_lookup_required",
                "source_spreadsheet_google_acl_required",
                "broker_source_spreadsheet_allowlist_required",
            ],
        )
        _add_gate(
            target,
            gate_type="external_source_authority",
            status="blocked",
            deterministic_inputs=[source["id"], source.get("candidate_source_spreadsheet_id")],
            pass_conditions=[
                "Source argument resolves to the candidate spreadsheet ID or another reviewed source ID.",
                "Google ACL and broker allowlist authorize the source spreadsheet before any source data read.",
            ],
            failure_signals=[
                "Source spreadsheet is read without source ACL and broker allowlist evidence.",
                "Candidate URL is treated as authority without matching formula source argument resolution.",
            ],
        )
        targets.append(target)
    return targets


def _formula_error_targets(table_io: dict[str, Any]) -> list[dict[str, Any]]:
    targets = []
    for item in table_io.get("review_queue", []):
        if item["type"] != "formula_result_authority_gap":
            continue
        target = _target_seed(
            target_id=f"target_{_slug(item['id'])}",
            target_type="formula_error_surface",
            priority="high",
            sheet=None,
            range_text=None,
            related_pipeline_ids=[
                pipeline["id"]
                for pipeline in table_io.get("pipelines", [])
                if "formula_error_observed" in pipeline.get("review_flags", [])
            ],
            evidence_refs=item.get("evidence_refs", []),
            authority_blockers=["formula_result_authority_not_established"],
        )
        _add_gate(
            target,
            gate_type="formula_error_reconciliation",
            status="blocked",
            deterministic_inputs=item.get("evidence_refs", []),
            pass_conditions=[
                "Each error annotation is mapped to affected pipeline inputs/outputs.",
                "Formula-result authority remains blocked until source/result errors are resolved.",
            ],
            failure_signals=[
                "Error annotations are ignored during graph promotion.",
                "Affected pipelines are accepted without error reconciliation evidence.",
            ],
        )
        targets.append(target)
    return targets


def _remaining_read_target(read_plan: dict[str, Any]) -> dict[str, Any]:
    target = _target_seed(
        target_id="target_remaining_bounded_read_batch",
        target_type="remaining_bounded_sampling",
        priority="medium",
        sheet=None,
        range_text=None,
        related_pipeline_ids=[],
        evidence_refs=[
            item
            for batch in read_plan["batches"]
            for item in batch["read_candidate_ids"]
        ],
        authority_blockers=[],
    )
    _add_gate(
        target,
        gate_type="bounded_read_policy_check",
        status="planned",
        deterministic_inputs=[
            batch["operation"]
            for batch in read_plan["batches"]
        ],
        pass_conditions=[
            "Every planned bounded read stays within broker parser-window policy.",
            "No source spreadsheet range is included in bounded reads until separately authorized.",
        ],
        failure_signals=[
            "A planned batch exceeds range or cell policy limits.",
            "A source spreadsheet read is mixed into current-workbook bounded sampling.",
        ],
    )
    return target


def _broker_read_plan(tuning: dict[str, Any], *, max_ranges: int) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in tuning.get("remaining_read_queue", []):
        if item.get("status") not in {"pending_bounded_sampling", "verified_for_current_policy_limits"}:
            continue
        grouped.setdefault(item["operation"], []).append(item)
    batches = []
    for operation, items in sorted(grouped.items()):
        selected = items[:max_ranges]
        if not selected:
            continue
        batches.append(
            {
                "id": f"broker_batch_{_slug(operation)}",
                "operation": operation,
                "ranges": [item["range"] for item in selected],
                "read_candidate_ids": [item["id"] for item in selected],
                "status": "planned_not_executed",
                "authority": "broker_bounded_parser_window_only",
            }
        )
    return {
        "status": "planned_not_executed",
        "max_ranges_per_operation": max_ranges,
        "batches": batches,
        "blocked_source_reads": [],
        "unauthorized_source_read_count": 0,
    }


def _target_seed(
    *,
    target_id: str,
    target_type: str,
    priority: str,
    sheet: str | None,
    range_text: str | None,
    related_pipeline_ids: list[str],
    evidence_refs: list[str],
    authority_blockers: list[str],
) -> dict[str, Any]:
    return {
        "id": target_id,
        "type": "google_sheets_cross_validation_target",
        "target_type": target_type,
        "status": "blocked" if authority_blockers else "candidate",
        "priority": priority,
        "sheet": sheet,
        "range": range_text,
        "related_pipeline_ids": sorted(set(related_pipeline_ids)),
        "evidence_refs": sorted({str(item) for item in evidence_refs if item}),
        "authority_blockers": authority_blockers,
        "planned_gates": [],
        "next_action": _next_action(target_type, authority_blockers),
    }


def _add_gate(
    target: dict[str, Any],
    *,
    gate_type: str,
    status: str,
    deterministic_inputs: list[Any],
    pass_conditions: list[str],
    failure_signals: list[str],
) -> None:
    target["planned_gates"].append(
        {
            "id": f"gate_{_slug(target['id'])}_{_slug(gate_type)}",
            "type": "deterministic_validation_gate",
            "target_id": target["id"],
            "gate_type": gate_type,
            "status": status,
            "deterministic_inputs": [str(item) for item in deterministic_inputs if item],
            "pass_conditions": pass_conditions,
            "failure_signals": failure_signals,
        }
    )


def _authority_blockers_for_pipeline(pipeline: dict[str, Any]) -> list[str]:
    blockers = ["formula_result_authority_not_established"]
    flags = set(pipeline.get("review_flags", []))
    if "source_allowlist_required" in flags:
        blockers.append("source_spreadsheet_authority_not_established")
    if "formula_error_observed" in flags:
        blockers.append("formula_error_reconciliation_required")
    return blockers


def _next_action(target_type: str, authority_blockers: list[str]) -> str:
    if any("source_spreadsheet" in blocker for blocker in authority_blockers):
        return "resolve_source_acl_and_broker_allowlist_before_source_read"
    if "formula_error_reconciliation_required" in authority_blockers:
        return "reconcile_formula_errors_before_graph_promotion"
    if target_type == "remaining_bounded_sampling":
        return "execute_planned_broker_batches_in_later_stage"
    return "run_planned_deterministic_gates_after_required_evidence_is_available"


def _summary(
    targets: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    read_plan: dict[str, Any],
) -> dict[str, int | str]:
    target_types = Counter(item["target_type"] for item in targets)
    priorities = Counter(item["priority"] for item in targets)
    gate_statuses = Counter(item["status"] for item in gates)
    return {
        "validation_target_count": len(targets),
        "high_priority_target_count": priorities["high"],
        "medium_priority_target_count": priorities["medium"],
        "low_priority_target_count": priorities["low"],
        "blocked_target_count": sum(1 for item in targets if item["status"] == "blocked"),
        "pipeline_target_count": target_types["pipeline_flow"],
        "external_source_target_count": target_types["external_source_authority"],
        "formula_error_target_count": target_types["formula_error_surface"],
        "remaining_bounded_sampling_target_count": target_types["remaining_bounded_sampling"],
        "planned_gate_count": gate_statuses["planned"],
        "blocked_gate_count": gate_statuses["blocked"],
        "broker_read_batch_count": len(read_plan["batches"]),
        "planned_bounded_read_range_count": sum(len(batch["ranges"]) for batch in read_plan["batches"]),
        "unauthorized_source_read_count": read_plan["unauthorized_source_read_count"],
        "plan_status": "validation_plan_only_no_live_read",
    }


def _parser_observations(
    targets: list[dict[str, Any]],
    read_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Cross-validation plan was generated without performing new live reads.",
        }
    ]
    if any("source_spreadsheet_authority_not_established" in item["authority_blockers"] for item in targets):
        observations.append(
            {
                "level": "warning",
                "message": "Source spreadsheet reads remain blocked until source ACL and broker allowlist evidence is available.",
            }
        )
    if any("formula_error_reconciliation_required" in item["authority_blockers"] for item in targets):
        observations.append(
            {
                "level": "warning",
                "message": "Formula-error surfaces block pipeline output promotion until reconciled.",
            }
        )
    if read_plan["batches"]:
        observations.append(
            {
                "level": "info",
                "message": f"{sum(len(batch['ranges']) for batch in read_plan['batches'])} bounded read ranges are planned for later broker execution.",
            }
        )
    return observations


def _priority_sort(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 9)


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


def render_google_sheets_cross_validation_plan_section(plan: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in plan["summary"].items()
    )
    target_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['priority'])}</td>"
        f"<td>{_esc(item['target_type'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item.get('sheet'))}<br><code>{_esc(item.get('range'))}</code></td>"
        f"<td>{_esc(', '.join(item['authority_blockers']))}</td>"
        f"<td>{_esc(item['next_action'])}</td>"
        "</tr>"
        for item in plan["validation_targets"][:80]
    )
    gate_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['gate_type'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['target_id'])}</td>"
        f"<td>{_esc(' / '.join(item['pass_conditions'][:2]))}</td>"
        "</tr>"
        for item in plan["deterministic_gates"][:80]
    )
    batch_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['operation'])}</td>"
        f"<td>{_esc(len(item['ranges']))}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(', '.join(item['ranges'][:4]))}</td>"
        "</tr>"
        for item in plan["broker_read_plan"]["batches"]
    )
    if not batch_rows:
        batch_rows = '<tr><td colspan="4">No bounded broker batches planned.</td></tr>'
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in plan["parser_observations"]
    )
    return f"""
  <h2>Live Cross-Validation Plan</h2>
  <section class="grid">{metrics}</section>
  <h2>Validation Targets</h2>
  <section class="panel"><table><thead><tr><th>Priority</th><th>Type</th><th>Status</th><th>Surface</th><th>Authority Blockers</th><th>Next Action</th></tr></thead><tbody>{target_rows}</tbody></table></section>
  <h2>Deterministic Gates</h2>
  <section class="panel"><table><thead><tr><th>Gate</th><th>Status</th><th>Target</th><th>Pass Conditions</th></tr></thead><tbody>{gate_rows}</tbody></table></section>
  <h2>Planned Broker Batches</h2>
  <section class="panel"><table><thead><tr><th>Operation</th><th>Range Count</th><th>Status</th><th>Sample Ranges</th></tr></thead><tbody>{batch_rows}</tbody></table></section>
  <h2>Cross-Validation Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plan deterministic cross-validation targets for Google Sheets pipeline candidates."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--access-preflight", type=Path, required=True)
    parser.add_argument("--live-manifest", type=Path, required=True)
    parser.add_argument("--live-view-formula-profile", type=Path, required=True)
    parser.add_argument("--live-block-candidates", type=Path, required=True)
    parser.add_argument("--bounded-window-sample", type=Path, required=True)
    parser.add_argument("--live-block-candidate-tuning", type=Path, required=True)
    parser.add_argument("--live-table-io-pipelines", type=Path, required=True)
    args = parser.parse_args()

    plan = build_google_sheets_cross_validation_plan(
        live_table_io_pipelines_path=args.live_table_io_pipelines,
        live_block_candidate_tuning_path=args.live_block_candidate_tuning,
    )
    write_google_sheets_cross_validation_plan_package(
        out_dir=args.out_dir,
        access_preflight_path=args.access_preflight,
        live_manifest_path=args.live_manifest,
        live_view_formula_profile_path=args.live_view_formula_profile,
        live_block_candidates_path=args.live_block_candidates,
        bounded_window_sample_path=args.bounded_window_sample,
        live_block_candidate_tuning_path=args.live_block_candidate_tuning,
        live_table_io_pipelines_path=args.live_table_io_pipelines,
        cross_validation_plan=plan,
    )


if __name__ == "__main__":
    main()
