from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1"
READONLY_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
DYNAMIC_FORMULA_CLASSES = {
    "importrange",
    "import_function",
    "query",
    "arrayformula",
    "indirect",
    "volatile_reference",
    "custom_function_like",
}


def build_live_manifest(
    *,
    access_preflight: dict[str, Any],
    top_left_sample: dict[str, Any],
    grid_profiles: dict[str, dict[str, Any]] | None = None,
    profile_range: str = "A1:Z80",
    live_fetch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    grid_profiles = grid_profiles or {}
    formula_profile = _formula_profile(top_left_sample)
    sheets = [
        _sheet_profile(tab, top_left_sample, formula_profile, grid_profiles)
        for tab in access_preflight.get("tabs", [])
    ]
    permission_gaps = _permission_gaps()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": access_preflight["spreadsheet_id"],
            "spreadsheet_url": access_preflight.get("spreadsheet_url"),
            "title": access_preflight.get("title", ""),
            "locale": access_preflight.get("locale", ""),
            "time_zone": access_preflight.get("time_zone", ""),
            "source_artifacts": {
                "access_preflight": "access-preflight.json",
                "inspection": "inspection.json",
                "top_left_sample": "top-left-sample.json",
            },
        },
        "authority": _authority(access_preflight),
        "limits": {
            "profile_range": profile_range,
            "value_sample_authorities": ["FORMULA", "FORMATTED_VALUE"],
            "grid_profile_authority": "Sheets API includeGridData readonly",
            "formula_result_authority": "not_established",
        },
        "live_fetch": live_fetch or {
            "performed": False,
            "reason": "manifest built from existing access preflight and sample artifacts",
        },
        "workbook": {
            "sheet_count": len(sheets),
            "sheets": sheets,
        },
        "formula_profile": formula_profile["summary"],
        "view_state_profile": _view_state_profile(sheets),
        "parser_observations": _parser_observations(
            access_preflight,
            sheets,
            formula_profile["summary"],
            permission_gaps,
        ),
        "permission_gaps": permission_gaps,
        "summary": _summary(sheets, formula_profile["summary"]),
    }


