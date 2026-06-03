from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from openpyxl.utils import range_boundaries

from workbook_manifest import _relationships, _workbook_sheets

SCHEMA_VERSION = "0.1"

CELL_REF_RE = re.compile(
    r"(?:(?P<sheet>'(?:[^']|'')+'|[A-Za-z_가-힣][A-Za-z0-9_가-힣 .&()-]*)!)?"
    r"(?P<start>\$?[A-Z]{1,3}\$?\d+)"
    r"(?::(?P<end>\$?[A-Z]{1,3}\$?\d+))?"
)
CELL_RE = re.compile(r"^([A-Z]{1,3})([0-9]+)$")


def build_formula_pattern_profile(
    workbook_path: Path,
    *,
    sheets: list[str] | None = None,
    row_windows: list[str] | None = None,
    default_max_rows: int = 50,
    max_columns: int = 160,
    sample_limit: int = 50,
) -> dict[str, Any]:
    workbook_path = workbook_path.expanduser().resolve()
    if not workbook_path.exists():
        raise FileNotFoundError(f"missing workbook: {workbook_path}")

    with ZipFile(workbook_path) as zf:
        workbook_rels = _relationships(zf, "xl/_rels/workbook.xml.rels")
        workbook_sheets = {
            sheet["name"]: sheet for sheet in _workbook_sheets(zf, workbook_rels)
        }
        selected_sheets = sheets or list(workbook_sheets)
        windows_by_sheet = _windows_by_sheet(
            selected_sheets,
            row_windows or [],
            default_max_rows=default_max_rows,
        )
        sheet_profiles = [
            _sheet_profile(
                zf,
                workbook_sheets[sheet_name],
                windows_by_sheet[sheet_name],
                max_columns=max_columns,
                sample_limit=sample_limit,
            )
            for sheet_name in selected_sheets
        ]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "path": str(workbook_path),
            "file_name": workbook_path.name,
            "size_bytes": workbook_path.stat().st_size,
            "sha256": _sha256(workbook_path),
        },
        "limits": {
            "default_max_rows": default_max_rows,
            "max_columns": max_columns,
            "sample_limit": sample_limit,
        },
        "sheets": sheet_profiles,
        "summary": _summary(sheet_profiles),
        "parser_observations": [
            {
                "level": "info",
                "message": "Formula signatures normalize A1 references relative to each formula cell so repeated formula structure can be detected before full table splitting.",
            }
        ],
    }


def _windows_by_sheet(
    selected_sheets: list[str],
    row_windows: list[str],
    *,
    default_max_rows: int,
) -> dict[str, list[tuple[int, int]]]:
    windows = {sheet: [(1, default_max_rows)] for sheet in selected_sheets}
    if not row_windows:
        return windows

    windows = {sheet: [] for sheet in selected_sheets}
    for spec in row_windows:
        sheet_name, bounds = _parse_row_window(spec)
        windows.setdefault(sheet_name, []).append(bounds)

    for sheet_name in selected_sheets:
        if not windows[sheet_name]:
            windows[sheet_name].append((1, default_max_rows))
    return windows


def _parse_row_window(spec: str) -> tuple[str, tuple[int, int]]:
    if ":" not in spec or "-" not in spec:
        raise ValueError("row window must look like Sheet Name:1-20")
    sheet_name, row_bounds = spec.rsplit(":", 1)
    start_text, end_text = row_bounds.split("-", 1)
    start = int(start_text)
    end = int(end_text)
    if start < 1 or end < start:
        raise ValueError("row window bounds must be positive and ordered")
    return sheet_name, (start, end)


