from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from html import escape
import json
from pathlib import Path
import re
import time
from typing import Any, Callable
from uuid import uuid4

from .sheets_api import (
    build_metadata_url,
    build_spreadsheet_batch_update_url,
    build_values_update_url,
    build_values_window_url,
    first_visible_sheet_title,
    google_get_json,
    google_post_json,
    qualify_ranges,
    quote_sheet_title,
    sheet_title_for_gid,
)


DEFAULT_TABLE_IO_PACKAGE_ROOT = Path("review-packages/sheets-bridge/mcp-table-io-flow")
DEFAULT_REFACTOR_PACKAGE_ROOT = Path("review-packages/sheets-bridge/mcp-refactor")
SUPPORTED_REFACTOR_PATTERN = "monthly_product_performance_v1"
SHEET_REF_RE = re.compile(r"'((?:[^']|'')+)'!")
MONTH_RE = re.compile(r"(20\d{2}\.\d{1,2})")
ERROR_PREFIXES = ("#REF!", "#VALUE!", "#N/A", "#DIV/0!", "#ERROR!", "#NAME?", "#NUM!")


def visualize_table_io(
    *,
    spreadsheet_id: str,
    access_token: str,
    gid: str = "",
    target_range: str = "",
    max_rows: int = 300,
    max_columns: int = 80,
    pattern: str = "auto",
    package_root: Path | str = DEFAULT_TABLE_IO_PACKAGE_ROOT,
    now: datetime | None = None,
    transport: Callable[[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    if max_rows < 1 or max_columns < 1:
        raise ValueError("max_rows and max_columns must be positive")

    transport = transport or google_get_json
    captured_at = (now or datetime.now(UTC)).isoformat()
    metadata = transport(build_metadata_url(spreadsheet_id), access_token)
    qualified_range = _qualified_target_range(
        metadata=metadata,
        gid=gid,
        target_range=target_range,
        max_rows=max_rows,
        max_columns=max_columns,
    )
    target_title = _sheet_title_from_qualified_range(qualified_range)
    target_tab = _sheet_summary_for_title(metadata, target_title)

    values_snapshot = transport(
        build_values_window_url(
            spreadsheet_id=spreadsheet_id,
            ranges=[qualified_range],
            value_render_option="FORMATTED_VALUE",
        ),
        access_token,
    )
    formulas_snapshot = transport(
        build_values_window_url(
            spreadsheet_id=spreadsheet_id,
            ranges=[qualified_range],
            value_render_option="FORMULA",
        ),
        access_token,
    )

    analysis = analyze_table_io(
        spreadsheet_id=spreadsheet_id,
        workbook_title=str((metadata.get("properties") or {}).get("title", "")),
        target_tab=target_tab,
        target_range=qualified_range,
        values=_first_value_matrix(values_snapshot),
        formulas=_first_value_matrix(formulas_snapshot),
        pattern=pattern,
        captured_at=captured_at,
    )
    package = write_table_io_package(
        analysis=analysis,
        package_root=package_root,
        request_id=f"table-io-{spreadsheet_id[:12]}-{target_tab.get('sheet_id', 'sheet')}",
        now=now,
    )
    return {
        "operation": "visualize.table_io",
        "spreadsheet_id": spreadsheet_id,
        "target_range": qualified_range,
        "detected_pattern": analysis["detected_pattern"],
        "summary": _table_io_summary(analysis),
        "package": package,
    }


def analyze_table_io(
    *,
    spreadsheet_id: str,
    workbook_title: str,
    target_tab: dict[str, Any],
    target_range: str,
    values: list[list[Any]],
    formulas: list[list[Any]],
    pattern: str = "auto",
    captured_at: str | None = None,
) -> dict[str, Any]:
    formulas_found = _formula_cells(formulas)
    source_counts = Counter()
    for formula in formulas_found:
        for sheet_name in SHEET_REF_RE.findall(formula):
            source_counts[sheet_name.replace("''", "'")] += 1

    detected_pattern = _detect_pattern(target_tab, values, formulas_found, source_counts)
    if pattern not in {"auto", detected_pattern, SUPPORTED_REFACTOR_PATTERN}:
        detected_pattern = "generic_table_flow_v1"
    if pattern == SUPPORTED_REFACTOR_PATTERN and detected_pattern != SUPPORTED_REFACTOR_PATTERN:
        detected_pattern = "unsupported_for_requested_pattern"

    if detected_pattern == SUPPORTED_REFACTOR_PATTERN:
        table_map = _monthly_product_table_map()
        major_patterns = _monthly_formula_patterns(formulas, source_counts)
        alternative_design = {
            "recommended": "minimal_formula_projection_sheet",
            "reason": "Per-cell SUMIF/SUMIFS formulas can be replaced by bounded array formulas on a new projection sheet while leaving the source tabs unchanged.",
            "current_formula_cell_count": len(formulas_found),
            "proposed_formula_anchor_count": 15,
            "write_strategy": "Create a new sheet, copy formats from the current output tab, then write array formula anchors only.",
        }
    else:
        table_map = _generic_table_map(target_range, values)
        major_patterns = _generic_formula_patterns(formulas_found, source_counts)
        alternative_design = {
            "recommended": "review_required",
            "reason": "No supported refactor pattern was detected. Use the visualization package to decide a sheet-specific design first.",
            "current_formula_cell_count": len(formulas_found),
            "proposed_formula_anchor_count": None,
            "write_strategy": "No writeback plan generated.",
        }

    return {
        "schema_version": "1.0",
        "artifact_kind": "sheets_bridge_table_io_flow",
        "generated_at": captured_at or datetime.now(UTC).isoformat(),
        "spreadsheet_id": spreadsheet_id,
        "workbook_title": workbook_title,
        "target_tab": target_tab,
        "target_range": target_range,
        "detected_pattern": detected_pattern,
        "table_map": table_map,
        "formula_summary": {
            "formula_cell_count": len(formulas_found),
            "source_reference_counts": dict(sorted(source_counts.items())),
            "major_patterns": major_patterns,
        },
        "alternative_design": alternative_design,
        "authority_boundary": [
            "This artifact is a point-in-time sanitized read through user OAuth.",
            "It does not contain OAuth tokens, cookies, service-account keys, or bearer headers.",
            "Refactor recommendations are proposals until a separate write tool applies them and validates the result.",
        ],
    }


def refactor_minimal_formula_sheet(
    *,
    spreadsheet_id: str,
    access_token: str,
    gid: str = "",
    source_output_sheet_title: str = "",
    source_sku_sheet_title: str = "",
    source_ad_sheet_title: str = "",
    output_sheet_title: str = "",
    validation_range: str = "A5:AQ129",
    dry_run: bool = False,
    validation_attempts: int = 6,
    validation_sleep_seconds: float = 2.0,
    package_root: Path | str = DEFAULT_REFACTOR_PACKAGE_ROOT,
    now: datetime | None = None,
    transport: Callable[[str, str], dict[str, Any]] | None = None,
    write_transport: Callable[[str, str, dict[str, Any]], dict[str, Any]] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    if validation_attempts < 1:
        raise ValueError("validation_attempts must be positive")

    transport = transport or google_get_json
    write_transport = write_transport or google_post_json
    sleep = sleep or time.sleep
    captured_at = (now or datetime.now(UTC)).isoformat()
    metadata = transport(build_metadata_url(spreadsheet_id), access_token)

    source_output_title = source_output_sheet_title or (
        sheet_title_for_gid(metadata, gid) if gid else first_visible_sheet_title(metadata)
    )
    source_output = _sheet_summary_for_title(metadata, source_output_title)
    source_sku_title = source_sku_sheet_title or _find_monthly_source_title(
        metadata,
        source_output_title=source_output_title,
        required_tokens=("SKU별 성과",),
    )
    source_ad_title = source_ad_sheet_title or _find_monthly_source_title(
        metadata,
        source_output_title=source_output_title,
        required_tokens=("광고비 현황",),
    )
    source_sku = _sheet_summary_for_title(metadata, source_sku_title)
    source_ad = _sheet_summary_for_title(metadata, source_ad_title)

    if not _looks_like_monthly_product_output(source_output_title):
        raise ValueError(f"unsupported refactor pattern for output sheet: {source_output_title}")

    new_sheet_title = _unique_sheet_title(
        metadata,
        output_sheet_title or _default_minimal_formula_sheet_title(source_output_title),
    )
    new_sheet_id = _unique_sheet_id(metadata)
    config = _minimal_formula_config(
        source_output=source_output,
        source_sku=source_sku,
        source_ad=source_ad,
        new_sheet_title=new_sheet_title,
        new_sheet_id=new_sheet_id,
        validation_range=validation_range,
    )
    formula_writes = build_minimal_formula_write_requests(config)
    structural_requests = build_minimal_formula_batch_requests(config)

    result: dict[str, Any] = {
        "schema_version": "1.0",
        "artifact_kind": "sheets_bridge_minimal_formula_refactor",
        "operation": "refactor.minimal_formula_sheet",
        "generated_at": captured_at,
        "spreadsheet_id": spreadsheet_id,
        "pattern": SUPPORTED_REFACTOR_PATTERN,
        "dry_run": dry_run,
        "source_output_sheet": source_output_title,
        "source_tabs": [source_sku_title, source_ad_title],
        "new_sheet_title": new_sheet_title,
        "new_sheet_id": new_sheet_id,
        "new_sheet_url": _sheet_url(spreadsheet_id, new_sheet_id),
        "formula_anchor_count": _count_formula_anchors(formula_writes),
        "write_ranges": [item["range"] for item in formula_writes],
        "rollback": {
            "type": "delete_created_sheet",
            "sheet_id": new_sheet_id,
            "sheet_title": new_sheet_title,
            "reason": "The original sheet is not modified; rollback is removing the newly created projection sheet.",
        },
    }

    if dry_run:
        result["planned_requests"] = {
            "structural_request_count": len(structural_requests),
            "formula_write_count": len(formula_writes),
        }
        result["validation"] = {"status": "not_run", "reason": "dry_run=true"}
        result["package"] = write_refactor_package(result=result, package_root=package_root, now=now)
        return result

    batch_response = write_transport(
        build_spreadsheet_batch_update_url(spreadsheet_id),
        access_token,
        {"requests": structural_requests},
    )
    values_response = write_transport(
        build_values_update_url(spreadsheet_id),
        access_token,
        {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {
                    "range": item["range"],
                    "majorDimension": "ROWS",
                    "values": item["values"],
                }
                for item in formula_writes
            ],
        },
    )
    validation = validate_minimal_formula_refactor(
        spreadsheet_id=spreadsheet_id,
        access_token=access_token,
        source_output_sheet_title=source_output_title,
        new_sheet_title=new_sheet_title,
        validation_range=validation_range,
        attempts=validation_attempts,
        sleep_seconds=validation_sleep_seconds,
        transport=transport,
        sleep=sleep,
    )

    result["batch_update_response"] = {
        "reply_count": len(batch_response.get("replies", []) or []),
    }
    result["values_update_response"] = {
        "total_updated_cells": values_response.get("totalUpdatedCells", 0),
        "total_updated_rows": values_response.get("totalUpdatedRows", 0),
        "total_updated_columns": values_response.get("totalUpdatedColumns", 0),
    }
    result["validation"] = validation
    result["package"] = write_refactor_package(result=result, package_root=package_root, now=now)
    return result


def build_minimal_formula_batch_requests(config: dict[str, Any]) -> list[dict[str, Any]]:
    source_sheet_id = int(config["source_output"]["sheet_id"])
    new_sheet_id = int(config["new_sheet_id"])
    product_end_row = int(config["product_end_row"])
    output_column_count = int(config["output_column_count"])
    return [
        {
            "addSheet": {
                "properties": {
                    "sheetId": new_sheet_id,
                    "title": config["new_sheet_title"],
                    "gridProperties": {
                        "rowCount": max(product_end_row, 130),
                        "columnCount": output_column_count,
                    },
                }
            }
        },
        {
            "copyPaste": {
                "source": {
                    "sheetId": source_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": product_end_row,
                    "startColumnIndex": 0,
                    "endColumnIndex": output_column_count,
                },
                "destination": {
                    "sheetId": new_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": product_end_row,
                    "startColumnIndex": 0,
                    "endColumnIndex": output_column_count,
                },
                "pasteType": "PASTE_FORMAT",
                "pasteOrientation": "NORMAL",
            }
        },
    ]


def build_minimal_formula_write_requests(config: dict[str, Any]) -> list[dict[str, Any]]:
    new_sheet = quote_sheet_title(str(config["new_sheet_title"]))
    output_sheet = quote_sheet_title(str(config["source_output"]["title"]))
    sku_sheet = quote_sheet_title(str(config["source_sku"]["title"]))
    ad_sheet = quote_sheet_title(str(config["source_ad"]["title"]))
    product_start_row = int(config["product_start_row"])
    product_end_row = int(config["product_end_row"])
    sku_end_row = int(config["sku_end_row"])
    ad_end_row = int(config["ad_end_row"])

    revenue_range = f"M{product_start_row}:AQ{product_end_row}"
    product_names = f"$C${product_start_row}:$C${product_end_row}"
    category_names = f"$B${product_start_row}:$B${product_end_row}"

    return [
        {
            "range": f"{new_sheet}!A1:I3",
            "values": [
                [
                    "MCP alternative: minimal formula product performance table",
                    "",
                    "",
                    "",
                    "",
                    "Start date",
                    f"={output_sheet}!G1",
                    "New total CAC",
                    f'=IFERROR(SUMIFS($I${product_start_row}:$I${product_end_row},$A${product_start_row}:$A${product_end_row},"신규")/SUMIFS($H${product_start_row}:$H${product_end_row},$A${product_start_row}:$A${product_end_row},"신규"),0)',
                ],
                [
                    "Generated by MCP Sheets Bridge minimal-formula refactor",
                    "",
                    "",
                    "",
                    "",
                    "Progress",
                    "=(TODAY()-$G$1)/31",
                    "",
                    "",
                ],
                ["", "", "", "", "", "Detail PAID plan", "", "Total", ""],
            ],
        },
        {
            "range": f"{new_sheet}!H4:L4",
            "values": [
                [
                    f"=SUM(H{product_start_row}:H{product_end_row})",
                    f"=SUM(I{product_start_row}:I{product_end_row})",
                    "",
                    "",
                    "=IFERROR(I4/H4,0)",
                ]
            ],
        },
        {"range": f"{new_sheet}!M2", "values": [["=SUM(M3:AQ3)"]]},
        {
            "range": f"{new_sheet}!M3",
            "values": [
                [
                    f'=ARRAYFORMULA(M4:AQ4-IFNA(BYCOL(FILTER({revenue_range},REGEXMATCH({category_names},"언어")),LAMBDA(c,SUM(c))),0))'
                ]
            ],
        },
        {
            "range": f"{new_sheet}!M4",
            "values": [[f"=BYCOL({revenue_range},LAMBDA(c,SUM(c)))"]],
        },
        {"range": f"{new_sheet}!A5", "values": [[f"=ARRAYFORMULA({output_sheet}!A5:AQ5)"]]},
        {
            "range": f"{new_sheet}!A6",
            "values": [[f"=ARRAYFORMULA({output_sheet}!A{product_start_row}:G{product_end_row})"]],
        },
        {
            "range": f"{new_sheet}!H6",
            "values": [[f"=BYROW({revenue_range},LAMBDA(r,SUM(r)))"]],
        },
        {
            "range": f"{new_sheet}!I6",
            "values": [
                [
                    f"=ARRAYFORMULA(MMULT(N({product_names}=TRANSPOSE({ad_sheet}!$D$2:$D${ad_end_row})),N({ad_sheet}!$E$2:$E${ad_end_row})))"
                ]
            ],
        },
        {
            "range": f"{new_sheet}!L6",
            "values": [
                [
                    f"=ARRAYFORMULA(IFERROR(I{product_start_row}:I{product_end_row}/H{product_start_row}:H{product_end_row},0))"
                ]
            ],
        },
        {
            "range": f"{new_sheet}!M6",
            "values": [
                [
                    f"=ARRAYFORMULA(MMULT(N({product_names}=TRANSPOSE({sku_sheet}!$C$4:$C${sku_end_row})),N({sku_sheet}!$H$4:$AL${sku_end_row})))"
                ]
            ],
        },
    ]


def validate_minimal_formula_refactor(
    *,
    spreadsheet_id: str,
    access_token: str,
    source_output_sheet_title: str,
    new_sheet_title: str,
    validation_range: str,
    attempts: int,
    sleep_seconds: float,
    transport: Callable[[str, str], dict[str, Any]],
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    coordinate = _range_coordinate(validation_range)
    source_range = f"{quote_sheet_title(source_output_sheet_title)}!{coordinate}"
    new_range = f"{quote_sheet_title(new_sheet_title)}!{coordinate}"
    comparison: dict[str, Any] = {}
    for attempt in range(1, attempts + 1):
        values = transport(
            build_values_window_url(
                spreadsheet_id=spreadsheet_id,
                ranges=[source_range, new_range],
                value_render_option="FORMATTED_VALUE",
            ),
            access_token,
        )
        ranges = values.get("valueRanges", []) if isinstance(values.get("valueRanges"), list) else []
        before = ranges[0].get("values", []) if len(ranges) > 0 and isinstance(ranges[0], dict) else []
        after = ranges[1].get("values", []) if len(ranges) > 1 and isinstance(ranges[1], dict) else []
        comparison = compare_value_matrices(before, after, dimensions=_range_dimensions(coordinate))
        comparison["attempt"] = attempt
        comparison["source_range"] = source_range
        comparison["new_range"] = new_range
        if comparison["mismatch_count"] == 0 and comparison["error_count"] == 0:
            comparison["status"] = "passed"
            return comparison
        if attempt < attempts:
            sleep(sleep_seconds)
    comparison["status"] = "failed"
    return comparison


def compare_value_matrices(
    before: list[list[Any]],
    after: list[list[Any]],
    *,
    dimensions: tuple[int, int],
) -> dict[str, Any]:
    before_padded = _pad_matrix(before, dimensions)
    after_padded = _pad_matrix(after, dimensions)
    mismatches = []
    error_cells = []
    for row_index, (before_row, after_row) in enumerate(zip(before_padded, after_padded), start=1):
        for column_index, (before_value, after_value) in enumerate(zip(before_row, after_row), start=1):
            before_text = _cell_text(before_value)
            after_text = _cell_text(after_value)
            if after_text.startswith(ERROR_PREFIXES):
                error_cells.append({"row": row_index, "column": column_index, "value": after_text})
            if before_text != after_text:
                mismatches.append(
                    {
                        "row": row_index,
                        "column": column_index,
                        "before": before_text,
                        "after": after_text,
                    }
                )
    return {
        "checked_cells": dimensions[0] * dimensions[1],
        "mismatch_count": len(mismatches),
        "error_count": len(error_cells),
        "sample_mismatches": mismatches[:20],
        "sample_errors": error_cells[:20],
    }


def write_table_io_package(
    *,
    analysis: dict[str, Any],
    package_root: Path | str = DEFAULT_TABLE_IO_PACKAGE_ROOT,
    request_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    created_at = (now or datetime.now(UTC)).isoformat()
    package_dir = _unique_package_dir(package_root, created_at, request_id or "table-io-flow")
    analysis_path = package_dir / "analysis.json"
    svg_path = package_dir / "table-io-flow.svg"
    html_path = package_dir / "index.html"
    manifest_path = package_dir / "manifest.json"
    handoff_path = package_dir / "mcp-handoff.json"

    svg = _build_table_io_svg(analysis)
    _write_json(analysis_path, analysis)
    svg_path.write_text(svg, encoding="utf-8")
    html_path.write_text(_build_table_io_html(analysis, svg), encoding="utf-8")
    _write_manifest(
        manifest_path=manifest_path,
        handoff_path=handoff_path,
        created_at=created_at,
        request_id=package_dir.name,
        package_dir=package_dir,
        primary_kind="table_io_flow_analysis",
        primary_path=analysis_path,
        extra_artifacts=[
            {"kind": "table_io_flow_svg", "path": str(svg_path.resolve())},
            {"kind": "table_io_flow_html", "path": str(html_path.resolve())},
        ],
    )
    return {
        "package_dir": str(package_dir.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "analysis_path": str(analysis_path.resolve()),
        "svg_path": str(svg_path.resolve()),
        "html_path": str(html_path.resolve()),
        "mcp_handoff_path": str(handoff_path.resolve()),
    }


def write_refactor_package(
    *,
    result: dict[str, Any],
    package_root: Path | str = DEFAULT_REFACTOR_PACKAGE_ROOT,
    request_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    created_at = (now or datetime.now(UTC)).isoformat()
    package_dir = _unique_package_dir(
        package_root,
        created_at,
        request_id or f"minimal-formula-{result.get('spreadsheet_id', 'sheet')}",
    )
    result_path = package_dir / "result.json"
    html_path = package_dir / "index.html"
    manifest_path = package_dir / "manifest.json"
    handoff_path = package_dir / "mcp-handoff.json"
    result_for_file = {key: value for key, value in result.items() if key != "package"}

    _write_json(result_path, result_for_file)
    html_path.write_text(_build_refactor_html(result_for_file), encoding="utf-8")
    _write_manifest(
        manifest_path=manifest_path,
        handoff_path=handoff_path,
        created_at=created_at,
        request_id=package_dir.name,
        package_dir=package_dir,
        primary_kind="minimal_formula_refactor_result",
        primary_path=result_path,
        extra_artifacts=[{"kind": "minimal_formula_refactor_html", "path": str(html_path.resolve())}],
    )
    return {
        "package_dir": str(package_dir.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "result_path": str(result_path.resolve()),
        "html_path": str(html_path.resolve()),
        "mcp_handoff_path": str(handoff_path.resolve()),
    }


def _qualified_target_range(
    *,
    metadata: dict[str, Any],
    gid: str,
    target_range: str,
    max_rows: int,
    max_columns: int,
) -> str:
    if target_range:
        return qualify_ranges(metadata, ranges=[target_range], gid=gid)[0]
    title = sheet_title_for_gid(metadata, gid) if gid else first_visible_sheet_title(metadata)
    sheet = _sheet_summary_for_title(metadata, title)
    rows = min(max(int(sheet.get("row_count") or 0), 1), max_rows)
    columns = min(max(int(sheet.get("column_count") or 0), 1), max_columns)
    return f"{quote_sheet_title(title)}!A1:{_column_label(columns)}{rows}"


def _sheet_title_from_qualified_range(qualified_range: str) -> str:
    title = qualified_range.split("!", 1)[0]
    if title.startswith("'") and title.endswith("'"):
        return title[1:-1].replace("''", "'")
    return title


def _sheet_summary_for_title(metadata: dict[str, Any], title: str) -> dict[str, Any]:
    for sheet in metadata.get("sheets", []) or []:
        props = sheet.get("properties", {}) if isinstance(sheet, dict) else {}
        if str(props.get("title", "")) == title:
            grid = props.get("gridProperties", {}) if isinstance(props.get("gridProperties"), dict) else {}
            return {
                "sheet_id": props.get("sheetId", 0),
                "title": props.get("title", ""),
                "index": props.get("index", 0),
                "hidden": bool(props.get("hidden")),
                "row_count": grid.get("rowCount", 0),
                "column_count": grid.get("columnCount", 0),
            }
    raise ValueError(f"sheet title not found in metadata: {title}")


def _first_value_matrix(snapshot: dict[str, Any]) -> list[list[Any]]:
    ranges = snapshot.get("valueRanges", []) if isinstance(snapshot.get("valueRanges"), list) else []
    if not ranges:
        return []
    values = ranges[0].get("values", []) if isinstance(ranges[0], dict) else []
    return values if isinstance(values, list) else []


def _formula_cells(values: list[list[Any]]) -> list[str]:
    formulas = []
    for row in values:
        if not isinstance(row, list):
            continue
        for value in row:
            text = str(value)
            if text.startswith("="):
                formulas.append(text)
    return formulas


def _detect_pattern(
    target_tab: dict[str, Any],
    values: list[list[Any]],
    formulas: list[str],
    source_counts: Counter[str],
) -> str:
    title = str(target_tab.get("title", ""))
    header_text = " ".join(_cell_text(value) for row in values[:8] for value in (row if isinstance(row, list) else []))
    source_text = " ".join(source_counts.keys())
    has_product_headers = all(token in header_text for token in ("상품", "결제액", "CAC"))
    has_sources = "SKU별 성과" in source_text and "광고비 현황" in source_text
    has_formulas = any("SUMIF" in formula or "SUMIFS" in formula for formula in formulas)
    if _looks_like_monthly_product_output(title) and has_product_headers and (has_sources or has_formulas):
        return SUPPORTED_REFACTOR_PATTERN
    return "generic_table_flow_v1"


def _looks_like_monthly_product_output(title: str) -> bool:
    return "상품별 성과" in title or "상품 성과" in title


def _monthly_product_table_map() -> list[dict[str, str]]:
    return [
        {
            "name": "Title and controls",
            "range": "A1:I2",
            "role": "annotation/control",
            "evidence": "Top rows contain title, start date, progress, and CAC control cells.",
        },
        {
            "name": "Daily summary",
            "range": "M3:AQ4",
            "role": "output summary",
            "evidence": "Summary rows aggregate the daily revenue matrix.",
        },
        {
            "name": "Product performance output",
            "range": "A5:AQ129",
            "role": "primary output table",
            "evidence": "Header row, product records, KPI columns, and daily revenue columns form one output table.",
        },
        {
            "name": "Product dimension fields",
            "range": "A6:G129",
            "role": "local dimension projection",
            "evidence": "Product roster and metadata are copied from the current output tab.",
        },
        {
            "name": "Daily revenue matrix",
            "range": "M6:AQ129",
            "role": "computed daily revenue output",
            "evidence": "SUMIF patterns reference the SKU performance source tab by product and date column.",
        },
        {
            "name": "Revenue/ad spend/CAC KPIs",
            "range": "H6:L129",
            "role": "computed KPI output",
            "evidence": "Totals and CAC are derived from daily revenue and ad-spend source data.",
        },
    ]


def _monthly_formula_patterns(
    formulas: list[list[Any]],
    source_counts: Counter[str],
) -> list[dict[str, Any]]:
    return [
        {
            "range": "M6:AQ129",
            "count": _formula_count_in_area(formulas, 6, 129, 13, 43),
            "pattern": "Daily revenue SUMIF matrix from SKU performance source tab.",
        },
        {
            "range": "I6:I129",
            "count": _formula_count_in_area(formulas, 6, 129, 9, 9),
            "pattern": "Ad spend SUMIFS by product from ad-spend source tab.",
        },
        {
            "range": "H6:H129",
            "count": _formula_count_in_area(formulas, 6, 129, 8, 8),
            "pattern": "Row total over daily revenue columns.",
        },
        {
            "range": "L6:L129",
            "count": _formula_count_in_area(formulas, 6, 129, 12, 12),
            "pattern": "CAC ratio from ad spend divided by revenue.",
        },
        {
            "range": "M3:AQ4",
            "count": _formula_count_in_area(formulas, 3, 4, 13, 43),
            "pattern": "Daily summary rows over the product matrix.",
        },
        {
            "range": "source tabs",
            "count": sum(source_counts.values()),
            "pattern": "External sheet references observed in output formulas.",
        },
    ]


def _generic_table_map(target_range: str, values: list[list[Any]]) -> list[dict[str, str]]:
    non_empty_rows = [
        index + 1
        for index, row in enumerate(values)
        if isinstance(row, list) and any(_cell_text(value) for value in row)
    ]
    if not non_empty_rows:
        return [{"name": "Analyzed window", "range": target_range, "role": "empty/review-required", "evidence": "No non-empty cells were returned."}]
    return [
        {
            "name": "Analyzed window",
            "range": target_range,
            "role": "review-required table candidate",
            "evidence": f"Non-empty rows were observed from local row {non_empty_rows[0]} to {non_empty_rows[-1]}.",
        }
    ]


def _generic_formula_patterns(
    formulas: list[str],
    source_counts: Counter[str],
) -> list[dict[str, Any]]:
    return [
        {
            "range": "analyzed window",
            "count": len(formulas),
            "pattern": "Formula cells in the bounded analysis range.",
        },
        {
            "range": "source tabs",
            "count": sum(source_counts.values()),
            "pattern": "Quoted sheet references observed in formulas.",
        },
    ]


def _formula_count_in_area(
    matrix: list[list[Any]],
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
) -> int:
    count = 0
    for row_index in range(start_row - 1, min(end_row, len(matrix))):
        row = matrix[row_index] if isinstance(matrix[row_index], list) else []
        for column_index in range(start_column - 1, min(end_column, len(row))):
            if str(row[column_index]).startswith("="):
                count += 1
    return count


def _minimal_formula_config(
    *,
    source_output: dict[str, Any],
    source_sku: dict[str, Any],
    source_ad: dict[str, Any],
    new_sheet_title: str,
    new_sheet_id: int,
    validation_range: str,
) -> dict[str, Any]:
    return {
        "source_output": source_output,
        "source_sku": source_sku,
        "source_ad": source_ad,
        "new_sheet_title": new_sheet_title,
        "new_sheet_id": new_sheet_id,
        "product_start_row": 6,
        "product_end_row": 129,
        "output_column_count": 43,
        "sku_end_row": max(int(source_sku.get("row_count") or 0), 4),
        "ad_end_row": max(int(source_ad.get("row_count") or 0), 2),
        "validation_range": validation_range,
    }


def _find_monthly_source_title(
    metadata: dict[str, Any],
    *,
    source_output_title: str,
    required_tokens: tuple[str, ...],
) -> str:
    month = _month_token(source_output_title)
    candidates = []
    for sheet in metadata.get("sheets", []) or []:
        props = sheet.get("properties", {}) if isinstance(sheet, dict) else {}
        title = str(props.get("title", ""))
        if all(token in title for token in required_tokens):
            candidates.append(title)
    if not candidates:
        raise ValueError(f"source sheet not found for tokens: {required_tokens}")
    if month:
        for title in candidates:
            if month in title:
                return title
    return candidates[0]


def _month_token(title: str) -> str:
    match = MONTH_RE.search(title)
    return match.group(1) if match else ""


def _default_minimal_formula_sheet_title(source_output_title: str) -> str:
    month = _month_token(source_output_title).replace(".", ".")
    if month:
        return f"MCP_ALT_MLL_{month}_min_formula"
    safe = "".join(ch if ch.isalnum() else "_" for ch in source_output_title)[:40].strip("_")
    return f"MCP_ALT_{safe or 'sheet'}_min_formula"


def _unique_sheet_title(metadata: dict[str, Any], desired: str) -> str:
    existing = {
        str((sheet.get("properties") or {}).get("title", ""))
        for sheet in metadata.get("sheets", []) or []
        if isinstance(sheet, dict)
    }
    if desired not in existing:
        return desired
    for index in range(2, 100):
        candidate = f"{desired} ({index})"
        if candidate not in existing:
            return candidate
    raise ValueError(f"could not allocate unique sheet title from: {desired}")


def _unique_sheet_id(metadata: dict[str, Any]) -> int:
    existing = {
        int((sheet.get("properties") or {}).get("sheetId", 0))
        for sheet in metadata.get("sheets", []) or []
        if isinstance(sheet, dict)
    }
    while True:
        candidate = uuid4().int % 900_000_000 + 10_000_000
        if candidate not in existing:
            return candidate


def _count_formula_anchors(write_requests: list[dict[str, Any]]) -> int:
    return sum(
        1
        for item in write_requests
        for row in item.get("values", []) or []
        for value in (row if isinstance(row, list) else [])
        if str(value).startswith("=")
    )


def _table_io_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    formula_summary = analysis.get("formula_summary", {}) if isinstance(analysis.get("formula_summary"), dict) else {}
    return {
        "workbook_title": analysis.get("workbook_title", ""),
        "target_tab": (analysis.get("target_tab") or {}).get("title", ""),
        "target_range": analysis.get("target_range", ""),
        "detected_pattern": analysis.get("detected_pattern", ""),
        "table_count": len(analysis.get("table_map", []) if isinstance(analysis.get("table_map"), list) else []),
        "formula_cell_count": formula_summary.get("formula_cell_count", 0),
        "source_reference_counts": formula_summary.get("source_reference_counts", {}),
    }


def _build_table_io_svg(analysis: dict[str, Any]) -> str:
    summary = _table_io_summary(analysis)
    source_counts = summary.get("source_reference_counts", {}) or {}
    source_lines = [f"{name}: {count}" for name, count in list(source_counts.items())[:4]]
    if not source_lines:
        source_lines = ["No quoted source sheet references detected"]
    source_text = "\n".join(source_lines)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="640" viewBox="0 0 1120 640" role="img" aria-label="Google Sheets table input output flow">
  <defs>
    <style>
      .bg{{fill:#f7fafc}} .box{{fill:#fff;stroke:#cbd7e3;stroke-width:2}} .source{{fill:#eef8ff;stroke:#7ab6d6}} .output{{fill:#effaf4;stroke:#73b98b}} .alt{{fill:#fff6e5;stroke:#e5ad45}} .title{{font:700 24px Arial,sans-serif;fill:#172033}} .h{{font:700 17px Arial,sans-serif;fill:#172033}} .t{{font:14px Arial,sans-serif;fill:#344155}} .small{{font:12px Arial,sans-serif;fill:#59677a}} .arrow{{stroke:#52616f;stroke-width:2.5;fill:none;marker-end:url(#arrow)}}
    </style>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#52616f"/></marker>
  </defs>
  <rect class="bg" width="1120" height="640"/>
  <text x="40" y="52" class="title">Sheets Bridge Table I/O Flow</text>
  <text x="40" y="82" class="small">{escape(str(summary.get("target_tab", "")))} · {escape(str(summary.get("target_range", "")))}</text>

  <rect x="50" y="130" width="260" height="150" rx="8" class="source"/>
  <text x="75" y="168" class="h">Input source tabs</text>
  {_svg_multiline(source_text, 75, 198)}

  <rect x="410" y="120" width="300" height="170" rx="8" class="box"/>
  <text x="435" y="158" class="h">Formula / join surface</text>
  <text x="435" y="194" class="t">Formula cells: {escape(str(summary.get("formula_cell_count", 0)))}</text>
  <text x="435" y="224" class="t">Pattern: {escape(str(summary.get("detected_pattern", "")))}</text>
  <text x="435" y="254" class="small">Aggregates product, date, revenue, ad spend, and CAC.</text>

  <rect x="820" y="130" width="260" height="150" rx="8" class="output"/>
  <text x="845" y="168" class="h">Output table</text>
  <text x="845" y="198" class="t">Product performance table</text>
  <text x="845" y="226" class="t">Dimensions + KPIs + daily matrix</text>

  <path d="M310 205 C350 205 365 205 410 205" class="arrow"/>
  <path d="M710 205 C750 205 775 205 820 205" class="arrow"/>

  <rect x="170" y="390" width="780" height="120" rx="8" class="alt"/>
  <text x="200" y="430" class="h">Alternative design</text>
  <text x="200" y="462" class="t">{escape(str((analysis.get("alternative_design") or {}).get("recommended", "")))}</text>
  <text x="200" y="492" class="small">{escape(str((analysis.get("alternative_design") or {}).get("write_strategy", "")))}</text>
  <path d="M560 290 L560 390" class="arrow"/>
</svg>
'''


def _svg_multiline(text: str, x: int, y: int) -> str:
    lines = text.splitlines()[:5]
    return "\n".join(
        f'<text x="{x}" y="{y + index * 22}" class="t">{escape(line)}</text>'
        for index, line in enumerate(lines)
    )


def _build_table_io_html(analysis: dict[str, Any], svg: str) -> str:
    rows = "\n".join(
        f"<tr><td>{escape(item.get('name', ''))}</td><td><code>{escape(item.get('range', ''))}</code></td><td>{escape(item.get('role', ''))}</td><td>{escape(item.get('evidence', ''))}</td></tr>"
        for item in analysis.get("table_map", []) or []
    )
    formulas = "\n".join(
        f"<tr><td><code>{escape(str(item.get('range', '')))}</code></td><td>{escape(str(item.get('count', '')))}</td><td>{escape(str(item.get('pattern', '')))}</td></tr>"
        for item in (analysis.get("formula_summary") or {}).get("major_patterns", []) or []
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Sheets Bridge Table I/O Flow</title>
  <style>
    body{{font-family:Arial,'Apple SD Gothic Neo',sans-serif;margin:32px;color:#172033;background:#f7fafc}}
    main{{max-width:1160px;margin:0 auto}}
    section{{background:#fff;border:1px solid #d8e1ea;border-radius:8px;padding:20px;margin:18px 0}}
    h1{{margin:0 0 8px;font-size:28px}} h2{{font-size:20px;margin:0 0 12px}}
    table{{border-collapse:collapse;width:100%;font-size:14px}} th,td{{border-bottom:1px solid #e2e8f0;padding:10px;text-align:left;vertical-align:top}} th{{background:#f1f5f9}}
    code{{background:#eef3f8;padding:2px 5px;border-radius:4px}}
    .svg{{overflow:auto;background:#fff;border:1px solid #d8e1ea;border-radius:8px}}
  </style>
</head>
<body><main>
  <h1>Sheets Bridge Table I/O Flow</h1>
  <p>{escape(str(analysis.get("workbook_title", "")))} / {escape(str((analysis.get("target_tab") or {}).get("title", "")))}</p>
  <div class="svg">{svg}</div>
  <section><h2>Table Map</h2><table><thead><tr><th>Name</th><th>Range</th><th>Role</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table></section>
  <section><h2>Formula Patterns</h2><table><thead><tr><th>Range</th><th>Count</th><th>Pattern</th></tr></thead><tbody>{formulas}</tbody></table></section>
  <section><h2>Alternative Design</h2><pre>{escape(json.dumps(analysis.get("alternative_design", {}), ensure_ascii=False, indent=2))}</pre></section>
</main></body></html>
"""


def _build_refactor_html(result: dict[str, Any]) -> str:
    validation = result.get("validation", {}) if isinstance(result.get("validation"), dict) else {}
    status = validation.get("status", "")
    status_text = "passed" if status == "passed" else status or "not run"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Sheets Bridge Minimal Formula Refactor</title>
  <style>
    body{{font-family:Arial,'Apple SD Gothic Neo',sans-serif;margin:32px;color:#172033;background:#f7fafc}}
    main{{max-width:980px;margin:0 auto;background:#fff;border:1px solid #d8e1ea;border-radius:8px;padding:24px}}
    h1{{margin-top:0}} table{{border-collapse:collapse;width:100%}} th,td{{border-bottom:1px solid #e2e8f0;padding:10px;text-align:left;vertical-align:top}} th{{width:240px;background:#f1f5f9}}
    code{{background:#eef3f8;padding:2px 5px;border-radius:4px}} .ok{{color:#176b43;font-weight:700}} .warn{{color:#b45309;font-weight:700}}
  </style>
</head>
<body><main>
  <h1>Sheets Bridge Minimal Formula Refactor</h1>
  <p class="{ "ok" if status == "passed" else "warn" }">Validation: {escape(str(status_text))}</p>
  <table>
    <tr><th>Spreadsheet</th><td>{escape(str(result.get("spreadsheet_id", "")))}</td></tr>
    <tr><th>Source output sheet</th><td>{escape(str(result.get("source_output_sheet", "")))}</td></tr>
    <tr><th>New sheet</th><td>{escape(str(result.get("new_sheet_title", "")))}</td></tr>
    <tr><th>New sheet URL</th><td><a href="{escape(str(result.get("new_sheet_url", "")))}">{escape(str(result.get("new_sheet_url", "")))}</a></td></tr>
    <tr><th>Formula anchors</th><td>{escape(str(result.get("formula_anchor_count", "")))}</td></tr>
    <tr><th>Rollback</th><td>Delete created sheet id <code>{escape(str((result.get("rollback") or {}).get("sheet_id", "")))}</code>.</td></tr>
  </table>
  <h2>Validation</h2>
  <pre>{escape(json.dumps(validation, ensure_ascii=False, indent=2))}</pre>
</main></body></html>
"""


def _write_manifest(
    *,
    manifest_path: Path,
    handoff_path: Path,
    created_at: str,
    request_id: str,
    package_dir: Path,
    primary_kind: str,
    primary_path: Path,
    extra_artifacts: list[dict[str, str]],
) -> None:
    handoff = {
        "schema_version": "1.0",
        "artifact_kind": "sheets_bridge_mcp_handoff",
        "request_id": request_id,
        "created_at": created_at,
        "package_dir": str(package_dir.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "primary_artifact": {"kind": primary_kind, "path": str(primary_path.resolve())},
        "mcp_prompt": f"이 Sheets Bridge MCP 패키지를 검토해줘: {manifest_path.resolve()}",
        "analysis_boundary": [
            "Read manifest.json first.",
            "Use only sanitized local artifacts referenced by the manifest.",
            "Use only credential-free MCP outputs and review artifacts.",
        ],
    }
    manifest = {
        "schema_version": "1.0",
        "artifact_kind": "sheets_bridge_mcp_package",
        "request_id": request_id,
        "created_at": created_at,
        "source": "mcp_user_oauth",
        "artifacts": [
            {"kind": primary_kind, "path": str(primary_path.resolve())},
            *extra_artifacts,
            {"kind": "mcp_handoff", "path": str(handoff_path.resolve())},
        ],
    }
    _write_json(handoff_path, handoff)
    _write_json(manifest_path, manifest)


def _unique_package_dir(package_root: Path | str, created_at: str, request_id: str) -> Path:
    root = Path(package_root)
    base = root / created_at[:10] / _safe_id(request_id)
    candidate = base
    index = 2
    while candidate.exists():
        candidate = Path(f"{base}-{index}")
        index += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_id(value: object) -> str:
    raw = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(value))
    return raw[:120] or "mcp-package"


def _column_label(index: int) -> str:
    if index < 1:
        raise ValueError("column index must be positive")
    label = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label


def _range_coordinate(a1_range: str) -> str:
    return str(a1_range).split("!", 1)[-1].replace("$", "").upper()


def _range_dimensions(a1_range: str) -> tuple[int, int]:
    coordinate = _range_coordinate(a1_range)
    start, separator, end = coordinate.partition(":")
    end = end if separator else start
    start_col, start_row = _cell_coordinate(start)
    end_col, end_row = _cell_coordinate(end)
    if end_col < start_col or end_row < start_row:
        raise ValueError(f"range must be bounded A1: {a1_range}")
    return end_row - start_row + 1, end_col - start_col + 1


def _cell_coordinate(cell: str) -> tuple[int, int]:
    match = re.match(r"^([A-Z]{1,4})([1-9][0-9]*)$", str(cell).upper())
    if not match:
        raise ValueError(f"range must be bounded A1: {cell}")
    column = 0
    for char in match.group(1):
        column = column * 26 + ord(char) - 64
    return column, int(match.group(2))


def _pad_matrix(values: list[list[Any]], dimensions: tuple[int, int]) -> list[list[Any]]:
    rows, columns = dimensions
    padded = []
    source_rows = values if isinstance(values, list) else []
    for row_index in range(rows):
        source_row = source_rows[row_index] if row_index < len(source_rows) and isinstance(source_rows[row_index], list) else []
        padded.append([source_row[column_index] if column_index < len(source_row) else "" for column_index in range(columns)])
    return padded


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _sheet_url(spreadsheet_id: str, sheet_id: int) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit?gid={sheet_id}#gid={sheet_id}"
