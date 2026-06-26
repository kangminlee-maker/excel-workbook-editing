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


def build_google_sheets_evidence_package(
    *,
    live_manifest_path: Path,
    live_block_candidates_path: Path,
    live_table_io_pipelines_path: Path,
    live_cross_validation_plan_path: Path,
    live_validation_batch_execution_path: Path,
    live_gate_execution_path: Path,
) -> dict[str, Any]:
    live_manifest_path = live_manifest_path.expanduser().resolve()
    live_block_candidates_path = live_block_candidates_path.expanduser().resolve()
    live_table_io_pipelines_path = live_table_io_pipelines_path.expanduser().resolve()
    live_cross_validation_plan_path = live_cross_validation_plan_path.expanduser().resolve()
    live_validation_batch_execution_path = live_validation_batch_execution_path.expanduser().resolve()
    live_gate_execution_path = live_gate_execution_path.expanduser().resolve()
    manifest = _read_json(live_manifest_path)
    block_candidates = _read_json(live_block_candidates_path)
    table_io = _read_json(live_table_io_pipelines_path)
    validation_plan = _read_json(live_cross_validation_plan_path)
    validation_batch = _read_json(live_validation_batch_execution_path)
    gate_execution = _read_json(live_gate_execution_path)
    target_plan_by_id = {
        target["id"]: target
        for target in validation_plan.get("validation_targets", [])
    }
    accepted_target_results = [
        item for item in gate_execution.get("target_results", [])
        if item["status"] == "accepted"
    ]
    accepted_pipeline_ids = sorted(
        {
            pipeline_id
            for target in accepted_target_results
            for pipeline_id in target_plan_by_id.get(target["target_id"], {}).get("related_pipeline_ids", [])
        }
    )
    accepted_pipelines = [
        pipeline for pipeline in table_io.get("pipelines", [])
        if pipeline["id"] in accepted_pipeline_ids
    ]
    accepted_gate_results = [
        item for item in gate_execution.get("gate_results", [])
        if item["status"] == "accepted"
    ]
    blocked_gate_results = [
        item for item in gate_execution.get("gate_results", [])
        if item["status"] == "blocked"
    ]
    blocked_target_results = [
        item for item in gate_execution.get("target_results", [])
        if item["status"] == "blocked"
    ]
    review_queue = _review_queue(
        table_io=table_io,
        gate_execution=gate_execution,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": manifest["source"]["spreadsheet_id"],
            "spreadsheet_url": manifest["source"].get("spreadsheet_url"),
            "title": manifest["source"]["title"],
            "source_artifacts": {
                "live_manifest": str(live_manifest_path),
                "live_block_candidates": str(live_block_candidates_path),
                "live_table_io_pipelines": str(live_table_io_pipelines_path),
                "live_cross_validation_plan": str(live_cross_validation_plan_path),
                "live_validation_batch_execution": str(live_validation_batch_execution_path),
                "live_gate_execution": str(live_gate_execution_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "package_status": "connected_sheets_evidence_package_candidate",
            "formula_result_authority": "not_established",
            "source_spreadsheet_read_authority": "blocked_until_source_access_evidence",
            "graph_promotion_status": "not_promoted",
        },
        "workbook_facts": {
            "sheet_count": manifest["summary"]["sheet_count"],
            "hidden_sheet_count": manifest["summary"]["hidden_sheet_count"],
            "view_state_risk_surface_count": _view_state_risk_surface_count(manifest),
            "formula_signal_count": manifest["formula_profile"]["total_formula_count_in_profile_windows"],
            "candidate_block_count": block_candidates["summary"]["block_count"],
            "candidate_region_count": block_candidates["summary"]["cell_region_count"],
        },
        "accepted_evidence": {
            "gate_results": accepted_gate_results,
            "target_results": accepted_target_results,
            "pipelines": accepted_pipelines,
            "validation_evidence_updates": validation_batch.get("evidence_updates", []),
        },
        "blocked_evidence": {
            "gate_results": blocked_gate_results,
            "target_results": blocked_target_results,
        },
        "review_queue": review_queue,
        "lineage_refs": _lineage_refs(
            manifest,
            block_candidates,
            table_io,
            validation_plan,
            validation_batch,
            gate_execution,
        ),
        "summary": _summary(
            accepted_gate_results=accepted_gate_results,
            accepted_target_results=accepted_target_results,
            accepted_pipelines=accepted_pipelines,
            blocked_gate_results=blocked_gate_results,
            blocked_target_results=blocked_target_results,
            review_queue=review_queue,
            validation_batch=validation_batch,
        ),
        "parser_observations": _parser_observations(review_queue),
    }


def write_google_sheets_evidence_package(
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
    evidence_package: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = out_dir / "live-evidence-package.json"
    evidence_path.write_text(
        json.dumps(evidence_package, ensure_ascii=False, indent=2) + "\n",
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
        ),
        encoding="utf-8",
    )


def _review_queue(
    *,
    table_io: dict[str, Any],
    gate_execution: dict[str, Any],
) -> list[dict[str, Any]]:
    queue = []
    for item in table_io.get("external_sources", []):
        queue.append(
            {
                "id": f"review_{item['id']}",
                "type": "external_source_authority_blocker",
                "severity": "high",
                "message": "External IMPORTRANGE source remains blocked until source argument resolution, Google ACL, and source access evidence are confirmed.",
                "evidence_refs": item.get("evidence_refs", []),
                "status": item["status"],
            }
        )
    for item in table_io.get("review_queue", []):
        queue.append(
            {
                "id": item["id"],
                "type": item["type"],
                "severity": item["severity"],
                "message": item["message"],
                "evidence_refs": item.get("evidence_refs", []),
                "status": item["status"],
            }
        )
    blocked_gate_ids = [
        item["id"]
        for item in gate_execution.get("gate_results", [])
        if item["status"] == "blocked"
    ]
    if blocked_gate_ids:
        queue.append(
            {
                "id": "review_blocked_gate_results",
                "type": "blocked_deterministic_gates",
                "severity": "high",
                "message": "Blocked deterministic gates must be resolved before graph promotion.",
                "evidence_refs": blocked_gate_ids[:20],
                "status": "blocked",
            }
        )
    return queue


def _view_state_risk_surface_count(manifest: dict[str, Any]) -> int:
    count = 0
    for sheet in manifest.get("workbook", {}).get("sheets", []):
        view_state = sheet.get("view_state_counts", {})
        if (
            sheet.get("state") == "hidden"
            or view_state.get("hidden_rows_in_profile_window", 0)
            or view_state.get("filtered_rows_in_profile_window", 0)
            or view_state.get("hidden_columns_in_profile_window", 0)
        ):
            count += 1
    return count


def _lineage_refs(*artifacts: dict[str, Any]) -> list[str]:
    refs = []
    for artifact in artifacts:
        source_artifacts = artifact.get("source", {}).get("source_artifacts") or artifact.get("source_artifacts") or {}
        refs.extend(str(value) for value in source_artifacts.values())
    return sorted(set(refs))


def _summary(
    *,
    accepted_gate_results: list[dict[str, Any]],
    accepted_target_results: list[dict[str, Any]],
    accepted_pipelines: list[dict[str, Any]],
    blocked_gate_results: list[dict[str, Any]],
    blocked_target_results: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
    validation_batch: dict[str, Any],
) -> dict[str, Any]:
    return {
        "accepted_gate_count": len(accepted_gate_results),
        "accepted_target_count": len(accepted_target_results),
        "accepted_pipeline_count": len(accepted_pipelines),
        "blocked_gate_count": len(blocked_gate_results),
        "blocked_target_count": len(blocked_target_results),
        "review_queue_count": len(review_queue),
        "validation_evidence_update_count": len(validation_batch.get("evidence_updates", [])),
        "source_spreadsheet_read_count": validation_batch["summary"]["source_spreadsheet_read_count"],
        "package_status": "connected_sheets_evidence_package_candidate",
    }


def _parser_observations(review_queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Evidence package promotes only accepted deterministic evidence into the package body.",
        }
    ]
    if review_queue:
        observations.append(
            {
                "level": "warning",
                "message": f"{len(review_queue)} review queue items remain outside the accepted evidence body.",
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


def render_google_sheets_evidence_package_section(evidence_package: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in evidence_package["summary"].items()
    )
    fact_rows = "".join(
        "<tr>"
        f"<td>{_esc(key)}</td>"
        f"<td>{_esc(value)}</td>"
        "</tr>"
        for key, value in evidence_package["workbook_facts"].items()
    )
    pipeline_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['role'])}</td>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['output_refs'][0]['label'])}</td>"
        f"<td>{_esc(item['confidence'])}</td>"
        "</tr>"
        for item in evidence_package["accepted_evidence"]["pipelines"][:40]
    )
    if not pipeline_rows:
        pipeline_rows = '<tr><td colspan="4">No accepted pipelines in evidence body.</td></tr>'
    queue_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['severity'])}</td>"
        f"<td>{_esc(item['type'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in evidence_package["review_queue"][:80]
    )
    if not queue_rows:
        queue_rows = '<tr><td colspan="4">No review queue items.</td></tr>'
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in evidence_package["parser_observations"]
    )
    return f"""
  <h2>Live Evidence Package</h2>
  <section class="grid">{metrics}</section>
  <h2>Workbook Facts</h2>
  <section class="panel"><table><thead><tr><th>Fact</th><th>Value</th></tr></thead><tbody>{fact_rows}</tbody></table></section>
  <h2>Accepted Pipeline Evidence</h2>
  <section class="panel"><table><thead><tr><th>Role</th><th>Pipeline</th><th>Output</th><th>Confidence</th></tr></thead><tbody>{pipeline_rows}</tbody></table></section>
  <h2>Evidence Review Queue</h2>
  <section class="panel"><table><thead><tr><th>Severity</th><th>Type</th><th>Status</th><th>Message</th></tr></thead><tbody>{queue_rows}</tbody></table></section>
  <h2>Evidence Package Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble connected Google Sheets parser evidence package."
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
    args = parser.parse_args()

    evidence_package = build_google_sheets_evidence_package(
        live_manifest_path=args.live_manifest,
        live_block_candidates_path=args.live_block_candidates,
        live_table_io_pipelines_path=args.live_table_io_pipelines,
        live_cross_validation_plan_path=args.live_cross_validation_plan,
        live_validation_batch_execution_path=args.live_validation_batch_execution,
        live_gate_execution_path=args.live_gate_execution,
    )
    write_google_sheets_evidence_package(
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
        evidence_package=evidence_package,
    )


if __name__ == "__main__":
    main()
