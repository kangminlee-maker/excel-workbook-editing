from __future__ import annotations

import argparse
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openpyxl.utils import range_boundaries

from google_sheets_live_manifest import render_live_manifest_html
from google_sheets_source_evidence import (
    build_source_evidence_request,
    load_source_evidence_results,
    source_evidence_response_record,
)


SCHEMA_VERSION = "0.1"


def build_bounded_window_sample(
    *,
    live_block_candidates_path: Path,
    spreadsheet_id: str,
    principal: str = "",
    source_evidence_results_path: Path | None = None,
    source_evidence_results: list[dict[str, Any]] | None = None,
    max_ranges_per_operation: int = 3,
    timeout_seconds: int = 60,
    retry_count: int = 0,
) -> dict[str, Any]:
    live_block_candidates_path = live_block_candidates_path.expanduser().resolve()
    block_candidates = _read_json(live_block_candidates_path)
    plan = _sampling_plan(
        block_candidates,
        spreadsheet_id=spreadsheet_id,
        principal=principal,
        max_ranges_per_operation=max_ranges_per_operation,
        timeout_seconds=timeout_seconds,
        retry_count=retry_count,
    )
    source_results = list(source_evidence_results or [])
    source_results.extend(load_source_evidence_results(source_evidence_results_path))
    responses = [
        _response_record(request, source_results[index])
        for index, request in enumerate(plan["planned_requests"][: len(source_results)])
    ]
    window_summaries = _window_summaries(responses)
    tuning_observations = _tuning_observations(window_summaries, responses)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": spreadsheet_id,
            "title": block_candidates["source"]["title"],
            "source_artifacts": {
                "live_block_candidates": str(live_block_candidates_path),
            },
        },
        "authority": {
            "source_document": "connected_google_sheet_evidence",
            "evidence_backed_read": bool(responses),
            "credential_boundary": "source evidence artifacts are read locally; live Google access is handled by an approved external access surface",
            "formula_result_authority": "not_established",
            "candidate_tuning_status": "bounded_sample_only",
        },
        "sampling_plan": plan,
        "source_evidence_results": responses,
        "window_summaries": window_summaries,
        "tuning_observations": tuning_observations,
        "summary": _summary(plan, responses, window_summaries, tuning_observations),
    }