def _sheet_profile(
    zf: ZipFile,
    sheet: dict[str, Any],
    windows: list[tuple[int, int]],
    *,
    max_columns: int,
    sample_limit: int,
) -> dict[str, Any]:
    if sheet["entry"] not in zf.namelist():
        return {
            "name": sheet["name"],
            "entry": sheet["entry"],
            "windows": [],
            "summary": {
                "window_count": 0,
                "formula_count": 0,
                "signature_group_count": 0,
                "repeated_signature_group_count": 0,
            },
            "parser_observations": [
                {"level": "error", "message": "Worksheet XML entry is missing."}
            ],
        }

    formulas_by_window = [[] for _ in windows]
    max_row = max(end for _, end in windows)
    shared_signatures: dict[str, str] = {}
    with zf.open(sheet["entry"]) as handle:
        current_cell: str | None = None
        current_row: int | None = None
        current_column: int | None = None
        for event, elem in ET.iterparse(handle, events=("start", "end")):
            tag = _local_name(elem.tag)
            if event == "start":
                if tag == "row":
                    current_row = _int_text(elem.attrib.get("r"))
                    if current_row is not None and current_row > max_row:
                        break
                elif tag == "c":
                    current_cell = elem.attrib.get("r")
                    current_row, current_column = _cell_position(current_cell)
            elif event == "end":
                if tag == "f" and current_cell and current_row and current_column:
                    if current_column <= max_columns:
                        item = _formula_item(
                            current_cell,
                            current_row,
                            current_column,
                            elem.text or "",
                            dict(elem.attrib),
                            shared_signatures,
                        )
                        for index, (start, end) in enumerate(windows):
                            if start <= current_row <= end:
                                formulas_by_window[index].append(item)
                elif tag == "c":
                    current_cell = None
                    current_row = None
                    current_column = None
                elem.clear()

    window_profiles = [
        _window_profile(start, end, formulas, max_columns, sample_limit)
        for (start, end), formulas in zip(windows, formulas_by_window)
    ]
    return {
        "name": sheet["name"],
        "entry": sheet["entry"],
        "windows": window_profiles,
        "summary": {
            "window_count": len(window_profiles),
            "formula_count": sum(window["formula_count"] for window in window_profiles),
            "signature_group_count": sum(
                window["signature_group_count"] for window in window_profiles
            ),
            "repeated_signature_group_count": sum(
                window["repeated_signature_group_count"] for window in window_profiles
            ),
        },
        "parser_observations": [],
    }


def _formula_item(
    cell: str,
    row: int,
    column: int,
    formula: str,
    attributes: dict[str, str],
    shared_signatures: dict[str, str],
) -> dict[str, Any]:
    signature = _formula_signature(formula, attributes, row, column, shared_signatures)
    shared_index = attributes.get("si")
    if formula and attributes.get("t") == "shared" and shared_index is not None:
        shared_signatures[shared_index] = signature
    return {
        "cell": cell,
        "row": row,
        "column": column,
        "formula": formula,
        "attributes": attributes,
        "signature": signature,
    }


def _window_profile(
    start_row: int,
    end_row: int,
    formulas: list[dict[str, Any]],
    max_columns: int,
    sample_limit: int,
) -> dict[str, Any]:
    groups = _signature_groups(formulas, sample_limit=10)
    return {
        "start_row": start_row,
        "end_row": end_row,
        "max_columns": max_columns,
        "formula_count": len(formulas),
        "signature_group_count": len(groups),
        "repeated_signature_group_count": sum(
            1 for group in groups if group["formula_count"] > 1
        ),
        "structure_hint": _structure_hint(formulas, groups),
        "formula_samples": formulas[:sample_limit],
        "signature_groups": groups,
    }


