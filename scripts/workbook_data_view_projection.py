from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"


def build_data_view_projection(
    *,
    validated_document_graph_path: Path,
    readonly_sample_path: Path,
) -> dict[str, Any]:
    validated_document_graph_path = validated_document_graph_path.expanduser().resolve()
    readonly_sample_path = readonly_sample_path.expanduser().resolve()
    graph_package = _read_json(validated_document_graph_path)
    readonly_sample = _read_json(readonly_sample_path)

    sample_index = _sample_index(readonly_sample)
    semantic_context = _semantic_context_by_data_view(graph_package)
    object_index = _object_index(graph_package)

    projections = []
    for view in graph_package.get("graph", {}).get("data_views", []):
        projection = _project_data_view(
            view,
            sample_index=sample_index,
            semantic_context=semantic_context.get(view["id"], {}),
            related_objects=object_index.get((view.get("sheet"), view.get("range")), []),
        )
        projections.append(projection)

    document_objects = _project_document_objects(graph_package)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "validated_document_graph": str(validated_document_graph_path),
            "readonly_sample": str(readonly_sample_path),
        },
        "method": {
            "name": "deterministic_data_view_projection",
            "authority": "validated_graph_projection_not_excel_recalculation",
            "decision_policy": (
                "Project accepted data views and accepted document objects from the validated "
                "graph into reviewable table, pivot, text, image, summary, and formula-preview "
                "surfaces. Formula text is preserved as evidence but formula results are not "
                "treated as recalculated authority."
            ),
        },
        "data_view_projections": sorted(projections, key=lambda item: item["id"]),
        "document_object_projections": sorted(document_objects, key=lambda item: item["id"]),
        "carry_forward": graph_package.get("carry_forward", {}),
        "summary": _summary(projections, document_objects, graph_package),
        "parser_observations": _parser_observations(projections, document_objects, graph_package),
    }


def _project_data_view(
    view: dict[str, Any],
    *,
    sample_index: dict[str, dict[int, dict[str, Any]]],
    semantic_context: dict[str, Any],
    related_objects: list[dict[str, Any]],
) -> dict[str, Any]:
    bounds = _parse_range(view.get("range"))
    preview = _preview_rows(
        sheet=view.get("sheet"),
        bounds=bounds,
        sample_index=sample_index,
    )
    metrics = _preview_metrics(preview)
    warnings = []
    if preview["status"] == "not_sampled":
        warnings.append("no_readonly_sample_rows_for_view_range")
    if metrics["formula_cell_count"]:
        warnings.append("formula_text_only_not_recalculated_result")
    return {
        "id": f"projection:{view['id']}",
        "type": "data_view_projection",
        "projection_kind": _projection_kind(view),
        "data_view_id": view["id"],
        "view_kind": view.get("view_kind"),
        "role": view.get("role"),
        "sheet": view.get("sheet"),
        "range": view.get("range"),
        "semantic_context": semantic_context or {
            "semantic_concept_ids": [],
            "semantic_labels": [],
            "accepted_aliases": [],
        },
        "related_object_ids": [item["id"] for item in related_objects],
        "preview": preview,
        "metrics": metrics,
        "formula_policy": {
            "formula_text_is_evidence_only": True,
            "excel_recalculation_required_for_formula_results": bool(metrics["formula_cell_count"]),
        },
        "warnings": warnings,
        "evidence_refs": view.get("evidence_refs", []),
        "source_artifact_refs": view.get("source_artifact_refs", []) + [
            "validated_document_graph",
            "readonly_sample",
        ],
    }


def _project_document_objects(graph_package: dict[str, Any]) -> list[dict[str, Any]]:
    object_types = {
        "ImageBlock": "image_ref",
        "TextRegion": "text_block",
        "RowBandBlock": "row_band",
        "PivotTableBlock": "pivot_table_block",
        "PivotTableValueRegion": "pivot_value_region",
    }
    projections = []
    for node in graph_package.get("graph", {}).get("nodes", []):
        ontology_class = node.get("ontology_class")
        if ontology_class not in object_types:
            continue
        projections.append(
            {
                "id": f"object_projection:{node['id']}",
                "type": "document_object_projection",
                "object_kind": object_types[ontology_class],
                "source_node_id": node["id"],
                "label": node.get("label"),
                "sheet": node.get("sheet"),
                "range": node.get("range"),
                "properties": node.get("properties", {}),
                "evidence_refs": node.get("evidence_refs", []),
                "source_artifact_refs": node.get("source_artifact_refs", []) + [
                    "validated_document_graph"
                ],
            }
        )
    return projections


