from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_gate_execution(
    *,
    live_cross_validation_plan_path: Path,
    live_validation_batch_execution_path: Path,
    live_table_io_pipelines_path: Path,
    live_block_candidate_tuning_path: Path,
) -> dict[str, Any]:
    live_cross_validation_plan_path = live_cross_validation_plan_path.expanduser().resolve()
    live_validation_batch_execution_path = live_validation_batch_execution_path.expanduser().resolve()
    live_table_io_pipelines_path = live_table_io_pipelines_path.expanduser().resolve()
    live_block_candidate_tuning_path = live_block_candidate_tuning_path.expanduser().resolve()
    plan = _read_json(live_cross_validation_plan_path)
    validation_batch = _read_json(live_validation_batch_execution_path)
    table_io = _read_json(live_table_io_pipelines_path)
    tuning = _read_json(live_block_candidate_tuning_path)
    context = _context(plan, validation_batch, table_io, tuning)
    gate_results = [
        _execute_gate(gate, context)
        for gate in plan.get("deterministic_gates", [])
    ]
    target_results = _target_results(plan, gate_results)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": plan["source"]["spreadsheet_id"],
            "spreadsheet_url": plan["source"].get("spreadsheet_url"),
            "title": plan["source"]["title"],
            "source_artifacts": {
                "live_cross_validation_plan": str(live_cross_validation_plan_path),
                "live_validation_batch_execution": str(live_validation_batch_execution_path),
                "live_table_io_pipelines": str(live_table_io_pipelines_path),
                "live_block_candidate_tuning": str(live_block_candidate_tuning_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "gate_execution_status": "deterministic_evidence_only",
            "formula_result_authority": "not_established",
            "source_spreadsheet_read_authority": "blocked_until_source_acl_and_broker_allowlist",
            "accepted_gate_is_not_graph_promotion": True,
        },
        "gate_results": gate_results,
        "target_results": target_results,
        "summary": _summary(gate_results, target_results),
        "parser_observations": _parser_observations(gate_results),
    }


def write_google_sheets_gate_execution_package(
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
    gate_execution: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    gate_path = out_dir / "live-gate-execution.json"
    gate_path.write_text(
        json.dumps(gate_execution, ensure_ascii=False, indent=2) + "\n",
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
        ),
        encoding="utf-8",
    )


def _context(
    plan: dict[str, Any],
    validation_batch: dict[str, Any],
    table_io: dict[str, Any],
    tuning: dict[str, Any],
) -> dict[str, Any]:
    pipeline_ids = {item["id"] for item in table_io.get("pipelines", [])}
    sampled_region_ids = {item["id"] for item in tuning.get("sampled_regions", [])}
    evidence_update_ids = {item["id"] for item in validation_batch.get("evidence_updates", [])}
    source_read_count = validation_batch.get("summary", {}).get("source_spreadsheet_read_count", 0)
    successful_response_count = validation_batch.get("summary", {}).get("successful_response_count", 0)
    planned_request_count = validation_batch.get("summary", {}).get("planned_request_count", 0)
    return {
        "pipeline_ids": pipeline_ids,
        "sampled_region_ids": sampled_region_ids,
        "evidence_update_ids": evidence_update_ids,
        "source_read_count": source_read_count,
        "broker_batches_succeeded": planned_request_count == successful_response_count,
        "planned_request_count": planned_request_count,
        "formula_result_authority": plan["authority"]["formula_result_authority"],
    }