def _signature_groups(
    formulas: list[dict[str, Any]],
    *,
    sample_limit: int,
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for formula in formulas:
        signature = formula["signature"]
        group = groups.setdefault(
            signature,
            {
                "signature": signature,
                "formula_count": 0,
                "row_min": formula["row"],
                "row_max": formula["row"],
                "column_min": formula["column"],
                "column_max": formula["column"],
                "sample_cells": [],
                "formula_examples": [],
            },
        )
        group["formula_count"] += 1
        group["row_min"] = min(group["row_min"], formula["row"])
        group["row_max"] = max(group["row_max"], formula["row"])
        group["column_min"] = min(group["column_min"], formula["column"])
        group["column_max"] = max(group["column_max"], formula["column"])
        if len(group["sample_cells"]) < sample_limit:
            group["sample_cells"].append(formula["cell"])
        if formula["formula"] and formula["formula"] not in group["formula_examples"]:
            if len(group["formula_examples"]) < 3:
                group["formula_examples"].append(formula["formula"])
    return sorted(groups.values(), key=lambda item: item["formula_count"], reverse=True)


def _structure_hint(
    formulas: list[dict[str, Any]],
    groups: list[dict[str, Any]],
) -> str:
    if not formulas:
        return "value_only_window"
    formula_rows = {formula["row"] for formula in formulas}
    repeated_groups = [group for group in groups if group["formula_count"] >= 3]
    if len(formula_rows) == 1:
        return "summary_formula_band"
    if repeated_groups:
        return "repeated_formula_region_candidate"
    return "mixed_formula_region"


def _formula_signature(
    formula: str,
    attributes: dict[str, str],
    row: int,
    column: int,
    shared_signatures: dict[str, str],
) -> str:
    if not formula:
        shared_index = attributes.get("si")
        if shared_index is not None and shared_index in shared_signatures:
            return shared_signatures[shared_index]
        if shared_index is not None:
            return f"SHARED_FORMULA(si={shared_index})"
        return "EMPTY_FORMULA"
    expression = formula[1:] if formula.startswith("=") else formula
    return CELL_REF_RE.sub(
        lambda match: _relative_reference(match, row, column),
        expression.upper(),
    )


def _relative_reference(match: re.Match[str], row: int, column: int) -> str:
    sheet_prefix = ""
    if match.group("sheet"):
        sheet_prefix = f"{match.group('sheet')}!"
    start = _clean_cell_ref(match.group("start"))
    end = _clean_cell_ref(match.group("end") or match.group("start"))
    start_token = _relative_cell_token(start, row, column)
    if end == start:
        return f"{sheet_prefix}{start_token}"
    return f"{sheet_prefix}{start_token}:{_relative_cell_token(end, row, column)}"


def _relative_cell_token(cell: str, anchor_row: int, anchor_column: int) -> str:
    match = CELL_RE.match(cell)
    if not match:
        return cell
    column_letters, row_text = match.groups()
    target_column = range_boundaries(f"{cell}:{cell}")[0]
    target_row = int(row_text)
    return f"R[{target_row - anchor_row}]C[{target_column - anchor_column}]"


def _clean_cell_ref(value: str) -> str:
    return value.replace("$", "")


def _cell_position(cell: str | None) -> tuple[int | None, int | None]:
    if not cell:
        return None, None
    match = CELL_RE.match(cell)
    if not match:
        return None, None
    column_letters, row_text = match.groups()
    column = range_boundaries(f"{column_letters}{row_text}:{column_letters}{row_text}")[0]
    return int(row_text), column


def _summary(sheets: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "sheet_count": len(sheets),
        "window_count": sum(sheet["summary"]["window_count"] for sheet in sheets),
        "formula_count": sum(sheet["summary"]["formula_count"] for sheet in sheets),
        "signature_group_count": sum(
            sheet["summary"]["signature_group_count"] for sheet in sheets
        ),
        "repeated_signature_group_count": sum(
            sheet["summary"]["repeated_signature_group_count"] for sheet in sheets
        ),
    }


def _int_text(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build formula pattern signatures for selected workbook row windows."
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sheet", action="append", dest="sheets")
    parser.add_argument("--row-window", action="append", dest="row_windows")
    parser.add_argument("--default-max-rows", type=int, default=50)
    parser.add_argument("--max-columns", type=int, default=160)
    parser.add_argument("--sample-limit", type=int, default=50)
    args = parser.parse_args()

    profile = build_formula_pattern_profile(
        args.workbook,
        sheets=args.sheets,
        row_windows=args.row_windows,
        default_max_rows=args.default_max_rows,
        max_columns=args.max_columns,
        sample_limit=args.sample_limit,
    )
    payload = json.dumps(profile, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
