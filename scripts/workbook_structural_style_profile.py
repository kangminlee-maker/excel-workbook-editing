from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from openpyxl.utils import range_boundaries

SCHEMA_VERSION = "0.1"
MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def build_structural_style_profile(
    manifest_path: Path,
    readonly_sample_path: Path,
    *,
    sheets: list[str] | None = None,
    max_sheet_xml_bytes: int = 50_000_000,
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    readonly_sample_path = readonly_sample_path.expanduser().resolve()
    manifest = _read_json(manifest_path)
    sample = _read_json(readonly_sample_path)
    workbook_path = Path(manifest["source"]["path"]).expanduser().resolve()
    if not workbook_path.exists():
        raise FileNotFoundError(f"missing workbook: {workbook_path}")

    manifest_sheets = {sheet["name"]: sheet for sheet in manifest["workbook"]["sheets"]}
    sample_sheets = {sheet["name"]: sheet for sheet in sample["sheets"]}
    selected_sheets = sheets or [sheet["name"] for sheet in manifest["workbook"]["sheets"]]

    with ZipFile(workbook_path) as zf:
        style_catalog = _style_catalog(zf)
        sheet_profiles = []
        for sheet_name in selected_sheets:
            if sheet_name not in manifest_sheets:
                raise ValueError(f"missing manifest sheet: {sheet_name}")
            if sheet_name not in sample_sheets:
                raise ValueError(f"missing readonly sample sheet: {sheet_name}")
            sheet_profiles.append(
                _sheet_profile(
                    zf,
                    manifest_sheets[sheet_name],
                    sample_sheets[sheet_name],
                    style_catalog=style_catalog,
                    max_sheet_xml_bytes=max_sheet_xml_bytes,
                )
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "manifest": str(manifest_path),
            "readonly_sample": str(readonly_sample_path),
        },
        "source": manifest["source"],
        "limits": {"max_sheet_xml_bytes": max_sheet_xml_bytes},
        "style_catalog": style_catalog,
        "sheets": sheet_profiles,
        "summary": _summary(sheet_profiles),
        "parser_observations": _parser_observations(sheet_profiles),
    }


def _sheet_profile(
    zf: ZipFile,
    manifest_sheet: dict[str, Any],
    sample_sheet: dict[str, Any],
    *,
    style_catalog: dict[str, Any],
    max_sheet_xml_bytes: int,
) -> dict[str, Any]:
    entry = manifest_sheet["entry"]
    windows = [
        {"start_row": window["start_row"], "end_row": window["end_row"]}
        for window in sample_sheet["windows"]
    ]
    base = {
        "name": manifest_sheet["name"],
        "entry": entry,
        "dimension": manifest_sheet.get("dimension"),
        "dimension_bounds": manifest_sheet.get("dimension_bounds"),
        "windows": windows,
    }
    if not entry or entry not in zf.namelist():
        return {
            **base,
            "detail_status": "missing_entry",
            "entry_size_bytes": 0,
            "merge_ranges": [],
            "row_dimensions": [],
            "column_dimensions": [],
            "sampled_style_cells": [],
            "style_boundaries": [],
            "summary": _sheet_summary([], [], [], [], []),
            "parser_observations": [
                {"level": "warning", "message": "Worksheet XML entry is missing."}
            ],
        }

    info = zf.getinfo(entry)
    if info.file_size > max_sheet_xml_bytes:
        return {
            **base,
            "detail_status": "skipped_large_xml",
            "entry_size_bytes": info.file_size,
            "merge_ranges": [],
            "row_dimensions": [],
            "column_dimensions": [],
            "sampled_style_cells": [],
            "style_boundaries": [],
            "summary": _sheet_summary([], [], [], [], []),
            "parser_observations": [
                {
                    "level": "warning",
                    "message": "Worksheet XML was too large for structural style profiling in this pass.",
                }
            ],
        }

    scanned = _scan_sheet(
        zf,
        entry,
        windows=windows,
        style_catalog=style_catalog,
    )
    return {
        **base,
        "detail_status": "scanned",
        "entry_size_bytes": info.file_size,
        **scanned,
        "summary": _sheet_summary(
            scanned["merge_ranges"],
            scanned["row_dimensions"],
            scanned["column_dimensions"],
            scanned["sampled_style_cells"],
            scanned["style_boundaries"],
        ),
        "parser_observations": [],
    }


