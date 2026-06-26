from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any


DEFAULT_FORMULA_TEMPLATE = "=IFERROR(SUMPRODUCT(({row_label_range}={row_label_cell})*({column_label_range}={column_label_cell})*{measure_range}),0)"
ERROR_PREFIXES = ("#REF!", "#VALUE!", "#N/A", "#DIV/0!", "#ERROR!", "#NAME?", "#NUM!")
DEFAULT_OUTPUT_FORMAT = {
    "header_bold": True,
    "freeze_header_rows": 2,
    "auto_resize_columns": True,
    "protect_created_sheet": False,
}


def normalize_formula_table_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")
    source = spec.get("source") if isinstance(spec.get("source"), dict) else {}
    fields = spec.get("fields") if isinstance(spec.get("fields"), dict) else {}
    output = spec.get("output") if isinstance(spec.get("output"), dict) else {}
    artifact_type = str(spec.get("artifact_type") or source.get("artifact_type") or source.get("type") or "").strip()
    if not artifact_type:
        artifact_type = "excel_workbook" if source.get("workbook_path") else "google_sheets"
    if artifact_type not in {"google_sheets", "excel_workbook"}:
        raise ValueError("spec source artifact_type must be google_sheets or excel_workbook")
    spreadsheet_id = str(spec.get("spreadsheet_id") or source.get("spreadsheet_id") or "")
    workbook_path = str(spec.get("workbook_path") or source.get("workbook_path") or "")
    if artifact_type == "google_sheets" and not spreadsheet_id:
        raise ValueError("spec.spreadsheet_id is required for google_sheets")
    if artifact_type == "excel_workbook" and not workbook_path:
        raise ValueError("spec.source.workbook_path is required for excel_workbook")
    creation_mode = str(output.get("creation_mode") or "").strip().lower()
    if not creation_mode:
        creation_mode = "copy" if artifact_type == "excel_workbook" else "sheet"
    if creation_mode not in {"copy", "sheet"}:
        raise ValueError("spec.output.creation_mode must be copy or sheet")
    if artifact_type == "google_sheets" and output.get("workbook_path"):
        raise ValueError("output.workbook_path is only valid for excel_workbook creation_mode='copy'")
    if artifact_type == "excel_workbook" and creation_mode == "sheet" and output.get("workbook_path"):
        raise ValueError("output.workbook_path is only valid when output.creation_mode='copy'")
    qualified_range = str(source.get("qualified_range") or "")
    if "!" not in qualified_range:
        raise ValueError("spec.source.qualified_range is required")
    start_col, start_row, end_col, end_row = range_bounds(qualified_range)
    header_row = int(source.get("header_row") or 1)
    if header_row < 1 or start_row + header_row > end_row:
        raise ValueError("spec.source.header_row must be inside the source range")
    formula_template = _formula_template(spec)
    output_format = _normalize_output_format(output.get("format") if isinstance(output.get("format"), dict) else {})
    output_canvas = _normalize_output_canvas(spec.get("output_canvas"))
    normalized_fields = {
        role: _normalize_field(fields.get(role), role)
        for role in ("row_label", "column_label", "measure")
    }
    for role, field in normalized_fields.items():
        field_column_index = column_index(field["column"])
        if field_column_index < start_col or field_column_index > end_col:
            raise ValueError(f"spec.fields.{role}.column is outside the source range")
    return {
        "schema_version": "1.0",
        "spec_kind": "formula_table_apply_v1",
        "artifact_type": artifact_type,
        "spreadsheet_id": spreadsheet_id,
        "source": {
            "artifact_type": artifact_type,
            "spreadsheet_id": spreadsheet_id,
            "workbook_path": str(Path(workbook_path).expanduser().resolve()) if workbook_path else "",
            "sheet_title": str(source.get("sheet_title") or sheet_title_from_qualified_range(qualified_range)),
            "qualified_range": qualified_range,
            "header_row": header_row,
        },
        "fields": normalized_fields,
        "output_canvas": output_canvas,
        "llm_prompt": str(spec.get("llm_prompt") or ""),
        "formula": {"template": formula_template},
        "output": {
            "sheet_title": str(output.get("sheet_title") or f"FORMULA_TABLE_{datetime.now(UTC).strftime('%Y%m%d_%H%M')}"),
            "title": str(output.get("title") or "Formula Table"),
            "creation_mode": creation_mode,
            "workbook_path": str(output.get("workbook_path") or ""),
            "copy_title": str(output.get("copy_title") or ""),
            "format": output_format,
        },
    }


