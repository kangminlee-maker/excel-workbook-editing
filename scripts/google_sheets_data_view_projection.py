from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_data_view_projection(
    *,
    live_validated_document_graph_path: Path,
    live_evidence_package_path: Path,
    top_left_sample_path: Path,
) -> dict[str, Any]:
    live_validated_document_graph_path = live_validated_document_graph_path.expanduser().resolve()
    live_evidence_package_path = live_evidence_package_path.expanduser().resolve()
    top_left_sample_path = top_left_sample_path.expanduser().resolve()

    graph = _read_json(live_validated_document_graph_path)
    evidence = _read_json(live_evidence_package_path)
    top_left_sample = _read_json(top_left_sample_path)
    pipeline_index = {
        pipeline["id"]: pipeline
        for pipeline in evidence["accepted_evidence"].get("pipelines", [])
    }
    sample_index = {
        tab["title"]: tab
        for tab in top_left_sample.get("tabs", [])
    }
    projections = []
    for node in graph["graph"]["nodes"]:
        if node["type"] == "calculation_pipeline":
            pipeline = pipeline_index.get(node["properties"].get("pipeline_id"))
            if pipeline:
                projections.append(_pipeline_projection(node, pipeline, sample_index))
        elif node["type"] in {"workbook_document", "accepted_evidence_body"}:
            projections.append(_summary_projection(node))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": graph["source"]["spreadsheet_id"],
            "spreadsheet_url": graph["source"].get("spreadsheet_url"),
            "title": graph["source"]["title"],
            "source_artifacts": {
                "live_validated_document_graph": str(live_validated_document_graph_path),
                "live_evidence_package": str(live_evidence_package_path),
                "top_left_sample": str(top_left_sample_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "projection_status": "read_model_projection_only",
            "formula_result_authority": "not_established",
            "semantic_review_resolution": "not_performed",
            "shared_ontology_updates": 0,
        },
        "method": {
            "name": "connected_sheets_data_view_projection",
            "authority": "validated_graph_projection_not_formula_recalculation",
            "decision_policy": (
                "Project accepted graph nodes into reviewer-facing data views. Preserve formula "
                "text and sampled displays as evidence only; do not recalculate formulas, resolve "
                "carry-forward queues, or promote semantic ontology updates."
            ),
        },
        "data_view_projections": sorted(projections, key=lambda item: item["id"]),
        "carry_forward": graph["carry_forward"],
        "summary": _summary(projections, graph),
        "parser_observations": _parser_observations(projections, graph),
    }