def _scan_sheet(
    zf: ZipFile,
    entry: str,
    *,
    windows: list[dict[str, int]],
    style_catalog: dict[str, Any],
) -> dict[str, Any]:
    merge_ranges: list[dict[str, Any]] = []
    row_dimensions: list[dict[str, Any]] = []
    column_dimensions: list[dict[str, Any]] = []
    sampled_style_cells: list[dict[str, Any]] = []
    current_row: int | None = None
    row_cells: list[dict[str, Any]] = []
    boundary_accumulator: dict[tuple[int, int], dict[str, Any]] = {}

    with zf.open(entry) as handle:
        for event, elem in ET.iterparse(handle, events=("start", "end")):
            tag = _local_name(elem.tag)
            if event == "start":
                if tag == "col":
                    column_dimensions.append(_column_dimension(elem))
                elif tag == "row":
                    current_row = _int_or_none(elem.attrib.get("r"))
                    if current_row is not None and _row_in_windows(current_row, windows):
                        row_dimensions.append(_row_dimension(elem))
                    row_cells = []
                elif tag == "c":
                    cell_ref = elem.attrib.get("r")
                    position = _cell_position(cell_ref)
                    if position is None:
                        continue
                    row, column = position
                    if not _row_in_windows(row, windows):
                        continue
                    style_id = int(elem.attrib.get("s", "0"))
                    style = _style_by_id(style_catalog, style_id)
                    cell = {
                        "cell": cell_ref,
                        "row": row,
                        "column": column,
                        "style_id": style_id,
                        "visual_signature": style["visual_signature"],
                        "number_format_signature": style["number_format_signature"],
                    }
                    row_cells.append(cell)
                    sampled_style_cells.append(cell)
                elif tag == "mergeCell":
                    ref = elem.attrib.get("ref")
                    bounds = _range_bounds(ref)
                    if ref and bounds:
                        merge_ranges.append({"range": ref, "bounds": bounds})
            elif event == "end":
                if tag == "row":
                    if current_row is not None and _row_in_windows(current_row, windows):
                        _accumulate_style_boundaries(
                            boundary_accumulator,
                            current_row,
                            row_cells,
                        )
                    current_row = None
                    row_cells = []
                elem.clear()

    return {
        "merge_ranges": merge_ranges,
        "row_dimensions": row_dimensions,
        "column_dimensions": column_dimensions,
        "sampled_style_cells": sampled_style_cells,
        "style_boundaries": _style_boundaries(boundary_accumulator),
    }


def _accumulate_style_boundaries(
    boundaries: dict[tuple[int, int], dict[str, Any]],
    row: int,
    cells: list[dict[str, Any]],
) -> None:
    ordered = sorted(cells, key=lambda cell: cell["column"])
    for left, right in zip(ordered, ordered[1:]):
        if right["column"] != left["column"] + 1:
            continue
        if left["visual_signature"] == right["visual_signature"]:
            continue
        key = (left["column"], right["column"])
        item = boundaries.setdefault(
            key,
            {
                "type": "style_discontinuity_boundary",
                "left_end_column": left["column"],
                "right_start_column": right["column"],
                "row_count": 0,
                "sample_rows": [],
                "left_visual_signature": left["visual_signature"],
                "right_visual_signature": right["visual_signature"],
            },
        )
        item["row_count"] += 1
        if len(item["sample_rows"]) < 10:
            item["sample_rows"].append(row)


