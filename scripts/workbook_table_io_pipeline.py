from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl.utils import range_boundaries

SCHEMA_VERSION = "0.1"


def build_table_io_pipelines(block_candidates_path: Path) -> dict[str, Any]:
    block_candidates_path = block_candidates_path.expanduser().resolve()
    candidates = _read_json(block_candidates_path)
    sheet_index = _sheet_index(candidates)
    pipelines: dict[str, dict[str, Any]] = {}

    for sheet in candidates.get("sheets", []):
        for group in sheet.get("relation_groups", []):
            output_ref = _output_ref_for_relation_group(sheet_index, sheet["name"], group)
            pipeline_id = f"pipeline_{_slug(output_ref['id'])}"
            pipeline = pipelines.setdefault(
                pipeline_id,
                _pipeline_seed(pipeline_id, output_ref),
            )
            input_ref = _input_ref_for_relation_group(sheet_index, group)
            transform_ref = _formula_transform_ref(group)
            _append_unique_ref(pipeline["input_refs"], input_ref)
            _append_unique_ref(pipeline["transform_refs"], transform_ref)
            _add_pipeline_flags(pipeline, input_ref, transform_ref)
            pipeline["evidence_refs"].append(group["id"])

        for relation in sheet.get("relations", []):
            if relation["type"] != "derived_from_pivot_cache_source":
                continue
            pivot_block = sheet_index["blocks_by_id"].get(relation["from"])
            if not pivot_block:
                continue
            output_ref = _block_ref(pivot_block, kind="pivot_table")
            pipeline_id = f"pipeline_{_slug(output_ref['id'])}"
            pipeline = pipelines.setdefault(
                pipeline_id,
                _pipeline_seed(pipeline_id, output_ref),
            )
            input_ref = _input_ref_from_pivot_relation(sheet_index, relation)
            transform_ref = {
                "id": f"transform_{_slug(relation['id'])}",
                "kind": "pivot_cache",
                "relation_group_id": None,
                "relation_id": relation["id"],
                "relation_type": relation["type"],
                "formula_signature": None,
                "formula_cell_count": 0,
                "reference_count": 1,
                "evidence": ["pivot_cache_source"],
            }
            _append_unique_ref(pipeline["input_refs"], input_ref)
            _append_unique_ref(pipeline["transform_refs"], transform_ref)
            _add_pipeline_flags(pipeline, input_ref, transform_ref)
            pipeline["evidence_refs"].append(relation["id"])

    output = [_finalize_pipeline(pipeline) for pipeline in pipelines.values()]
    output.sort(key=lambda pipeline: (-pipeline["confidence"], pipeline["id"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "block_candidates": str(block_candidates_path),
        },
        "pipelines": output,
        "summary": _summary(output),
        "parser_observations": [
            {
                "level": "info",
                "message": "Table I/O pipelines are deterministic projections over relation groups, pivot cache source relations, and 2D cell regions. They are candidates, not accepted final graph claims.",
            }
        ],
    }


def _sheet_index(candidates: dict[str, Any]) -> dict[str, Any]:
    sheets = {sheet["name"]: sheet for sheet in candidates.get("sheets", [])}
    blocks_by_id = {}
    for sheet in sheets.values():
        for block in sheet.get("blocks", []):
            blocks_by_id[block["id"]] = block
    return {"sheets": sheets, "blocks_by_id": blocks_by_id}


def _pipeline_seed(pipeline_id: str, output_ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": pipeline_id,
        "type": "table_io_pipeline",
        "status": "candidate",
        "role": "unknown",
        "output_ref": output_ref,
        "input_refs": [],
        "transform_refs": [],
        "evidence_refs": [],
        "confidence": 0.5,
        "review_flags": [],
    }


def _output_ref_for_relation_group(
    sheet_index: dict[str, Any],
    sheet_name: str,
    group: dict[str, Any],
) -> dict[str, Any]:
    sheet = sheet_index["sheets"][sheet_name]
    source_cells = group.get("source_cell_samples", [])
    for cell in source_cells:
        region = _region_for_cell(sheet, cell)
        if region:
            return _region_ref(sheet_name, region)
    source_block = sheet_index["blocks_by_id"].get(group["source_block_id"])
    if source_block:
        return _block_ref(source_block, kind=source_block["type"])
    return {
        "id": group["source_block_id"],
        "kind": "unresolved_block",
        "workbook": None,
        "sheet": sheet_name,
        "range": None,
        "block_id": group["source_block_id"],
        "region_id": None,
        "bounds": None,
        "label": group["source_block_id"],
    }


def _input_ref_for_relation_group(
    sheet_index: dict[str, Any],
    group: dict[str, Any],
) -> dict[str, Any]:
    if group.get("target_workbook"):
        return {
            "id": f"external:{group['target_workbook']}!{group['target_sheet']}!{_bounds_label(group.get('target_bounds_union'))}",
            "kind": "external_workbook_range",
            "workbook": group["target_workbook"],
            "sheet": group["target_sheet"],
            "range": _bounds_label(group.get("target_bounds_union")),
            "block_id": None,
            "region_id": None,
            "bounds": group.get("target_bounds_union"),
            "label": group["target_workbook"],
        }

    target_sheet = sheet_index["sheets"].get(group["target_sheet"])
    target_bounds = group.get("target_bounds_union")
    if target_sheet and target_bounds:
        region = _region_for_bounds(target_sheet, target_bounds)
        if region:
            return _region_ref(group["target_sheet"], region)
        block = _block_for_bounds(target_sheet, target_bounds)
        if block:
            return _block_ref(block, kind=block["type"])
    return {
        "id": f"range:{group['target_sheet']}!{_bounds_label(target_bounds)}",
        "kind": "workbook_range",
        "workbook": None,
        "sheet": group["target_sheet"],
        "range": _bounds_label(target_bounds),
        "block_id": None,
        "region_id": None,
        "bounds": target_bounds,
        "label": group["target_sheet"],
    }


def _formula_transform_ref(group: dict[str, Any]) -> dict[str, Any]:
    evidence = ["formula_signature_group"]
    if group.get("reference_kind") == "pivot_function":
        evidence.append("pivot_function")
    if group.get("target_workbook"):
        evidence.append("external_workbook")
    return {
        "id": group["id"],
        "kind": "formula_signature_group",
        "relation_group_id": group["id"],
        "relation_id": None,
        "relation_type": group["relation_type"],
        "formula_signature": group["formula_signature"],
        "formula_cell_count": group["formula_cell_count"],
        "reference_count": group["reference_count"],
        "evidence": evidence,
    }


def _input_ref_from_pivot_relation(
    sheet_index: dict[str, Any],
    relation: dict[str, Any],
) -> dict[str, Any]:
    target = relation["to"].removeprefix("range:")
    sheet, range_text = _split_sheet_range(target)
    bounds = _range_bounds_or_none(range_text)
    target_sheet = sheet_index["sheets"].get(sheet)
    if target_sheet and bounds:
        region = _region_for_bounds(target_sheet, bounds)
        if region:
            return _region_ref(sheet, region)
        block = _block_for_bounds(target_sheet, bounds)
        if block:
            return _block_ref(block, kind=block["type"])
    return {
        "id": relation["to"],
        "kind": "pivot_cache_source_range",
        "workbook": None,
        "sheet": sheet or None,
        "range": range_text or target,
        "block_id": None,
        "region_id": None,
        "bounds": bounds,
        "label": relation["to"],
    }


def _split_sheet_range(value: str) -> tuple[str, str]:
    if value.startswith("'"):
        marker = "'!"
        if marker in value:
            sheet, range_text = value[1:].split(marker, 1)
            return sheet.replace("''", "'"), range_text
    sheet, _, range_text = value.partition("!")
    return sheet, range_text


def _region_ref(sheet_name: str, region: dict[str, Any]) -> dict[str, Any]:
    bounds = region["bounds"]
    return {
        "id": region["id"],
        "kind": "cell_region",
        "workbook": None,
        "sheet": sheet_name,
        "range": f"{bounds['start_cell']}:{bounds['end_cell']}",
        "block_id": region.get("parent_seed_block_id"),
        "region_id": region["id"],
        "bounds": {
            "min_row": bounds["start_row"],
            "min_column": bounds["start_column"],
            "max_row": bounds["end_row"],
            "max_column": bounds["end_column"],
        },
        "label": region.get("label") or region["id"],
    }


def _block_ref(block: dict[str, Any], *, kind: str) -> dict[str, Any]:
    bounds = block["bounds"]
    start_cell = bounds.get("start_cell")
    end_cell = bounds.get("end_cell")
    range_text = f"{start_cell}:{end_cell}" if start_cell and end_cell else None
    return {
        "id": block["id"],
        "kind": kind,
        "workbook": None,
        "sheet": block["source"]["sheet"],
        "range": range_text,
        "block_id": block["id"],
        "region_id": None,
        "bounds": {
            "min_row": bounds["start_row"],
            "min_column": bounds["start_column"],
            "max_row": bounds["end_row"],
            "max_column": bounds["end_column"],
        },
        "label": block.get("label") or block["id"],
    }


def _region_for_cell(sheet: dict[str, Any], cell: str) -> dict[str, Any] | None:
    position = _cell_position(cell)
    if position is None:
        return None
    row, column = position
    for region in sheet.get("cell_regions", []):
        bounds = region["bounds"]
        if (
            bounds["start_row"] <= row <= bounds["end_row"]
            and bounds["start_column"] <= column <= bounds["end_column"]
        ):
            return region
    return None


def _region_for_bounds(sheet: dict[str, Any], bounds: dict[str, int]) -> dict[str, Any] | None:
    candidates = []
    for region in sheet.get("cell_regions", []):
        area = _bounds_overlap_area(region["bounds"], bounds)
        if area > 0:
            candidates.append((area, region))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _block_for_bounds(sheet: dict[str, Any], bounds: dict[str, int]) -> dict[str, Any] | None:
    candidates = []
    for block in sheet.get("blocks", []):
        area = _bounds_overlap_area(block["bounds"], bounds)
        if area > 0:
            candidates.append((area, block))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _bounds_overlap_area(left: dict[str, Any], right: dict[str, Any]) -> int:
    left_min_col = left.get("start_column") or left.get("min_column")
    left_max_col = left.get("end_column") or left.get("max_column")
    left_min_row = left.get("start_row") or left.get("min_row")
    left_max_row = left.get("end_row") or left.get("max_row")
    right_min_col = right.get("start_column") or right.get("min_column")
    right_max_col = right.get("end_column") or right.get("max_column")
    right_min_row = right.get("start_row") or right.get("min_row")
    right_max_row = right.get("end_row") or right.get("max_row")
    if any(
        value is None
        for value in (
            left_min_col,
            left_max_col,
            left_min_row,
            left_max_row,
            right_min_col,
            right_max_col,
            right_min_row,
            right_max_row,
        )
    ):
        return 0
    rows = max(0, min(left_max_row, right_max_row) - max(left_min_row, right_min_row) + 1)
    columns = max(0, min(left_max_col, right_max_col) - max(left_min_col, right_min_col) + 1)
    return rows * columns


def _add_pipeline_flags(
    pipeline: dict[str, Any],
    input_ref: dict[str, Any],
    transform_ref: dict[str, Any],
) -> None:
    if input_ref["kind"] in {"workbook_range", "external_workbook_range"}:
        _add_unique(pipeline["review_flags"], "unresolved_input_region")
    if input_ref["kind"] == "external_workbook_range":
        _add_unique(pipeline["review_flags"], "external_workbook_dependency")
    if input_ref["kind"] == "pivot_cache_source_range" or transform_ref["kind"] == "pivot_cache":
        _add_unique(pipeline["review_flags"], "pivot_cache_dependency")
    if input_ref["sheet"] == pipeline["output_ref"]["sheet"]:
        _add_unique(pipeline["review_flags"], "same_sheet_dataflow")
    if transform_ref["kind"] == "formula_signature_group" and transform_ref["formula_cell_count"] >= 10:
        _add_unique(pipeline["review_flags"], "repeated_formula_family")


def _finalize_pipeline(pipeline: dict[str, Any]) -> dict[str, Any]:
    pipeline["evidence_refs"] = sorted(set(pipeline["evidence_refs"]))
    pipeline["role"] = _pipeline_role(pipeline)
    pipeline["confidence"] = _pipeline_confidence(pipeline)
    return pipeline


def _pipeline_role(pipeline: dict[str, Any]) -> str:
    transform_kinds = {item["kind"] for item in pipeline["transform_refs"]}
    signatures = [
        item.get("formula_signature") or ""
        for item in pipeline["transform_refs"]
        if item["kind"] == "formula_signature_group"
    ]
    input_sheets = {item.get("sheet") for item in pipeline["input_refs"]}
    output_sheet = pipeline["output_ref"].get("sheet")
    if "pivot_cache" in transform_kinds:
        return "report"
    if any("SUBTOTAL(" in signature or "SUMIFS(" in signature for signature in signatures):
        return "summary"
    if any(sheet and sheet != output_sheet for sheet in input_sheets):
        return "bridge"
    if signatures:
        return "transform"
    return "unknown"


def _pipeline_confidence(pipeline: dict[str, Any]) -> float:
    confidence = 0.55
    if pipeline["output_ref"]["kind"] in {"cell_region", "pivot_table"}:
        confidence += 0.12
    if pipeline["input_refs"]:
        confidence += 0.08
    if any(item["kind"] == "pivot_cache" for item in pipeline["transform_refs"]):
        confidence += 0.12
    if "unresolved_input_region" in pipeline["review_flags"]:
        confidence -= 0.08
    if "external_workbook_dependency" in pipeline["review_flags"]:
        confidence -= 0.05
    return round(max(0.0, min(confidence, 0.92)), 4)


def _append_unique_ref(items: list[dict[str, Any]], value: dict[str, Any]) -> None:
    if all(item["id"] != value["id"] for item in items):
        items.append(value)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _summary(pipelines: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "pipeline_count": len(pipelines),
        "formula_pipeline_count": sum(
            1
            for pipeline in pipelines
            if any(item["kind"] == "formula_signature_group" for item in pipeline["transform_refs"])
        ),
        "pivot_pipeline_count": sum(
            1
            for pipeline in pipelines
            if any(item["kind"] == "pivot_cache" for item in pipeline["transform_refs"])
        ),
        "external_dependency_pipeline_count": sum(
            1 for pipeline in pipelines if "external_workbook_dependency" in pipeline["review_flags"]
        ),
        "unresolved_input_pipeline_count": sum(
            1 for pipeline in pipelines if "unresolved_input_region" in pipeline["review_flags"]
        ),
        "summary_role_count": sum(1 for pipeline in pipelines if pipeline["role"] == "summary"),
        "bridge_role_count": sum(1 for pipeline in pipelines if pipeline["role"] == "bridge"),
        "report_role_count": sum(1 for pipeline in pipelines if pipeline["role"] == "report"),
    }


def _bounds_label(bounds: dict[str, Any] | None) -> str | None:
    if not bounds:
        return None
    return (
        f"R{bounds['min_row']}:R{bounds['max_row']},"
        f"C{bounds['min_column']}:C{bounds['max_column']}"
    )


def _range_bounds_or_none(value: str | None) -> dict[str, int] | None:
    if not value:
        return None
    try:
        min_col, min_row, max_col, max_row = range_boundaries(value)
    except ValueError:
        return None
    if None in (min_col, min_row, max_col, max_row):
        return None
    return {
        "min_row": min_row,
        "min_column": min_col,
        "max_row": max_row,
        "max_column": max_col,
    }


def _cell_position(value: str) -> tuple[int, int] | None:
    bounds = _range_bounds_or_none(value)
    if bounds is None:
        return None
    return bounds["min_row"], bounds["min_column"]


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Project formula, pivot, and region evidence into table-level I/O pipelines."
    )
    parser.add_argument("block_candidates", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    package = build_table_io_pipelines(args.block_candidates)
    text = json.dumps(package, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