def extract_layout_labels(spec: dict[str, Any], values: list[list[Any]]) -> dict[str, Any]:
    canvas_labels = _output_canvas_labels(spec.get("output_canvas"))
    if canvas_labels["row_labels"] and canvas_labels["column_labels"]:
        return {**canvas_labels, "source": "output_canvas"}

    source = spec["source"]
    start_col, _start_row, _end_col, _end_row = range_bounds(source["qualified_range"])
    header_row = int(source["header_row"])
    row_column_index = column_index(spec["fields"]["row_label"]["column"]) - start_col
    column_column_index = column_index(spec["fields"]["column_label"]["column"]) - start_col
    row_labels = []
    column_labels = []
    for row in values[header_row:]:
        if not isinstance(row, list):
            continue
        row_label = _cell_text(row[row_column_index] if 0 <= row_column_index < len(row) else "")
        column_label = _cell_text(row[column_column_index] if 0 <= column_column_index < len(row) else "")
        if row_label and row_label not in row_labels:
            row_labels.append(row_label)
        if column_label and column_label not in column_labels:
            column_labels.append(column_label)
    return {"row_labels": row_labels, "column_labels": column_labels, "source": "source_values"}


def build_formula_table_grid(
    *,
    spec: dict[str, Any],
    row_labels: list[str],
    column_labels: list[str],
    output_sheet_title: str,
) -> list[list[Any]]:
    source = spec["source"]
    fields = spec["fields"]
    formula_template = spec["formula"]["template"]
    source_sheet = quote_sheet_title(source["sheet_title"])
    _start_col, start_row, _end_col, end_row = range_bounds(source["qualified_range"])
    data_start_row = start_row + int(source["header_row"])
    row_range = _bounded_column_range(source_sheet, fields["row_label"]["column"], data_start_row, end_row)
    column_range = _bounded_column_range(source_sheet, fields["column_label"]["column"], data_start_row, end_row)
    measure_range = _bounded_column_range(source_sheet, fields["measure"]["column"], data_start_row, end_row)
    grid: list[list[Any]] = [
        [spec["output"]["title"], "", "Generated by spreadsheet-processing formula-table builder"],
        [fields["row_label"]["header"], *column_labels],
    ]
    for row_index, row_label in enumerate(row_labels, start=3):
        formula_row = [row_label]
        for output_column_index, column_label_value in enumerate(column_labels, start=2):
            formula_row.append(
                _render_formula_template(
                    template=formula_template,
                    measure_range=measure_range,
                    row_range=row_range,
                    column_range=column_range,
                    row_criteria=f"$A{row_index}",
                    column_criteria=f"{column_label(output_column_index)}$2",
                    row_value=row_label,
                    column_value=column_label_value,
                    source_sheet=source_sheet,
                    source_range=source["qualified_range"],
                    output_sheet=quote_sheet_title(output_sheet_title),
                )
            )
        grid.append(formula_row)
    if len(grid) == 2:
        grid.append(["No matching labels found"])
    return grid


def formula_table_readback_validation(values: list[list[Any]], expected_rows: int, expected_columns: int) -> dict[str, Any]:
    errors = []
    for row_index, row in enumerate(values, start=1):
        if not isinstance(row, list):
            continue
        for value_column_index, value in enumerate(row, start=1):
            text = _cell_text(value)
            if text.startswith(ERROR_PREFIXES):
                errors.append({"row": row_index, "column": value_column_index, "value": text})
    return {
        "status": "passed" if not errors else "failed",
        "expected_rows": expected_rows,
        "expected_columns": expected_columns,
        "readback_rows": len(values),
        "error_count": len(errors),
        "sample_errors": errors[:20],
    }


def count_formula_cells(values: list[list[Any]]) -> int:
    return sum(1 for row in values for value in row if isinstance(value, str) and value.startswith("="))


def quote_sheet_title(title: str) -> str:
    return "'" + str(title).replace("'", "''") + "'"


def sheet_title_from_qualified_range(qualified_range: str) -> str:
    title = str(qualified_range).split("!", 1)[0]
    if title.startswith("'") and title.endswith("'"):
        return title[1:-1].replace("''", "'")
    return title


