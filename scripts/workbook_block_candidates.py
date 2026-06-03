from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl.utils import get_column_letter, range_boundaries

SCHEMA_VERSION = "0.1"

FORMULA_REF_RE = re.compile(
    r"(?:(?P<target>'(?:[^']|'')+'|\[[^\]]+\][^!]+|[A-Za-z_가-힣][A-Za-z0-9_가-힣_.]*)!)?"
    r"(?P<start>\$?[A-Z]{1,3}\$?\d+)"
    r"(?::(?P<end>\$?[A-Z]{1,3}\$?\d+))?"
)
CELL_RE = re.compile(r"^([A-Z]{1,3})([0-9]+)$")


def build_block_candidates(
    manifest_path: Path,
    readonly_sample_path: Path,
    *,
    formula_patterns_path: Path | None = None,
    structural_style_profile_path: Path | None = None,
    sheets: list[str] | None = None,
    max_blank_gap: int = 1,
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    readonly_sample_path = readonly_sample_path.expanduser().resolve()
    formula_patterns_path = formula_patterns_path.expanduser().resolve() if formula_patterns_path else None
    structural_style_profile_path = (
        structural_style_profile_path.expanduser().resolve()
        if structural_style_profile_path
        else None
    )
    manifest = _read_json(manifest_path)
    sample = _read_json(readonly_sample_path)
    formula_patterns = _read_json(formula_patterns_path) if formula_patterns_path else None
    structural_style_profile = (
        _read_json(structural_style_profile_path)
        if structural_style_profile_path
        else None
    )

    manifest_sheets = {
        sheet["name"]: sheet for sheet in manifest["workbook"]["sheets"]
    }
    sample_sheets = {sheet["name"]: sheet for sheet in sample["sheets"]}
    pattern_sheets = {
        sheet["name"]: sheet
        for sheet in (formula_patterns or {}).get("sheets", [])
    }
    structural_style_sheets = {
        sheet["name"]: sheet
        for sheet in (structural_style_profile or {}).get("sheets", [])
    }
    selected_sheets = sheets or sorted(set(manifest_sheets) & set(sample_sheets))

    sheet_packages = []
    for sheet_name in selected_sheets:
        if sheet_name not in manifest_sheets:
            raise ValueError(f"missing manifest sheet: {sheet_name}")
        if sheet_name not in sample_sheets:
            raise ValueError(f"missing readonly sample sheet: {sheet_name}")
        sheet_packages.append(
            _sheet_candidates(
                manifest_sheets[sheet_name],
                sample_sheets[sheet_name],
                formula_sheet_profile=pattern_sheets.get(sheet_name),
                structural_style_sheet=structural_style_sheets.get(sheet_name),
                max_blank_gap=max_blank_gap,
            )
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "manifest": str(manifest_path),
            "readonly_sample": str(readonly_sample_path),
            "formula_patterns": str(formula_patterns_path) if formula_patterns_path else None,
            "structural_style_profile": (
                str(structural_style_profile_path)
                if structural_style_profile_path
                else None
            ),
        },
        "sheets": sheet_packages,
        "summary": _summary(sheet_packages),
    }


def _sheet_candidates(
    manifest_sheet: dict[str, Any],
    sample_sheet: dict[str, Any],
    *,
    formula_sheet_profile: dict[str, Any] | None,
    structural_style_sheet: dict[str, Any] | None,
    max_blank_gap: int,
) -> dict[str, Any]:
    image_blocks = [_image_block(manifest_sheet["name"], obj) for obj in manifest_sheet["drawing_objects"]]
    pivot_blocks = [
        _pivot_block(manifest_sheet["name"], pivot)
        for pivot in manifest_sheet.get("pivot_tables", [])
        if pivot.get("location", {}).get("bounds")
    ]
    row_groups = _row_band_groups(sample_sheet, max_blank_gap=max_blank_gap)
    row_bands = [
        _row_band(manifest_sheet["name"], index=index + 1, rows=rows)
        for index, rows in enumerate(row_groups)
    ]
    _mark_pivot_value_samples(row_bands, pivot_blocks)
    cell_regions, cell_region_split_candidates = _cell_regions_from_row_groups(
        manifest_sheet["name"],
        row_bands,
        row_groups,
        structural_style_sheet=structural_style_sheet,
    )
    boundary_gate_results = _boundary_gate_results(
        manifest_sheet["name"],
        cell_regions,
        cell_region_split_candidates,
        structural_style_sheet,
    )
    blocks = image_blocks + pivot_blocks + row_bands
    relations = _relations(image_blocks, pivot_blocks, row_bands, blocks, manifest_sheet["name"])
    relation_groups = _relation_groups(
        row_bands,
        blocks,
        relations,
        manifest_sheet["name"],
        formula_sheet_profile,
    )
    return {
        "name": manifest_sheet["name"],
        "dimension": manifest_sheet["dimension"],
        "dimension_bounds": manifest_sheet["dimension_bounds"],
        "blocks": blocks,
        "cell_regions": cell_regions,
        "cell_region_split_candidates": cell_region_split_candidates,
        "boundary_gate_results": boundary_gate_results,
        "relations": relations,
        "relation_groups": relation_groups,
        "parser_observations": _sheet_observations(
            image_blocks,
            pivot_blocks,
            row_bands,
            cell_region_split_candidates,
        ),
    }


def _image_block(sheet_name: str, obj: dict[str, Any]) -> dict[str, Any]:
    start = obj["from"]
    end = obj["to"]
    return {
        "id": f"{_slug(sheet_name)}_image_{_slug(obj['id'])}",
        "type": "image",
        "subtype": "image_anchor",
        "label": obj["name"],
        "source": {
            "sheet": sheet_name,
            "kind": "drawing_object",
            "drawing_entry": obj["drawing_entry"],
            "media_entry": obj["media_entry"],
        },
        "bounds": {
            "start_row": start["row"],
            "end_row": end["row"],
            "start_column": start["column"],
            "end_column": end["column"],
            "start_cell": start["cell"],
            "end_cell": end["cell"],
        },
        "metrics": {
            "row_span": end["row"] - start["row"] + 1,
            "column_span": end["column"] - start["column"] + 1,
        },
        "preview": [obj["name"] or obj["media_entry"]],
        "evidence": ["manifest.drawing_objects"],
        "confidence": 1.0,
    }


