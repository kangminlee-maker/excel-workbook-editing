from __future__ import annotations

from time import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
import re


AUTH_SCHEME = "".join(("Be", "arer"))
GRID_FIELD_MASKS = {
    "grid_basic_v1": ",".join(
        [
            "spreadsheetId",
            "sheets(properties(sheetId,title,index,hidden,gridProperties(rowCount,columnCount,frozenRowCount,frozenColumnCount)),"
            "data(startRow,startColumn,rowData(values(formattedValue,userEnteredValue,effectiveValue,dataValidation,note,pivotTable)),"
            "rowMetadata(hiddenByUser,hiddenByFilter,pixelSize),columnMetadata(hiddenByUser,pixelSize)),"
            "merges,protectedRanges(protectedRangeId,range,warningOnly),basicFilter,filterViews(filterViewId,title,range),"
            "charts(chartId,spec/title,position),bandedRanges(bandedRangeId,range))",
        ]
    ),
    "grid_formula_v1": ",".join(
        [
            "spreadsheetId",
            "sheets(properties(sheetId,title,index,hidden,gridProperties(rowCount,columnCount,frozenRowCount,frozenColumnCount)),"
            "data(startRow,startColumn,rowData(values(formattedValue,userEnteredValue,effectiveValue,userEnteredFormat(backgroundColor,textFormat(bold,italic,fontSize,foregroundColor),horizontalAlignment,verticalAlignment),dataValidation,note,pivotTable)),"
            "rowMetadata(hiddenByUser,hiddenByFilter,pixelSize),columnMetadata(hiddenByUser,pixelSize)),"
            "merges,protectedRanges(protectedRangeId,range,warningOnly),basicFilter,filterViews(filterViewId,title,range),"
            "charts(chartId,spec/title,position),bandedRanges(bandedRangeId,range))",
        ]
    ),
}
SHEETS_METADATA_FIELDS = ",".join(
    [
        "spreadsheetId",
        "properties(title,locale,timeZone)",
        "sheets(properties(sheetId,title,index,hidden,gridProperties(rowCount,columnCount)),protectedRanges(protectedRangeId,range,warningOnly))",
        "namedRanges(name,range)",
    ]
)
A1_CELL_RE = re.compile(r"^\$?([A-Za-z]+)\$?([1-9][0-9]*)$")


def build_metadata_url(spreadsheet_id: str) -> str:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    query = urlencode(
        {
            "includeGridData": "false",
            "fields": SHEETS_METADATA_FIELDS,
        }
    )
    return f"https://sheets.googleapis.com/v4/spreadsheets/{quote(spreadsheet_id, safe='')}?{query}"


def build_grid_window_url(
    *,
    spreadsheet_id: str,
    ranges: list[str],
    field_mask: str = "grid_basic_v1",
) -> str:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    if not ranges:
        raise ValueError("at least one range is required")
    fields = GRID_FIELD_MASKS.get(field_mask)
    if not fields:
        raise ValueError("field_mask is not supported")
    query = urlencode(
        {
            "includeGridData": "true",
            "ranges": ranges,
            "fields": fields,
        },
        doseq=True,
    )
    return f"https://sheets.googleapis.com/v4/spreadsheets/{quote(spreadsheet_id, safe='')}?{query}"


def build_values_window_url(
    *,
    spreadsheet_id: str,
    ranges: list[str],
    value_render_option: str,
) -> str:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    if not ranges:
        raise ValueError("at least one range is required")
    query = urlencode(
        {
            "ranges": ranges,
            "valueRenderOption": value_render_option,
            "dateTimeRenderOption": "FORMATTED_STRING",
        },
        doseq=True,
    )
    return (
        f"https://sheets.googleapis.com/v4/spreadsheets/"
        f"{quote(spreadsheet_id, safe='')}/values:batchGet?{query}"
    )


def build_values_batch_update_url(*, spreadsheet_id: str) -> str:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    return (
        f"https://sheets.googleapis.com/v4/spreadsheets/"
        f"{quote(spreadsheet_id, safe='')}/values:batchUpdate"
    )


