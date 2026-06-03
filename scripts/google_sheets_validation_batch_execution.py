from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openpyxl.utils import range_boundaries

from google_sheets_live_manifest import render_live_manifest_html


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "cli" / "sheets-bridge"))

from sheets_bridge_cli import (  # noqa: E402
    DEFAULT_BROKER_URL,
    build_inspect_request,
    invoke_broker_inspect,
)


SCHEMA_VERSION = "0.1"


def build_google_sheets_validation_batch_execution(
    *,
    live_cross_validation_plan_path: Path,
    spreadsheet_id: str,
    principal: str,
    execute: bool = False,
    broker_url: str = DEFAULT_BROKER_URL,
    timeout_seconds: int = 60,
    retry_count: int = 0,
    broker_invoker=None,
) -> dict[str, Any]:
    live_cross_validation_plan_path = live_cross_validation_plan_path.expanduser().resolve()
    plan = _read_json(live_cross_validation_plan_path)
    requests = _planned_requests(
        plan,
        spreadsheet_id=spreadsheet_id,
        principal=principal,
        timeout_seconds=timeout_seconds,
        retry_count=retry_count,
    )
    responses = []
    if execute:
        for request in requests:
            response = _invoke_request(
                request,
                broker_url=broker_url,
                broker_invoker=broker_invoker,
            )
            responses.append(_response_record(request, response))
    windows = _window_summaries(responses)
    evidence_updates = _evidence_updates(windows)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": spreadsheet_id,
            "title": plan["source"]["title"],
            "source_artifacts": {
                "live_cross_validation_plan": str(live_cross_validation_plan_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "broker_backed_read": execute,
            "read_scope": "current_workbook_planned_broker_batches_only",
            "source_spreadsheet_reads_performed": False,
            "credential_boundary": "identity token sent only to broker; no OAuth tokens, access tokens, bearer headers, or service account keys stored",
            "formula_result_authority": "not_established",
        },
        "execution_plan": {
            "source_plan_status": plan["broker_read_plan"]["status"],
            "planned_request_count": len(requests),
            "planned_requests": requests,
            "blocked_source_reads": plan["broker_read_plan"].get("blocked_source_reads", []),
        },
        "broker_responses": responses,
        "window_summaries": windows,
        "evidence_updates": evidence_updates,
        "summary": _summary(requests, responses, windows, evidence_updates),
        "parser_observations": _parser_observations(requests, responses, windows),
    }


def write_google_sheets_validation_batch_execution_package(
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
    validation_batch_execution: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    execution_path = out_dir / "live-validation-batch-execution.json"
    execution_path.write_text(
        json.dumps(validation_batch_execution, ensure_ascii=False, indent=2) + "\n",
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
            live_validation_batch_execution=validation_batch_execution,
        ),
        encoding="utf-8",
    )


def _planned_requests(
    plan: dict[str, Any],
    *,
    spreadsheet_id: str,
    principal: str,
    timeout_seconds: int,
    retry_count: int,
) -> list[dict[str, Any]]:
    requests = []
    for batch in plan.get("broker_read_plan", {}).get("batches", []):
        total_cells = sum(_range_cell_count(range_text) for range_text in batch["ranges"])
        request = build_inspect_request(
            spreadsheet_id=spreadsheet_id,
            principal=principal,
            operation=batch["operation"],
            ranges=batch["ranges"],
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            total_cell_count=total_cells,
        )
        request["source_batch_id"] = batch["id"]
        request["read_candidate_ids"] = batch["read_candidate_ids"]
        requests.append(request)
    return requests


def _invoke_request(
    request: dict[str, Any],
    *,
    broker_url: str,
    broker_invoker,
) -> dict[str, Any]:
    if broker_invoker:
        return broker_invoker(request)
    return invoke_broker_inspect(broker_url=broker_url, request=request)