def _execute_gate(gate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    gate_type = gate["gate_type"]
    if gate["status"] == "blocked":
        return _gate_result(
            gate,
            "blocked",
            "Gate was explicitly blocked by the validation plan and no resolving authority evidence is present.",
            _blocking_evidence(gate_type),
        )
    if gate_type == "formula_text_dependency_trace":
        pipeline_inputs = [
            item for item in gate["deterministic_inputs"]
            if item in context["pipeline_ids"]
        ]
        if pipeline_inputs:
            return _gate_result(
                gate,
                "accepted",
                "Pipeline dependency evidence is traceable to table I/O pipeline artifacts; formula-result authority remains separate.",
                pipeline_inputs,
            )
        return _gate_result(
            gate,
            "review_required",
            "No matching pipeline artifact was found for formula dependency trace inputs.",
            gate["deterministic_inputs"],
        )
    if gate_type == "bounded_sample_surface_trace":
        sampled_inputs = [
            item for item in gate["deterministic_inputs"]
            if item in context["sampled_region_ids"] or item in context["evidence_update_ids"]
        ]
        if sampled_inputs:
            return _gate_result(
                gate,
                "accepted",
                "Bounded sample surface exists in tuning or validation evidence.",
                sampled_inputs,
            )
        return _gate_result(
            gate,
            "review_required",
            "Bounded sample surface input was not found in current evidence artifacts.",
            gate["deterministic_inputs"],
        )
    if gate_type == "bounded_read_policy_check":
        if context["broker_batches_succeeded"] and context["source_read_count"] == 0:
            return _gate_result(
                gate,
                "accepted",
                "Planned current-workbook broker batches executed successfully and no source-spreadsheet reads occurred.",
                [f"planned_request_count={context['planned_request_count']}"],
            )
        return _gate_result(
            gate,
            "review_required",
            "Broker batch execution did not fully satisfy planned policy checks.",
            [f"source_read_count={context['source_read_count']}"],
        )
    return _gate_result(
        gate,
        "review_required",
        "No deterministic executor is available for this planned gate type.",
        gate["deterministic_inputs"],
    )


def _gate_result(
    gate: dict[str, Any],
    status: str,
    rationale: str,
    evidence_refs: list[Any],
) -> dict[str, Any]:
    return {
        "id": f"result_{gate['id']}",
        "type": "deterministic_gate_result",
        "gate_id": gate["id"],
        "target_id": gate["target_id"],
        "gate_type": gate["gate_type"],
        "status": status,
        "rationale": rationale,
        "evidence_refs": [str(item) for item in evidence_refs if item],
    }


def _blocking_evidence(gate_type: str) -> list[str]:
    if gate_type == "external_source_authority":
        return ["source ACL required", "broker source allowlist required"]
    if gate_type == "formula_error_reconciliation":
        return ["formula error reconciliation required", "formula result authority not established"]
    return ["validation plan blocked gate"]


def _target_results(plan: dict[str, Any], gate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in gate_results:
        by_target[result["target_id"]].append(result)
    targets_by_id = {target["id"]: target for target in plan.get("validation_targets", [])}
    results = []
    for target_id, target in targets_by_id.items():
        gates = by_target.get(target_id, [])
        statuses = {item["status"] for item in gates}
        if "blocked" in statuses:
            status = "blocked"
        elif "review_required" in statuses:
            status = "review_required"
        elif gates:
            status = "accepted"
        else:
            status = "review_required"
        results.append(
            {
                "id": f"target_result_{_slug(target_id)}",
                "type": "deterministic_target_result",
                "target_id": target_id,
                "target_type": target["target_type"],
                "status": status,
                "gate_result_ids": [item["id"] for item in gates],
                "authority_blockers": target.get("authority_blockers", []),
            }
        )
    return sorted(results, key=lambda item: (item["status"], item["target_id"]))


def _summary(gate_results: list[dict[str, Any]], target_results: list[dict[str, Any]]) -> dict[str, Any]:
    gate_statuses = Counter(item["status"] for item in gate_results)
    target_statuses = Counter(item["status"] for item in target_results)
    return {
        "gate_result_count": len(gate_results),
        "accepted_gate_count": gate_statuses["accepted"],
        "review_required_gate_count": gate_statuses["review_required"],
        "blocked_gate_count": gate_statuses["blocked"],
        "target_result_count": len(target_results),
        "accepted_target_count": target_statuses["accepted"],
        "review_required_target_count": target_statuses["review_required"],
        "blocked_target_count": target_statuses["blocked"],
        "gate_execution_status": "deterministic_evidence_only",
    }


def _parser_observations(gate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Accepted gates indicate deterministic evidence checks passed; they are not graph promotion decisions.",
        }
    ]
    if any(item["status"] == "blocked" for item in gate_results):
        observations.append(
            {
                "level": "warning",
                "message": "Some gates remain blocked by source authority or formula-error reconciliation gaps.",
            }
        )
    if any(item["status"] == "review_required" for item in gate_results):
        observations.append(
            {
                "level": "warning",
                "message": "Some gates require review because current evidence does not close them deterministically.",
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


def render_google_sheets_gate_execution_section(gate_execution: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in gate_execution["summary"].items()
    )
    gate_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['gate_type'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['target_id'])}</td>"
        f"<td>{_esc(item['rationale'])}</td>"
        "</tr>"
        for item in gate_execution["gate_results"][:100]
    )
    target_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['target_type'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['target_id'])}</td>"
        f"<td>{_esc(', '.join(item['authority_blockers']))}</td>"
        "</tr>"
        for item in gate_execution["target_results"][:100]
    )
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in gate_execution["parser_observations"]
    )
    return f"""
  <h2>Live Gate Execution</h2>
  <section class="grid">{metrics}</section>
  <h2>Gate Results</h2>
  <section class="panel"><table><thead><tr><th>Gate</th><th>Status</th><th>Target</th><th>Rationale</th></tr></thead><tbody>{gate_rows}</tbody></table></section>
  <h2>Target Results</h2>
  <section class="panel"><table><thead><tr><th>Target Type</th><th>Status</th><th>Target</th><th>Authority Blockers</th></tr></thead><tbody>{target_rows}</tbody></table></section>
  <h2>Gate Execution Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute deterministic gates over Google Sheets validation evidence."
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
    args = parser.parse_args()

    gate_execution = build_google_sheets_gate_execution(
        live_cross_validation_plan_path=args.live_cross_validation_plan,
        live_validation_batch_execution_path=args.live_validation_batch_execution,
        live_table_io_pipelines_path=args.live_table_io_pipelines,
        live_block_candidate_tuning_path=args.live_block_candidate_tuning,
    )
    write_google_sheets_gate_execution_package(
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
        gate_execution=gate_execution,
    )


if __name__ == "__main__":
    main()