def normalize_metadata(
    metadata: dict[str, Any],
    *,
    snapshot_id: str,
    captured_at: str,
    elapsed_ms: int = 0,
    policy_summary: dict[str, Any] | None = None,
    auth_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    properties = metadata.get("properties", {})
    sheets = metadata.get("sheets", []) if isinstance(metadata.get("sheets"), list) else []
    named_ranges = (
        metadata.get("namedRanges", [])
        if isinstance(metadata.get("namedRanges"), list)
        else []
    )

    artifacts = []
    if policy_summary:
        artifacts.append({"kind": "broker_policy", "summary": policy_summary})
    if auth_summary:
        artifacts.append({"kind": "broker_auth", "summary": auth_summary})

    return {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "spreadsheet_id": metadata.get("spreadsheetId", ""),
        "title": properties.get("title", ""),
        "locale": properties.get("locale", ""),
        "time_zone": properties.get("timeZone", ""),
        "tabs": [_normalize_sheet(sheet) for sheet in sheets],
        "named_ranges": [
            {
                "name": named_range.get("name", ""),
                "range": _normalize_grid_range(named_range.get("range")),
            }
            for named_range in named_ranges
        ],
        "protected_ranges": [
            {
                "protected_range_id": protected_range.get("protectedRangeId", 0),
                "range": _normalize_grid_range(protected_range.get("range")),
                "warning_only": bool(protected_range.get("warningOnly")),
            }
            for sheet in sheets
            for protected_range in sheet.get("protectedRanges", []) or []
        ],
        "data_validations": [],
        "formula_samples": [],
        "cell_states": [],
        "telemetry": {
            "request_count": 1,
            "retry_count": 0,
            "elapsed_ms": elapsed_ms,
            "timeout_budget": {
                "read_seconds": 60,
                "write_seconds": 60,
                "poll_seconds": 120,
            },
        },
        "artifacts": artifacts,
    }


def fetch_metadata(
    *,
    spreadsheet_id: str,
    access_token: str,
    transport,
) -> tuple[dict[str, Any], int]:
    if not access_token:
        raise ValueError("access_token is required")
    started_at = time()
    metadata = transport(build_metadata_url(spreadsheet_id), access_token)
    return metadata, int((time() - started_at) * 1000)


def fetch_grid_window(
    *,
    spreadsheet_id: str,
    ranges: list[str],
    field_mask: str,
    access_token: str,
    transport,
) -> tuple[dict[str, Any], int]:
    if not access_token:
        raise ValueError("access_token is required")
    started_at = time()
    metadata = transport(
        build_grid_window_url(
            spreadsheet_id=spreadsheet_id,
            ranges=ranges,
            field_mask=field_mask,
        ),
        access_token,
    )
    return metadata, int((time() - started_at) * 1000)


def fetch_values_window(
    *,
    spreadsheet_id: str,
    ranges: list[str],
    value_render_option: str,
    access_token: str,
    transport,
) -> tuple[dict[str, Any], int]:
    if not access_token:
        raise ValueError("access_token is required")
    started_at = time()
    values = transport(
        build_values_window_url(
            spreadsheet_id=spreadsheet_id,
            ranges=ranges,
            value_render_option=value_render_option,
        ),
        access_token,
    )
    return values, int((time() - started_at) * 1000)


def apply_values_update(
    *,
    spreadsheet_id: str,
    write_requests: list[dict[str, Any]],
    access_token: str,
    transport,
) -> tuple[dict[str, Any], int]:
    if not access_token:
        raise ValueError("access_token is required")
    if not write_requests:
        raise ValueError("write_requests are required")
    started_at = time()
    body = {
        "valueInputOption": "USER_ENTERED",
        "includeValuesInResponse": True,
        "responseValueRenderOption": "FORMULA",
        "responseDateTimeRenderOption": "FORMATTED_STRING",
        "data": [
            {
                "range": str(write_request.get("range", "")),
                "majorDimension": "ROWS",
                "values": write_request.get("values", []),
            }
            for write_request in write_requests
        ],
    }
    response = transport(build_values_batch_update_url(spreadsheet_id=spreadsheet_id), access_token, body)
    return response, int((time() - started_at) * 1000)


def rollback_write_requests_from_values_snapshot(
    *,
    ranges: list[str],
    values_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    value_ranges = values_snapshot.get("valueRanges", [])
    by_range = {
        str(value_range.get("range", "")): value_range
        for value_range in value_ranges
        if isinstance(value_range, dict)
    }
    write_requests = []
    for requested_range in ranges:
        value_range = by_range.get(requested_range, {})
        values = value_range.get("values", []) if isinstance(value_range, dict) else []
        row_count, column_count = range_dimensions(requested_range)
        write_requests.append(
            {
                "range": requested_range,
                "values": pad_values(values, row_count=row_count, column_count=column_count),
            }
        )
    return write_requests


def pad_values(values: Any, *, row_count: int, column_count: int) -> list[list[Any]]:
    rows = values if isinstance(values, list) else []
    padded: list[list[Any]] = []
    for row_index in range(row_count):
        source_row = rows[row_index] if row_index < len(rows) and isinstance(rows[row_index], list) else []
        padded.append(
            [
                source_row[column_index] if column_index < len(source_row) else ""
                for column_index in range(column_count)
            ]
        )
    return padded


def range_dimensions(a1_range: str) -> tuple[int, int]:
    coordinate = a1_range.rsplit("!", 1)[-1].replace("$", "")
    start, separator, end = coordinate.partition(":")
    end = end if separator else start
    start_cell = _cell_coordinate(start)
    end_cell = _cell_coordinate(end)
    if start_cell is None or end_cell is None:
        raise ValueError("range must be bounded A1")
    start_column, start_row = start_cell
    end_column, end_row = end_cell
    if end_column < start_column or end_row < start_row:
        raise ValueError("range must be bounded A1")
    return end_row - start_row + 1, end_column - start_column + 1


def normalize_grid_window(
    metadata: dict[str, Any],
    *,
    snapshot_id: str,
    captured_at: str,
    operation: str,
    ranges: list[str],
    field_mask: str,
    elapsed_ms: int = 0,
    policy_summary: dict[str, Any] | None = None,
    auth_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _window_base(
        metadata,
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        operation=operation,
        ranges=ranges,
        elapsed_ms=elapsed_ms,
        policy_summary=policy_summary,
        auth_summary=auth_summary,
        extra={
            "field_mask": field_mask,
            "windows": [
                _normalize_grid_sheet(sheet)
                for sheet in metadata.get("sheets", []) or []
            ],
        },
    )


def normalize_values_window(
    values: dict[str, Any],
    *,
    snapshot_id: str,
    captured_at: str,
    operation: str,
    ranges: list[str],
    value_render_option: str,
    elapsed_ms: int = 0,
    policy_summary: dict[str, Any] | None = None,
    auth_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _window_base(
        values,
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        operation=operation,
        ranges=ranges,
        elapsed_ms=elapsed_ms,
        policy_summary=policy_summary,
        auth_summary=auth_summary,
        extra={
            "value_render_option": value_render_option,
            "windows": [
                {
                    "range": value_range.get("range", ""),
                    "major_dimension": value_range.get("majorDimension", ""),
                    "values": value_range.get("values", []),
                    "row_count": len(value_range.get("values", []) or []),
                    "column_count": max(
                        (len(row) for row in value_range.get("values", []) or []),
                        default=0,
                    ),
                }
                for value_range in values.get("valueRanges", []) or []
            ],
        },
    )


def normalize_values_apply_result(
    *,
    spreadsheet_id: str,
    snapshot_id: str,
    captured_at: str,
    operation: str,
    write_requests: list[dict[str, Any]],
    before_values: dict[str, Any],
    update_response: dict[str, Any],
    readback_values: dict[str, Any],
    rollback_write_requests: list[dict[str, Any]],
    elapsed_ms: int = 0,
    policy_summary: dict[str, Any] | None = None,
    auth_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifacts = []
    if policy_summary:
        artifacts.append({"kind": "broker_policy", "summary": policy_summary})
    if auth_summary:
        artifacts.append({"kind": "broker_auth", "summary": auth_summary})
    ranges = [str(write_request.get("range", "")) for write_request in write_requests]
    return {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "operation": operation,
        "spreadsheet_id": spreadsheet_id,
        "updated_ranges": ranges,
        "write_count": len(write_requests),
        "updated_cells": update_response.get("totalUpdatedCells", 0),
        "updated_rows": update_response.get("totalUpdatedRows", 0),
        "updated_columns": update_response.get("totalUpdatedColumns", 0),
        "before": _normalize_value_ranges(before_values),
        "after": _normalize_value_ranges(readback_values),
        "rollback": {
            "operation": "rollback.values_restore",
            "spreadsheet_id": spreadsheet_id,
            "ranges": ranges,
            "write_requests": rollback_write_requests,
            "rollback_of_request_id": "",
        },
        "telemetry": {
            "request_count": 3,
            "retry_count": 0,
            "elapsed_ms": elapsed_ms,
            "timeout_budget": {
                "read_seconds": 60,
                "write_seconds": 60,
                "poll_seconds": 120,
            },
        },
        "artifacts": artifacts,
    }


def _normalize_value_ranges(values: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "range": value_range.get("range", ""),
            "major_dimension": value_range.get("majorDimension", ""),
            "values": value_range.get("values", []),
            "row_count": len(value_range.get("values", []) or []),
            "column_count": max(
                (len(row) for row in value_range.get("values", []) or []),
                default=0,
            ),
        }
        for value_range in values.get("valueRanges", []) or []
        if isinstance(value_range, dict)
    ]


def http_metadata_transport(url: str, access_token: str) -> dict[str, Any]:
    if not access_token:
        raise ValueError("access_token is required")
    request = Request(
        url,
        headers={
            "Authorization": f"{AUTH_SCHEME} {access_token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=60) as response:
            return _json_loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Sheets request failed with HTTP {error.code}: {body}") from error


def http_values_write_transport(url: str, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
    if not access_token:
        raise ValueError("access_token is required")
    import json

    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"{AUTH_SCHEME} {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            return _json_loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body_text = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Sheets write failed with HTTP {error.code}: {body_text}") from error


def _window_base(
    response: dict[str, Any],
    *,
    snapshot_id: str,
    captured_at: str,
    operation: str,
    ranges: list[str],
    elapsed_ms: int,
    policy_summary: dict[str, Any] | None,
    auth_summary: dict[str, Any] | None,
    extra: dict[str, Any],
) -> dict[str, Any]:
    artifacts = []
    if policy_summary:
        artifacts.append({"kind": "broker_policy", "summary": policy_summary})
    if auth_summary:
        artifacts.append({"kind": "broker_auth", "summary": auth_summary})
    return {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "operation": operation,
        "spreadsheet_id": response.get("spreadsheetId", ""),
        "requested_ranges": ranges,
        "telemetry": {
            "request_count": 1,
            "retry_count": 0,
            "elapsed_ms": elapsed_ms,
            "timeout_budget": {
                "read_seconds": 60,
                "write_seconds": 60,
                "poll_seconds": 120,
            },
        },
        "artifacts": artifacts,
        **extra,
    }


def _normalize_grid_sheet(sheet: dict[str, Any]) -> dict[str, Any]:
    properties = _normalize_sheet(sheet)
    data = sheet.get("data", []) if isinstance(sheet.get("data"), list) else []
    return {
        **properties,
        "windows": [_normalize_grid_data(window) for window in data],
        "merges": [_normalize_grid_range(item) for item in sheet.get("merges", []) or []],
        "protected_ranges": [
            {
                "protected_range_id": item.get("protectedRangeId", 0),
                "range": _normalize_grid_range(item.get("range")),
                "warning_only": bool(item.get("warningOnly")),
            }
            for item in sheet.get("protectedRanges", []) or []
        ],
        "object_counts": {
            "charts": len(sheet.get("charts", []) or []),
            "banded_ranges": len(sheet.get("bandedRanges", []) or []),
            "filter_views": len(sheet.get("filterViews", []) or []),
            "has_basic_filter": bool(sheet.get("basicFilter")),
        },
    }


def _normalize_grid_data(window: dict[str, Any]) -> dict[str, Any]:
    row_data = window.get("rowData", []) if isinstance(window.get("rowData"), list) else []
    return {
        "start_row": window.get("startRow", 0),
        "start_column": window.get("startColumn", 0),
        "row_count": len(row_data),
        "rows": [_normalize_row(row) for row in row_data],
        "row_metadata": [
            _normalize_dimension_metadata(item)
            for item in window.get("rowMetadata", []) or []
        ],
        "column_metadata": [
            _normalize_dimension_metadata(item)
            for item in window.get("columnMetadata", []) or []
        ],
    }


def _normalize_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    values = row.get("values", []) if isinstance(row.get("values"), list) else []
    return [_normalize_cell(cell) for cell in values]


def _normalize_cell(cell: dict[str, Any]) -> dict[str, Any]:
    return {
        "formatted_value": cell.get("formattedValue", ""),
        "user_entered_value": cell.get("userEnteredValue", {}),
        "effective_value": cell.get("effectiveValue", {}),
        "note": cell.get("note", ""),
        "has_data_validation": bool(cell.get("dataValidation")),
        "has_pivot_table": bool(cell.get("pivotTable")),
        "format": _normalize_cell_format(cell.get("userEnteredFormat")),
    }


def _normalize_cell_format(format_value: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(format_value, dict):
        return {}
    text_format = format_value.get("textFormat") if isinstance(format_value.get("textFormat"), dict) else {}
    return {
        "bold": bool(text_format.get("bold")),
        "italic": bool(text_format.get("italic")),
        "font_size": text_format.get("fontSize", 0),
        "horizontal_alignment": format_value.get("horizontalAlignment", ""),
        "vertical_alignment": format_value.get("verticalAlignment", ""),
    }


def _normalize_dimension_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "hidden_by_user": bool(metadata.get("hiddenByUser")),
        "hidden_by_filter": bool(metadata.get("hiddenByFilter")),
        "pixel_size": metadata.get("pixelSize", 0),
    }


def _normalize_sheet(sheet: dict[str, Any]) -> dict[str, Any]:
    properties = sheet.get("properties", {})
    grid = properties.get("gridProperties", {})
    return {
        "sheet_id": properties.get("sheetId", 0),
        "title": properties.get("title", ""),
        "index": properties.get("index", 0),
        "row_count": grid.get("rowCount", 0),
        "column_count": grid.get("columnCount", 0),
        "hidden": bool(properties.get("hidden")),
    }


def _normalize_grid_range(range_value: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "sheet_id": (range_value or {}).get("sheetId", 0),
        "range": _format_grid_range(range_value),
    }


def _format_grid_range(range_value: dict[str, Any] | None) -> str:
    if not range_value:
        return "A1"
    start_column = _column_name(range_value.get("startColumnIndex", 0) + 1)
    start_row = range_value.get("startRowIndex", 0) + 1
    end_column = _column_name(
        range_value.get("endColumnIndex", range_value.get("startColumnIndex", 0) + 1)
    )
    end_row = range_value.get("endRowIndex", range_value.get("startRowIndex", 0) + 1)
    return f"{start_column}{start_row}:{end_column}{end_row}"


def _column_name(column_number: int) -> str:
    current = max(1, column_number)
    name = ""
    while current > 0:
        current -= 1
        name = chr(65 + (current % 26)) + name
        current //= 26
    return name


def _cell_coordinate(cell: str) -> tuple[int, int] | None:
    match = A1_CELL_RE.match(cell)
    if not match:
        return None
    column = 0
    for char in match.group(1).upper():
        column = column * 26 + ord(char) - 64
    return column, int(match.group(2))


def _json_loads(text: str) -> dict[str, Any]:
    import json

    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value
