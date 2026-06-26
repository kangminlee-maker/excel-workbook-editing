from __future__ import annotations

from datetime import UTC, datetime
import json
import re
from typing import Any
from urllib.parse import quote, urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
from uuid import uuid4


AUTH_SCHEME = "".join(("Be", "arer"))
SHEETS_URL_PATTERN = re.compile(r"^https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)")
A1_CELL_RE = re.compile(r"^\$?([A-Za-z]+)\$?([1-9][0-9]*)$")
PLAIN_A1_RANGE_RE = re.compile(r"^\$?[A-Za-z]{1,4}\$?\d{1,7}(?::\$?[A-Za-z]{1,4}\$?\d{1,7})?$")
SHEETS_METADATA_FIELDS = ",".join(
    [
        "spreadsheetId",
        "properties(title,locale,timeZone)",
        "sheets(properties(sheetId,title,index,hidden,gridProperties(rowCount,columnCount)),protectedRanges(protectedRangeId,range,warningOnly))",
        "namedRanges(name,range)",
    ]
)
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


class SheetsApiError(RuntimeError):
    """Raised when a Google Sheets API request fails."""


def parse_spreadsheet_url(url: str) -> dict[str, str]:
    match = SHEETS_URL_PATTERN.match(str(url or ""))
    parsed = urlparse(str(url or ""))
    query = parse_qs(parsed.query)
    fragment = parse_qs(parsed.fragment)
    return {
        "spreadsheet_id": match.group(1) if match else "",
        "gid": (fragment.get("gid") or query.get("gid") or [""])[0],
        "range": (fragment.get("range") or query.get("range") or [""])[0],
    }


def inspect_sheet(
    *,
    spreadsheet_id: str,
    access_token: str,
    operation: str = "inspect.metadata",
    ranges: list[str] | None = None,
    gid: str = "",
    field_mask: str = "grid_basic_v1",
    auth_summary: dict[str, Any] | None = None,
    transport=None,
) -> dict[str, Any]:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    request_ranges = ranges or []
    snapshot_id = f"snapshot-{uuid4()}"
    captured_at = datetime.now(UTC).isoformat()
    transport = transport or google_get_json
    auth_summary = auth_summary or {"mode": "user_oauth"}

    metadata = transport(build_metadata_url(spreadsheet_id), access_token)
    if operation == "inspect.metadata":
        return normalize_metadata(
            metadata,
            snapshot_id=snapshot_id,
            captured_at=captured_at,
            auth_summary=auth_summary,
        )

    qualified_ranges = qualify_ranges(metadata, ranges=request_ranges, gid=gid)
    if operation in {"inspect.values_window", "inspect.formula_window"}:
        value_render_option = "FORMULA" if operation == "inspect.formula_window" else "FORMATTED_VALUE"
        values = transport(
            build_values_window_url(
                spreadsheet_id=spreadsheet_id,
                ranges=qualified_ranges,
                value_render_option=value_render_option,
            ),
            access_token,
        )
        return normalize_values_window(
            values,
            spreadsheet_id=spreadsheet_id,
            snapshot_id=snapshot_id,
            captured_at=captured_at,
            operation=operation,
            ranges=qualified_ranges,
            value_render_option=value_render_option,
            auth_summary=auth_summary,
        )

    if operation == "inspect.grid_window":
        grid = transport(
            build_grid_window_url(
                spreadsheet_id=spreadsheet_id,
                ranges=qualified_ranges,
                field_mask=field_mask,
            ),
            access_token,
        )
        return normalize_grid_window(
            grid,
            snapshot_id=snapshot_id,
            captured_at=captured_at,
            operation=operation,
            ranges=qualified_ranges,
            field_mask=field_mask,
            auth_summary=auth_summary,
        )

    raise ValueError(f"unsupported operation: {operation}")