def range_bounds(a1_range: str) -> tuple[int, int, int, int]:
    coordinate = str(a1_range).split("!", 1)[-1].replace("$", "").upper()
    start, separator, end = coordinate.partition(":")
    end = end if separator else start
    start_col, start_row = _cell_coordinate(start)
    end_col, end_row = _cell_coordinate(end)
    if end_col < start_col or end_row < start_row:
        raise ValueError(f"range must be bounded A1: {a1_range}")
    return start_col, start_row, end_col, end_row


def column_index(column: str) -> int:
    index = 0
    for char in str(column).upper():
        if not ("A" <= char <= "Z"):
            raise ValueError(f"invalid column label: {column}")
        index = index * 26 + ord(char) - 64
    if index < 1:
        raise ValueError(f"invalid column label: {column}")
    return index


def column_label(index: int) -> str:
    if index < 1:
        raise ValueError("column index must be positive")
    label = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        label = chr(65 + remainder) + label
    return label


def _cell_coordinate(cell: str) -> tuple[int, int]:
    match = re.match(r"^([A-Z]{1,4})([1-9][0-9]*)$", str(cell).upper())
    if not match:
        raise ValueError(f"range must be bounded A1: {cell}")
    return column_index(match.group(1)), int(match.group(2))


def _normalize_output_canvas(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    rows: list[list[str]] = []
    max_column = -1
    for raw_row in value:
        if not isinstance(raw_row, list):
            continue
        row = [_cell_text(cell) for cell in raw_row]
        rows.append(row)
        for raw_column_index, cell in enumerate(row):
            if cell:
                max_column = max(max_column, raw_column_index)
    while rows and not any(rows[-1]):
        rows.pop()
    if not rows or max_column < 0:
        return []
    return [row[: max_column + 1] for row in rows]


def _output_canvas_labels(value: Any) -> dict[str, list[str]]:
    canvas = _normalize_output_canvas(value)
    if not canvas:
        return {"row_labels": [], "column_labels": []}
    column_labels = [
        label for label in (_cell_text(cell) for cell in canvas[0][1:]) if label
    ]
    row_labels = [
        label for label in (_cell_text(row[0] if row else "") for row in canvas[1:]) if label
    ]
    return {
        "row_labels": _dedupe_preserving_order(row_labels),
        "column_labels": _dedupe_preserving_order(column_labels),
    }


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _normalize_field(value: Any, role: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"spec.fields.{role} is required")
    column = str(value.get("column") or "").upper()
    if not re.match(r"^[A-Z]{1,4}$", column):
        raise ValueError(f"spec.fields.{role}.column must be a column label")
    return {
        "column": column,
        "header": str(value.get("header") or column),
        "selected_cell": str(value.get("selected_cell") or ""),
    }


def _formula_template(spec: dict[str, Any]) -> str:
    formula = spec.get("formula") if isinstance(spec.get("formula"), dict) else {}
    template = str(formula.get("template") or spec.get("formula_template") or "")
    if not template:
        template = DEFAULT_FORMULA_TEMPLATE
    if not template.strip().startswith("="):
        raise ValueError("formula template must start with '='")
    return template.strip()


def _normalize_output_format(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "header_bold": bool(value.get("header_bold", DEFAULT_OUTPUT_FORMAT["header_bold"])),
        "freeze_header_rows": max(0, int(value.get("freeze_header_rows", DEFAULT_OUTPUT_FORMAT["freeze_header_rows"]) or 0)),
        "auto_resize_columns": bool(value.get("auto_resize_columns", DEFAULT_OUTPUT_FORMAT["auto_resize_columns"])),
        "protect_created_sheet": bool(value.get("protect_created_sheet", DEFAULT_OUTPUT_FORMAT["protect_created_sheet"])),
    }


def _render_formula_template(
    *,
    template: str,
    measure_range: str,
    row_range: str,
    column_range: str,
    row_criteria: str,
    column_criteria: str,
    row_value: str,
    column_value: str,
    source_sheet: str,
    source_range: str,
    output_sheet: str,
) -> str:
    replacements = {
        "measure_range": measure_range,
        "row_label_range": row_range,
        "column_label_range": column_range,
        "row_label_cell": row_criteria,
        "column_label_cell": column_criteria,
        "row_label_value": _formula_string(row_value),
        "column_label_value": _formula_string(column_value),
        "source_sheet": source_sheet,
        "source_range": source_range,
        "output_sheet": output_sheet,
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def _bounded_column_range(sheet_ref: str, column: str, start_row: int, end_row: int) -> str:
    return f"{sheet_ref}!${column}${start_row}:${column}${end_row}"


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _formula_string(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'