def write_google_sheets_data_view_projection_package(
    *,
    out_dir: Path,
    access_preflight_path: Path,
    live_manifest_path: Path,
    live_view_formula_profile_path: Path,
    live_block_candidates_path: Path,
    bounded_window_sample_path: Path,
    live_block_candidate_tuning_path: Path,
    live_table_io_pipelines_path: Path,
    live_cross_validation_plan_path: Path,
    live_validation_batch_execution_path: Path,
    live_gate_execution_path: Path,
    live_evidence_package_path: Path,
    live_document_ontology_mapping_path: Path,
    live_action_contracts_path: Path,
    live_domain_source_model_path: Path,
    live_semantic_proposals_path: Path,
    live_semantic_proposal_validation_path: Path,
    live_validated_document_graph_path: Path,
    data_view_projection: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    projection_path = out_dir / "live-data-view-projection.json"
    projection_path.write_text(
        json.dumps(data_view_projection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "index.html").write_text(
        render_live_manifest_html(
            access_preflight=_read_json(access_preflight_path),
            manifest=_read_json(live_manifest_path),
            live_view_formula_profile=_read_json(live_view_formula_profile_path),
            live_block_candidates=_read_json(live_block_candidates_path),
            live_bounded_window_sample=_read_json(bounded_window_sample_path),
            live_block_candidate_tuning=_read_json(live_block_candidate_tuning_path),
            live_table_io_pipelines=_read_json(live_table_io_pipelines_path),
            live_cross_validation_plan=_read_json(live_cross_validation_plan_path),
            live_validation_batch_execution=_read_json(live_validation_batch_execution_path),
            live_gate_execution=_read_json(live_gate_execution_path),
            live_evidence_package=_read_json(live_evidence_package_path),
            live_document_ontology_mapping=_read_json(live_document_ontology_mapping_path),
            live_action_contracts=_read_json(live_action_contracts_path),
            live_domain_source_model=_read_json(live_domain_source_model_path),
            live_semantic_proposals=_read_json(live_semantic_proposals_path),
            live_semantic_proposal_validation=_read_json(live_semantic_proposal_validation_path),
            live_validated_document_graph=_read_json(live_validated_document_graph_path),
            live_data_view_projection=data_view_projection,
        ),
        encoding="utf-8",
    )


def _pipeline_projection(
    node: dict[str, Any],
    pipeline: dict[str, Any],
    sample_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    output_ref = pipeline["output_refs"][0] if pipeline.get("output_refs") else {}
    input_ref = pipeline["input_refs"][0] if pipeline.get("input_refs") else {}
    transform = pipeline["transform_refs"][0] if pipeline.get("transform_refs") else {}
    preview = _sample_preview(output_ref, sample_index)
    warnings = ["formula_text_only_not_recalculated_result"]
    if preview["status"] == "not_sampled":
        warnings.append("top_left_sample_does_not_cover_output_range")
    if pipeline.get("review_flags"):
        warnings.extend(pipeline["review_flags"])
    return {
        "id": f"projection_{node['id']}",
        "type": "data_view_projection",
        "projection_kind": "calculation_pipeline_projection",
        "source_node_id": node["id"],
        "pipeline_id": pipeline["id"],
        "label": node.get("label"),
        "role": pipeline.get("role"),
        "sheet": output_ref.get("sheet"),
        "range": output_ref.get("range"),
        "input_refs": _ref_summaries(pipeline.get("input_refs", [])),
        "output_refs": _ref_summaries(pipeline.get("output_refs", [])),
        "transform_summary": {
            "kind": transform.get("kind"),
            "formula_count": transform.get("formula_count", 0),
            "signature_group_count": len(transform.get("signature_group_ids", [])),
            "repeated_formula_family": bool(transform.get("repeated_formula_family")),
        },
        "preview": preview,
        "formula_policy": {
            "formula_text_is_evidence_only": True,
            "formula_result_authority": "not_established",
            "recalculation_not_performed": True,
        },
        "warnings": _unique(warnings),
        "evidence_refs": _unique([*node.get("evidence_refs", []), *pipeline.get("evidence_refs", [])]),
    }


def _summary_projection(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"projection_{node['id']}",
        "type": "data_view_projection",
        "projection_kind": "document_summary_projection",
        "source_node_id": node["id"],
        "pipeline_id": None,
        "label": node.get("label"),
        "role": node["type"],
        "sheet": None,
        "range": None,
        "input_refs": [],
        "output_refs": [],
        "transform_summary": {},
        "preview": {
            "status": "metadata_only",
            "rows": [],
            "sampled_row_count": 0,
            "sampled_formula_cell_count": 0,
        },
        "formula_policy": {
            "formula_text_is_evidence_only": True,
            "formula_result_authority": "not_established",
            "recalculation_not_performed": True,
        },
        "warnings": [],
        "evidence_refs": node.get("evidence_refs", []),
    }


def _sample_preview(
    ref: dict[str, Any],
    sample_index: dict[str, dict[str, Any]],
    *,
    max_rows: int = 8,
    max_columns: int = 12,
) -> dict[str, Any]:
    sheet = ref.get("sheet")
    bounds = ref.get("bounds") or _bounds_from_a1(ref.get("range"))
    tab = sample_index.get(sheet or "")
    if not tab or not bounds:
        return {
            "status": "not_sampled",
            "rows": [],
            "sampled_row_count": 0,
            "sampled_formula_cell_count": 0,
        }
    display_rows = tab.get("display_rows", [])
    formula_rows = tab.get("formula_rows", [])
    rows = []
    formula_count = 0
    for row_number in range(bounds["start_row"], min(bounds["end_row"], len(display_rows)) + 1):
        display_row = display_rows[row_number - 1] if row_number - 1 < len(display_rows) else []
        formula_row = formula_rows[row_number - 1] if row_number - 1 < len(formula_rows) else []
        cells = []
        for col_number in range(bounds["start_column"], bounds["end_column"] + 1):
            display_value = display_row[col_number - 1] if col_number - 1 < len(display_row) else ""
            formula_value = formula_row[col_number - 1] if col_number - 1 < len(formula_row) else ""
            if display_value == "" and formula_value == "":
                continue
            has_formula = isinstance(formula_value, str) and formula_value.startswith("=")
            formula_count += int(has_formula)
            cells.append(
                {
                    "column": col_number,
                    "display": display_value,
                    "formula": formula_value if has_formula else None,
                }
            )
            if len(cells) >= max_columns:
                break
        if cells:
            rows.append({"row": row_number, "cells": cells})
        if len(rows) >= max_rows:
            break
    if not rows:
        return {
            "status": "not_sampled",
            "rows": [],
            "sampled_row_count": 0,
            "sampled_formula_cell_count": 0,
        }
    return {
        "status": "sampled_from_top_left_window",
        "rows": rows,
        "sampled_row_count": len(rows),
        "sampled_formula_cell_count": formula_count,
        "source_sample_range": tab.get("sample_range"),
    }


def _bounds_from_a1(a1_range: str | None) -> dict[str, int] | None:
    if not a1_range:
        return None
    match = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)$", a1_range)
    if not match:
        return None
    return {
        "start_column": _column_to_number(match.group(1)),
        "start_row": int(match.group(2)),
        "end_column": _column_to_number(match.group(3)),
        "end_row": int(match.group(4)),
    }


def _column_to_number(column: str) -> int:
    number = 0
    for char in column:
        number = number * 26 + ord(char) - ord("A") + 1
    return number


def _ref_summaries(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.get("id"),
            "kind": item.get("kind"),
            "role": item.get("role"),
            "sheet": item.get("sheet"),
            "range": item.get("range"),
            "label": item.get("label"),
            "authority": item.get("authority"),
        }
        for item in refs
    ]


def _summary(projections: list[dict[str, Any]], graph: dict[str, Any]) -> dict[str, Any]:
    kinds = Counter(item["projection_kind"] for item in projections)
    statuses = Counter(item["preview"]["status"] for item in projections)
    return {
        "data_view_projection_count": len(projections),
        "calculation_pipeline_projection_count": kinds["calculation_pipeline_projection"],
        "document_summary_projection_count": kinds["document_summary_projection"],
        "sampled_projection_count": statuses["sampled_from_top_left_window"],
        "metadata_only_projection_count": statuses["metadata_only"],
        "not_sampled_projection_count": statuses["not_sampled"],
        "formula_warning_projection_count": sum(
            1 for item in projections if "formula_text_only_not_recalculated_result" in item["warnings"]
        ),
        "carry_forward_document_review_count": len(graph["carry_forward"]["document_review_queue"]),
        "carry_forward_semantic_review_count": len(graph["carry_forward"]["semantic_validation_review_queue"]),
        "shared_ontology_update_count": 0,
        "projection_status": "projected_with_carry_forward_warnings",
    }


def _parser_observations(projections: list[dict[str, Any]], graph: dict[str, Any]) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Data view projection is a read model over accepted graph nodes only.",
        }
    ]
    if any("formula_text_only_not_recalculated_result" in item["warnings"] for item in projections):
        observations.append(
            {
                "level": "warning",
                "message": "Formula text appears in projections, but formula-result authority is not established.",
            }
        )
    if graph["carry_forward"]["semantic_validation_review_queue"]:
        observations.append(
            {
                "level": "warning",
                "message": "Semantic validation review items remain unresolved and were not promoted.",
            }
        )
    return observations