def apply_values_update(
    *,
    spreadsheet_id: str,
    access_token: str,
    write_requests: list[dict[str, Any]],
    gid: str = "",
    operation: str = "apply.values_update",
    auth_summary: dict[str, Any] | None = None,
    transport=None,
    write_transport=None,
) -> dict[str, Any]:
    if operation not in {"apply.values_update", "rollback.values_restore"}:
        raise ValueError(f"unsupported values write operation: {operation}")
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    if not write_requests:
        raise ValueError("write_requests are required")

    snapshot_id = f"snapshot-{uuid4()}"
    captured_at = datetime.now(UTC).isoformat()
    transport = transport or google_get_json
    write_transport = write_transport or google_post_json
    auth_summary = auth_summary or {"mode": "user_oauth"}

    metadata = transport(build_metadata_url(spreadsheet_id), access_token)
    qualified_write_requests = qualify_write_requests(metadata, write_requests=write_requests, gid=gid)
    ranges = [item["range"] for item in qualified_write_requests]
    before_values = transport(
        build_values_window_url(
            spreadsheet_id=spreadsheet_id,
            ranges=ranges,
            value_render_option="FORMULA",
        ),
        access_token,
    )
    rollback_write_requests = rollback_write_requests_from_values_snapshot(
        ranges=ranges,
        values_snapshot=before_values,
    )
    update_response = write_transport(
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
                for item in qualified_write_requests
            ],
        },
    )
    readback_values = transport(
        build_values_window_url(
            spreadsheet_id=spreadsheet_id,
            ranges=ranges,
            value_render_option="FORMULA",
        ),
        access_token,
    )
    return normalize_values_apply_result(
        spreadsheet_id=spreadsheet_id,
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        operation=operation,
        write_requests=qualified_write_requests,
        before_values=before_values,
        update_response=update_response,
        readback_values=readback_values,
        rollback_write_requests=rollback_write_requests,
        auth_summary=auth_summary,
    )


def build_metadata_url(spreadsheet_id: str) -> str:
    query = urlencode({"includeGridData": "false", "fields": SHEETS_METADATA_FIELDS})
    return f"https://sheets.googleapis.com/v4/spreadsheets/{quote(spreadsheet_id, safe='')}?{query}"


def build_values_window_url(*, spreadsheet_id: str, ranges: list[str], value_render_option: str) -> str:
    query = urlencode(
        {
            "ranges": ranges,
            "valueRenderOption": value_render_option,
            "dateTimeRenderOption": "FORMATTED_STRING",
        },
        doseq=True,
    )
    return f"https://sheets.googleapis.com/v4/spreadsheets/{quote(spreadsheet_id, safe='')}/values:batchGet?{query}"


def build_grid_window_url(*, spreadsheet_id: str, ranges: list[str], field_mask: str) -> str:
    if field_mask not in GRID_FIELD_MASKS:
        raise ValueError("unsupported field_mask")
    query = urlencode(
        {
            "includeGridData": "true",
            "ranges": ranges,
            "fields": GRID_FIELD_MASKS[field_mask],
        },
        doseq=True,
    )
    return f"https://sheets.googleapis.com/v4/spreadsheets/{quote(spreadsheet_id, safe='')}?{query}"


def build_values_update_url(spreadsheet_id: str) -> str:
    return f"https://sheets.googleapis.com/v4/spreadsheets/{quote(spreadsheet_id, safe='')}/values:batchUpdate"


def build_spreadsheet_batch_update_url(spreadsheet_id: str) -> str:
    return f"https://sheets.googleapis.com/v4/spreadsheets/{quote(spreadsheet_id, safe='')}:batchUpdate"


def build_drive_copy_url(file_id: str) -> str:
    query = urlencode({"fields": "id,name,mimeType,webViewLink"})
    return f"https://www.googleapis.com/drive/v3/files/{quote(file_id, safe='')}/copy?{query}"


def build_drive_delete_url(file_id: str) -> str:
    return f"https://www.googleapis.com/drive/v3/files/{quote(file_id, safe='')}"