def _semantic_context_by_data_view(
    graph_package: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    concepts = {
        node["id"]: node
        for node in graph_package.get("graph", {}).get("nodes", [])
        if node.get("type") == "semantic_concept"
    }
    aliases_by_concept: dict[str, list[str]] = defaultdict(list)
    for alias in graph_package.get("graph", {}).get("semantic_aliases", []):
        aliases_by_concept[alias.get("canonical_concept_id")].append(alias.get("alias"))

    context: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "semantic_concept_ids": [],
            "semantic_labels": [],
            "accepted_aliases": [],
        }
    )
    for concept_id, concept in concepts.items():
        data_view_ids = concept.get("properties", {}).get("data_view_ids", [])
        for data_view_id in data_view_ids:
            context[data_view_id]["semantic_concept_ids"].append(concept_id)
            context[data_view_id]["semantic_labels"].append(concept.get("label"))
            context[data_view_id]["accepted_aliases"].extend(aliases_by_concept.get(concept_id, []))
    return {
        data_view_id: {
            "semantic_concept_ids": _unique(values["semantic_concept_ids"]),
            "semantic_labels": _unique(values["semantic_labels"]),
            "accepted_aliases": _unique(values["accepted_aliases"]),
        }
        for data_view_id, values in context.items()
    }


def _object_index(graph_package: dict[str, Any]) -> dict[tuple[str | None, str | None], list[dict[str, Any]]]:
    index: dict[tuple[str | None, str | None], list[dict[str, Any]]] = defaultdict(list)
    for node in graph_package.get("graph", {}).get("nodes", []):
        if node.get("type") in {"document_block", "cell_region"} and node.get("range"):
            index[(node.get("sheet"), node.get("range"))].append(node)
    return index


def _sample_index(readonly_sample: dict[str, Any]) -> dict[str, dict[int, dict[str, Any]]]:
    index: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for sheet in readonly_sample.get("sheets", []):
        for window in sheet.get("windows", []):
            for row in window.get("rows", []):
                index[sheet["name"]][int(row["row"])] = row
    return index


def _preview_rows(
    *,
    sheet: str | None,
    bounds: dict[str, int] | None,
    sample_index: dict[str, dict[int, dict[str, Any]]],
    max_rows: int = 12,
    max_cells_per_row: int = 16,
) -> dict[str, Any]:
    if not sheet or not bounds:
        return {"status": "not_sampled", "rows": [], "sampled_row_count": 0}
    sheet_rows = sample_index.get(sheet, {})
    rows = []
    for row_number in range(bounds["min_row"], bounds["max_row"] + 1):
        row = sheet_rows.get(row_number)
        if not row:
            continue
        cells = [
            cell
            for cell in row.get("cells", [])
            if bounds["min_column"] <= int(cell["column"]) <= bounds["max_column"]
        ][:max_cells_per_row]
        if cells or rows:
            rows.append(
                {
                    "row": row_number,
                    "cells": [
                        {
                            "cell": cell.get("cell"),
                            "column": cell.get("column"),
                            "value_type": cell.get("value_type"),
                            "value_preview": cell.get("value_preview"),
                            "formula": cell.get("formula"),
                        }
                        for cell in cells
                    ],
                }
            )
        if len(rows) >= max_rows:
            break
    if not rows:
        return {"status": "not_sampled", "rows": [], "sampled_row_count": 0}
    sampled_row_count = len(rows)
    full_span = bounds["max_row"] - bounds["min_row"] + 1
    status = "sampled" if sampled_row_count >= min(full_span, max_rows) else "partial"
    return {
        "status": status,
        "rows": rows,
        "sampled_row_count": sampled_row_count,
        "range_row_span": full_span,
        "range_column_span": bounds["max_column"] - bounds["min_column"] + 1,
    }