def write_bounded_window_sample_package(
    *,
    out_dir: Path,
    access_preflight_path: Path,
    live_manifest_path: Path,
    live_view_formula_profile_path: Path,
    live_block_candidates_path: Path,
    bounded_window_sample: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_path = out_dir / "live-bounded-window-sample.json"
    sample_path.write_text(
        json.dumps(bounded_window_sample, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    access_preflight = _read_json(access_preflight_path)
    manifest = _read_json(live_manifest_path)
    view_formula_profile = _read_json(live_view_formula_profile_path)
    block_candidates = _read_json(live_block_candidates_path)
    (out_dir / "index.html").write_text(
        render_live_manifest_html(
            access_preflight=access_preflight,
            manifest=manifest,
            live_view_formula_profile=view_formula_profile,
            live_block_candidates=block_candidates,
            live_bounded_window_sample=bounded_window_sample,
        ),
        encoding="utf-8",
    )


def _sampling_plan(
    block_candidates: dict[str, Any],
    *,
    spreadsheet_id: str,
    principal: str,
    max_ranges_per_operation: int,
    timeout_seconds: int,
    retry_count: int,
) -> dict[str, Any]:
    candidates = []
    for sheet in block_candidates["sheets"]:
        for item in sheet["read_candidates"]:
            if item["status"] != "verified_for_current_policy_limits":
                continue
            candidates.append(
                {
                    **item,
                    "sheet": sheet["name"],
                    "sheet_index": sheet["index"],
                    "priority": _candidate_priority(item, sheet),
                }
            )
    planned_requests = []
    for operation in ("inspect.values_window", "inspect.formula_window"):
        operation_candidates = [
            candidate for candidate in candidates if candidate["operation"] == operation
        ]
        operation_candidates.sort(key=lambda item: (-item["priority"], item["sheet_index"], item["range"]))
        ranges = []
        candidate_ids = []
        for candidate in operation_candidates:
            if candidate["range"] in ranges:
                continue
            ranges.append(candidate["range"])
            candidate_ids.append(candidate["id"])
            if len(ranges) >= max_ranges_per_operation:
                break
        if not ranges:
            continue
        total_cells = sum(_range_cell_count(item) for item in ranges)
        request = build_source_evidence_request(
            spreadsheet_id=spreadsheet_id,
            principal=principal,
            operation=operation,
            ranges=ranges,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            total_cell_count=total_cells,
        )
        planned_requests.append(
            {
                **request,
                "candidate_ids": candidate_ids,
            }
        )
    return {
        "selection_policy": {
            "max_ranges_per_operation": max_ranges_per_operation,
            "priority_order": [
                "formula-bearing profile window with missing display sample",
                "current visible period-tab continuation",
                "formula-surface continuation",
                "large sheet continuation",
            ],
        },
        "candidate_pool_count": len(candidates),
        "planned_request_count": len(planned_requests),
        "planned_requests": planned_requests,
    }


def _candidate_priority(candidate: dict[str, Any], sheet: dict[str, Any]) -> int:
    reason = candidate.get("reason", "")
    if "formula text but no display rows" in reason:
        return 100
    if "confirm formula-bearing profile window" in reason:
        return 95
    if sheet["index"] == 0:
        return 90
    if "formula surface" in reason:
        return 80
    if re.match(r"^\d{2}_\d{4}$", sheet["name"]):
        return 70
    return 50


def _response_record(request: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    return source_evidence_response_record(
        request=request,
        response=response,
        candidate_ids=request.get("candidate_ids", []),
    )


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


def _tuning_observations(
    window_summaries: list[dict[str, Any]],
    responses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    observations = []
    for summary in window_summaries:
        if summary["non_empty_cell_count"] == 0:
            observations.append(
                {
                    "level": "warning",
                    "range": summary["range"],
                    "message": "Bounded sample returned no non-empty cells; candidate may be outside meaningful region or hidden by source logic.",
                }
            )
        if summary["url_cell_samples"]:
            observations.append(
                {
                    "level": "info",
                    "range": summary["range"],
                    "message": "Sample includes URL-like cells that may resolve external source references.",
                    "evidence": summary["url_cell_samples"][:3],
                }
            )
        if summary["error_display_count"]:
            observations.append(
                {
                    "level": "warning",
                    "range": summary["range"],
                    "message": "Sample includes displayed error values; formula result authority remains unresolved.",
                }
            )
        if summary["formula_cell_count"]:
            observations.append(
                {
                    "level": "info",
                    "range": summary["range"],
                    "message": "Formula-window sample confirms formula text in this bounded range.",
                }
            )
    if not responses:
        observations.append(
            {
                "level": "warning",
                "range": None,
                "message": "Sampling plan was generated but source evidence results were not supplied.",
            }
        )
    return observations


def _summary(
    plan: dict[str, Any],
    responses: list[dict[str, Any]],
    window_summaries: list[dict[str, Any]],
    tuning_observations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "planned_request_count": plan["planned_request_count"],
        "evidence_result_count": len(responses),
        "successful_response_count": sum(1 for item in responses if item["ok"]),
        "window_count": len(window_summaries),
        "non_empty_cell_count": sum(item["non_empty_cell_count"] for item in window_summaries),
        "formula_cell_count": sum(item["formula_cell_count"] for item in window_summaries),
        "error_display_count": sum(item["error_display_count"] for item in window_summaries),
        "url_sample_count": sum(len(item["url_cell_samples"]) for item in window_summaries),
        "tuning_observation_count": len(tuning_observations),
        "sampling_status": "evidence_supplied" if responses else "planned_only",
    }


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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def render_bounded_window_sample_section(sample: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in sample["summary"].items()
    )
    plan_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['operation'])}</td>"
        f"<td>{_esc(', '.join(item['ranges']))}</td>"
        f"<td>{_esc(item.get('total_cell_count'))}</td>"
        f"<td>{_esc(', '.join(item.get('candidate_ids', [])))}</td>"
        "</tr>"
        for item in sample["sampling_plan"]["planned_requests"]
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
        for item in sample["window_summaries"]
    )
    if not window_rows:
        window_rows = '<tr><td colspan="6">No source evidence windows supplied.</td></tr>'
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item.get('range'))}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in sample["tuning_observations"]
    )
    return f"""
  <h2>Bounded Candidate-Window Sampling</h2>
  <section class="grid">{metrics}</section>
  <h2>Sampling Plan</h2>
  <section class="panel"><table><thead><tr><th>Operation</th><th>Ranges</th><th>Cells</th><th>Candidate IDs</th></tr></thead><tbody>{plan_rows}</tbody></table></section>
  <h2>Source Evidence Window Summaries</h2>
  <section class="panel"><table><thead><tr><th>Operation</th><th>Range</th><th>Non-empty</th><th>Formula cells</th><th>Error cells</th><th>Preview</th></tr></thead><tbody>{window_rows}</tbody></table></section>
  <h2>Sampling Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Range</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plan bounded parser-window samples and merge local source evidence results."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--access-preflight", type=Path, required=True)
    parser.add_argument("--live-manifest", type=Path, required=True)
    parser.add_argument("--live-view-formula-profile", type=Path, required=True)
    parser.add_argument("--live-block-candidates", type=Path, required=True)
    parser.add_argument("--spreadsheet-id", required=True)
    parser.add_argument("--principal", default="")
    parser.add_argument("--source-evidence-results", type=Path)
    parser.add_argument("--max-ranges-per-operation", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--retry-count", type=int, default=0)
    args = parser.parse_args()

    sample = build_bounded_window_sample(
        live_block_candidates_path=args.live_block_candidates,
        spreadsheet_id=args.spreadsheet_id,
        principal=args.principal,
        source_evidence_results_path=args.source_evidence_results,
        max_ranges_per_operation=args.max_ranges_per_operation,
        timeout_seconds=args.timeout_seconds,
        retry_count=args.retry_count,
    )
    write_bounded_window_sample_package(
        out_dir=args.out_dir,
        access_preflight_path=args.access_preflight,
        live_manifest_path=args.live_manifest,
        live_view_formula_profile_path=args.live_view_formula_profile,
        live_block_candidates_path=args.live_block_candidates,
        bounded_window_sample=sample,
    )


if __name__ == "__main__":
    main()