def _pivot_block(sheet_name: str, pivot: dict[str, Any]) -> dict[str, Any]:
    bounds = pivot["location"]["bounds"]
    cache = pivot.get("cache") or {}
    cache_source = cache.get("source") or {}
    cache_source_sheet = cache_source.get("sheet")
    cache_source_range = cache_source.get("range")
    label = pivot.get("name") or pivot["id"]
    return {
        "id": f"{_slug(sheet_name)}_pivot_{_slug(label)}",
        "type": "pivot_table",
        "subtype": "pivot_table",
        "label": label,
        "source": {
            "sheet": sheet_name,
            "kind": "pivot_table_definition",
            "pivot_table_entry": pivot["entry"],
            "cache_id": pivot["cache_id"],
            "cache_source_sheet": cache_source_sheet,
            "cache_source_range": cache_source_range,
        },
        "bounds": {
            "start_row": bounds["min_row"],
            "end_row": bounds["max_row"],
            "start_column": bounds["min_column"],
            "end_column": bounds["max_column"],
            "start_cell": _cell(bounds["min_row"], bounds["min_column"]),
            "end_cell": _cell(bounds["max_row"], bounds["max_column"]),
        },
        "metrics": {
            "row_span": bounds["max_row"] - bounds["min_row"] + 1,
            "column_span": bounds["max_column"] - bounds["min_column"] + 1,
            "pivot_field_count": pivot["field_counts"]["pivot_fields"],
            "row_field_count": pivot["field_counts"]["row_fields"],
            "column_field_count": pivot["field_counts"]["column_fields"],
            "page_field_count": pivot["field_counts"]["page_fields"],
            "data_field_count": pivot["field_counts"]["data_fields"],
            "cache_record_count": cache.get("record_count"),
            "cache_field_count": cache.get("cache_field_count"),
        },
        "preview": _pivot_preview(label, pivot, cache_source),
        "evidence": ["manifest.pivot_tables", "manifest.pivot_caches"],
        "confidence": 1.0,
    }


def _pivot_preview(
    label: str,
    pivot: dict[str, Any],
    cache_source: dict[str, Any],
) -> list[str]:
    preview = [
        f"Pivot table: {label}",
        f"Location: {pivot['location']['range']}",
    ]
    source_sheet = cache_source.get("sheet")
    source_range = cache_source.get("range")
    if source_sheet or source_range:
        preview.append(f"Cache source: {source_sheet}!{source_range}")
    field_counts = pivot["field_counts"]
    preview.append(
        "Fields: "
        f"pivot {field_counts['pivot_fields']}, "
        f"row {field_counts['row_fields']}, "
        f"column {field_counts['column_fields']}, "
        f"page {field_counts['page_fields']}, "
        f"data {field_counts['data_fields']}"
    )
    return preview


def _row_bands(
    sheet_name: str,
    sample_sheet: dict[str, Any],
    *,
    max_blank_gap: int,
) -> list[dict[str, Any]]:
    return [
        _row_band(sheet_name, index=index + 1, rows=rows)
        for index, rows in enumerate(
            _row_band_groups(sample_sheet, max_blank_gap=max_blank_gap)
        )
    ]


def _row_band_groups(
    sample_sheet: dict[str, Any],
    *,
    max_blank_gap: int,
) -> list[list[dict[str, Any]]]:
    rows_by_number: dict[int, dict[str, Any]] = {}
    for window in sample_sheet["windows"]:
        for row in window["rows"]:
            existing = rows_by_number.get(row["row"])
            if existing is None:
                rows_by_number[row["row"]] = row
                continue
            rows_by_number[row["row"]] = _merge_rows(existing, row)

    grouped_rows: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    blank_gap = 0
    for row_number in sorted(rows_by_number):
        row = rows_by_number[row_number]
        if row["non_empty_count"] == 0:
            if current:
                blank_gap += 1
                if blank_gap > max_blank_gap:
                    grouped_rows.append(current)
                    current = []
                    blank_gap = 0
            continue
        if current and blank_gap:
            blank_gap = 0
        current.append(row)
    if current:
        grouped_rows.append(current)

    return grouped_rows


