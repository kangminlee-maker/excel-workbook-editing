from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CELL_REF_RE = re.compile(
    r"(?P<sheet_prefix>(?:'(?P<qsheet>[^']+)'|(?P<sheet>[A-Za-z0-9_.\[\] ()-]+))!)?"
    r"(?P<ref>\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?|\$?[A-Z]{1,3}:\$?[A-Z]{1,3}|\$?\d+:\$?\d+)"
)
CELL_RE = re.compile(r"\$?([A-Z]{1,3})\$?(\d+)$")
RANGE_RE = re.compile(r"(\$?[A-Z]{1,3}\$?\d+):(\$?[A-Z]{1,3}\$?\d+)$")
DOUBLE_QUOTED_RE = re.compile(r'"(?:[^"]|"")*"')
FUNCTION_RE = re.compile(r"([A-Z][A-Z0-9_.]*)\s*\(", re.IGNORECASE)
TARGET_COLUMN_COUNT = 1848
COLUMN_BLOCK_WIDTH = 40
TARGET_SHEET_TITLE = "[ML] 매출_최종"
METRIC_BASIS = {
    "canonical_metric": "payment_amount",
    "korean_label": "결제액",
    "source_label_warning": "Workbook labels use `매출`, but the user-confirmed business meaning in this sheet is payment amount, not accounting revenue.",
    "accounting_revenue_basis": "not_applicable",
}
AUTOMATION_TOOL_SIGNATURES = {
    "supermetrics": ["supermetrics", "zsupermetrics"],
    "zapier": ["zapier"],
    "apps_script": ["apps script", "appsscript", "script"],
}


def col_to_index(col: str) -> int:
    result = 0
    for char in col.replace("$", "").upper():
        if not ("A" <= char <= "Z"):
            raise ValueError(f"invalid column: {col}")
        result = result * 26 + ord(char) - 64
    return result


def index_to_col(index: int) -> str:
    if index < 1:
        raise ValueError(f"invalid column index: {index}")
    value = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        value = chr(65 + remainder) + value
    return value


def split_a1_range(a1_range: str) -> tuple[str, str, int, int]:
    sheet, coords = a1_range.split("!", 1)
    sheet = sheet.strip("'")
    start = coords.split(":", 1)[0]
    match = CELL_RE.match(start)
    if not match:
        raise ValueError(f"unsupported range start: {a1_range}")
    start_col = col_to_index(match.group(1))
    start_row = int(match.group(2))
    return sheet, coords, start_row, start_col


def parse_a1_window_bounds(a1_range: str) -> dict[str, Any]:
    sheet, coords = a1_range.split("!", 1)
    sheet = sheet.strip("'")
    start, end = (coords.split(":", 1) + [coords])[:2]
    start_match = CELL_RE.match(start)
    end_match = CELL_RE.match(end)
    if not start_match or not end_match:
        raise ValueError(f"unsupported bounded range: {a1_range}")
    start_col = col_to_index(start_match.group(1))
    end_col = col_to_index(end_match.group(1))
    start_row = int(start_match.group(2))
    end_row = int(end_match.group(2))
    return {
        "sheet_title": sheet,
        "start_row": min(start_row, end_row),
        "end_row": max(start_row, end_row),
        "start_column": min(start_col, end_col),
        "end_column": max(start_col, end_col),
    }


def bbox_inside_window(bbox: dict[str, Any], window: dict[str, Any]) -> bool:
    start_match = CELL_RE.match(bbox["start_cell"])
    end_match = CELL_RE.match(bbox["end_cell"])
    if not start_match or not end_match:
        return False
    start_col = col_to_index(start_match.group(1))
    end_col = col_to_index(end_match.group(1))
    start_row = int(start_match.group(2))
    end_row = int(end_match.group(2))
    return (
        window["start_row"] <= start_row <= end_row <= window["end_row"]
        and window["start_column"] <= start_col <= end_col <= window["end_column"]
    )


def mask_double_quoted_text(formula: str) -> str:
    return DOUBLE_QUOTED_RE.sub('""', formula)


def normalize_ref(raw_ref: str, formula_row: int, formula_col: int) -> str:
    if ":" in raw_ref:
        left, right = raw_ref.split(":", 1)
        if CELL_RE.match(left) and CELL_RE.match(right):
            return f"{normalize_ref(left, formula_row, formula_col)}:{normalize_ref(right, formula_row, formula_col)}"
        return raw_ref.replace("$", "")

    match = CELL_RE.match(raw_ref)
    if not match:
        return raw_ref.replace("$", "")
    ref_col = col_to_index(match.group(1))
    ref_row = int(match.group(2))
    return f"R[{ref_row - formula_row}]C[{ref_col - formula_col}]"


def classify_formula(formula: str) -> list[str]:
    masked = mask_double_quoted_text(formula.upper())
    classes = []
    for name in ["IMPORTRANGE", "INDIRECT", "QUERY", "FILTER", "ARRAYFORMULA", "SUMIF", "SUMIFS", "VLOOKUP", "XLOOKUP"]:
        if f"{name}(" in masked:
            classes.append(name.lower())
    return classes


def extract_references(formula: str, current_sheet: str, row: int, col: int) -> list[dict[str, Any]]:
    masked = mask_double_quoted_text(formula)
    refs = []
    for match in CELL_REF_RE.finditer(masked):
        sheet = match.group("qsheet") or match.group("sheet") or current_sheet
        raw_ref = match.group("ref")
        if sheet == current_sheet:
            kind = "same_sheet"
        else:
            kind = "cross_sheet"
        if re.match(r"\$?[A-Z]{1,3}:\$?[A-Z]{1,3}$", raw_ref):
            ref_shape = "column_range"
        elif re.match(r"\$?\d+:\$?\d+$", raw_ref):
            ref_shape = "row_range"
        elif ":" in raw_ref:
            ref_shape = "cell_range"
        else:
            ref_shape = "cell"
        refs.append(
            {
                "referenced_sheet": sheet.strip(),
                "referenced_range": raw_ref.replace("$", ""),
                "reference_kind": kind,
                "reference_shape": ref_shape,
            }
        )
    return refs


def normalize_formula(formula: str, current_sheet: str, row: int, col: int) -> str:
    masked = mask_double_quoted_text(formula)

    def replace(match: re.Match[str]) -> str:
        sheet = (match.group("qsheet") or match.group("sheet") or current_sheet).strip()
        raw_ref = match.group("ref")
        normalized = normalize_ref(raw_ref, row, col)
        if sheet == current_sheet:
            return normalized
        return f"{sheet}!{normalized}"

    return CELL_REF_RE.sub(replace, masked)