def google_get_json(url: str, access_token: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Authorization": f"{AUTH_SCHEME} {access_token}",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise SheetsApiError("Google Sheets response must be a JSON object")
    return data


def google_post_json(url: str, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
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
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise SheetsApiError("Google Sheets write response must be a JSON object")
    return data


def google_delete_json(url: str, access_token: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Authorization": f"{AUTH_SCHEME} {access_token}",
            "Accept": "application/json",
        },
        method="DELETE",
    )
    with urlopen(request, timeout=60) as response:
        raw = response.read().decode("utf-8").strip()
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise SheetsApiError("Google Drive delete response must be a JSON object")
    return data


def qualify_ranges(metadata: dict[str, Any], *, ranges: list[str], gid: str = "") -> list[str]:
    if not ranges:
        raise ValueError("at least one range is required for window operations")
    sheet_title = sheet_title_for_gid(metadata, gid) if gid else first_visible_sheet_title(metadata)
    qualified = []
    for range_text in ranges:
        normalized = str(range_text).strip()
        if not normalized:
            continue
        if "!" in normalized:
            qualified.append(normalized)
        elif PLAIN_A1_RANGE_RE.match(normalized):
            qualified.append(f"{quote_sheet_title(sheet_title)}!{normalized.replace('$', '').upper()}")
        else:
            raise ValueError(f"range must be bounded A1: {range_text}")
    if not qualified:
        raise ValueError("at least one range is required for window operations")
    return qualified


def qualify_write_requests(
    metadata: dict[str, Any],
    *,
    write_requests: list[dict[str, Any]],
    gid: str = "",
) -> list[dict[str, Any]]:
    ranges = [str(item.get("range", "")).strip() for item in write_requests]
    qualified_ranges = qualify_ranges(metadata, ranges=ranges, gid=gid)
    if len(qualified_ranges) != len(write_requests):
        raise ValueError("write_requests contain empty or invalid ranges")
    qualified = []
    for request_item, qualified_range in zip(write_requests, qualified_ranges):
        values = request_item.get("values")
        dimensions = range_dimensions(qualified_range)
        if dimensions is None or not _values_match_dimensions(values, dimensions):
            raise ValueError(f"write values must exactly match range dimensions: {qualified_range}")
        qualified.append({"range": qualified_range, "values": values})
    return qualified


def sheet_title_for_gid(metadata: dict[str, Any], gid: str) -> str:
    for sheet in metadata.get("sheets", []) or []:
        props = sheet.get("properties", {}) if isinstance(sheet, dict) else {}
        if str(props.get("sheetId", "")) == str(gid):
            return str(props.get("title", ""))
    raise ValueError(f"sheet gid not found in metadata: {gid}")


def first_visible_sheet_title(metadata: dict[str, Any]) -> str:
    for sheet in metadata.get("sheets", []) or []:
        props = sheet.get("properties", {}) if isinstance(sheet, dict) else {}
        if not props.get("hidden") and props.get("title"):
            return str(props["title"])
    raise ValueError("spreadsheet has no visible sheet title")


def quote_sheet_title(title: str) -> str:
    return "'" + str(title).replace("'", "''") + "'"


def range_dimensions(a1_range: str) -> tuple[int, int] | None:
    coordinate = a1_range.rsplit("!", 1)[-1].replace("$", "")
    start, separator, end = coordinate.partition(":")
    end = end if separator else start
    start_cell = _cell_coordinate(start)
    end_cell = _cell_coordinate(end)
    if start_cell is None or end_cell is None:
        return None
    start_column, start_row = start_cell
    end_column, end_row = end_cell
    if end_column < start_column or end_row < start_row:
        return None
    return end_row - start_row + 1, end_column - start_column + 1


def rollback_write_requests_from_values_snapshot(
    *,
    ranges: list[str],
    values_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    by_range = {
        str(item.get("range", "")): item.get("values", [])
        for item in values_snapshot.get("valueRanges", []) or []
        if isinstance(item, dict)
    }
    rollback = []
    for range_text in ranges:
        dimensions = range_dimensions(range_text)
        if dimensions is None:
            raise ValueError(f"rollback range must be bounded A1: {range_text}")
        rollback.append(
            {
                "range": range_text,
                "values": _pad_values(by_range.get(range_text, []), dimensions),
            }
        )
    return rollback


def normalize_metadata(
    metadata: dict[str, Any],
    *,
    snapshot_id: str,
    captured_at: str,
    auth_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    props = metadata.get("properties", {}) if isinstance(metadata.get("properties"), dict) else {}
    sheets = metadata.get("sheets", []) if isinstance(metadata.get("sheets"), list) else []
    artifacts = [{"kind": "google_auth", "summary": auth_summary}] if auth_summary else []
    return {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "operation": "inspect.metadata",
        "spreadsheet_id": metadata.get("spreadsheetId", ""),
        "title": props.get("title", ""),
        "locale": props.get("locale", ""),
        "time_zone": props.get("timeZone", ""),
        "tabs": [_normalize_sheet(sheet) for sheet in sheets],
        "named_ranges": [
            {"name": item.get("name", ""), "range": _normalize_grid_range(item.get("range"))}
            for item in metadata.get("namedRanges", []) or []
        ],
        "protected_ranges": [
            {
                "protected_range_id": item.get("protectedRangeId", 0),
                "range": _normalize_grid_range(item.get("range")),
                "warning_only": bool(item.get("warningOnly")),
            }
            for sheet in sheets
            for item in sheet.get("protectedRanges", []) or []
        ],
        "artifacts": artifacts,
    }


def normalize_values_window(
    values: dict[str, Any],
    *,
    spreadsheet_id: str,
    snapshot_id: str,
    captured_at: str,
    operation: str,
    ranges: list[str],
    value_render_option: str,
    auth_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _window_base(
        spreadsheet_id=spreadsheet_id,
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        operation=operation,
        ranges=ranges,
        auth_summary=auth_summary,
        extra={
            "value_render_option": value_render_option,
            "windows": [
                {
                    "range": item.get("range", ""),
                    "major_dimension": item.get("majorDimension", ""),
                    "values": item.get("values", []),
                    "row_count": len(item.get("values", []) or []),
                    "column_count": max((len(row) for row in item.get("values", []) or []), default=0),
                }
                for item in values.get("valueRanges", []) or []
            ],
        },
    )


def normalize_grid_window(
    metadata: dict[str, Any],
    *,
    snapshot_id: str,
    captured_at: str,
    operation: str,
    ranges: list[str],
    field_mask: str,
    auth_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _window_base(
        spreadsheet_id=metadata.get("spreadsheetId", ""),
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        operation=operation,
        ranges=ranges,
        auth_summary=auth_summary,
        extra={
            "field_mask": field_mask,
            "windows": [_normalize_grid_sheet(sheet) for sheet in metadata.get("sheets", []) or []],
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
    auth_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ranges = [item["range"] for item in write_requests]
    artifacts = [{"kind": "google_auth", "summary": auth_summary}] if auth_summary else []
    return {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "operation": operation,
        "spreadsheet_id": spreadsheet_id,
        "requested_ranges": ranges,
        "value_input_option": "USER_ENTERED",
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
            "rollback_of_request_id": snapshot_id,
        },
        "artifacts": artifacts,
    }


def _window_base(
    *,
    spreadsheet_id: str,
    snapshot_id: str,
    captured_at: str,
    operation: str,
    ranges: list[str],
    auth_summary: dict[str, Any] | None,
    extra: dict[str, Any],
) -> dict[str, Any]:
    artifacts = [{"kind": "google_auth", "summary": auth_summary}] if auth_summary else []
    return {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "operation": operation,
        "spreadsheet_id": spreadsheet_id,
        "requested_ranges": ranges,
        "artifacts": artifacts,
        **extra,
    }


def _normalize_sheet(sheet: dict[str, Any]) -> dict[str, Any]:
    props = sheet.get("properties", {}) if isinstance(sheet.get("properties"), dict) else {}
    grid = props.get("gridProperties", {}) if isinstance(props.get("gridProperties"), dict) else {}
    return {
        "sheet_id": props.get("sheetId", 0),
        "title": props.get("title", ""),
        "index": props.get("index", 0),
        "hidden": bool(props.get("hidden")),
        "row_count": grid.get("rowCount", 0),
        "column_count": grid.get("columnCount", 0),
        "frozen_row_count": grid.get("frozenRowCount", 0),
        "frozen_column_count": grid.get("frozenColumnCount", 0),
    }


def _normalize_value_ranges(values: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "range": item.get("range", ""),
            "major_dimension": item.get("majorDimension", ""),
            "values": item.get("values", []),
            "row_count": len(item.get("values", []) or []),
            "column_count": max((len(row) for row in item.get("values", []) or []), default=0),
        }
        for item in values.get("valueRanges", []) or []
        if isinstance(item, dict)
    ]


def _values_match_dimensions(values: Any, dimensions: tuple[int, int]) -> bool:
    expected_rows, expected_columns = dimensions
    if not isinstance(values, list) or len(values) != expected_rows:
        return False
    for row in values:
        if not isinstance(row, list) or len(row) != expected_columns:
            return False
    return True


def _pad_values(values: Any, dimensions: tuple[int, int]) -> list[list[Any]]:
    expected_rows, expected_columns = dimensions
    source_rows = values if isinstance(values, list) else []
    padded = []
    for row_index in range(expected_rows):
        source_row = source_rows[row_index] if row_index < len(source_rows) and isinstance(source_rows[row_index], list) else []
        padded.append(
            [
                source_row[column_index] if column_index < len(source_row) else ""
                for column_index in range(expected_columns)
            ]
        )
    return padded


def _cell_coordinate(cell: str) -> tuple[int, int] | None:
    match = A1_CELL_RE.match(cell)
    if not match:
        return None
    column = 0
    for char in match.group(1).upper():
        column = column * 26 + ord(char) - 64
    return column, int(match.group(2))


def _normalize_grid_sheet(sheet: dict[str, Any]) -> dict[str, Any]:
    return {
        **_normalize_sheet(sheet),
        "windows": [_normalize_grid_data(item) for item in sheet.get("data", []) or []],
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
    rows = window.get("rowData", []) if isinstance(window.get("rowData"), list) else []
    return {
        "start_row": window.get("startRow", 0),
        "start_column": window.get("startColumn", 0),
        "row_count": len(rows),
        "rows": [[_normalize_cell(cell) for cell in row.get("values", []) or []] for row in rows],
        "row_metadata": [_normalize_dimension_metadata(item) for item in window.get("rowMetadata", []) or []],
        "column_metadata": [_normalize_dimension_metadata(item) for item in window.get("columnMetadata", []) or []],
    }


def _normalize_cell(cell: dict[str, Any]) -> dict[str, Any]:
    return {
        "formatted_value": cell.get("formattedValue", ""),
        "user_entered_value": cell.get("userEnteredValue", {}),
        "effective_value": cell.get("effectiveValue", {}),
        "note": cell.get("note", ""),
        "has_data_validation": bool(cell.get("dataValidation")),
        "has_pivot_table": bool(cell.get("pivotTable")),
        "format": _normalize_format(cell.get("userEnteredFormat")),
    }


def _normalize_format(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    text_format = value.get("textFormat") if isinstance(value.get("textFormat"), dict) else {}
    return {
        "bold": bool(text_format.get("bold")),
        "italic": bool(text_format.get("italic")),
        "font_size": text_format.get("fontSize", 0),
        "horizontal_alignment": value.get("horizontalAlignment", ""),
        "vertical_alignment": value.get("verticalAlignment", ""),
    }


def _normalize_dimension_metadata(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "hidden_by_user": bool(value.get("hiddenByUser")),
        "hidden_by_filter": bool(value.get("hiddenByFilter")),
        "pixel_size": value.get("pixelSize", 0),
    }


def _normalize_grid_range(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "sheet_id": value.get("sheetId", 0),
        "start_row_index": value.get("startRowIndex", 0),
        "end_row_index": value.get("endRowIndex", 0),
        "start_column_index": value.get("startColumnIndex", 0),
        "end_column_index": value.get("endColumnIndex", 0),
    }