def _style_boundaries(boundaries: dict[tuple[int, int], dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for item in boundaries.values():
        row_count = item["row_count"]
        confidence = 0.48
        if row_count >= 5:
            confidence = 0.68
        elif row_count >= 2:
            confidence = 0.58
        output.append(
            {
                **item,
                "confidence": confidence,
                "reason": "Adjacent sampled cells have different visual style signatures across one or more rows.",
            }
        )
    return sorted(
        output,
        key=lambda item: (-item["row_count"], item["left_end_column"], item["right_start_column"]),
    )


def _style_catalog(zf: ZipFile) -> dict[str, Any]:
    if "xl/styles.xml" not in zf.namelist():
        return {
            "available": False,
            "cell_xf_count": 0,
            "cell_xfs": [],
        }
    root = ET.fromstring(zf.read("xl/styles.xml"))
    cell_xfs = []
    cell_xfs_elem = root.find(f"{MAIN_NS}cellXfs")
    if cell_xfs_elem is not None:
        for index, xf in enumerate(cell_xfs_elem.findall(f"{MAIN_NS}xf")):
            alignment = xf.find(f"{MAIN_NS}alignment")
            alignment_attrib = dict(alignment.attrib) if alignment is not None else {}
            visual_signature = "|".join(
                [
                    f"font:{xf.attrib.get('fontId', '0')}",
                    f"fill:{xf.attrib.get('fillId', '0')}",
                    f"border:{xf.attrib.get('borderId', '0')}",
                    f"align:{alignment_attrib}",
                ]
            )
            number_format_signature = f"numFmt:{xf.attrib.get('numFmtId', '0')}"
            cell_xfs.append(
                {
                    "style_id": index,
                    "numFmtId": xf.attrib.get("numFmtId", "0"),
                    "fontId": xf.attrib.get("fontId", "0"),
                    "fillId": xf.attrib.get("fillId", "0"),
                    "borderId": xf.attrib.get("borderId", "0"),
                    "xfId": xf.attrib.get("xfId"),
                    "applyNumberFormat": xf.attrib.get("applyNumberFormat"),
                    "applyFont": xf.attrib.get("applyFont"),
                    "applyFill": xf.attrib.get("applyFill"),
                    "applyBorder": xf.attrib.get("applyBorder"),
                    "alignment": alignment_attrib,
                    "visual_signature": visual_signature,
                    "number_format_signature": number_format_signature,
                }
            )
    return {
        "available": True,
        "cell_xf_count": len(cell_xfs),
        "cell_xfs": cell_xfs,
    }


def _style_by_id(style_catalog: dict[str, Any], style_id: int) -> dict[str, Any]:
    cell_xfs = style_catalog.get("cell_xfs", [])
    if 0 <= style_id < len(cell_xfs):
        return cell_xfs[style_id]
    return {
        "visual_signature": "font:0|fill:0|border:0|align:{}",
        "number_format_signature": "numFmt:0",
    }


def _row_dimension(elem: ET.Element) -> dict[str, Any]:
    return {
        "row": _int_or_none(elem.attrib.get("r")),
        "height": _float_or_none(elem.attrib.get("ht")),
        "custom_height": elem.attrib.get("customHeight") == "1",
        "hidden": elem.attrib.get("hidden") == "1",
        "style_id": _int_or_none(elem.attrib.get("s")),
    }


def _column_dimension(elem: ET.Element) -> dict[str, Any]:
    return {
        "min_column": _int_or_none(elem.attrib.get("min")),
        "max_column": _int_or_none(elem.attrib.get("max")),
        "width": _float_or_none(elem.attrib.get("width")),
        "custom_width": elem.attrib.get("customWidth") == "1",
        "hidden": elem.attrib.get("hidden") == "1",
        "style_id": _int_or_none(elem.attrib.get("style")),
    }


def _sheet_summary(
    merge_ranges: list[dict[str, Any]],
    row_dimensions: list[dict[str, Any]],
    column_dimensions: list[dict[str, Any]],
    sampled_style_cells: list[dict[str, Any]],
    style_boundaries: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "merge_range_count": len(merge_ranges),
        "sampled_row_dimension_count": len(row_dimensions),
        "column_dimension_count": len(column_dimensions),
        "sampled_style_cell_count": len(sampled_style_cells),
        "style_boundary_count": len(style_boundaries),
        "hidden_row_count": sum(1 for row in row_dimensions if row["hidden"]),
        "hidden_column_dimension_count": sum(1 for col in column_dimensions if col["hidden"]),
    }


def _summary(sheets: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "sheet_count": len(sheets),
        "scanned_sheet_count": sum(1 for sheet in sheets if sheet["detail_status"] == "scanned"),
        "skipped_large_xml_sheet_count": sum(
            1 for sheet in sheets if sheet["detail_status"] == "skipped_large_xml"
        ),
        "merge_range_count": sum(sheet["summary"]["merge_range_count"] for sheet in sheets),
        "sampled_style_cell_count": sum(
            sheet["summary"]["sampled_style_cell_count"] for sheet in sheets
        ),
        "style_boundary_count": sum(sheet["summary"]["style_boundary_count"] for sheet in sheets),
        "hidden_row_count": sum(sheet["summary"]["hidden_row_count"] for sheet in sheets),
        "hidden_column_dimension_count": sum(
            sheet["summary"]["hidden_column_dimension_count"] for sheet in sheets
        ),
    }


def _parser_observations(sheets: list[dict[str, Any]]) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": "Structural style profile is deterministic evidence for later 2D region boundary gates; it is not a final split decision.",
        }
    ]
    skipped = [sheet["name"] for sheet in sheets if sheet["detail_status"] == "skipped_large_xml"]
    if skipped:
        observations.append(
            {
                "level": "warning",
                "message": f"Skipped large worksheet XML for structural style profiling: {', '.join(skipped)}.",
            }
        )
    return observations


def _row_in_windows(row: int, windows: list[dict[str, int]]) -> bool:
    return any(window["start_row"] <= row <= window["end_row"] for window in windows)


def _range_bounds(value: str | None) -> dict[str, int] | None:
    if not value:
        return None
    try:
        min_col, min_row, max_col, max_row = range_boundaries(value)
    except ValueError:
        return None
    return {
        "min_row": min_row,
        "min_column": min_col,
        "max_row": max_row,
        "max_column": max_col,
    }


def _cell_position(value: str | None) -> tuple[int, int] | None:
    bounds = _range_bounds(value)
    if bounds is None:
        return None
    return bounds["min_row"], bounds["min_column"]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _float_or_none(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract deterministic merged-range and style-boundary evidence from workbook XML."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("readonly_sample", type=Path)
    parser.add_argument("--sheet", action="append", dest="sheets")
    parser.add_argument("--max-sheet-xml-bytes", type=int, default=50_000_000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    package = build_structural_style_profile(
        args.manifest,
        args.readonly_sample,
        sheets=args.sheets,
        max_sheet_xml_bytes=args.max_sheet_xml_bytes,
    )
    text = json.dumps(package, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