def _response_record(request: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    payload = response.get("payload", {}) if response.get("ok") else response
    return {
        "operation": request["operation"],
        "source_batch_id": request.get("source_batch_id"),
        "requested_ranges": request["ranges"],
        "read_candidate_ids": request.get("read_candidate_ids", []),
        "ok": bool(response.get("ok")),
        "payload": payload,
    }


def _window_summaries(responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for response in responses:
        payload = response.get("payload", {})
        operation = response["operation"]
        for window in payload.get("windows", []) or []:
            values = window.get("values", []) or []
            summaries.append(
                {
                    "operation": operation,
                    "range": window.get("range", ""),
                    "row_count": window.get("row_count", len(values)),
                    "column_count": window.get("column_count", _max_columns(values)),
                    "non_empty_cell_count": _non_empty_cell_count(values),
                    "formula_cell_count": _formula_cell_count(values),
                    "error_display_count": _error_display_count(values),
                    "url_cell_samples": _url_cell_samples(values),
                    "text_preview": _text_preview(values),
                }
            )
    return summaries


def _evidence_updates(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    updates = []
    for window in windows:
        if window["non_empty_cell_count"]:
            updates.append(
                {
                    "id": f"evidence_display_{_slug(window['operation'])}_{_slug(window['range'])}",
                    "type": "bounded_window_surface_observed",
                    "range": window["range"],
                    "operation": window["operation"],
                    "status": "candidate_evidence",
                    "effect": "supports_surface_presence_gate",
                }
            )
        if window["formula_cell_count"]:
            updates.append(
                {
                    "id": f"evidence_formula_{_slug(window['range'])}",
                    "type": "bounded_formula_text_observed",
                    "range": window["range"],
                    "operation": window["operation"],
                    "status": "candidate_evidence",
                    "effect": "supports_formula_text_dependency_trace_gate",
                }
            )
        if window["error_display_count"]:
            updates.append(
                {
                    "id": f"evidence_error_{_slug(window['range'])}",
                    "type": "bounded_error_surface_observed",
                    "range": window["range"],
                    "operation": window["operation"],
                    "status": "requires_formula_result_review",
                    "effect": "keeps_formula_error_reconciliation_gate_blocked",
                }
            )
    return updates


def _summary(
    requests: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    windows: list[dict[str, Any]],
    evidence_updates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "planned_request_count": len(requests),
        "executed_request_count": len(responses),
        "successful_response_count": sum(1 for item in responses if item["ok"]),
        "window_count": len(windows),
        "non_empty_cell_count": sum(item["non_empty_cell_count"] for item in windows),
        "formula_cell_count": sum(item["formula_cell_count"] for item in windows),
        "error_display_count": sum(item["error_display_count"] for item in windows),
        "url_sample_count": sum(len(item["url_cell_samples"]) for item in windows),
        "evidence_update_count": len(evidence_updates),
        "source_spreadsheet_read_count": 0,
        "execution_status": "executed" if responses else "planned_only",
    }


def _parser_observations(
    requests: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    windows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Validation batch execution uses only current-workbook broker-bounded parser windows.",
        }
    ]
    if requests and not responses:
        observations.append(
            {
                "level": "warning",
                "message": "Execution plan was generated but broker execution was not performed.",
            }
        )
    if any(not response["ok"] for response in responses):
        observations.append(
            {
                "level": "error",
                "message": "At least one planned broker batch failed.",
            }
        )
    if any(window["formula_cell_count"] for window in windows):
        observations.append(
            {
                "level": "info",
                "message": "Formula-window evidence was returned for planned validation ranges.",
            }
        )
    if any(window["error_display_count"] for window in windows):
        observations.append(
            {
                "level": "warning",
                "message": "Returned windows include displayed errors; formula-result authority remains unestablished.",
            }
        )
    return observations


def _range_cell_count(range_text: str) -> int:
    _, a1 = range_text.split("!", 1)
    min_col, min_row, max_col, max_row = range_boundaries(a1)
    return (max_col - min_col + 1) * (max_row - min_row + 1)


def _max_columns(values: list[list[Any]]) -> int:
    return max((len(row) for row in values), default=0)


def _non_empty_cell_count(values: list[list[Any]]) -> int:
    return sum(1 for row in values for value in row if value not in ("", None))


def _formula_cell_count(values: list[list[Any]]) -> int:
    return sum(
        1
        for row in values
        for value in row
        if isinstance(value, str) and value.startswith("=")
    )


def _error_display_count(values: list[list[Any]]) -> int:
    return sum(
        1
        for row in values
        for value in row
        if isinstance(value, str) and value.startswith("#")
    )


def _url_cell_samples(values: list[list[Any]]) -> list[str]:
    samples = []
    for row_index, row in enumerate(values, start=1):
        for column_index, value in enumerate(row, start=1):
            if isinstance(value, str) and value.startswith("http"):
                samples.append(f"R{row_index}C{column_index}: {value}")
            if len(samples) >= 5:
                return samples
    return samples


def _text_preview(values: list[list[Any]]) -> list[str]:
    preview = []
    for row_index, row in enumerate(values, start=1):
        non_empty = [str(value).replace("\n", " ").strip() for value in row if value not in ("", None)]
        if non_empty:
            preview.append(f"R{row_index}: " + " | ".join(non_empty[:8]))
        if len(preview) >= 6:
            break
    return preview


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


def render_google_sheets_validation_batch_execution_section(execution: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in execution["summary"].items()
    )
    request_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['operation'])}</td>"
        f"<td>{_esc(item.get('total_cell_count'))}</td>"
        f"<td>{_esc(', '.join(item['ranges'][:4]))}</td>"
        "</tr>"
        for item in execution["execution_plan"]["planned_requests"]
    )
    window_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['operation'])}</td>"
        f"<td>{_esc(item['range'])}</td>"
        f"<td>{_esc(item['non_empty_cell_count'])}</td>"
        f"<td>{_esc(item['formula_cell_count'])}</td>"
        f"<td>{_esc(item['error_display_count'])}</td>"
        f"<td>{_esc(' / '.join(item['text_preview'][:2]))}</td>"
        "</tr>"
        for item in execution["window_summaries"][:80]
    )
    if not window_rows:
        window_rows = '<tr><td colspan="6">No executed validation windows.</td></tr>'
    update_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['type'])}</td>"
        f"<td>{_esc(item['range'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['effect'])}</td>"
        "</tr>"
        for item in execution["evidence_updates"][:80]
    )
    if not update_rows:
        update_rows = '<tr><td colspan="4">No evidence updates emitted.</td></tr>'
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in execution["parser_observations"]
    )
    return f"""
  <h2>Validation Batch Execution</h2>
  <section class="grid">{metrics}</section>
  <h2>Executed Broker Requests</h2>
  <section class="panel"><table><thead><tr><th>Operation</th><th>Cells</th><th>Sample Ranges</th></tr></thead><tbody>{request_rows}</tbody></table></section>
  <h2>Validation Window Summaries</h2>
  <section class="panel"><table><thead><tr><th>Operation</th><th>Range</th><th>Non-empty</th><th>Formula cells</th><th>Error cells</th><th>Preview</th></tr></thead><tbody>{window_rows}</tbody></table></section>
  <h2>Validation Evidence Updates</h2>
  <section class="panel"><table><thead><tr><th>Type</th><th>Range</th><th>Status</th><th>Effect</th></tr></thead><tbody>{update_rows}</tbody></table></section>
  <h2>Validation Execution Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute planned current-workbook bounded validation batches for Google Sheets."
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
    parser.add_argument("--spreadsheet-id", required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("--broker-url", default=DEFAULT_BROKER_URL)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--retry-count", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    execution = build_google_sheets_validation_batch_execution(
        live_cross_validation_plan_path=args.live_cross_validation_plan,
        spreadsheet_id=args.spreadsheet_id,
        principal=args.principal,
        execute=args.execute,
        broker_url=args.broker_url,
        timeout_seconds=args.timeout_seconds,
        retry_count=args.retry_count,
    )
    write_google_sheets_validation_batch_execution_package(
        out_dir=args.out_dir,
        access_preflight_path=args.access_preflight,
        live_manifest_path=args.live_manifest,
        live_view_formula_profile_path=args.live_view_formula_profile,
        live_block_candidates_path=args.live_block_candidates,
        bounded_window_sample_path=args.bounded_window_sample,
        live_block_candidate_tuning_path=args.live_block_candidate_tuning,
        live_table_io_pipelines_path=args.live_table_io_pipelines,
        live_cross_validation_plan_path=args.live_cross_validation_plan,
        validation_batch_execution=execution,
    )


if __name__ == "__main__":
    main()