def _preview_metrics(preview: dict[str, Any]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in preview.get("rows", []):
        for cell in row.get("cells", []):
            value_type = cell.get("value_type") or "unknown"
            counter[value_type] += 1
            if cell.get("formula"):
                counter["formula_cell_count"] += 1
    return {
        "sampled_row_count": int(preview.get("sampled_row_count") or 0),
        "sampled_cell_count": sum(count for key, count in counter.items() if key != "formula_cell_count"),
        "formula_cell_count": max(
            counter.get("formula", 0),
            counter.get("formula_cell_count", 0),
        ),
        "number_cell_count": counter.get("number", 0),
        "string_cell_count": counter.get("string", 0),
        "datetime_cell_count": counter.get("datetime", 0),
    }


def _projection_kind(view: dict[str, Any]) -> str:
    view_kind = view.get("view_kind")
    if view_kind == "pivot_report_view":
        return "pivot_view_projection"
    if view_kind == "formula_summary_view":
        return "formula_summary_projection"
    if view_kind == "formula_transform_view":
        return "formula_transform_projection"
    return "table_view_projection"


def _parse_range(range_text: str | None) -> dict[str, int] | None:
    if not range_text:
        return None
    match = re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", range_text)
    if not match:
        match = re.fullmatch(r"([A-Z]+)(\d+)", range_text)
        if not match:
            return None
        col, row = match.groups()
        return {
            "min_row": int(row),
            "max_row": int(row),
            "min_column": _column_index(col),
            "max_column": _column_index(col),
        }
    start_col, start_row, end_col, end_row = match.groups()
    return {
        "min_row": min(int(start_row), int(end_row)),
        "max_row": max(int(start_row), int(end_row)),
        "min_column": min(_column_index(start_col), _column_index(end_col)),
        "max_column": max(_column_index(start_col), _column_index(end_col)),
    }


def _column_index(column: str) -> int:
    result = 0
    for char in column:
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result


def _summary(
    projections: list[dict[str, Any]],
    document_objects: list[dict[str, Any]],
    graph_package: dict[str, Any],
) -> dict[str, Any]:
    kinds = Counter(item["projection_kind"] for item in projections)
    preview_statuses = Counter(item["preview"]["status"] for item in projections)
    object_kinds = Counter(item["object_kind"] for item in document_objects)
    return {
        "data_view_projection_count": len(projections),
        "pivot_view_projection_count": kinds.get("pivot_view_projection", 0),
        "formula_summary_projection_count": kinds.get("formula_summary_projection", 0),
        "formula_transform_projection_count": kinds.get("formula_transform_projection", 0),
        "sampled_projection_count": preview_statuses.get("sampled", 0),
        "partial_projection_count": preview_statuses.get("partial", 0),
        "not_sampled_projection_count": preview_statuses.get("not_sampled", 0),
        "document_object_projection_count": len(document_objects),
        "image_ref_projection_count": object_kinds.get("image_ref", 0),
        "pivot_object_projection_count": object_kinds.get("pivot_table_block", 0),
        "row_band_projection_count": object_kinds.get("row_band", 0),
        "carry_forward_document_review_count": len(
            graph_package.get("carry_forward", {}).get("document_review_queue", [])
        ),
        "carry_forward_proposal_review_count": len(
            graph_package.get("carry_forward", {}).get("proposal_review_queue", [])
        ),
        "projection_status": "projected_with_carry_forward_warnings",
    }


def _parser_observations(
    projections: list[dict[str, Any]],
    document_objects: list[dict[str, Any]],
    graph_package: dict[str, Any],
) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": f"Projected {len(projections)} accepted data views and {len(document_objects)} accepted document objects.",
        }
    ]
    formula_count = sum(item["metrics"]["formula_cell_count"] for item in projections)
    if formula_count:
        observations.append(
            {
                "level": "warning",
                "message": f"{formula_count} sampled formula cells are shown as formula text only; Excel recalculation is still required for formula-result authority.",
            }
        )
    carry_forward = graph_package.get("carry_forward", {})
    if carry_forward.get("proposal_review_queue") or carry_forward.get("document_review_queue"):
        observations.append(
            {
                "level": "warning",
                "message": "Carry-forward review and quarantine queues remain attached to the projection output.",
            }
        )
    return observations


def _unique(values: list[Any]) -> list[Any]:
    seen = set()
    out = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Project accepted data views from a validated workbook document graph."
    )
    parser.add_argument("--validated-document-graph", type=Path, required=True)
    parser.add_argument("--readonly-sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    projection = build_data_view_projection(
        validated_document_graph_path=args.validated_document_graph,
        readonly_sample_path=args.readonly_sample,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(projection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