def _merge_rows(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    cells_by_ref = {cell["cell"]: cell for cell in left["cells"]}
    cells_by_ref.update({cell["cell"]: cell for cell in right["cells"]})
    cells = sorted(cells_by_ref.values(), key=lambda cell: cell["column"])
    non_empty_count = len(cells)
    formula_count = sum(1 for cell in cells if cell["value_type"] == "formula")
    columns = [cell["column"] for cell in cells]
    return {
        "row": left["row"],
        "non_empty_count": non_empty_count,
        "formula_count": formula_count,
        "first_non_empty_column": min(columns) if columns else None,
        "last_non_empty_column": max(columns) if columns else None,
        "cells": cells,
    }


def _row_band(sheet_name: str, *, index: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    cells = [cell for row in rows for cell in row["cells"]]
    columns = [cell["column"] for cell in cells]
    row_numbers = [row["row"] for row in rows]
    metrics = _cell_metrics(cells)
    formula_references = _formula_references(sheet_name, cells)
    metrics["formula_reference_count"] = len(formula_references)
    subtype = _classify_row_band(rows, metrics)
    return {
        "id": f"{_slug(sheet_name)}_row_band_{index}",
        "type": "row_band",
        "subtype": subtype,
        "label": _label(rows),
        "source": {
            "sheet": sheet_name,
            "kind": "readonly_sample_rows",
        },
        "bounds": {
            "start_row": min(row_numbers),
            "end_row": max(row_numbers),
            "start_column": min(columns) if columns else None,
            "end_column": max(columns) if columns else None,
            "start_cell": None,
            "end_cell": None,
        },
        "metrics": metrics,
        "preview": _preview_rows(rows),
        "formula_references": formula_references,
        "evidence": ["readonly_sample.windows"],
        "confidence": _subtype_confidence(subtype),
    }


def _cell_regions_from_row_groups(
    sheet_name: str,
    row_bands: list[dict[str, Any]],
    row_groups: list[list[dict[str, Any]]],
    *,
    structural_style_sheet: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    regions: list[dict[str, Any]] = []
    split_candidates: list[dict[str, Any]] = []
    for band, rows in zip(row_bands, row_groups, strict=True):
        segments, split_signals = _column_segments_for_rows(rows)
        style_signals = _style_split_signals_for_rows(rows, structural_style_sheet)
        split_signals.extend(style_signals)
        parent_regions: list[dict[str, Any]] = []
        for segment_index, (start_column, end_column) in enumerate(segments, start=1):
            segment_rows = _rows_for_column_segment(
                rows,
                start_column=start_column,
                end_column=end_column,
            )
            region = _cell_region(
                sheet_name,
                parent=band,
                index=len(regions) + 1,
                segment_index=segment_index,
                rows=segment_rows,
                start_column=start_column,
                end_column=end_column,
                split_signals=[
                    signal
                    for signal in split_signals
                    if (
                        signal["left_end_column"] == end_column
                        or signal["right_start_column"] == start_column
                        or (
                            start_column
                            <= signal["left_end_column"]
                            and signal["right_start_column"]
                            <= end_column
                        )
                    )
                ],
            )
            if region is None:
                continue
            regions.append(region)
            parent_regions.append(region)
        split_candidates.extend(
            _cell_region_split_candidates(sheet_name, band, parent_regions, split_signals)
        )
    return regions, split_candidates


def _style_split_signals_for_rows(
    rows: list[dict[str, Any]],
    structural_style_sheet: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not structural_style_sheet:
        return []
    row_numbers = [row["row"] for row in rows]
    if not row_numbers:
        return []
    row_min = min(row_numbers)
    row_max = max(row_numbers)
    signals = []
    for boundary in structural_style_sheet.get("style_boundaries", []):
        sample_rows = boundary.get("sample_rows", [])
        if not any(row_min <= row <= row_max for row in sample_rows):
            continue
        if boundary.get("row_count", 0) < 2:
            continue
        signals.append(
            {
                "type": "style_discontinuity_boundary",
                "left_end_column": boundary["left_end_column"],
                "right_start_column": boundary["right_start_column"],
                "gap_column_count": 0,
                "row_count": boundary.get("row_count", 0),
                "sample_rows": boundary.get("sample_rows", []),
                "confidence": boundary.get("confidence", 0.48),
                "reason": boundary.get(
                    "reason",
                    "Structural style profile found a repeated visual style discontinuity.",
                ),
            }
        )
    return signals


def _column_segments_for_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[tuple[int, int]], list[dict[str, Any]]]:
    occupied_columns = sorted(
        {cell["column"] for row in rows for cell in row["cells"]}
    )
    if not occupied_columns:
        return [], []

    clusters: list[tuple[int, int]] = []
    cluster_start = occupied_columns[0]
    previous = occupied_columns[0]
    split_signals: list[dict[str, Any]] = []
    for column in occupied_columns[1:]:
        if column == previous + 1:
            previous = column
            continue
        clusters.append((cluster_start, previous))
        split_signals.append(
            {
                "type": "blank_column_boundary",
                "left_end_column": previous,
                "right_start_column": column,
                "gap_column_count": column - previous - 1,
                "confidence": 0.84,
                "reason": "A blank column gap separates occupied cell clusters inside the same row-oriented seed.",
            }
        )
        cluster_start = column
        previous = column
    clusters.append((cluster_start, previous))

    for signal in _repeated_header_split_signals(rows):
        if signal not in split_signals:
            split_signals.append(signal)

    segments: list[tuple[int, int]] = []
    for start_column, end_column in clusters:
        boundaries = sorted(
            {
                signal["left_end_column"]
                for signal in split_signals
                if signal["type"] == "repeated_header_touching_boundary"
                and start_column <= signal["left_end_column"] < end_column
            }
        )
        segment_start = start_column
        for boundary in boundaries:
            segments.append((segment_start, boundary))
            segment_start = boundary + 1
        segments.append((segment_start, end_column))
    return segments, split_signals


def _repeated_header_split_signals(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str]] = set()
    for row in rows[:10]:
        cells = [
            cell
            for cell in sorted(row["cells"], key=lambda item: item["column"])
            if cell.get("value_preview") is not None
        ]
        if len(cells) < 4:
            continue
        string_cells = [cell for cell in cells if cell.get("value_type") == "string"]
        if len(string_cells) / max(len(cells), 1) < 0.8:
            continue
        labels = [_normalized_header_label(cell["value_preview"]) for cell in cells]
        if any(not label for label in labels):
            continue
        for boundary_index in range(2, len(labels) - 1):
            max_length = min(boundary_index, len(labels) - boundary_index, 4)
            for length in range(max_length, 1, -1):
                left = labels[boundary_index - length : boundary_index]
                right = labels[boundary_index : boundary_index + length]
                if left != right:
                    continue
                left_end_column = cells[boundary_index - 1]["column"]
                right_start_column = cells[boundary_index]["column"]
                if right_start_column != left_end_column + 1:
                    continue
                key = (left_end_column, right_start_column, "repeated_header_touching_boundary")
                if key in seen:
                    continue
                seen.add(key)
                signals.append(
                    {
                        "type": "repeated_header_touching_boundary",
                        "left_end_column": left_end_column,
                        "right_start_column": right_start_column,
                        "gap_column_count": 0,
                        "confidence": 0.7,
                        "reason": "A repeated header sequence touches another header sequence, so adjacent columns may contain separate tables.",
                    }
                )
                break
    return signals


def _normalized_header_label(value: Any) -> str:
    return re.sub(r"\s+", "", str(value).strip().lower())


def _rows_for_column_segment(
    rows: list[dict[str, Any]],
    *,
    start_column: int,
    end_column: int,
) -> list[dict[str, Any]]:
    segment_rows = []
    for row in rows:
        cells = [
            cell
            for cell in row["cells"]
            if start_column <= cell["column"] <= end_column
        ]
        if not cells:
            continue
        segment_rows.append(
            {
                **row,
                "non_empty_count": len(cells),
                "formula_count": sum(
                    1 for cell in cells if cell.get("value_type") == "formula"
                ),
                "first_non_empty_column": min(cell["column"] for cell in cells),
                "last_non_empty_column": max(cell["column"] for cell in cells),
                "cells": cells,
            }
        )
    return segment_rows


def _cell_region(
    sheet_name: str,
    *,
    parent: dict[str, Any],
    index: int,
    segment_index: int,
    rows: list[dict[str, Any]],
    start_column: int,
    end_column: int,
    split_signals: list[dict[str, Any]],
) -> dict[str, Any] | None:
    cells = [cell for row in rows for cell in row["cells"]]
    if not cells:
        return None
    row_numbers = [row["row"] for row in rows]
    metrics = _cell_metrics(cells)
    metrics.update(
        {
            "row_span": max(row_numbers) - min(row_numbers) + 1,
            "column_span": end_column - start_column + 1,
            "density": round(
                len(cells)
                / max((max(row_numbers) - min(row_numbers) + 1) * (end_column - start_column + 1), 1),
                4,
            ),
            "parent_row_span": parent["metrics"].get("row_count"),
            "parent_column_span": (
                parent["bounds"]["end_column"] - parent["bounds"]["start_column"] + 1
                if parent["bounds"].get("start_column") is not None
                and parent["bounds"].get("end_column") is not None
                else None
            ),
        }
    )
    subtype = _classify_cell_region(parent, rows, metrics)
    return {
        "id": f"{_slug(sheet_name)}_cell_region_{index}",
        "type": "cell_region",
        "subtype": subtype,
        "parent_seed_block_id": parent["id"],
        "label": _label(rows),
        "source": {
            "sheet": sheet_name,
            "kind": "derived_from_row_oriented_seed",
            "parent_seed_block_id": parent["id"],
            "segment_index": segment_index,
        },
        "bounds": {
            "start_row": min(row_numbers),
            "end_row": max(row_numbers),
            "start_column": start_column,
            "end_column": end_column,
            "start_cell": _cell(min(row_numbers), start_column),
            "end_cell": _cell(max(row_numbers), end_column),
        },
        "metrics": metrics,
        "split_signals": split_signals,
        "preview": _preview_rows(rows),
        "evidence": [
            "readonly_sample.windows",
            "row_oriented_seed",
            "column_segmentation",
        ],
        "confidence": _cell_region_confidence(parent, split_signals),
    }


def _classify_cell_region(
    parent: dict[str, Any],
    rows: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> str:
    if parent["subtype"] == "pivot_table_value_sample":
        return "pivot_table_value_region"
    if parent["subtype"] == "formula_summary_candidate":
        return "formula_summary_region"
    if parent["subtype"] == "text_or_label_candidate":
        return "text_or_label_region"
    first = next((row for row in rows if row["non_empty_count"] > 0), None)
    if first:
        first_types = {cell["value_type"] for cell in first["cells"]}
        if (
            first["non_empty_count"] >= 2
            and first_types <= {"string"}
            and metrics["row_count"] >= 2
            and (
                metrics["number_cell_count"] > 0
                or metrics["formula_cell_count"] > 0
            )
        ):
            return "table_region_candidate"
    return "mixed_cell_region"


def _cell_region_confidence(
    parent: dict[str, Any],
    split_signals: list[dict[str, Any]],
) -> float:
    confidence = min(parent["confidence"] + 0.04, 0.82)
    if any(signal["type"] == "blank_column_boundary" for signal in split_signals):
        confidence = max(confidence, 0.78)
    if any(signal["type"] == "repeated_header_touching_boundary" for signal in split_signals):
        confidence = max(confidence, 0.72)
    return round(confidence, 2)


def _cell_region_split_candidates(
    sheet_name: str,
    parent: dict[str, Any],
    regions: list[dict[str, Any]],
    split_signals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates = []
    regions_by_start = {region["bounds"]["start_column"]: region for region in regions}
    regions_by_end = {region["bounds"]["end_column"]: region for region in regions}
    for signal in split_signals:
        left = regions_by_end.get(signal["left_end_column"])
        right = regions_by_start.get(signal["right_start_column"])
        within = _region_containing_boundary(regions, signal)
        if left is None and right is None and within is None:
            continue
        candidates.append(
            {
                "id": (
                    f"split_{_slug(parent['id'])}_"
                    f"c{signal['left_end_column']}_c{signal['right_start_column']}"
                ),
                "type": signal["type"],
                "sheet": sheet_name,
                "parent_seed_block_id": parent["id"],
                "from_region_id": left["id"] if left else None,
                "to_region_id": right["id"] if right else None,
                "boundary_within_region_id": within["id"] if within else None,
                "boundary_after_column": signal["left_end_column"],
                "boundary_before_column": signal["right_start_column"],
                "metrics": {
                    "gap_column_count": signal["gap_column_count"],
                    "row_count": signal.get("row_count"),
                    "sample_row_count": len(signal.get("sample_rows", [])),
                },
                "reason": signal["reason"],
                "evidence": ["readonly_sample.windows", "column_segmentation"],
                "confidence": signal["confidence"],
            }
        )
    return candidates


def _region_containing_boundary(
    regions: list[dict[str, Any]],
    signal: dict[str, Any],
) -> dict[str, Any] | None:
    for region in regions:
        bounds = region["bounds"]
        if (
            bounds["start_column"]
            <= signal["left_end_column"]
            and signal["right_start_column"]
            <= bounds["end_column"]
        ):
            return region
    return None


def _boundary_gate_results(
    sheet_name: str,
    cell_regions: list[dict[str, Any]],
    split_candidates: list[dict[str, Any]],
    structural_style_sheet: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    results = [
        _split_candidate_gate_result(sheet_name, candidate)
        for candidate in split_candidates
    ]
    results.extend(
        _merged_title_gate_results(sheet_name, cell_regions, structural_style_sheet)
    )
    return sorted(results, key=lambda item: (-item["score"], item["id"]))


def _split_candidate_gate_result(
    sheet_name: str,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    candidate_type = candidate["type"]
    metrics = candidate.get("metrics", {})
    evidence = [candidate_type]
    if candidate.get("from_region_id") and candidate.get("to_region_id"):
        evidence.append("materialized_region_boundary")
    if candidate.get("boundary_within_region_id"):
        evidence.append("within_region_boundary_signal")

    if candidate_type == "blank_column_boundary":
        score = 0.86
        status = "strong_candidate"
        decision = "accept_as_split_candidate"
        rationale = "Blank columns are strong deterministic evidence that one row-oriented seed may contain separate 2D regions."
    elif candidate_type == "repeated_header_touching_boundary":
        score = 0.76
        status = "review_candidate"
        decision = "requires_human_or_visual_review"
        rationale = "Repeated touching headers suggest adjacent tables, but the boundary should be checked against visual and formula evidence."
    else:
        row_count = metrics.get("row_count") or 0
        score = 0.42 + min(row_count, 10) * 0.02
        if candidate.get("from_region_id") and candidate.get("to_region_id"):
            score += 0.08
        score = min(score, 0.68)
        status = "review_candidate" if score >= 0.6 else "weak_signal"
        decision = "do_not_auto_split"
        rationale = "Style discontinuity is useful high-recall evidence, but it is too noisy to accept without corroborating visual, formula, or header evidence."

    return {
        "id": f"gate_{candidate['id']}",
        "type": "split_candidate_gate",
        "sheet": sheet_name,
        "candidate_id": candidate["id"],
        "candidate_type": candidate_type,
        "related_region_ids": [
            value
            for value in [
                candidate.get("from_region_id"),
                candidate.get("to_region_id"),
                candidate.get("boundary_within_region_id"),
            ]
            if value
        ],
        "score": round(score, 4),
        "status": status,
        "decision": decision,
        "evidence": evidence,
        "rationale": rationale,
    }


def _merged_title_gate_results(
    sheet_name: str,
    cell_regions: list[dict[str, Any]],
    structural_style_sheet: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not structural_style_sheet:
        return []
    results = []
    for merge in structural_style_sheet.get("merge_ranges", []):
        bounds = merge.get("bounds")
        if not bounds:
            continue
        for region in cell_regions:
            relation = _merged_range_region_relation(bounds, region["bounds"])
            if relation is None:
                continue
            score = 0.72 if relation == "title_above_region" else 0.62
            results.append(
                {
                    "id": f"gate_merged_{_slug(sheet_name)}_{_slug(merge['range'])}_{region['id']}",
                    "type": "merged_range_title_gate",
                    "sheet": sheet_name,
                    "candidate_id": None,
                    "candidate_type": "merged_range_title_boundary",
                    "related_region_ids": [region["id"]],
                    "score": score,
                    "status": "review_candidate",
                    "decision": "use_as_title_or_section_boundary_evidence",
                    "evidence": ["merged_range", relation],
                    "rationale": "Merged ranges often mark titles, section headers, or grouped table headers and should be cross-checked before accepting nearby boundaries.",
                }
            )
    return results


def _merged_range_region_relation(
    merge_bounds: dict[str, int],
    region_bounds: dict[str, Any],
) -> str | None:
    merge_start_col = merge_bounds["min_column"]
    merge_end_col = merge_bounds["max_column"]
    region_start_col = region_bounds["start_column"]
    region_end_col = region_bounds["end_column"]
    if region_start_col is None or region_end_col is None:
        return None
    column_overlap = _overlap(
        merge_start_col,
        merge_end_col,
        region_start_col,
        region_end_col,
    )
    if column_overlap == 0:
        return None
    region_col_span = region_end_col - region_start_col + 1
    overlap_ratio = column_overlap / max(region_col_span, 1)
    if merge_bounds["max_row"] < region_bounds["start_row"]:
        row_gap = region_bounds["start_row"] - merge_bounds["max_row"]
        if row_gap <= 2 and overlap_ratio >= 0.35:
            return "title_above_region"
    if (
        region_bounds["start_row"]
        <= merge_bounds["min_row"]
        <= region_bounds["end_row"]
        and overlap_ratio >= 0.35
    ):
        return "merged_header_inside_region"
    return None


def _cell_metrics(cells: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "row_count": len({cell["row"] for cell in cells}),
        "non_empty_cell_count": len(cells),
        "formula_cell_count": 0,
        "string_cell_count": 0,
        "number_cell_count": 0,
        "datetime_cell_count": 0,
    }
    for cell in cells:
        value_type = cell["value_type"]
        if value_type == "formula":
            counts["formula_cell_count"] += 1
        elif value_type == "string":
            counts["string_cell_count"] += 1
        elif value_type == "number":
            counts["number_cell_count"] += 1
        elif value_type == "datetime":
            counts["datetime_cell_count"] += 1
    return counts


def _classify_row_band(rows: list[dict[str, Any]], metrics: dict[str, Any]) -> str:
    first = next((row for row in rows if row["non_empty_count"] > 0), None)
    if first is None:
        return "empty"
    first_types = {cell["value_type"] for cell in first["cells"]}
    has_header_shape = (
        first["non_empty_count"] >= 2
        and first_types <= {"string"}
        and metrics["row_count"] >= 2
    )
    if has_header_shape and (
        metrics["number_cell_count"] > 0 or metrics["formula_cell_count"] > 0
    ):
        return "table_candidate"
    if metrics["formula_cell_count"] > 0 and metrics["row_count"] <= 5:
        return "formula_summary_candidate"
    if metrics["row_count"] <= 2 and metrics["non_empty_cell_count"] <= 4:
        return "text_or_label_candidate"
    return "mixed_row_band"


def _subtype_confidence(subtype: str) -> float:
    if subtype == "table_candidate":
        return 0.72
    if subtype == "formula_summary_candidate":
        return 0.68
    if subtype == "text_or_label_candidate":
        return 0.62
    return 0.5


def _label(rows: list[dict[str, Any]]) -> str | None:
    for row in rows:
        for cell in row["cells"]:
            if cell["value_preview"]:
                return str(cell["value_preview"])
    return None


def _preview_rows(rows: list[dict[str, Any]], *, limit: int = 5) -> list[str]:
    preview: list[str] = []
    for row in rows[:limit]:
        values = [
            str(cell["value_preview"])
            for cell in row["cells"][:8]
            if cell["value_preview"] is not None
        ]
        preview.append(f"R{row['row']}: " + " | ".join(values))
    return preview


def _formula_references(sheet_name: str, cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    references: dict[tuple[str, str | None, str, str, str], dict[str, Any]] = {}
    for cell in cells:
        formula = cell.get("formula")
        if not formula:
            continue
        formula_text = str(formula)
        for reference in _getpivotdata_references(sheet_name, cell, formula_text):
            key = (
                reference["kind"],
                reference["target_workbook"],
                reference["target_sheet"],
                reference["target_range"],
                reference["formula_cell"],
            )
            references[key] = reference

        formula_without_strings = _mask_function_calls(
            _mask_string_literals(formula_text),
            "GETPIVOTDATA",
        )
        for match in FORMULA_REF_RE.finditer(formula_without_strings):
            target = _formula_target(match.group("target"), default_sheet=sheet_name)
            start_ref = _clean_cell_ref(match.group("start"))
            end_ref = _clean_cell_ref(match.group("end") or match.group("start"))
            ref = f"{start_ref}:{end_ref}" if end_ref != start_ref else start_ref
            bounds = _range_bounds(ref)
            if bounds is None:
                continue
            kind = (
                "external_workbook_range"
                if target["workbook"] is not None
                else "workbook_range"
            )
            key = (kind, target["workbook"], target["sheet"], ref, cell["cell"])
            references[key] = {
                "kind": kind,
                "formula_cell": cell["cell"],
                "target_workbook": target["workbook"],
                "target_sheet": target["sheet"],
                "target_range": ref,
                "target_bounds": bounds,
                "formula_function": None,
                "formula_preview": formula_text[:160],
            }
    return list(references.values())


def _getpivotdata_references(
    sheet_name: str,
    cell: dict[str, Any],
    formula: str,
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for call in _function_calls(formula, "GETPIVOTDATA"):
        args = _split_formula_args(call)
        if len(args) < 2:
            continue
        pivot_ref = args[1].strip()
        match = FORMULA_REF_RE.fullmatch(pivot_ref)
        if match is None:
            continue
        target = _formula_target(match.group("target"), default_sheet=sheet_name)
        start_ref = _clean_cell_ref(match.group("start"))
        end_ref = _clean_cell_ref(match.group("end") or match.group("start"))
        ref = f"{start_ref}:{end_ref}" if end_ref != start_ref else start_ref
        bounds = _range_bounds(ref)
        if bounds is None:
            continue
        references.append(
            {
                "kind": "pivot_function",
                "formula_cell": cell["cell"],
                "target_workbook": target["workbook"],
                "target_sheet": target["sheet"],
                "target_range": ref,
                "target_bounds": bounds,
                "formula_function": "GETPIVOTDATA",
                "formula_preview": formula[:160],
            }
        )
    return references


def _function_calls(formula: str, function_name: str) -> list[str]:
    calls: list[str] = []
    for match in re.finditer(rf"{re.escape(function_name)}\s*\(", formula, re.IGNORECASE):
        start = match.end()
        depth = 1
        in_string = False
        index = start
        while index < len(formula):
            char = formula[index]
            if char == '"':
                in_string = not in_string
            elif not in_string:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                    if depth == 0:
                        calls.append(formula[start:index])
                        break
            index += 1
    return calls


def _split_formula_args(args_text: str) -> list[str]:
    args: list[str] = []
    current: list[str] = []
    depth = 0
    in_string = False
    for char in args_text:
        if char == '"':
            in_string = not in_string
            current.append(char)
            continue
        if not in_string:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                args.append("".join(current).strip())
                current = []
                continue
        current.append(char)
    if current:
        args.append("".join(current).strip())
    return args


def _mask_string_literals(formula: str) -> str:
    result: list[str] = []
    in_string = False
    for char in formula:
        if char == '"':
            in_string = not in_string
            result.append(char)
        elif in_string:
            result.append(" ")
        else:
            result.append(char)
    return "".join(result)


def _mask_function_calls(formula: str, function_name: str) -> str:
    chars = list(formula)
    for match in re.finditer(rf"{re.escape(function_name)}\s*\(", formula, re.IGNORECASE):
        start = match.start()
        index = match.end()
        depth = 1
        while index < len(formula):
            char = formula[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    for mask_index in range(start, index + 1):
                        chars[mask_index] = " "
                    break
            index += 1
    return "".join(chars)


def _formula_target(value: str | None, *, default_sheet: str) -> dict[str, str | None]:
    if not value:
        return {"workbook": None, "sheet": default_sheet}
    target = value
    if target.startswith("'") and target.endswith("'"):
        target = target[1:-1].replace("''", "'")
    workbook = None
    bracket_start = target.rfind("[")
    bracket_end = target.find("]", bracket_start + 1)
    if bracket_start != -1 and bracket_end != -1:
        workbook = target[bracket_start + 1 : bracket_end]
        target = target[bracket_end + 1 :]
    return {"workbook": workbook, "sheet": target or default_sheet}


def _clean_cell_ref(value: str) -> str:
    return value.replace("$", "")


def _range_bounds(value: str) -> dict[str, int] | None:
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


def _mark_pivot_value_samples(
    row_bands: list[dict[str, Any]],
    pivot_blocks: list[dict[str, Any]],
) -> None:
    for band in row_bands:
        overlapping_pivots = [
            pivot
            for pivot in pivot_blocks
            if _bounds_overlap_ratio(band["bounds"], pivot["bounds"]) >= 0.35
        ]
        if not overlapping_pivots:
            continue
        band["subtype"] = "pivot_table_value_sample"
        band["metrics"]["pivot_overlap_count"] = len(overlapping_pivots)
        band["evidence"] = sorted(set([*band["evidence"], "manifest.pivot_tables"]))
        band["confidence"] = max(band["confidence"], 0.76)


def _relations(
    image_blocks: list[dict[str, Any]],
    pivot_blocks: list[dict[str, Any]],
    row_bands: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    sheet_name: str,
) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for image in image_blocks:
        for band in row_bands:
            relation = _layout_relation(image, band)
            if relation:
                relations.append(relation)
    relations.extend(_pivot_relations(pivot_blocks, row_bands))
    relations.extend(_formula_relations(row_bands, blocks, sheet_name))
    return relations


def _layout_relation(image: dict[str, Any], band: dict[str, Any]) -> dict[str, Any] | None:
    image_bounds = image["bounds"]
    band_bounds = band["bounds"]
    if band_bounds["start_column"] is None or band_bounds["end_column"] is None:
        return None

    overlap_rows = _overlap(
        image_bounds["start_row"],
        image_bounds["end_row"],
        band_bounds["start_row"],
        band_bounds["end_row"],
    )
    image_rows = image_bounds["end_row"] - image_bounds["start_row"] + 1
    band_rows = band_bounds["end_row"] - band_bounds["start_row"] + 1
    overlap_ratio = overlap_rows / max(min(image_rows, band_rows), 1)

    relation_type = None
    reason = None
    overlap_columns = _overlap(
        image_bounds["start_column"],
        image_bounds["end_column"],
        band_bounds["start_column"],
        band_bounds["end_column"],
    )
    image_columns = image_bounds["end_column"] - image_bounds["start_column"] + 1
    band_columns = band_bounds["end_column"] - band_bounds["start_column"] + 1
    column_overlap_ratio = overlap_columns / max(min(image_columns, band_columns), 1)

    if overlap_rows > 0 and overlap_columns > 0 and overlap_ratio >= 0.25:
        relation_type = "overlaps_anchor"
        reason = "Row band overlaps the image anchor area; the image may be covering or illustrating that grid region."
    elif overlap_rows > 0 and band_bounds["end_column"] < image_bounds["start_column"]:
        relation_type = "adjacent_left_of"
        reason = "Row band vertically overlaps the image and is positioned to its left."
    elif overlap_rows > 0 and band_bounds["start_column"] > image_bounds["end_column"]:
        relation_type = "adjacent_right_of"
        reason = "Row band vertically overlaps the image and is positioned to its right."
    elif band_bounds["end_row"] < image_bounds["start_row"]:
        row_gap = image_bounds["start_row"] - band_bounds["end_row"]
        if row_gap <= 3:
            relation_type = "above"
            reason = "Row band is immediately above the image."
    elif band_bounds["start_row"] > image_bounds["end_row"]:
        row_gap = band_bounds["start_row"] - image_bounds["end_row"]
        if row_gap <= 3:
            relation_type = "below"
            reason = "Row band is immediately below the image."

    if relation_type is None:
        return None

    confidence = 0.55
    if overlap_ratio >= 0.5:
        confidence = 0.78
    elif overlap_ratio > 0:
        confidence = 0.68

    return {
        "id": f"rel_{image['id']}__{band['id']}",
        "type": relation_type,
        "from": band["id"],
        "to": image["id"],
        "metrics": {
            "overlap_rows": overlap_rows,
            "overlap_ratio": round(overlap_ratio, 4),
            "overlap_columns": overlap_columns,
            "column_overlap_ratio": round(column_overlap_ratio, 4),
        },
        "reason": reason,
        "confidence": confidence,
    }


def _pivot_relations(
    pivot_blocks: list[dict[str, Any]],
    row_bands: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for pivot in pivot_blocks:
        cache_source_sheet = pivot["source"].get("cache_source_sheet")
        cache_source_range = pivot["source"].get("cache_source_range")
        if cache_source_sheet or cache_source_range:
            relations.append(
                {
                    "id": f"rel_{pivot['id']}__pivot_cache_source",
                    "type": "derived_from_pivot_cache_source",
                    "from": pivot["id"],
                    "to": f"range:{cache_source_sheet}!{cache_source_range}",
                    "metrics": {
                        "cache_record_count": pivot["metrics"].get("cache_record_count"),
                        "cache_field_count": pivot["metrics"].get("cache_field_count"),
                    },
                    "reason": "Pivot table values are derived from its pivot cache worksheet source, not raw cells inside the displayed pivot range.",
                    "confidence": 1.0,
                }
            )
        for band in row_bands:
            overlap_ratio = _bounds_overlap_ratio(band["bounds"], pivot["bounds"])
            if overlap_ratio < 0.35:
                continue
            relations.append(
                {
                    "id": f"rel_{band['id']}__{pivot['id']}",
                    "type": "sample_of_pivot_table",
                    "from": band["id"],
                    "to": pivot["id"],
                    "metrics": {
                        "overlap_ratio": round(overlap_ratio, 4),
                        "overlap_cells": _bounds_overlap_area(band["bounds"], pivot["bounds"]),
                    },
                    "reason": "The sampled row band overlaps a pivot table definition range, so it should be treated as pivot-rendered values instead of a plain source table.",
                    "confidence": 0.88,
                }
            )
    return relations


def _formula_relations(
    row_bands: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    sheet_name: str,
) -> list[dict[str, Any]]:
    relations: dict[str, dict[str, Any]] = {}
    for source in row_bands:
        for reference in source.get("formula_references", []):
            classified = _classify_formula_reference(
                source,
                reference,
                blocks,
                sheet_name,
            )
            key = f"{source['id']}|{classified['relation_type']}|{classified['target_id']}"
            existing = relations.get(key)
            if existing is None:
                reason = _formula_relation_reason(classified["relation_type"])
                relations[key] = {
                    "id": f"rel_{_slug(source['id'])}__{_slug(classified['target_id'])}__formula",
                    "type": classified["relation_type"],
                    "from": source["id"],
                    "to": classified["target_id"],
                    "metrics": {
                        "reference_count": 1,
                        "formula_cell_count": 1,
                        "overlap_cells": classified["overlap_cells"],
                        "external_workbook": reference.get("target_workbook"),
                        "formula_function": reference.get("formula_function"),
                    },
                    "reason": reason,
                    "confidence": 0.72,
                }
                continue
            existing["metrics"]["reference_count"] += 1
            existing["metrics"]["formula_cell_count"] += 1
            existing["metrics"]["overlap_cells"] += classified["overlap_cells"]
    return list(relations.values())


def _classify_formula_reference(
    source: dict[str, Any],
    reference: dict[str, Any],
    blocks: list[dict[str, Any]],
    sheet_name: str,
) -> dict[str, Any]:
    target_sheet = reference["target_sheet"]
    target_workbook = reference.get("target_workbook")
    target_id = _formula_reference_target_id(reference)
    relation_type = "formula_references_workbook_range"
    overlap_cells = 0
    if reference["kind"] == "external_workbook_range":
        relation_type = "formula_references_external_workbook"
    elif reference["kind"] == "pivot_function":
        relation_type = "formula_references_pivot_table"
        if target_sheet == sheet_name and target_workbook is None:
            target_block = _target_block_for_reference(
                blocks,
                source["id"],
                reference,
                block_types={"pivot_table"},
            )
            if target_block is not None:
                target_id = target_block["id"]
                overlap_cells = _bounds_ref_overlap_area(
                    target_block["bounds"],
                    reference,
                )
    elif target_sheet == sheet_name and target_workbook is None:
        target_block = _target_block_for_reference(blocks, source["id"], reference)
        if target_block is not None:
            target_id = target_block["id"]
            relation_type = "formula_references"
            overlap_cells = _bounds_ref_overlap_area(target_block["bounds"], reference)
    return {
        "relation_type": relation_type,
        "target_id": target_id,
        "overlap_cells": overlap_cells,
    }


def _relation_groups(
    row_bands: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    sheet_name: str,
    formula_sheet_profile: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    relation_ids = {
        (relation["from"], relation["type"], relation["to"]): relation["id"]
        for relation in relations
    }
    profile_groups = _profile_groups_by_signature(formula_sheet_profile)
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for source in row_bands:
        for reference in source.get("formula_references", []):
            classified = _classify_formula_reference(
                source,
                reference,
                blocks,
                sheet_name,
            )
            signature = _formula_signature_for_reference(reference)
            profile = profile_groups.get(signature)
            key = (
                source["id"],
                classified["relation_type"],
                reference["kind"],
                reference.get("target_workbook"),
                reference["target_sheet"],
                reference.get("formula_function"),
                signature,
            )
            group = groups.setdefault(
                key,
                {
                    "id": f"group_{_slug(source['id'])}_{len(groups) + 1}",
                    "type": "formula_signature_group",
                    "source_block_id": source["id"],
                    "relation_type": classified["relation_type"],
                    "reference_kind": reference["kind"],
                    "target_workbook": reference.get("target_workbook"),
                    "target_sheet": reference["target_sheet"],
                    "formula_function": reference.get("formula_function"),
                    "formula_signature": signature,
                    "formula_cell_count": 0,
                    "reference_count": 0,
                    "target_range_count": 0,
                    "source_cell_samples": [],
                    "target_range_samples": [],
                    "target_bounds_union": None,
                    "pattern_profile": _relation_group_profile(profile),
                    "relation_ids": [],
                    "_formula_cells": set(),
                    "_target_ranges": set(),
                    "_relation_ids": set(),
                },
            )
            group["reference_count"] += 1
            _add_limited(group["source_cell_samples"], reference["formula_cell"])
            _add_limited(group["target_range_samples"], reference["target_range"])
            group["_formula_cells"].add(reference["formula_cell"])
            group["_target_ranges"].add(reference["target_range"])
            group["target_bounds_union"] = _union_bounds(
                group["target_bounds_union"],
                reference["target_bounds"],
            )
            relation_id = relation_ids.get(
                (
                    source["id"],
                    classified["relation_type"],
                    classified["target_id"],
                )
            )
            if relation_id:
                group["_relation_ids"].add(relation_id)

    output = []
    for group in groups.values():
        group["formula_cell_count"] = len(group.pop("_formula_cells"))
        group["target_range_count"] = len(group.pop("_target_ranges"))
        group["relation_ids"] = sorted(group.pop("_relation_ids"))[:20]
        output.append(group)
    return sorted(
        output,
        key=lambda item: (item["source_block_id"], -item["formula_cell_count"], item["formula_signature"]),
    )


def _profile_groups_by_signature(
    formula_sheet_profile: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    if not formula_sheet_profile:
        return groups
    for window in formula_sheet_profile.get("windows", []):
        structure_hint = window.get("structure_hint")
        for group in window.get("signature_groups", []):
            signature = group["signature"]
            existing = groups.get(signature)
            if existing is None:
                groups[signature] = {
                    "matched": True,
                    "structure_hint": structure_hint,
                    "formula_count": group["formula_count"],
                    "row_min": group["row_min"],
                    "row_max": group["row_max"],
                    "column_min": group["column_min"],
                    "column_max": group["column_max"],
                }
                continue
            existing["formula_count"] += group["formula_count"]
            existing["row_min"] = min(existing["row_min"], group["row_min"])
            existing["row_max"] = max(existing["row_max"], group["row_max"])
            existing["column_min"] = min(existing["column_min"], group["column_min"])
            existing["column_max"] = max(existing["column_max"], group["column_max"])
    return groups


def _relation_group_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    if not profile:
        return {
            "matched": False,
            "structure_hint": None,
            "formula_count": None,
            "row_min": None,
            "row_max": None,
            "column_min": None,
            "column_max": None,
        }
    return profile


def _formula_signature_for_reference(reference: dict[str, Any]) -> str:
    position = _cell_position(reference["formula_cell"])
    if position is None:
        return "UNKNOWN_SIGNATURE"
    row, column = position
    formula = reference.get("formula_preview") or ""
    expression = formula[1:] if formula.startswith("=") else formula
    return FORMULA_REF_RE.sub(
        lambda match: _relative_reference(match, row, column),
        expression.upper(),
    )


def _relative_reference(match: re.Match[str], row: int, column: int) -> str:
    target_prefix = f"{match.group('target')}!" if match.group("target") else ""
    start = _clean_cell_ref(match.group("start"))
    end = _clean_cell_ref(match.group("end") or match.group("start"))
    start_token = _relative_cell_token(start, row, column)
    if end == start:
        return f"{target_prefix}{start_token}"
    return f"{target_prefix}{start_token}:{_relative_cell_token(end, row, column)}"


def _relative_cell_token(cell: str, anchor_row: int, anchor_column: int) -> str:
    position = _cell_position(cell)
    if position is None:
        return cell
    target_row, target_column = position
    return f"R[{target_row - anchor_row}]C[{target_column - anchor_column}]"


def _cell_position(cell: str) -> tuple[int, int] | None:
    match = CELL_RE.match(_clean_cell_ref(cell))
    if not match:
        return None
    column_letters, row_text = match.groups()
    column = range_boundaries(f"{column_letters}{row_text}:{column_letters}{row_text}")[0]
    return int(row_text), column


def _add_limited(items: list[str], value: str, *, limit: int = 10) -> None:
    if value not in items and len(items) < limit:
        items.append(value)


def _union_bounds(
    current: dict[str, int] | None,
    bounds: dict[str, int],
) -> dict[str, int]:
    if current is None:
        return dict(bounds)
    return {
        "min_row": min(current["min_row"], bounds["min_row"]),
        "min_column": min(current["min_column"], bounds["min_column"]),
        "max_row": max(current["max_row"], bounds["max_row"]),
        "max_column": max(current["max_column"], bounds["max_column"]),
    }


def _target_block_for_reference(
    blocks: list[dict[str, Any]],
    source_id: str,
    reference: dict[str, Any],
    *,
    block_types: set[str] | None = None,
) -> dict[str, Any] | None:
    allowed_types = block_types or {"row_band", "pivot_table"}
    candidates = [
        block
        for block in blocks
        if block["id"] != source_id
        and block["type"] in allowed_types
        and _bounds_ref_overlap_area(block["bounds"], reference) > 0
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda block: _bounds_ref_overlap_area(block["bounds"], reference),
    )


def _formula_reference_target_id(reference: dict[str, Any]) -> str:
    workbook = reference.get("target_workbook")
    sheet = reference["target_sheet"]
    ref = reference["target_range"]
    if reference["kind"] == "external_workbook_range":
        return f"external_workbook:{workbook}!{sheet}!{ref}"
    if reference["kind"] == "pivot_function":
        return f"pivot_range:{sheet}!{ref}"
    return f"range:{sheet}!{ref}"


def _formula_relation_reason(relation_type: str) -> str:
    if relation_type == "formula_references_external_workbook":
        return "Formula text references a range in another workbook, so the dependency must be validated through external link evidence."
    if relation_type == "formula_references_pivot_table":
        return "Formula text uses a pivot-table function reference, so the dependency points to a pivot table view rather than a plain source range."
    if relation_type == "formula_references_workbook_range":
        return "Formula text references a workbook range that is not represented by a current candidate block."
    return "Formula text in the source block references the target range or block."


def _bounds_ref_overlap_area(bounds: dict[str, Any], reference: dict[str, Any]) -> int:
    ref_bounds = reference["target_bounds"]
    return _bounds_overlap_area(
        bounds,
        {
            "start_row": ref_bounds["min_row"],
            "end_row": ref_bounds["max_row"],
            "start_column": ref_bounds["min_column"],
            "end_column": ref_bounds["max_column"],
        },
    )


def _bounds_overlap_ratio(left: dict[str, Any], right: dict[str, Any]) -> float:
    area = _bounds_overlap_area(left, right)
    if area == 0:
        return 0.0
    left_area = _bounds_area(left)
    right_area = _bounds_area(right)
    return area / max(min(left_area, right_area), 1)


def _bounds_overlap_area(left: dict[str, Any], right: dict[str, Any]) -> int:
    if (
        left.get("start_column") is None
        or left.get("end_column") is None
        or right.get("start_column") is None
        or right.get("end_column") is None
    ):
        return 0
    rows = _overlap(left["start_row"], left["end_row"], right["start_row"], right["end_row"])
    columns = _overlap(
        left["start_column"],
        left["end_column"],
        right["start_column"],
        right["end_column"],
    )
    return rows * columns


def _bounds_area(bounds: dict[str, Any]) -> int:
    if bounds.get("start_column") is None or bounds.get("end_column") is None:
        return 0
    return (
        (bounds["end_row"] - bounds["start_row"] + 1)
        * (bounds["end_column"] - bounds["start_column"] + 1)
    )


def _overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    return max(0, min(a_end, b_end) - max(a_start, b_start) + 1)


def _sheet_observations(
    image_blocks: list[dict[str, Any]],
    pivot_blocks: list[dict[str, Any]],
    row_bands: list[dict[str, Any]],
    cell_region_split_candidates: list[dict[str, Any]],
) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": "Block candidates are deterministic seeds from manifest anchors and read-only row samples; they are not final document graph nodes.",
        }
    ]
    if image_blocks and not row_bands:
        observations.append(
            {
                "level": "warning",
                "message": "Image anchors exist, but no row bands were available from the read-only sample.",
            }
        )
    if pivot_blocks:
        observations.append(
            {
                "level": "info",
                "message": "Pivot tables are modeled as separate pivot_table blocks using pivot table definitions and cache sources.",
            }
        )
    if cell_region_split_candidates:
        observations.append(
            {
                "level": "info",
                "message": "2D cell region split candidates were produced from blank column gaps or repeated touching headers.",
            }
        )
    return observations


def _summary(sheets: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "sheet_count": len(sheets),
        "block_count": sum(len(sheet["blocks"]) for sheet in sheets),
        "image_block_count": sum(
            1 for sheet in sheets for block in sheet["blocks"] if block["type"] == "image"
        ),
        "row_band_count": sum(
            1 for sheet in sheets for block in sheet["blocks"] if block["type"] == "row_band"
        ),
        "pivot_table_block_count": sum(
            1 for sheet in sheets for block in sheet["blocks"] if block["type"] == "pivot_table"
        ),
        "cell_region_count": sum(
            len(sheet.get("cell_regions", [])) for sheet in sheets
        ),
        "cell_region_split_candidate_count": sum(
            len(sheet.get("cell_region_split_candidates", [])) for sheet in sheets
        ),
        "touching_header_split_candidate_count": sum(
            1
            for sheet in sheets
            for candidate in sheet.get("cell_region_split_candidates", [])
            if candidate["type"] == "repeated_header_touching_boundary"
        ),
        "style_boundary_split_candidate_count": sum(
            1
            for sheet in sheets
            for candidate in sheet.get("cell_region_split_candidates", [])
            if candidate["type"] == "style_discontinuity_boundary"
        ),
        "boundary_gate_result_count": sum(
            len(sheet.get("boundary_gate_results", [])) for sheet in sheets
        ),
        "strong_boundary_candidate_count": sum(
            1
            for sheet in sheets
            for result in sheet.get("boundary_gate_results", [])
            if result["status"] == "strong_candidate"
        ),
        "weak_boundary_signal_count": sum(
            1
            for sheet in sheets
            for result in sheet.get("boundary_gate_results", [])
            if result["status"] == "weak_signal"
        ),
        "merged_title_boundary_count": sum(
            1
            for sheet in sheets
            for result in sheet.get("boundary_gate_results", [])
            if result["candidate_type"] == "merged_range_title_boundary"
        ),
        "relation_group_count": sum(
            len(sheet.get("relation_groups", [])) for sheet in sheets
        ),
        "formula_relation_count": sum(
            1
            for sheet in sheets
            for relation in sheet["relations"]
            if relation["type"].startswith("formula_references")
        ),
        "relation_count": sum(len(sheet["relations"]) for sheet in sheets),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower()


def _cell(row: int, column: int) -> str:
    return f"{get_column_letter(column)}{row}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic document block candidates from workbook manifest and read-only samples."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("readonly_sample", type=Path)
    parser.add_argument("--formula-patterns", type=Path)
    parser.add_argument("--structural-style-profile", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sheet", action="append", dest="sheets")
    parser.add_argument("--max-blank-gap", type=int, default=1)
    args = parser.parse_args()

    package = build_block_candidates(
        args.manifest,
        args.readonly_sample,
        formula_patterns_path=args.formula_patterns,
        structural_style_profile_path=args.structural_style_profile,
        sheets=args.sheets,
        max_blank_gap=args.max_blank_gap,
    )
    payload = json.dumps(package, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