def load_window_files(run_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    windows = []
    for path in sorted(run_dir.glob("*window-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        payload = data.get("payload", data)
        if payload.get("operation") in {"inspect.formula_window", "inspect.values_window"}:
            windows.append((path, payload))
    return windows


def collect_formula_inventory(run_dir: Path, sheet_title: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    formula_by_cell: dict[str, dict[str, Any]] = {}
    window_summaries = []
    for path, payload in load_window_files(run_dir):
        operation = payload["operation"]
        for window in payload.get("windows", []):
            range_name = window.get("range") or payload.get("requested_ranges", [""])[0]
            sheet, _coords, start_row, start_col = split_a1_range(range_name)
            values = window.get("values", [])
            nonempty = 0
            formula_count = 0
            for row_offset, row_values in enumerate(values):
                row_index = start_row + row_offset
                for col_offset, value in enumerate(row_values):
                    if value not in ("", None):
                        nonempty += 1
                    if operation != "inspect.formula_window" or not (isinstance(value, str) and value.startswith("=")):
                        continue
                    col_index = start_col + col_offset
                    address = f"{index_to_col(col_index)}{row_index}"
                    key = f"{sheet}!{address}"
                    formula_count += 1
                    formula_by_cell.setdefault(
                        key,
                        {
                            "sheet_title": sheet,
                            "cell": address,
                            "row": row_index,
                            "column": col_index,
                            "formula": value,
                            "classifications": classify_formula(value),
                            "source_windows": [],
                        },
                    )
                    formula_by_cell[key]["source_windows"].append(path.name)
            window_summaries.append(
                {
                    "artifact": path.name,
                    "operation": operation,
                    "range": range_name,
                    "rows_observed": len(values),
                    "max_columns_observed": max((len(row) for row in values), default=0),
                    "nonempty_cells": nonempty,
                    "formula_cells": formula_count,
                }
            )

    inventory = sorted(formula_by_cell.values(), key=lambda item: (item["row"], item["column"]))
    references = []
    for item in inventory:
        item_refs = extract_references(item["formula"], item["sheet_title"], item["row"], item["column"])
        item["reference_count"] = len(item_refs)
        item["normalized_signature"] = normalize_formula(
            item["formula"], item["sheet_title"], item["row"], item["column"]
        )
        item["signature_hash"] = short_hash(item["normalized_signature"])
        for index, ref in enumerate(item_refs):
            references.append(
                {
                    "from_sheet": item["sheet_title"],
                    "from_cell": item["cell"],
                    "from_row": item["row"],
                    "from_column": item["column"],
                    "reference_index": index,
                    **ref,
                }
            )
    return inventory, references, window_summaries


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def row_band_name(row: int) -> str:
    if row <= 20:
        return "summary_rows_1_20"
    if row <= 119:
        return "pre_detail_rows_21_119"
    return "detail_rows_120_453"


def column_block_name(column: int) -> str:
    start = ((column - 1) // COLUMN_BLOCK_WIDTH) * COLUMN_BLOCK_WIDTH + 1
    end = min(start + COLUMN_BLOCK_WIDTH - 1, TARGET_COLUMN_COUNT)
    return f"cols_{index_to_col(start)}_{index_to_col(end)}"


def referenced_orientation(raw_range: str) -> str:
    raw_range = raw_range.replace("$", "")
    if re.match(r"[A-Z]{1,3}:[A-Z]{1,3}$", raw_range):
        return "column_range"
    if re.match(r"\d+:\d+$", raw_range):
        return "row_range"
    cell_match = CELL_RE.match(raw_range)
    if cell_match:
        return "cell"
    range_match = RANGE_RE.match(raw_range)
    if not range_match:
        return "unresolved"
    left = CELL_RE.match(range_match.group(1))
    right = CELL_RE.match(range_match.group(2))
    if not left or not right:
        return "unresolved"
    left_col = col_to_index(left.group(1))
    right_col = col_to_index(right.group(1))
    left_row = int(left.group(2))
    right_row = int(right.group(2))
    if left_col == right_col:
        return "vertical_range"
    if left_row == right_row:
        return "horizontal_range"
    return "block_range"


def primary_function(formula: str) -> str:
    functions = [function.upper() for function in FUNCTION_RE.findall(formula)]
    if not functions:
        return "NO_FUNCTION"
    if "SUMIFS" in functions:
        return "SUMIFS"
    if "SUMIF" in functions:
        return "SUMIF"
    if "SUM" in functions:
        return "SUM"
    return functions[0]


def formula_family_kind(item: dict[str, Any], refs: list[dict[str, Any]]) -> str:
    function = primary_function(item["formula"])
    current_sheet = item["sheet_title"]
    cross_refs = [ref for ref in refs if ref["referenced_sheet"] != current_sheet]
    orientations = Counter(referenced_orientation(ref["referenced_range"]) for ref in refs)
    dominant_orientation = orientations.most_common(1)[0][0] if orientations else "no_reference"
    if function in {"SUMIFS", "SUMIF"} and cross_refs:
        return "cross_sheet_conditional_aggregate"
    if function in {"SUMIFS", "SUMIF"}:
        return "same_sheet_conditional_aggregate"
    if function == "SUM":
        if dominant_orientation == "vertical_range":
            return "same_sheet_vertical_sum"
        if dominant_orientation == "horizontal_range":
            return "same_sheet_horizontal_sum"
        return "same_sheet_sum"
    if function == "TEXT":
        return "text_projection"
    if cross_refs:
        return "cross_sheet_formula"
    return "same_sheet_arithmetic_or_formula"


def build_pattern_groups(inventory: list[dict[str, Any]], references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs_by_cell = defaultdict(list)
    for ref in references:
        refs_by_cell[(ref["from_sheet"], ref["from_cell"])].append(ref)

    groups: dict[str, dict[str, Any]] = {}
    for item in inventory:
        group_id = f"pg_{item['signature_hash']}"
        group = groups.setdefault(
            group_id,
            {
                "pattern_group_id": group_id,
                "normalized_signature": item["normalized_signature"],
                "formula_count": 0,
                "sample_formula": item["formula"],
                "sample_cells": [],
                "min_row": item["row"],
                "max_row": item["row"],
                "min_column": item["column"],
                "max_column": item["column"],
                "classifications": set(),
                "referenced_sheets": Counter(),
                "reference_shapes": Counter(),
            },
        )
        group["formula_count"] += 1
        if len(group["sample_cells"]) < 30:
            group["sample_cells"].append(item["cell"])
        group["min_row"] = min(group["min_row"], item["row"])
        group["max_row"] = max(group["max_row"], item["row"])
        group["min_column"] = min(group["min_column"], item["column"])
        group["max_column"] = max(group["max_column"], item["column"])
        group["classifications"].update(item["classifications"])
        for ref in refs_by_cell[(item["sheet_title"], item["cell"])]:
            group["referenced_sheets"][ref["referenced_sheet"]] += 1
            group["reference_shapes"][ref["reference_shape"]] += 1

    result = []
    for group in groups.values():
        group["output_bbox"] = {
            "start_cell": f"{index_to_col(group['min_column'])}{group['min_row']}",
            "end_cell": f"{index_to_col(group['max_column'])}{group['max_row']}",
            "rows": group["max_row"] - group["min_row"] + 1,
            "columns": group["max_column"] - group["min_column"] + 1,
        }
        group["classifications"] = sorted(group["classifications"])
        group["referenced_sheets"] = [
            {"sheet": sheet, "count": count} for sheet, count in group["referenced_sheets"].most_common()
        ]
        group["reference_shapes"] = dict(group["reference_shapes"])
        result.append(group)
    return sorted(result, key=lambda item: (-item["formula_count"], item["pattern_group_id"]))


def references_by_formula_cell(references: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    refs_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for ref in references:
        refs_by_cell[(ref["from_sheet"], ref["from_cell"])].append(ref)
    return refs_by_cell


def build_region_families(inventory: list[dict[str, Any]], references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs_by_cell = references_by_formula_cell(references)
    families: dict[str, dict[str, Any]] = {}
    for item in inventory:
        refs = refs_by_cell[(item["sheet_title"], item["cell"])]
        source_sheets = sorted(
            sheet
            for sheet in {ref["referenced_sheet"] for ref in refs}
            if sheet != item["sheet_title"]
        )
        source_bucket = "|".join(source_sheets) if source_sheets else "self"
        orientations = Counter(referenced_orientation(ref["referenced_range"]) for ref in refs)
        dominant_orientation = orientations.most_common(1)[0][0] if orientations else "no_reference"
        kind = formula_family_kind(item, refs)
        function = primary_function(item["formula"])
        key = "|".join(
            [
                row_band_name(item["row"]),
                column_block_name(item["column"]),
                kind,
                function,
                source_bucket,
                dominant_orientation,
            ]
        )
        family_id = f"rf_{short_hash(key)}"
        family = families.setdefault(
            family_id,
            {
                "region_family_id": family_id,
                "family_key": key,
                "row_band": row_band_name(item["row"]),
                "column_block": column_block_name(item["column"]),
                "formula_kind": kind,
                "primary_function": function,
                "source_bucket": source_bucket,
                "dominant_reference_orientation": dominant_orientation,
                "formula_count": 0,
                "sample_cells": [],
                "sample_formulas": [],
                "signature_hashes": Counter(),
                "referenced_sheets": Counter(),
                "reference_orientations": Counter(),
                "reference_shapes": Counter(),
                "source_windows": Counter(),
                "min_row": item["row"],
                "max_row": item["row"],
                "min_column": item["column"],
                "max_column": item["column"],
            },
        )
        family["formula_count"] += 1
        if len(family["sample_cells"]) < 24:
            family["sample_cells"].append(item["cell"])
        if len(family["sample_formulas"]) < 5 and item["formula"] not in family["sample_formulas"]:
            family["sample_formulas"].append(item["formula"])
        family["signature_hashes"][item["signature_hash"]] += 1
        family["min_row"] = min(family["min_row"], item["row"])
        family["max_row"] = max(family["max_row"], item["row"])
        family["min_column"] = min(family["min_column"], item["column"])
        family["max_column"] = max(family["max_column"], item["column"])
        for source_window in item.get("source_windows", []):
            family["source_windows"][source_window] += 1
        for ref in refs:
            family["referenced_sheets"][ref["referenced_sheet"]] += 1
            family["reference_shapes"][ref["reference_shape"]] += 1
            family["reference_orientations"][referenced_orientation(ref["referenced_range"])] += 1

    result = []
    for family in families.values():
        family["output_bbox"] = {
            "start_cell": f"{index_to_col(family['min_column'])}{family['min_row']}",
            "end_cell": f"{index_to_col(family['max_column'])}{family['max_row']}",
            "rows": family["max_row"] - family["min_row"] + 1,
            "columns": family["max_column"] - family["min_column"] + 1,
        }
        family["signature_hashes"] = [
            {"signature_hash": key, "count": count}
            for key, count in family["signature_hashes"].most_common(20)
        ]
        family["referenced_sheets"] = [
            {"sheet": key, "count": count}
            for key, count in family["referenced_sheets"].most_common(20)
        ]
        family["reference_orientations"] = dict(family["reference_orientations"])
        family["reference_shapes"] = dict(family["reference_shapes"])
        family["source_windows"] = [
            {"artifact": key, "count": count}
            for key, count in family["source_windows"].most_common()
        ]
        result.append(family)
    return sorted(result, key=lambda item: (-item["formula_count"], item["region_family_id"]))


def build_table_pipeline_candidates(region_families: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    aggregate_edges: dict[tuple[str, str], dict[str, Any]] = {}
    for family in region_families:
        source_sheets = [
            item["sheet"]
            for item in family["referenced_sheets"]
            if item["sheet"] != "[ML] 매출_최종"
        ]
        if not source_sheets:
            source_sheets = ["[ML] 매출_최종"]
        for source_sheet in source_sheets:
            source_kind = "source_sheet" if source_sheet != "[ML] 매출_최종" else "same_sheet_formula_region"
            edge_key = (source_sheet, family["formula_kind"])
            aggregate = aggregate_edges.setdefault(
                edge_key,
                {
                    "pipeline_candidate_id": f"pipe_{short_hash('|'.join(edge_key))}",
                    "source": {"sheet": source_sheet, "kind": source_kind},
                    "target_kind": "formula_region_family",
                    "formula_kind": family["formula_kind"],
                    "primary_functions": Counter(),
                    "family_count": 0,
                    "formula_count": 0,
                    "region_family_ids": [],
                    "sample_output_bboxes": [],
                    "status": "candidate",
                    "authority": "formula_reference_sampled",
                },
            )
            aggregate["family_count"] += 1
            aggregate["formula_count"] += family["formula_count"]
            aggregate["primary_functions"][family["primary_function"]] += family["formula_count"]
            if len(aggregate["region_family_ids"]) < 30:
                aggregate["region_family_ids"].append(family["region_family_id"])
            if len(aggregate["sample_output_bboxes"]) < 12:
                aggregate["sample_output_bboxes"].append(family["output_bbox"])

    for candidate in aggregate_edges.values():
        candidate["primary_functions"] = [
            {"function": key, "count": count}
            for key, count in candidate["primary_functions"].most_common()
        ]
        candidates.append(candidate)

    candidates = sorted(candidates, key=lambda item: (-item["formula_count"], item["pipeline_candidate_id"]))
    mermaid = ["flowchart LR"]
    target_nodes = {}
    source_nodes = {}
    for candidate in candidates[:40]:
        source_id = f"src_{short_hash(candidate['source']['sheet'])}"
        target_id = f"tgt_{short_hash(candidate['formula_kind'])}"
        source_nodes[source_id] = candidate["source"]["sheet"]
        target_nodes[target_id] = candidate["formula_kind"]
    for node_id, label in source_nodes.items():
        mermaid.append(f'  {node_id}["{escape_mermaid(label)}"]')
    for node_id, label in target_nodes.items():
        mermaid.append(f'  {node_id}["{escape_mermaid(label)}"]')
    for candidate in candidates[:40]:
        source_id = f"src_{short_hash(candidate['source']['sheet'])}"
        target_id = f"tgt_{short_hash(candidate['formula_kind'])}"
        mermaid.append(
            f'  {source_id} -->|"{candidate["formula_count"]}"| {target_id}'
        )
    return {
        "schema_version": 1,
        "stage": "formula_dataflow_table_pipeline_candidates",
        "coverage_status": "sampled_partial",
        "pipeline_candidates": candidates,
        "mermaid": "\n".join(mermaid),
        "review_note": "Candidates are aggregated from sampled formula references and need coverage gates before acceptance.",
    }


def build_region_graph(pattern_groups: list[dict[str, Any]], references: list[dict[str, Any]]) -> dict[str, Any]:
    referenced_sheet_counts = Counter(ref["referenced_sheet"] for ref in references)
    top_groups = pattern_groups[:30]
    nodes = []
    edges = []
    nodes.append({"id": "sheet_current", "label": "[ML] current sampled formula regions", "kind": "sheet"})
    for sheet, count in referenced_sheet_counts.most_common(30):
        node_id = f"input_{short_hash(sheet)}"
        nodes.append({"id": node_id, "label": sheet, "kind": "referenced_sheet", "reference_count": count})
        edges.append(
            {
                "from": node_id,
                "to": "sheet_current",
                "kind": "formula_reference",
                "reference_count": count,
                "status": "candidate",
            }
        )
    for group in top_groups:
        nodes.append(
            {
                "id": group["pattern_group_id"],
                "label": f"{group['output_bbox']['start_cell']}:{group['output_bbox']['end_cell']}",
                "kind": "pattern_group",
                "formula_count": group["formula_count"],
            }
        )
        edges.append(
            {
                "from": "sheet_current",
                "to": group["pattern_group_id"],
                "kind": "output_pattern",
                "formula_count": group["formula_count"],
                "status": "candidate",
            }
        )
    mermaid = ["flowchart LR"]
    for node in nodes[:80]:
        mermaid.append(f'  {node["id"]}["{escape_mermaid(node["label"])}"]')
    for edge in edges[:120]:
        label = edge.get("reference_count") or edge.get("formula_count") or ""
        mermaid.append(f'  {edge["from"]} -->|"{label}"| {edge["to"]}')
    return {
        "nodes": nodes,
        "edges": edges,
        "mermaid": "\n".join(mermaid),
        "coverage_note": "Graph is based on sampled windows only, not full-sheet coverage.",
    }


def build_review_summary(
    summary: dict[str, Any],
    inventory: list[dict[str, Any]],
    references: list[dict[str, Any]],
    pattern_groups: list[dict[str, Any]],
    region_families: list[dict[str, Any]],
    pipeline_package: dict[str, Any],
    automation_inventory: dict[str, Any],
    region_gate_package: dict[str, Any],
    pipeline_gate_package: dict[str, Any],
) -> dict[str, Any]:
    function_counts: Counter[str] = Counter()
    for item in inventory:
        for function_name in FUNCTION_RE.findall(item["formula"]):
            function_counts[function_name.upper()] += 1
    referenced_sheet_counts = Counter(ref["referenced_sheet"] for ref in references)
    reference_shape_counts = Counter(ref["reference_shape"] for ref in references)
    classification_counts: Counter[str] = Counter()
    for item in inventory:
        for classification in item["classifications"]:
            classification_counts[classification] += 1
    return {
        "schema_version": 1,
        "generated_at": summary["generated_at"],
        "stage": "formula_dataflow_review_summary",
        "coverage_status": summary["coverage_status"],
        "coverage_note": summary["coverage_note"],
        "metrics": {
            "formula_cell_count": summary["formula_cell_count"],
            "reference_edge_count": summary["reference_edge_count"],
            "pattern_group_count": summary["pattern_group_count"],
            "region_family_count": len(region_families),
            "pipeline_candidate_count": len(pipeline_package["pipeline_candidates"]),
            "automation_tool_finding_count": len(automation_inventory["tool_findings"]),
            "detected_automation_tool_count": sum(
                1 for item in automation_inventory["tool_findings"] if item["status"] == "detected"
            ),
            "region_family_gate_count": len(region_gate_package["region_family_gates"]),
            "pipeline_gate_count": len(pipeline_gate_package["pipeline_gates"]),
            "sampled_window_count": len(summary["window_summaries"]),
        },
        "top_functions": [
            {"function": name, "count": count} for name, count in function_counts.most_common(20)
        ],
        "top_referenced_sheets": [
            {"sheet": sheet, "count": count} for sheet, count in referenced_sheet_counts.most_common(20)
        ],
        "reference_shape_counts": dict(reference_shape_counts),
        "formula_classification_counts": dict(classification_counts),
        "top_pattern_groups": [
            {
                "pattern_group_id": group["pattern_group_id"],
                "formula_count": group["formula_count"],
                "output_bbox": group["output_bbox"],
                "referenced_sheets": group["referenced_sheets"][:5],
                "sample_formula": group["sample_formula"],
                "normalized_signature": group["normalized_signature"],
            }
            for group in pattern_groups[:20]
        ],
        "top_region_families": [
            {
                "region_family_id": family["region_family_id"],
                "formula_count": family["formula_count"],
                "row_band": family["row_band"],
                "column_block": family["column_block"],
                "formula_kind": family["formula_kind"],
                "primary_function": family["primary_function"],
                "output_bbox": family["output_bbox"],
                "referenced_sheets": family["referenced_sheets"][:5],
                "sample_formulas": family["sample_formulas"][:3],
            }
            for family in region_families[:30]
        ],
        "top_pipeline_candidates": pipeline_package["pipeline_candidates"][:20],
        "metric_basis": METRIC_BASIS,
        "connected_automation_summary": automation_inventory["summary"],
        "region_gate_summary": region_gate_package["gate_summary"],
        "pipeline_gate_summary": pipeline_gate_package["gate_summary"],
        "review_findings": [
            {
                "id": "partial_coverage",
                "status": "review_required",
                "message": "Current artifacts are sampled windows only. Full-sheet conclusions require additional column chunks.",
            },
            {
                "id": "strong_self_aggregation_pattern",
                "status": "observed",
                "message": "Large repeated self-sheet SUM patterns indicate many report/output cells are aggregations over nearby rows or columns.",
            },
            {
                "id": "raw_payment_amount_source_dependency",
                "status": "observed",
                "message": "Repeated SUMIFS patterns reference raw `매출`-labeled sheets; interpret these as payment-amount sources for this workbook, not accounting revenue sources.",
            },
            {
                "id": "metric_basis_payment_amount",
                "status": "user_confirmed",
                "message": "The user confirmed that `매출` in this sheet means 결제액/payment amount, not accounting revenue.",
            },
            {
                "id": "region_family_reduction",
                "status": "observed",
                "message": "Region-family grouping reduces formula signatures into broader role-like families suitable for table-level pipeline review.",
            },
            {
                "id": "connected_automation_detected",
                "status": automation_inventory["summary"]["overall_status"],
                "message": automation_inventory["summary"]["message"],
            },
            {
                "id": "deterministic_gate_tuning",
                "status": pipeline_gate_package["gate_summary"]["overall_status"],
                "message": "Pipeline candidates now carry deterministic gate outcomes for coverage, source metadata, value-pair authority, self-reference risk, and connected automation context.",
            },
        ],
    }


def load_metadata_payload(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "metadata.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("payload", data)


def build_connected_automation_inventory(
    metadata: dict[str, Any],
    inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    tabs = metadata.get("tabs", []) if isinstance(metadata.get("tabs"), list) else []
    named_ranges = metadata.get("named_ranges", []) if isinstance(metadata.get("named_ranges"), list) else []

    def record_signal(tool: str, signal_type: str, label: str, detail: dict[str, Any]) -> None:
        evidence[tool].append(
            {
                "signal_type": signal_type,
                "label": label,
                "detail": detail,
            }
        )

    for tab in tabs:
        title = str(tab.get("title", ""))
        lowered = title.lower()
        for tool, signatures in AUTOMATION_TOOL_SIGNATURES.items():
            if any(signature in lowered for signature in signatures):
                record_signal(
                    tool,
                    "tab_title",
                    title,
                    {
                        "sheet_id": tab.get("sheet_id"),
                        "hidden": tab.get("hidden"),
                        "row_count": tab.get("row_count"),
                        "column_count": tab.get("column_count"),
                    },
                )

    for named_range in named_ranges:
        name = str(named_range.get("name", ""))
        lowered = name.lower()
        for tool, signatures in AUTOMATION_TOOL_SIGNATURES.items():
            if any(signature in lowered for signature in signatures):
                record_signal(
                    tool,
                    "named_range",
                    name,
                    {"range": named_range.get("range")},
                )

    for item in inventory:
        formula = str(item.get("formula", ""))
        lowered = formula.lower()
        for tool, signatures in AUTOMATION_TOOL_SIGNATURES.items():
            if any(signature in lowered for signature in signatures):
                record_signal(
                    tool,
                    "sampled_formula_text",
                    item.get("cell", ""),
                    {
                        "formula_excerpt": formula[:260],
                        "sheet_title": item.get("sheet_title"),
                    },
                )

    tool_findings = []
    for tool in ["supermetrics", "zapier", "apps_script"]:
        signals = evidence.get(tool, [])
        if signals:
            status = "detected"
            confidence = "strong" if any(signal["signal_type"] in {"tab_title", "named_range"} for signal in signals) else "sample_signal"
            message = f"{tool} signals are present in the current metadata or sampled formulas."
        elif tool == "apps_script":
            status = "not_inspected"
            confidence = "unknown"
            message = "Apps Script bindings and triggers require a separate Apps Script/Drive authority path."
        else:
            status = "not_detected_in_current_artifacts"
            confidence = "not_absence_proof"
            message = f"No {tool} signal was found in current metadata or sampled formula artifacts."
        tool_findings.append(
            {
                "tool": tool,
                "status": status,
                "confidence": confidence,
                "message": message,
                "evidence": signals[:20],
            }
        )

    detected = [item["tool"] for item in tool_findings if item["status"] == "detected"]
    if detected:
        overall_status = "review_required"
        message = (
            "Connected automation evidence exists and source freshness/scope must be classified "
            "before promoting full dataflow claims."
        )
    else:
        overall_status = "unknown"
        message = "No connected automation was detected in current artifacts, but Apps Script/admin-level automations were not inspected."

    return {
        "schema_version": 1,
        "stage": "connected_automation_inventory",
        "coverage_status": "metadata_and_sampled_formula_artifacts_only",
        "summary": {
            "overall_status": overall_status,
            "detected_tools": detected,
            "message": message,
            "apps_script_authority": "not_requested",
            "external_automation_authority": "not_available_from_sheets_metadata_alone",
        },
        "tool_findings": tool_findings,
        "authority_gaps": [
            {
                "gap": "apps_script_project_and_trigger_inventory",
                "status": "not_requested",
                "needed_for": "Bound script, custom function, trigger, macro, and add-on execution analysis.",
                "required_path": "Add an inspect.apps_script source evidence operation with Apps Script/Drive authority and redaction limits.",
            },
            {
                "gap": "external_automation_activity_inventory",
                "status": "not_available_from_current_source_evidence",
                "needed_for": "Zapier or other API clients that leave no in-spreadsheet structural trace.",
                "required_path": "Use Drive Activity, Workspace Admin audit/OAuth inventory, or explicit tool-side evidence.",
            },
            {
                "gap": "supermetrics_hidden_query_detail",
                "status": "not_captured",
                "needed_for": "Classifying Supermetrics query targets, refresh scope, freshness, and affected output sheets.",
                "required_path": "Read bounded grid/value windows from the hidden SupermetricsQueries tab when source evidence access is available.",
            },
        ],
        "next_inspections": [
            {
                "operation": "inspect.grid_window",
                "range": "'SupermetricsQueries'!A1:BA80",
                "purpose": "Classify visible Supermetrics query definitions and refresh controls without reading the full hidden tab.",
            },
            {
                "operation": "inspect.values_window",
                "range": "'SupermetricsQueries'!A1:BA80",
                "purpose": "Capture displayed query text and target-sheet labels for deterministic connector scoping.",
            },
        ],
    }


def captured_window_bounds(run_dir: Path, operation: str) -> list[dict[str, Any]]:
    bounds = []
    for _path, payload in load_window_files(run_dir):
        if payload.get("operation") != operation:
            continue
        for window in payload.get("windows", []):
            range_name = window.get("range") or (payload.get("requested_ranges") or [""])[0]
            try:
                parsed = parse_a1_window_bounds(range_name)
            except ValueError:
                continue
            parsed["range"] = range_name
            bounds.append(parsed)
    return bounds


def gate(status: str, gate_id: str, message: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "status": status,
        "message": message,
        "evidence": evidence or {},
    }


def build_region_family_gates(
    run_dir: Path,
    metadata: dict[str, Any],
    region_families: list[dict[str, Any]],
    automation_inventory: dict[str, Any],
) -> dict[str, Any]:
    tab_titles = {tab.get("title") for tab in metadata.get("tabs", []) if isinstance(tab, dict)}
    formula_windows = captured_window_bounds(run_dir, "inspect.formula_window")
    value_windows = captured_window_bounds(run_dir, "inspect.values_window")
    detected_automation = automation_inventory["summary"]["detected_tools"]
    family_gates = []

    for family in region_families:
        gates = []
        bbox = family["output_bbox"]
        source_windows = {item["artifact"] for item in family.get("source_windows", [])}
        in_formula_window = any(bbox_inside_window(bbox, window) for window in formula_windows)
        in_value_window = any(bbox_inside_window(bbox, window) for window in value_windows)
        referenced_sheets = [item["sheet"] for item in family.get("referenced_sheets", [])]
        external_refs = [sheet for sheet in referenced_sheets if sheet != TARGET_SHEET_TITLE]
        unknown_refs = [sheet for sheet in referenced_sheets if sheet not in tab_titles]

        if family["column_block"] == "cols_A_AN" and "formula-window-ML-sales-final-A1-AN453.json" in source_windows:
            gates.append(
                gate(
                    "accepted_sampled",
                    "coverage",
                    "Formula text is covered by the captured full-height A:AN column chunk.",
                    {"coverage_scope": "A1:AN453 full-height chunk"},
                )
            )
        elif in_formula_window:
            gates.append(
                gate(
                    "review_required",
                    "coverage",
                    "Formula text is observed only in sampled row-band or partial windows; more full-height chunks are required.",
                    {"coverage_scope": "sample_slice_only", "source_windows": sorted(source_windows)},
                )
            )
        elif source_windows:
            gates.append(
                gate(
                    "review_required",
                    "coverage",
                    "Formula text exists in sampled artifacts, but the aggregated family bbox is not covered by one complete captured window.",
                    {"coverage_scope": "aggregate_bbox_spans_sample_windows", "source_windows": sorted(source_windows)},
                )
            )
        else:
            gates.append(
                gate(
                    "blocked",
                    "coverage",
                    "Region family is not backed by a captured formula window.",
                    {"source_windows": sorted(source_windows)},
                )
            )

        if unknown_refs:
            gates.append(
                gate(
                    "blocked",
                    "source_sheet_metadata_authority",
                    "One or more referenced sheets are not present in workbook metadata.",
                    {"unknown_referenced_sheets": unknown_refs},
                )
            )
        else:
            gates.append(
                gate(
                    "accepted_sampled",
                    "source_sheet_metadata_authority",
                    "Referenced sheets are present in workbook metadata; this does not validate source freshness or contents.",
                    {"referenced_sheets": referenced_sheets},
                )
            )

        if in_value_window:
            gates.append(
                gate(
                    "accepted_sampled",
                    "formula_result_value_pair",
                    "A matching values window covers this sampled output bbox.",
                    {"output_bbox": bbox},
                )
            )
        else:
            gates.append(
                gate(
                    "review_required",
                    "formula_result_value_pair",
                    "No matching values window covers this sampled output bbox, so formula-result authority is not established.",
                    {"output_bbox": bbox},
                )
            )

        if (
            family["formula_kind"] == "same_sheet_conditional_aggregate"
            and family.get("reference_shapes", {}).get("column_range", 0)
            and TARGET_SHEET_TITLE in referenced_sheets
        ):
            gates.append(
                gate(
                    "review_required",
                    "whole_column_self_reference",
                    "Same-sheet SUMIFS/SUMIF uses whole-column references; source-region intent and circularity risk need inspection.",
                    {"reference_shapes": family.get("reference_shapes", {})},
                )
            )
        else:
            gates.append(
                gate(
                    "accepted_sampled",
                    "whole_column_self_reference",
                    "No sampled same-column whole-column conditional self-reference risk was detected for this family.",
                    {"formula_kind": family["formula_kind"]},
                )
            )

        if detected_automation and external_refs:
            gates.append(
                gate(
                    "review_required",
                    "connected_automation_context",
                    "Connected automation exists in workbook metadata; source refresh scope/freshness is not yet classified.",
                    {"detected_tools": detected_automation, "external_referenced_sheets": external_refs},
                )
            )
        else:
            gates.append(
                gate(
                    "accepted_sampled",
                    "connected_automation_context",
                    "No direct connected-automation review requirement was attached to this sampled family.",
                    {"detected_tools": detected_automation},
                )
            )

        statuses = {item["status"] for item in gates}
        if "blocked" in statuses:
            status = "blocked"
        elif "review_required" in statuses:
            status = "review_required"
        else:
            status = "accepted_sampled"

        family_gates.append(
            {
                "region_family_id": family["region_family_id"],
                "formula_kind": family["formula_kind"],
                "primary_function": family["primary_function"],
                "formula_count": family["formula_count"],
                "output_bbox": bbox,
                "referenced_sheets": referenced_sheets,
                "status": status,
                "gates": gates,
            }
        )

    status_counts = Counter(item["status"] for item in family_gates)
    gate_status_counts = Counter(
        f"{gate_item['gate_id']}:{gate_item['status']}"
        for item in family_gates
        for gate_item in item["gates"]
    )
    return {
        "schema_version": 1,
        "stage": "region_family_gate_tuning",
        "coverage_status": "sampled_partial",
        "gate_summary": {
            "overall_status": "review_required" if status_counts.get("review_required") or status_counts.get("blocked") else "accepted_sampled",
            "region_family_status_counts": dict(status_counts),
            "gate_status_counts": dict(gate_status_counts),
            "formula_window_count": len(formula_windows),
            "value_window_count": len(value_windows),
        },
        "region_family_gates": family_gates,
    }


def build_pipeline_gates(
    pipeline_package: dict[str, Any],
    region_gate_package: dict[str, Any],
    automation_inventory: dict[str, Any],
) -> dict[str, Any]:
    family_gates_by_id = {
        item["region_family_id"]: item for item in region_gate_package["region_family_gates"]
    }
    detected_automation = automation_inventory["summary"]["detected_tools"]
    pipeline_gates = []

    for candidate in pipeline_package["pipeline_candidates"]:
        linked_families = [
            family_gates_by_id[family_id]
            for family_id in candidate.get("region_family_ids", [])
            if family_id in family_gates_by_id
        ]
        family_status_counts = Counter(item["status"] for item in linked_families)
        gates = []
        if family_status_counts.get("blocked"):
            gates.append(
                gate(
                    "blocked",
                    "region_family_gate_rollup",
                    "At least one linked region family is blocked.",
                    {"family_status_counts": dict(family_status_counts)},
                )
            )
        elif family_status_counts.get("review_required"):
            gates.append(
                gate(
                    "review_required",
                    "region_family_gate_rollup",
                    "One or more linked region families require review before pipeline promotion.",
                    {"family_status_counts": dict(family_status_counts)},
                )
            )
        else:
            gates.append(
                gate(
                    "accepted_sampled",
                    "region_family_gate_rollup",
                    "Linked sampled region families passed current gates.",
                    {"family_status_counts": dict(family_status_counts)},
                )
            )

        if detected_automation and candidate["source"]["sheet"] != TARGET_SHEET_TITLE:
            gates.append(
                gate(
                    "review_required",
                    "source_refresh_context",
                    "Workbook has connected automation evidence; source-sheet refresh scope/freshness is not yet classified.",
                    {"detected_tools": detected_automation, "source_sheet": candidate["source"]["sheet"]},
                )
            )
        else:
            gates.append(
                gate(
                    "accepted_sampled",
                    "source_refresh_context",
                    "No source-level connected-automation gate was triggered for this sampled pipeline candidate.",
                    {"source_sheet": candidate["source"]["sheet"]},
                )
            )

        statuses = {item["status"] for item in gates}
        if "blocked" in statuses:
            status = "blocked"
        elif "review_required" in statuses:
            status = "review_required"
        else:
            status = "accepted_sampled"

        pipeline_gates.append(
            {
                "pipeline_candidate_id": candidate["pipeline_candidate_id"],
                "source": candidate["source"],
                "formula_kind": candidate["formula_kind"],
                "formula_count": candidate["formula_count"],
                "family_count": candidate["family_count"],
                "status": status,
                "gates": gates,
                "linked_region_family_ids": candidate.get("region_family_ids", []),
            }
        )

    status_counts = Counter(item["status"] for item in pipeline_gates)
    return {
        "schema_version": 1,
        "stage": "table_io_pipeline_gate_tuning",
        "coverage_status": "sampled_partial",
        "gate_summary": {
            "overall_status": "review_required" if status_counts.get("review_required") or status_counts.get("blocked") else "accepted_sampled",
            "pipeline_status_counts": dict(status_counts),
        },
        "pipeline_gates": pipeline_gates,
    }


def escape_mermaid(value: Any) -> str:
    return str(value).replace('"', "'")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_html(
    run_dir: Path,
    summary: dict[str, Any],
    pattern_groups: list[dict[str, Any]],
    region_families: list[dict[str, Any]],
    graph: dict[str, Any],
    pipeline_package: dict[str, Any],
    automation_inventory: dict[str, Any],
    region_gate_package: dict[str, Any],
    pipeline_gate_package: dict[str, Any],
) -> None:
    def status_class(status: str) -> str:
        if status in {"detected", "review_required"}:
            return "status-review"
        if status in {"blocked", "not_inspected"}:
            return "status-blocked"
        if status.startswith("accepted"):
            return "status-accepted"
        return "status-muted"

    top_groups = pattern_groups[:20]
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(group['pattern_group_id'])}</td>"
        f"<td>{group['formula_count']}</td>"
        f"<td>{html.escape(group['output_bbox']['start_cell'])}:{html.escape(group['output_bbox']['end_cell'])}</td>"
        f"<td>{html.escape(', '.join(ref['sheet'] for ref in group['referenced_sheets'][:4]))}</td>"
        f"<td><code>{html.escape(group['sample_formula'][:220])}</code></td>"
        "</tr>"
        for group in top_groups
    )
    window_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(item['artifact'])}</td>"
        f"<td>{html.escape(item['operation'])}</td>"
        f"<td>{html.escape(item['range'])}</td>"
        f"<td>{item['formula_cells']}</td>"
        f"<td>{item['nonempty_cells']}</td>"
        "</tr>"
        for item in summary["window_summaries"]
    )
    family_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(family['region_family_id'])}</td>"
        f"<td>{family['formula_count']}</td>"
        f"<td>{html.escape(family['formula_kind'])}</td>"
        f"<td>{html.escape(family['row_band'])}</td>"
        f"<td>{html.escape(family['column_block'])}</td>"
        f"<td>{html.escape(family['output_bbox']['start_cell'])}:{html.escape(family['output_bbox']['end_cell'])}</td>"
        f"<td>{html.escape(', '.join(ref['sheet'] for ref in family['referenced_sheets'][:4]))}</td>"
        f"<td><code>{html.escape((family['sample_formulas'] or [''])[0][:220])}</code></td>"
        "</tr>"
        for family in region_families[:30]
    )
    pipeline_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(candidate['pipeline_candidate_id'])}</td>"
        f"<td>{html.escape(candidate['source']['sheet'])}</td>"
        f"<td>{html.escape(candidate['formula_kind'])}</td>"
        f"<td>{candidate['family_count']}</td>"
        f"<td>{candidate['formula_count']}</td>"
        f"<td>{html.escape(candidate['status'])}</td>"
        "</tr>"
        for candidate in pipeline_package["pipeline_candidates"][:30]
    )
    automation_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(item['tool'])}</td>"
        f"<td><span class=\"pill {status_class(item['status'])}\">{html.escape(item['status'])}</span></td>"
        f"<td>{html.escape(item['confidence'])}</td>"
        f"<td>{html.escape(item['message'])}</td>"
        f"<td>{html.escape('; '.join(signal['signal_type'] + ': ' + signal['label'] for signal in item['evidence'][:8]))}</td>"
        "</tr>"
        for item in automation_inventory["tool_findings"]
    )
    authority_gap_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(item['gap'])}</td>"
        f"<td><span class=\"pill {status_class(item['status'])}\">{html.escape(item['status'])}</span></td>"
        f"<td>{html.escape(item['needed_for'])}</td>"
        f"<td>{html.escape(item['required_path'])}</td>"
        "</tr>"
        for item in automation_inventory["authority_gaps"]
    )
    pipeline_gate_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(item['pipeline_candidate_id'])}</td>"
        f"<td>{html.escape(item['source']['sheet'])}</td>"
        f"<td>{html.escape(item['formula_kind'])}</td>"
        f"<td>{item['formula_count']}</td>"
        f"<td><span class=\"pill {status_class(item['status'])}\">{html.escape(item['status'])}</span></td>"
        f"<td>{html.escape('; '.join(gate_item['gate_id'] + '=' + gate_item['status'] for gate_item in item['gates']))}</td>"
        "</tr>"
        for item in pipeline_gate_package["pipeline_gates"][:30]
    )
    region_gate_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(item['region_family_id'])}</td>"
        f"<td>{html.escape(item['formula_kind'])}</td>"
        f"<td>{item['formula_count']}</td>"
        f"<td>{html.escape(item['output_bbox']['start_cell'])}:{html.escape(item['output_bbox']['end_cell'])}</td>"
        f"<td><span class=\"pill {status_class(item['status'])}\">{html.escape(item['status'])}</span></td>"
        f"<td>{html.escape('; '.join(gate_item['gate_id'] + '=' + gate_item['status'] for gate_item in item['gates']))}</td>"
        "</tr>"
        for item in region_gate_package["region_family_gates"][:30]
    )
    html_text = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Formula Dataflow Discovery</title>
  <script type="module">import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs'; mermaid.initialize({{ startOnLoad: true }});</script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #1f2937; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0 28px; font-size: 13px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; vertical-align: top; }}
    th {{ background: #f3f4f6; text-align: left; }}
    code {{ white-space: pre-wrap; word-break: break-word; }}
    .metric {{ display: inline-block; border: 1px solid #d1d5db; padding: 10px 12px; margin: 4px; border-radius: 6px; background: #fafafa; }}
    .note {{ color: #6b7280; }}
    .pill {{ display: inline-block; border-radius: 999px; padding: 2px 8px; font-size: 12px; border: 1px solid #d1d5db; background: #f9fafb; }}
    .status-accepted {{ background: #ecfdf5; border-color: #a7f3d0; color: #065f46; }}
    .status-review {{ background: #fffbeb; border-color: #fde68a; color: #92400e; }}
    .status-blocked {{ background: #fef2f2; border-color: #fecaca; color: #991b1b; }}
    .status-muted {{ background: #f3f4f6; border-color: #d1d5db; color: #4b5563; }}
  </style>
</head>
<body>
  <h1>Formula Dataflow Discovery</h1>
  <p class="note">Sampled windows only. This is candidate evidence, not full-sheet truth. Business metric basis: 결제액/payment amount, not accounting revenue.</p>
  <section>
    <h2>Summary</h2>
    <div class="metric">Metric basis: {html.escape(summary['metric_basis']['korean_label'])}</div>
    <div class="metric">Formula cells: {summary['formula_cell_count']}</div>
    <div class="metric">Reference edges: {summary['reference_edge_count']}</div>
    <div class="metric">Pattern groups: {summary['pattern_group_count']}</div>
    <div class="metric">Region families: {summary['region_family_count']}</div>
    <div class="metric">Pipeline candidates: {summary['pipeline_candidate_count']}</div>
    <div class="metric">Automation status: {html.escape(automation_inventory['summary']['overall_status'])}</div>
    <div class="metric">Pipeline gate status: {html.escape(pipeline_gate_package['gate_summary']['overall_status'])}</div>
    <div class="metric">Sampled windows: {len(summary['window_summaries'])}</div>
  </section>
  <section>
    <h2>Metric Basis</h2>
    <p class="note">{html.escape(summary['metric_basis']['source_label_warning'])}</p>
  </section>
  <section>
    <h2>Connected Automation Inventory</h2>
    <p class="note">{html.escape(automation_inventory['summary']['message'])}</p>
    <table><thead><tr><th>Tool</th><th>Status</th><th>Confidence</th><th>Message</th><th>Evidence</th></tr></thead><tbody>{automation_rows}</tbody></table>
    <table><thead><tr><th>Authority gap</th><th>Status</th><th>Needed for</th><th>Required path</th></tr></thead><tbody>{authority_gap_rows}</tbody></table>
  </section>
  <section>
    <h2>Windows</h2>
    <table><thead><tr><th>Artifact</th><th>Operation</th><th>Range</th><th>Formula cells</th><th>Non-empty</th></tr></thead><tbody>{window_rows}</tbody></table>
  </section>
  <section>
    <h2>Dataflow Graph</h2>
    <pre class="mermaid">{html.escape(graph['mermaid'])}</pre>
  </section>
  <section>
    <h2>Pipeline Candidates</h2>
    <pre class="mermaid">{html.escape(pipeline_package['mermaid'])}</pre>
    <table><thead><tr><th>Pipeline</th><th>Source</th><th>Formula kind</th><th>Families</th><th>Formulas</th><th>Status</th></tr></thead><tbody>{pipeline_rows}</tbody></table>
  </section>
  <section>
    <h2>Pipeline Gates</h2>
    <table><thead><tr><th>Pipeline</th><th>Source</th><th>Formula kind</th><th>Formulas</th><th>Status</th><th>Gate rollup</th></tr></thead><tbody>{pipeline_gate_rows}</tbody></table>
  </section>
  <section>
    <h2>Region Family Gates</h2>
    <table><thead><tr><th>Family</th><th>Kind</th><th>Formulas</th><th>Output bbox</th><th>Status</th><th>Gate rollup</th></tr></thead><tbody>{region_gate_rows}</tbody></table>
  </section>
  <section>
    <h2>Region Families</h2>
    <table><thead><tr><th>Family</th><th>Count</th><th>Kind</th><th>Row band</th><th>Column block</th><th>Output bbox</th><th>Referenced sheets</th><th>Sample formula</th></tr></thead><tbody>{family_rows}</tbody></table>
  </section>
  <section>
    <h2>Top Pattern Groups</h2>
    <table><thead><tr><th>Group</th><th>Count</th><th>Output bbox</th><th>Referenced sheets</th><th>Sample formula</th></tr></thead><tbody>{rows}</tbody></table>
  </section>
</body>
</html>
"""
    (run_dir / "index.html").write_text(html_text, encoding="utf-8")


def build(run_dir: Path, sheet_title: str) -> dict[str, Any]:
    inventory, references, window_summaries = collect_formula_inventory(run_dir, sheet_title)
    pattern_groups = build_pattern_groups(inventory, references)
    region_families = build_region_families(inventory, references)
    pipeline_package = build_table_pipeline_candidates(region_families)
    metadata = load_metadata_payload(run_dir)
    automation_inventory = build_connected_automation_inventory(metadata, inventory)
    region_gate_package = build_region_family_gates(run_dir, metadata, region_families, automation_inventory)
    pipeline_gate_package = build_pipeline_gates(pipeline_package, region_gate_package, automation_inventory)
    graph = build_region_graph(pattern_groups, references)
    generated_at = datetime.now(timezone.utc).astimezone().isoformat()
    summary = {
        "schema_version": 1,
        "generated_at": generated_at,
        "stage": "formula_dataflow_discovery_sampled",
        "spreadsheet_id": "16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg",
        "sheet_title": sheet_title,
        "formula_cell_count": len(inventory),
        "reference_edge_count": len(references),
        "pattern_group_count": len(pattern_groups),
        "region_family_count": len(region_families),
        "pipeline_candidate_count": len(pipeline_package["pipeline_candidates"]),
        "window_summaries": window_summaries,
        "coverage_status": "sampled_partial",
        "coverage_note": "Includes captured windows only; the 1,848-column sheet still needs additional full-height chunks for complete inventory.",
        "metric_basis": METRIC_BASIS,
    }
    write_json(run_dir / "formula-inventory-ML-sales-final-sampled.json", {"summary": summary, "formulas": inventory})
    write_json(run_dir / "formula-reference-edges-ML-sales-final-sampled.json", {"summary": summary, "references": references})
    write_json(run_dir / "formula-pattern-groups-ML-sales-final-sampled.json", {"summary": summary, "pattern_groups": pattern_groups})
    write_json(run_dir / "region-families-ML-sales-final-sampled.json", {"summary": summary, "region_families": region_families})
    write_json(run_dir / "table-io-pipeline-candidates-ML-sales-final-sampled.json", {"summary": summary, **pipeline_package})
    write_json(run_dir / "connected-automation-inventory-ML-sales-final-sampled.json", automation_inventory)
    write_json(run_dir / "region-family-gates-ML-sales-final-sampled.json", region_gate_package)
    write_json(run_dir / "table-io-pipeline-gates-ML-sales-final-sampled.json", pipeline_gate_package)
    write_json(run_dir / "region-dataflow-graph-ML-sales-final-sampled.json", {"summary": summary, **graph})
    write_json(
        run_dir / "formula-dataflow-review-summary-ML-sales-final-sampled.json",
        build_review_summary(
            summary,
            inventory,
            references,
            pattern_groups,
            region_families,
            pipeline_package,
            automation_inventory,
            region_gate_package,
            pipeline_gate_package,
        ),
    )
    render_html(
        run_dir,
        summary,
        pattern_groups,
        region_families,
        graph,
        pipeline_package,
        automation_inventory,
        region_gate_package,
        pipeline_gate_package,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build sampled Google Sheets formula dataflow artifacts.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--sheet-title", default="[ML] 매출_최종")
    args = parser.parse_args()
    summary = build(args.run_dir, args.sheet_title)
    print(json.dumps({k: summary[k] for k in ["formula_cell_count", "reference_edge_count", "pattern_group_count", "region_family_count", "pipeline_candidate_count", "coverage_status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