def _unique(values: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def render_google_sheets_data_view_projection_section(projection: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in projection["summary"].items()
    )
    rows = "".join(
        "<tr>"
        f"<td>{_esc(item['projection_kind'])}</td>"
        f"<td>{_esc(item['label'])}</td>"
        f"<td>{_esc(item['sheet'])}</td>"
        f"<td>{_esc(item['range'])}</td>"
        f"<td>{_esc(item['preview']['status'])}</td>"
        f"<td>{_esc(', '.join(item['warnings']))}</td>"
        "</tr>"
        for item in projection["data_view_projections"]
    )
    preview_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['label'])}</td>"
        f"<td><code>{_esc(item['preview'].get('rows', [])[:3])}</code></td>"
        "</tr>"
        for item in projection["data_view_projections"]
        if item["preview"].get("rows")
    )
    if not preview_rows:
        preview_rows = '<tr><td colspan="2">No sampled preview rows.</td></tr>'
    return f"""
  <h2>Live Data View Projection</h2>
  <section class="grid">{metrics}</section>
  <h2>Projected Data Views</h2>
  <section class="panel"><table><thead><tr><th>Kind</th><th>Label</th><th>Sheet</th><th>Range</th><th>Preview</th><th>Warnings</th></tr></thead><tbody>{rows}</tbody></table></section>
  <h2>Projection Preview Samples</h2>
  <section class="panel"><table><thead><tr><th>Projection</th><th>Preview Rows</th></tr></thead><tbody>{preview_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Project accepted connected Google Sheets graph nodes into reviewable data views."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--access-preflight", type=Path, required=True)
    parser.add_argument("--live-manifest", type=Path, required=True)
    parser.add_argument("--live-view-formula-profile", type=Path, required=True)
    parser.add_argument("--live-block-candidates", type=Path, required=True)
    parser.add_argument("--bounded-window-sample", type=Path, required=True)
    parser.add_argument("--live-block-candidate-tuning", type=Path, required=True)
    parser.add_argument("--live-table-io-pipelines", type=Path, required=True)
    parser.add_argument("--live-cross-validation-plan", type=Path, required=True)
    parser.add_argument("--live-validation-batch-execution", type=Path, required=True)
    parser.add_argument("--live-gate-execution", type=Path, required=True)
    parser.add_argument("--live-evidence-package", type=Path, required=True)
    parser.add_argument("--live-document-ontology-mapping", type=Path, required=True)
    parser.add_argument("--live-action-contracts", type=Path, required=True)
    parser.add_argument("--live-domain-source-model", type=Path, required=True)
    parser.add_argument("--live-semantic-proposals", type=Path, required=True)
    parser.add_argument("--live-semantic-proposal-validation", type=Path, required=True)
    parser.add_argument("--live-validated-document-graph", type=Path, required=True)
    parser.add_argument("--top-left-sample", type=Path, required=True)
    args = parser.parse_args()

    projection = build_google_sheets_data_view_projection(
        live_validated_document_graph_path=args.live_validated_document_graph,
        live_evidence_package_path=args.live_evidence_package,
        top_left_sample_path=args.top_left_sample,
    )
    write_google_sheets_data_view_projection_package(
        out_dir=args.out_dir,
        access_preflight_path=args.access_preflight,
        live_manifest_path=args.live_manifest,
        live_view_formula_profile_path=args.live_view_formula_profile,
        live_block_candidates_path=args.live_block_candidates,
        bounded_window_sample_path=args.bounded_window_sample,
        live_block_candidate_tuning_path=args.live_block_candidate_tuning,
        live_table_io_pipelines_path=args.live_table_io_pipelines,
        live_cross_validation_plan_path=args.live_cross_validation_plan,
        live_validation_batch_execution_path=args.live_validation_batch_execution,
        live_gate_execution_path=args.live_gate_execution,
        live_evidence_package_path=args.live_evidence_package,
        live_document_ontology_mapping_path=args.live_document_ontology_mapping,
        live_action_contracts_path=args.live_action_contracts,
        live_domain_source_model_path=args.live_domain_source_model,
        live_semantic_proposals_path=args.live_semantic_proposals,
        live_semantic_proposal_validation_path=args.live_semantic_proposal_validation,
        live_validated_document_graph_path=args.live_validated_document_graph,
        data_view_projection=projection,
    )


if __name__ == "__main__":
    main()