def fetch_grid_profiles(
    *,
    spreadsheet_id: str,
    key_file: Path,
    subject: str,
    ranges: list[str],
    chunk_size: int = 8,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_file(
        str(key_file),
        scopes=[READONLY_SHEETS_SCOPE],
    ).with_subject(subject)
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    grid_profiles: dict[str, dict[str, Any]] = {}
    request_count = 0
    started = datetime.now(UTC)
    fields = ",".join(
        [
            "spreadsheetId",
            "sheets(properties(sheetId,title,index,hidden,gridProperties(rowCount,columnCount,frozenRowCount,frozenColumnCount)),"
            "data(startRow,startColumn,rowData(values(formattedValue,userEnteredValue,effectiveValue,"
            "userEnteredFormat(backgroundColor,textFormat(bold,italic,fontSize,foregroundColor),horizontalAlignment,verticalAlignment,borders),"
            "dataValidation,pivotTable,note)),rowMetadata(hiddenByUser,hiddenByFilter,pixelSize),columnMetadata(hiddenByUser,pixelSize)),"
            "merges,protectedRanges(protectedRangeId,range,warningOnly),basicFilter,filterViews(filterViewId,title,range),"
            "charts(chartId,spec/title,position),bandedRanges(bandedRangeId,range))",
        ]
    )

    for chunk in _chunks(ranges, max(1, chunk_size)):
        request_count += 1
        response = (
            service.spreadsheets()
            .get(
                spreadsheetId=spreadsheet_id,
                ranges=chunk,
                includeGridData=True,
                fields=fields,
            )
            .execute()
        )
        for sheet in response.get("sheets", []) or []:
            title = sheet.get("properties", {}).get("title", "")
            if title:
                grid_profiles[title] = _summarize_grid_sheet(sheet)

    elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    return grid_profiles, {
        "performed": True,
        "scope": READONLY_SHEETS_SCOPE,
        "request_count": request_count,
        "range_count": len(ranges),
        "elapsed_ms": elapsed_ms,
        "credential_handling": "external_key_file_used_not_copied",
    }


def render_live_manifest_html(
    *,
    access_preflight: dict[str, Any],
    manifest: dict[str, Any],
    live_view_formula_profile: dict[str, Any] | None = None,
    live_block_candidates: dict[str, Any] | None = None,
    live_bounded_window_sample: dict[str, Any] | None = None,
    live_block_candidate_tuning: dict[str, Any] | None = None,
    live_table_io_pipelines: dict[str, Any] | None = None,
    live_cross_validation_plan: dict[str, Any] | None = None,
    live_validation_batch_execution: dict[str, Any] | None = None,
    live_gate_execution: dict[str, Any] | None = None,
    live_evidence_package: dict[str, Any] | None = None,
    live_document_ontology_mapping: dict[str, Any] | None = None,
    live_action_contracts: dict[str, Any] | None = None,
    live_domain_source_model: dict[str, Any] | None = None,
    live_semantic_proposals: dict[str, Any] | None = None,
    live_semantic_proposal_validation: dict[str, Any] | None = None,
    live_validated_document_graph: dict[str, Any] | None = None,
    live_data_view_projection: dict[str, Any] | None = None,
    live_local_semantic_candidates: dict[str, Any] | None = None,
    live_shared_ontology_alignment_review: dict[str, Any] | None = None,
    live_process_redesign_review: dict[str, Any] | None = None,
    live_blocker_resolution_update: dict[str, Any] | None = None,
    live_formula_result_authority_checkpoint: dict[str, Any] | None = None,
    live_document_item_grouping_checkpoint: dict[str, Any] | None = None,
    live_version_breakpoint_detection: dict[str, Any] | None = None,
    live_semantic_gate_iteration: dict[str, Any] | None = None,
    live_carry_forward_review_packet: dict[str, Any] | None = None,
) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in manifest["summary"].items()
    )
    authority_rows = _kv_rows(
        {
            "spreadsheetId": manifest["source"]["spreadsheet_id"],
            "source authority": "live_google_sheet",
            "access mode": manifest["authority"]["access_mode"],
            "impersonated subject": manifest["authority"]["impersonated_subject"],
            "formula result authority": manifest["limits"]["formula_result_authority"],
            "write operation": manifest["authority"]["write_operation"],
        }
    )
    sheet_rows = "".join(_sheet_row(sheet) for sheet in manifest["workbook"]["sheets"])
    observation_rows = "".join(
        "<tr>"
        f"<td>{_pill(item['severity'], _tone(item['severity']))}</td>"
        f"<td>{_esc(item['message'])}</td>"
        f"<td>{_esc(', '.join(item.get('evidence_refs', [])))}</td>"
        "</tr>"
        for item in manifest["parser_observations"]
    )
    gap_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['capability'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['needed_when'])}</td>"
        f"<td>{_esc(item['do_not_workaround'])}</td>"
        "</tr>"
        for item in manifest["permission_gaps"]
    )
    dynamic_rows = "".join(
        "<tr>"
        f"<td>{_esc(key)}</td><td>{_esc(value)}</td>"
        "</tr>"
        for key, value in manifest["formula_profile"]["classification_counts"].items()
    )
    if not dynamic_rows:
        dynamic_rows = '<tr><td colspan="2">No dynamic formula classifications found.</td></tr>'
    extra_sections = ""
    if live_view_formula_profile:
        from google_sheets_live_view_formula_profile import (
            render_live_view_formula_profile_section,
        )

        extra_sections = render_live_view_formula_profile_section(
            live_view_formula_profile
        )
    if live_block_candidates:
        from google_sheets_live_block_candidates import (
            render_live_block_candidates_section,
        )

        extra_sections += render_live_block_candidates_section(live_block_candidates)
    if live_bounded_window_sample:
        from google_sheets_bounded_window_sample import (
            render_bounded_window_sample_section,
        )

        extra_sections += render_bounded_window_sample_section(
            live_bounded_window_sample
        )
    if live_block_candidate_tuning:
        from google_sheets_block_candidate_tuning import (
            render_block_candidate_tuning_section,
        )

        extra_sections += render_block_candidate_tuning_section(
            live_block_candidate_tuning
        )
    if live_table_io_pipelines:
        from google_sheets_table_io_pipelines import (
            render_google_sheets_table_io_pipelines_section,
        )

        extra_sections += render_google_sheets_table_io_pipelines_section(
            live_table_io_pipelines
        )
    if live_cross_validation_plan:
        from google_sheets_cross_validation_plan import (
            render_google_sheets_cross_validation_plan_section,
        )

        extra_sections += render_google_sheets_cross_validation_plan_section(
            live_cross_validation_plan
        )
    if live_validation_batch_execution:
        from google_sheets_validation_batch_execution import (
            render_google_sheets_validation_batch_execution_section,
        )

        extra_sections += render_google_sheets_validation_batch_execution_section(
            live_validation_batch_execution
        )
    if live_gate_execution:
        from google_sheets_gate_execution import (
            render_google_sheets_gate_execution_section,
        )

        extra_sections += render_google_sheets_gate_execution_section(
            live_gate_execution
        )
    if live_evidence_package:
        from google_sheets_evidence_package import (
            render_google_sheets_evidence_package_section,
        )

        extra_sections += render_google_sheets_evidence_package_section(
            live_evidence_package
        )
    if live_document_ontology_mapping:
        from google_sheets_document_ontology_mapping import (
            render_google_sheets_document_ontology_mapping_section,
        )

        extra_sections += render_google_sheets_document_ontology_mapping_section(
            live_document_ontology_mapping
        )
    if live_action_contracts:
        from google_sheets_action_contracts import (
            render_google_sheets_action_contracts_section,
        )

        extra_sections += render_google_sheets_action_contracts_section(
            live_action_contracts
        )
    if live_domain_source_model:
        from google_sheets_domain_source_model import (
            render_google_sheets_domain_source_model_section,
        )

        extra_sections += render_google_sheets_domain_source_model_section(
            live_domain_source_model
        )
    if live_semantic_proposals:
        from google_sheets_semantic_proposals import (
            render_google_sheets_semantic_proposals_section,
        )

        extra_sections += render_google_sheets_semantic_proposals_section(
            live_semantic_proposals
        )
    if live_semantic_proposal_validation:
        from google_sheets_semantic_proposal_validation import (
            render_google_sheets_semantic_proposal_validation_section,
        )

        extra_sections += render_google_sheets_semantic_proposal_validation_section(
            live_semantic_proposal_validation
        )
    if live_validated_document_graph:
        from google_sheets_validated_document_graph import (
            render_google_sheets_validated_document_graph_section,
        )

        extra_sections += render_google_sheets_validated_document_graph_section(
            live_validated_document_graph
        )
    if live_data_view_projection:
        from google_sheets_data_view_projection import (
            render_google_sheets_data_view_projection_section,
        )

        extra_sections += render_google_sheets_data_view_projection_section(
            live_data_view_projection
        )
    if live_local_semantic_candidates:
        from google_sheets_local_semantic_candidates import (
            render_google_sheets_local_semantic_candidates_section,
        )

        extra_sections += render_google_sheets_local_semantic_candidates_section(
            live_local_semantic_candidates
        )
    if live_shared_ontology_alignment_review:
        from google_sheets_shared_ontology_alignment_review import (
            render_google_sheets_shared_ontology_alignment_review_section,
        )

        extra_sections += render_google_sheets_shared_ontology_alignment_review_section(
            live_shared_ontology_alignment_review
        )
    if live_process_redesign_review:
        from google_sheets_process_redesign_review import (
            render_google_sheets_process_redesign_review_section,
        )

        extra_sections += render_google_sheets_process_redesign_review_section(
            live_process_redesign_review
        )
    if live_blocker_resolution_update:
        from google_sheets_blocker_resolution_update import (
            render_google_sheets_blocker_resolution_update_section,
        )

        extra_sections += render_google_sheets_blocker_resolution_update_section(
            live_blocker_resolution_update
        )
    if live_formula_result_authority_checkpoint:
        from google_sheets_formula_result_authority_checkpoint import (
            render_google_sheets_formula_result_authority_checkpoint_section,
        )

        extra_sections += (
            render_google_sheets_formula_result_authority_checkpoint_section(
                live_formula_result_authority_checkpoint
            )
        )
    if live_document_item_grouping_checkpoint:
        from google_sheets_document_item_grouping_checkpoint import (
            render_google_sheets_document_item_grouping_checkpoint_section,
        )

        extra_sections += (
            render_google_sheets_document_item_grouping_checkpoint_section(
                live_document_item_grouping_checkpoint
            )
        )
    if live_version_breakpoint_detection:
        from google_sheets_version_breakpoint_detection import (
            render_google_sheets_version_breakpoint_detection_section,
        )

        extra_sections += render_google_sheets_version_breakpoint_detection_section(
            live_version_breakpoint_detection
        )
    if live_semantic_gate_iteration:
        from google_sheets_semantic_gate_iteration import (
            render_google_sheets_semantic_gate_iteration_section,
        )

        extra_sections += render_google_sheets_semantic_gate_iteration_section(
            live_semantic_gate_iteration
        )
    if live_carry_forward_review_packet:
        from google_sheets_carry_forward_review_packet import (
            render_google_sheets_carry_forward_review_packet_section,
        )

        extra_sections += render_google_sheets_carry_forward_review_packet_section(
            live_carry_forward_review_packet
        )

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Google Sheets Live Manifest/Profile</title>
  <style>
    :root {{ color-scheme: light; --bg:#f6f7f9; --panel:#fff; --ink:#17202a; --muted:#667085; --line:#d8dee8; --accent:#166b8f; --ok:#147a46; --warn:#9a5b00; --bad:#a03535; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:var(--bg); }}
    header {{ padding:24px 28px; background:var(--panel); border-bottom:1px solid var(--line); }}
    main {{ padding:20px 28px 40px; max-width:1400px; margin:0 auto; }}
    h1 {{ margin:0 0 8px; font-size:24px; }}
    h2 {{ margin:28px 0 10px; font-size:18px; }}
    p {{ margin:6px 0; color:var(--muted); }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; }}
    .metric {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; min-height:72px; }}
    .label {{ color:var(--muted); font-size:12px; overflow-wrap:anywhere; }}
    .value {{ font-weight:700; font-size:20px; margin-top:4px; overflow-wrap:anywhere; }}
    .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; overflow:auto; }}
    table {{ width:100%; border-collapse:collapse; min-width:860px; }}
    th,td {{ border-bottom:1px solid var(--line); padding:8px 9px; text-align:left; vertical-align:top; }}
    th {{ background:#eef3f7; font-size:12px; color:#344054; position:sticky; top:0; }}
    code {{ white-space:pre-wrap; overflow-wrap:anywhere; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }}
    .pill {{ display:inline-block; border:1px solid #b9d6c6; color:var(--ok); background:#edf8f1; border-radius:999px; padding:2px 8px; font-size:12px; font-weight:650; margin:1px 2px 1px 0; }}
    .pill.warn {{ border-color:#e5c37b; color:var(--warn); background:#fff8e8; }}
    .pill.bad {{ border-color:#e8a1a1; color:var(--bad); background:#fff0f0; }}
    .kv {{ display:grid; grid-template-columns:210px 1fr; gap:6px 14px; }}
    .kv div:nth-child(odd) {{ color:var(--muted); }}
    @media (max-width:720px) {{ header,main {{ padding-left:14px; padding-right:14px; }} .kv {{ grid-template-columns:1fr; }} table {{ min-width:760px; }} }}
  </style>
</head>
<body>
<header>
  <h1>Google Sheets Live Manifest/Profile</h1>
  <p>{_esc(manifest["source"]["title"])} · profile range {_esc(manifest["limits"]["profile_range"])}</p>
</header>
<main>
  <section class="panel"><div class="kv">{authority_rows}</div></section>
  <h2>Summary</h2>
  <section class="grid">{metrics}</section>
  <h2>Sheet Profiles</h2>
  <section class="panel">
    <table>
      <thead><tr><th>#</th><th>Sheet</th><th>sheetId</th><th>State</th><th>Size</th><th>Sample</th><th>View State</th><th>Objects</th><th>Signals</th></tr></thead>
      <tbody>{sheet_rows}</tbody>
    </table>
  </section>
  <h2>Dynamic Formula Signals</h2>
  <section class="panel"><table><thead><tr><th>Class</th><th>Count</th></tr></thead><tbody>{dynamic_rows}</tbody></table></section>
  <h2>Parser Observations</h2>
  <section class="panel"><table><thead><tr><th>Severity</th><th>Message</th><th>Evidence</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
  <h2>Permission Gaps</h2>
  <section class="panel"><table><thead><tr><th>Capability</th><th>Status</th><th>Needed When</th><th>Handling</th></tr></thead><tbody>{gap_rows}</tbody></table></section>
{extra_sections}
</main>
</body>
</html>
"""


def write_live_manifest_package(
    *,
    out_dir: Path,
    access_preflight_path: Path,
    top_left_sample_path: Path,
    manifest: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "live-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    access_preflight = _read_json(access_preflight_path)
    (out_dir / "index.html").write_text(
        render_live_manifest_html(
            access_preflight=access_preflight,
            manifest=manifest,
        ),
        encoding="utf-8",
    )


def _sheet_profile(
    tab: dict[str, Any],
    top_left_sample: dict[str, Any],
    formula_profile: dict[str, Any],
    grid_profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    title = tab["title"]
    sample = _sample_for_sheet(top_left_sample, title)
    grid = grid_profiles.get(title, {})
    formula_counts = formula_profile["by_sheet"].get(
        title,
        {
            "formula_cell_count": 0,
            "dynamic_formula_cell_count": 0,
            "classification_counts": {},
            "cross_sheet_formula_count": 0,
        },
    )
    object_counts = {
        "charts": tab.get("chart_count", 0),
        "banded_ranges": tab.get("banded_range_count", 0),
        "protected_ranges": tab.get("protected_range_count", 0),
        "filter_views": tab.get("filter_view_count", 0),
        "basic_filter": 1 if tab.get("has_basic_filter") else 0,
        "merges_in_profile_window": grid.get("merge_count", 0),
    }
    view_state_counts = {
        "hidden_rows_in_profile_window": grid.get("hidden_row_count", 0),
        "filtered_rows_in_profile_window": grid.get("filtered_row_count", 0),
        "hidden_columns_in_profile_window": grid.get("hidden_column_count", 0),
    }
    style_counts = grid.get(
        "style_counts",
        {
            "bold_cell_count": 0,
            "filled_cell_count": 0,
            "bordered_cell_count": 0,
            "data_validation_cell_count": 0,
            "note_cell_count": 0,
        },
    )
    sheet = {
        "name": title,
        "sheet_id": tab["sheet_id"],
        "index": tab["index"],
        "state": "hidden" if tab.get("hidden") else "visible",
        "dimensions": {
            "row_count": tab.get("row_count", 0),
            "column_count": tab.get("column_count", 0),
            "frozen_row_count": tab.get("frozen_row_count", 0),
            "frozen_column_count": tab.get("frozen_column_count", 0),
        },
        "profile_window": {
            "range": sample.get("sample_range", "A1:Z80"),
            "grid_data_fetched": bool(grid),
        },
        "sample_counts": sample.get(
            "summary",
            {
                "non_empty_cell_count_in_sample": 0,
                "formula_cell_count_in_sample": 0,
            },
        ),
        "grid_counts": grid.get(
            "grid_counts",
            {
                "non_empty_cell_count": 0,
                "string_cell_count": 0,
                "number_cell_count": 0,
                "bool_cell_count": 0,
                "error_cell_count": 0,
                "pivot_table_cell_count": 0,
            },
        ),
        "view_state_counts": view_state_counts,
        "object_counts": object_counts,
        "style_counts": style_counts,
        "formula_counts": formula_counts,
        "role_hints": [],
        "risk_flags": [],
    }
    sheet["role_hints"] = _role_hints(sheet)
    sheet["risk_flags"] = _risk_flags(sheet)
    return sheet


def _formula_profile(top_left_sample: dict[str, Any]) -> dict[str, Any]:
    by_sheet: dict[str, Any] = defaultdict(
        lambda: {
            "formula_cell_count": 0,
            "dynamic_formula_cell_count": 0,
            "classification_counts": Counter(),
            "cross_sheet_formula_count": 0,
        }
    )
    classification_counts: Counter[str] = Counter()
    total_formula_count = 0
    cross_sheet_formula_count = 0
    formula_samples = top_left_sample.get("formula_samples") or []
    if formula_samples:
        for item in formula_samples:
            title = item.get("sheet_title", "")
            formula = item.get("formula", "")
            if not isinstance(formula, str) or not formula.startswith("="):
                continue
            total_formula_count += 1
            by_sheet[title]["formula_cell_count"] += 1
            classes = classify_formula(formula)
            if classes:
                by_sheet[title]["dynamic_formula_cell_count"] += 1
            for class_name in classes:
                by_sheet[title]["classification_counts"][class_name] += 1
                classification_counts[class_name] += 1
            if _has_cross_sheet_reference(formula, title):
                by_sheet[title]["cross_sheet_formula_count"] += 1
                cross_sheet_formula_count += 1
        return _serializable_formula_profile(
            by_sheet,
            classification_counts,
            total_formula_count,
            cross_sheet_formula_count,
        )

    for tab in top_left_sample.get("tabs", []):
        title = tab.get("title", "")
        for row in tab.get("formula_rows", []):
            for value in row:
                if isinstance(value, str) and value.startswith("="):
                    total_formula_count += 1
                    by_sheet[title]["formula_cell_count"] += 1
                    classes = classify_formula(value)
                    if classes:
                        by_sheet[title]["dynamic_formula_cell_count"] += 1
                    for class_name in classes:
                        by_sheet[title]["classification_counts"][class_name] += 1
                        classification_counts[class_name] += 1
                    if _has_cross_sheet_reference(value, title):
                        by_sheet[title]["cross_sheet_formula_count"] += 1
                        cross_sheet_formula_count += 1
    return _serializable_formula_profile(
        by_sheet,
        classification_counts,
        total_formula_count,
        cross_sheet_formula_count,
    )


def _serializable_formula_profile(
    by_sheet: dict[str, Any],
    classification_counts: Counter[str],
    total_formula_count: int,
    cross_sheet_formula_count: int,
) -> dict[str, Any]:
    serializable_by_sheet = {}
    for title, counts in by_sheet.items():
        serializable_by_sheet[title] = {
            **counts,
            "classification_counts": dict(counts["classification_counts"]),
        }
    return {
        "by_sheet": serializable_by_sheet,
        "summary": {
            "total_formula_count_in_profile_windows": total_formula_count,
            "dynamic_formula_count_in_profile_windows": sum(classification_counts.values()),
            "cross_sheet_formula_count_in_profile_windows": cross_sheet_formula_count,
            "classification_counts": dict(classification_counts),
        },
    }


def classify_formula(formula: str) -> list[str]:
    upper = formula.upper()
    classes: list[str] = []
    if "IMPORTRANGE" in upper:
        classes.append("importrange")
    if re.search(r"=\s*(IMPORTXML|IMPORTHTML|IMPORTDATA|IMPORTFEED)\b", upper):
        classes.append("import_function")
    if re.search(r"=\s*QUERY\b", upper):
        classes.append("query")
    if "ARRAYFORMULA" in upper:
        classes.append("arrayformula")
    if "INDIRECT" in upper:
        classes.append("indirect")
    if re.search(r"\b(OFFSET|TODAY|NOW|RAND|RANDBETWEEN)\s*\(", upper):
        classes.append("volatile_reference")
    if _looks_like_custom_function(upper):
        classes.append("custom_function_like")
    return classes


def _looks_like_custom_function(upper_formula: str) -> bool:
    if not re.match(r"=\s*[A-Z_][A-Z0-9_]*\s*\(", upper_formula):
        return False
    builtins = (
        "SUM|IF|IFS|COUNT|COUNTA|COUNTIF|COUNTIFS|VLOOKUP|XLOOKUP|INDEX|MATCH|"
        "FILTER|QUERY|ARRAYFORMULA|IMPORTRANGE|INDIRECT|SUMIF|SUMIFS|AVERAGE|"
        "AVERAGEIF|AVERAGEIFS|ROUND|ROUNDDOWN|ROUNDUP|IFERROR|DATE|DATEDIF|"
        "EOMONTH|TODAY|NOW|TEXT|VALUE|LEFT|RIGHT|MID|SPLIT|REGEXMATCH|"
        "REGEXEXTRACT|REGEXREPLACE|SUBTOTAL|SORT|UNIQUE|TRANSPOSE"
        "|OFFSET|DAY|MONTH|YEAR|WEEKDAY"
    )
    return re.match(rf"=\s*({builtins})\b", upper_formula) is None


def _has_cross_sheet_reference(formula: str, current_sheet: str) -> bool:
    if "!" not in formula:
        return False
    quoted = re.findall(r"'([^']+)'!", formula)
    unquoted = re.findall(r"(^|[^A-Z0-9_가-힣])([A-Za-z0-9_가-힣][A-Za-z0-9_가-힣 ._-]*)!", formula)
    referenced = quoted + [item[1].strip() for item in unquoted]
    return any(name and name != current_sheet for name in referenced)


def _summarize_grid_sheet(sheet: dict[str, Any]) -> dict[str, Any]:
    data = (sheet.get("data") or [{}])[0]
    grid_counts = Counter()
    style_counts = Counter()
    for row in data.get("rowData", []) or []:
        for cell in row.get("values", []) or []:
            if _cell_has_value(cell):
                grid_counts["non_empty_cell_count"] += 1
            effective = cell.get("effectiveValue") or {}
            entered = cell.get("userEnteredValue") or {}
            if "stringValue" in effective or "stringValue" in entered:
                grid_counts["string_cell_count"] += 1
            if "numberValue" in effective or "numberValue" in entered:
                grid_counts["number_cell_count"] += 1
            if "boolValue" in effective or "boolValue" in entered:
                grid_counts["bool_cell_count"] += 1
            if "errorValue" in effective or "errorValue" in entered:
                grid_counts["error_cell_count"] += 1
            if cell.get("pivotTable"):
                grid_counts["pivot_table_cell_count"] += 1
            if cell.get("dataValidation"):
                style_counts["data_validation_cell_count"] += 1
            if cell.get("note"):
                style_counts["note_cell_count"] += 1
            entered_format = cell.get("userEnteredFormat") or {}
            text_format = entered_format.get("textFormat") or {}
            if text_format.get("bold"):
                style_counts["bold_cell_count"] += 1
            if _has_fill(entered_format):
                style_counts["filled_cell_count"] += 1
            if _has_border(entered_format):
                style_counts["bordered_cell_count"] += 1

    row_metadata = data.get("rowMetadata", []) or []
    column_metadata = data.get("columnMetadata", []) or []
    return {
        "grid_counts": dict(grid_counts),
        "style_counts": {
            "bold_cell_count": style_counts["bold_cell_count"],
            "filled_cell_count": style_counts["filled_cell_count"],
            "bordered_cell_count": style_counts["bordered_cell_count"],
            "data_validation_cell_count": style_counts["data_validation_cell_count"],
            "note_cell_count": style_counts["note_cell_count"],
        },
        "hidden_row_count": sum(1 for row in row_metadata if row.get("hiddenByUser")),
        "filtered_row_count": sum(1 for row in row_metadata if row.get("hiddenByFilter")),
        "hidden_column_count": sum(1 for col in column_metadata if col.get("hiddenByUser")),
        "merge_count": len(sheet.get("merges", []) or []),
    }


def _cell_has_value(cell: dict[str, Any]) -> bool:
    return bool(
        cell.get("formattedValue")
        or cell.get("userEnteredValue")
        or cell.get("effectiveValue")
    )


def _has_fill(format_value: dict[str, Any]) -> bool:
    color = format_value.get("backgroundColor") or {}
    if not color:
        return False
    red = color.get("red", 1)
    green = color.get("green", 1)
    blue = color.get("blue", 1)
    return any(value < 0.98 for value in (red, green, blue))


def _has_border(format_value: dict[str, Any]) -> bool:
    borders = format_value.get("borders") or {}
    return any(bool(value) for value in borders.values())


def _sample_for_sheet(top_left_sample: dict[str, Any], title: str) -> dict[str, Any]:
    for tab in top_left_sample.get("tabs", []):
        if tab.get("title") == title:
            return tab
    return {
        "sample_range": "A1:Z80",
        "summary": {
            "non_empty_cell_count_in_sample": 0,
            "formula_cell_count_in_sample": 0,
        },
    }


def _authority(access_preflight: dict[str, Any]) -> dict[str, Any]:
    source = access_preflight.get("authority", {})
    return {
        "source_document": source.get("source_document", "live_google_sheet"),
        "access_mode": source.get(
            "access_mode",
            "sheets_api_readonly_with_domain_wide_delegation",
        ),
        "service_account_email": source.get("service_account_email", ""),
        "impersonated_subject": source.get("impersonated_subject", ""),
        "direct_service_account_access": source.get("direct_service_account_access", {}),
        "xlsx_round_trip": source.get("xlsx_round_trip", "not_used"),
        "write_operation": source.get("write_operation", "not_performed"),
    }


def _view_state_profile(sheets: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "hidden_sheet_count": sum(1 for sheet in sheets if sheet["state"] == "hidden"),
        "hidden_row_count_in_profile_windows": sum(
            sheet["view_state_counts"]["hidden_rows_in_profile_window"]
            for sheet in sheets
        ),
        "filtered_row_count_in_profile_windows": sum(
            sheet["view_state_counts"]["filtered_rows_in_profile_window"]
            for sheet in sheets
        ),
        "hidden_column_count_in_profile_windows": sum(
            sheet["view_state_counts"]["hidden_columns_in_profile_window"]
            for sheet in sheets
        ),
    }


def _role_hints(sheet: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    if re.match(r"^\d{2}_\d{4}$", sheet["name"]):
        hints.append("period_tab")
    if sheet["object_counts"]["charts"] >= 10:
        hints.append("chart_heavy_surface")
    if sheet["object_counts"]["banded_ranges"] >= 3:
        hints.append("banded_table_surface")
    if sheet["formula_counts"]["formula_cell_count"] > 0:
        hints.append("formula_surface")
    if sheet["formula_counts"]["dynamic_formula_cell_count"] > 0:
        hints.append("dynamic_formula_surface")
    if sheet["style_counts"]["bold_cell_count"] > 10:
        hints.append("styled_document_surface")
    if sheet["state"] == "hidden":
        hints.append("hidden_support_surface")
    return hints


def _risk_flags(sheet: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if sheet["state"] == "hidden":
        flags.append("hidden_sheet")
    if sheet["view_state_counts"]["hidden_rows_in_profile_window"]:
        flags.append("hidden_rows_in_profile_window")
    if sheet["view_state_counts"]["filtered_rows_in_profile_window"]:
        flags.append("filtered_rows_in_profile_window")
    if sheet["view_state_counts"]["hidden_columns_in_profile_window"]:
        flags.append("hidden_columns_in_profile_window")
    if sheet["formula_counts"]["dynamic_formula_cell_count"]:
        flags.append("dynamic_formula_dependency")
    if sheet["grid_counts"].get("error_cell_count", 0):
        flags.append("error_cells_in_profile_window")
    if sheet["object_counts"]["charts"] >= 50:
        flags.append("chart_heavy")
    return flags


def _summary(sheets: list[dict[str, Any]], formula_summary: dict[str, Any]) -> dict[str, int]:
    return {
        "sheet_count": len(sheets),
        "hidden_sheet_count": sum(1 for sheet in sheets if sheet["state"] == "hidden"),
        "sample_formula_count": formula_summary["total_formula_count_in_profile_windows"],
        "dynamic_formula_count": formula_summary[
            "dynamic_formula_count_in_profile_windows"
        ],
        "cross_sheet_formula_count": formula_summary[
            "cross_sheet_formula_count_in_profile_windows"
        ],
        "hidden_rows_in_profile_windows": sum(
            sheet["view_state_counts"]["hidden_rows_in_profile_window"]
            for sheet in sheets
        ),
        "filtered_rows_in_profile_windows": sum(
            sheet["view_state_counts"]["filtered_rows_in_profile_window"]
            for sheet in sheets
        ),
        "hidden_columns_in_profile_windows": sum(
            sheet["view_state_counts"]["hidden_columns_in_profile_window"]
            for sheet in sheets
        ),
        "chart_count": sum(sheet["object_counts"]["charts"] for sheet in sheets),
        "banded_range_count": sum(
            sheet["object_counts"]["banded_ranges"] for sheet in sheets
        ),
        "merge_count_in_profile_windows": sum(
            sheet["object_counts"]["merges_in_profile_window"] for sheet in sheets
        ),
        "pivot_table_cell_count_in_profile_windows": sum(
            sheet["grid_counts"].get("pivot_table_cell_count", 0) for sheet in sheets
        ),
        "error_cell_count_in_profile_windows": sum(
            sheet["grid_counts"].get("error_cell_count", 0) for sheet in sheets
        ),
    }


def _parser_observations(
    access_preflight: dict[str, Any],
    sheets: list[dict[str, Any]],
    formula_summary: dict[str, Any],
    permission_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    observations = [
        {
            "severity": "info",
            "message": "Live Google Sheet identity and tab sheetId values were preserved; no xlsx round-trip or write was performed.",
            "evidence_refs": ["access-preflight.json"],
        }
    ]
    direct = (
        access_preflight.get("authority", {})
        .get("direct_service_account_access", {})
        .get("status")
    )
    if direct and direct != "ok":
        observations.append(
            {
                "severity": "info",
                "message": "Service account direct access is not the authority path; DWD impersonation is required for this sheet.",
                "evidence_refs": ["access-preflight.json"],
            }
        )
    hidden_count = sum(1 for sheet in sheets if sheet["state"] == "hidden")
    if hidden_count:
        observations.append(
            {
                "severity": "warning",
                "message": f"{hidden_count} hidden tabs exist and must remain structural extraction authority even when not visually present.",
                "evidence_refs": ["live-manifest.json"],
            }
        )
    if formula_summary["dynamic_formula_count_in_profile_windows"]:
        observations.append(
            {
                "severity": "warning",
                "message": "Dynamic or external formula signals were found in sampled profile windows; loading and permission states must be classified before output claims.",
                "evidence_refs": ["top-left-sample.json"],
            }
        )
    if any(item["status"] == "not_requested" for item in permission_gaps):
        observations.append(
            {
                "severity": "warning",
                "message": "Some connected-document dependencies cannot be inspected with the current readonly Sheets scope and should not be inferred through alternate scraping.",
                "evidence_refs": ["live-manifest.json"],
            }
        )
    return observations


def _permission_gaps() -> list[dict[str, str]]:
    return [
        {
            "capability": "Apps Script binding / triggers",
            "status": "not_requested",
            "needed_when": "When classifying automation, webhook, trigger, or script-backed spreadsheet dependencies.",
            "do_not_workaround": "Ask for the required Drive/Apps Script permission before this stage; do not infer from DOM or export snapshots.",
        },
        {
            "capability": "Drive metadata / ownership / sharing graph",
            "status": "not_requested",
            "needed_when": "When validating sharing, owner, folder, revision, or rollback metadata beyond Sheets grid structure.",
            "do_not_workaround": "Ask for Drive metadata permission before this stage; do not replace the live document with an exported file.",
        },
    ]


def _sheet_row(sheet: dict[str, Any]) -> str:
    state_tone = "warn" if sheet["state"] == "hidden" else ""
    signals = "".join(_pill(value, "warn" if "risk" in value else "") for value in sheet["role_hints"])
    risks = "".join(_pill(value, "warn") for value in sheet["risk_flags"])
    if not signals and not risks:
        signals = _pill("no_major_signal")
    return (
        "<tr>"
        f"<td>{_esc(sheet['index'])}</td>"
        f"<td>{_esc(sheet['name'])}</td>"
        f"<td>{_esc(sheet['sheet_id'])}</td>"
        f"<td>{_pill(sheet['state'], state_tone)}</td>"
        f"<td>{_esc(sheet['dimensions']['row_count'])} x {_esc(sheet['dimensions']['column_count'])}</td>"
        f"<td>{_esc(sheet['sample_counts'].get('non_empty_cell_count_in_sample', 0))} cells<br>"
        f"{_esc(sheet['formula_counts']['formula_cell_count'])} formulas</td>"
        f"<td>hidden rows {_esc(sheet['view_state_counts']['hidden_rows_in_profile_window'])}<br>"
        f"filtered rows {_esc(sheet['view_state_counts']['filtered_rows_in_profile_window'])}<br>"
        f"hidden cols {_esc(sheet['view_state_counts']['hidden_columns_in_profile_window'])}</td>"
        f"<td>charts {_esc(sheet['object_counts']['charts'])}<br>"
        f"banded {_esc(sheet['object_counts']['banded_ranges'])}<br>"
        f"merges {_esc(sheet['object_counts']['merges_in_profile_window'])}</td>"
        f"<td>{signals}{risks}</td>"
        "</tr>"
    )


def _kv_rows(items: dict[str, Any]) -> str:
    return "".join(f"<div>{_esc(key)}</div><div><code>{_esc(value)}</code></div>" for key, value in items.items())


def _tone(severity: str) -> str:
    if severity == "warning":
        return "warn"
    if severity in {"error", "blocked"}:
        return "bad"
    return ""


def _pill(value: str, tone: str = "") -> str:
    return f'<span class="pill {tone}">{_esc(value)}</span>'


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a live Google Sheets manifest/profile artifact.")
    parser.add_argument("--access-preflight", required=True, type=Path)
    parser.add_argument("--top-left-sample", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--profile-range", default="A1:Z80")
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--subject")
    parser.add_argument("--fetch-grid-profile", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=8)
    args = parser.parse_args()

    access_preflight = _read_json(args.access_preflight)
    top_left_sample = _read_json(args.top_left_sample)
    grid_profiles: dict[str, dict[str, Any]] = {}
    live_fetch: dict[str, Any] | None = None

    if args.fetch_grid_profile:
        if not args.key_file or not args.subject:
            raise SystemExit("--key-file and --subject are required with --fetch-grid-profile")
        ranges = [
            f"'{sheet['title'].replace(chr(39), chr(39) + chr(39))}'!{args.profile_range}"
            for sheet in access_preflight.get("tabs", [])
            if sheet.get("title")
        ]
        grid_profiles, live_fetch = fetch_grid_profiles(
            spreadsheet_id=access_preflight["spreadsheet_id"],
            key_file=args.key_file,
            subject=args.subject,
            ranges=ranges,
            chunk_size=args.chunk_size,
        )

    manifest = build_live_manifest(
        access_preflight=access_preflight,
        top_left_sample=top_left_sample,
        grid_profiles=grid_profiles,
        profile_range=args.profile_range,
        live_fetch=live_fetch,
    )
    write_live_manifest_package(
        out_dir=args.out_dir,
        access_preflight_path=args.access_preflight,
        top_left_sample_path=args.top_left_sample,
        manifest=manifest,
    )
    print(json.dumps(manifest["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
