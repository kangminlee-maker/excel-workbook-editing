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


def build_google_sheets_table_io_pipelines(
    *,
    live_block_candidates_path: Path,
    live_view_formula_profile_path: Path,
    live_block_candidate_tuning_path: Path,
) -> dict[str, Any]:
    live_block_candidates_path = live_block_candidates_path.expanduser().resolve()
    live_view_formula_profile_path = live_view_formula_profile_path.expanduser().resolve()
    live_block_candidate_tuning_path = live_block_candidate_tuning_path.expanduser().resolve()
    block_candidates = _read_json(live_block_candidates_path)
    formula_profile = _read_json(live_view_formula_profile_path)
    tuning = _read_json(live_block_candidate_tuning_path)

    sheet_index = _sheet_index(block_candidates)
    sampled_index = _sampled_index(tuning)
    source_url_candidates = _source_url_candidates(tuning)
    error_annotations = _error_annotations(tuning)
    signature_index = _signature_index(formula_profile)
    pipelines = [
        _pipeline_from_edge(
            edge=edge,
            sheet_index=sheet_index,
            sampled_index=sampled_index,
            signature_index=signature_index,
            source_url_candidates=source_url_candidates,
            error_annotations=error_annotations,
        )
        for edge in formula_profile.get("dependency_edges", [])
    ]
    external_sources = _external_sources(
        formula_profile=formula_profile,
        source_url_candidates=source_url_candidates,
    )
    review_queue = _review_queue(
        pipelines=pipelines,
        external_sources=external_sources,
        tuning=tuning,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": block_candidates["source"]["spreadsheet_id"],
            "spreadsheet_url": block_candidates["source"].get("spreadsheet_url"),
            "title": block_candidates["source"]["title"],
            "source_artifacts": {
                "live_block_candidates": str(live_block_candidates_path),
                "live_view_formula_profile": str(live_view_formula_profile_path),
                "live_block_candidate_tuning": str(live_block_candidate_tuning_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "input_authority": "candidate_artifacts_plus_formula_text_and_bounded_samples",
            "pipeline_status": "candidate_not_accepted_graph_claim",
            "formula_text_authority": "formula_text_only",
            "formula_result_authority": "not_established",
            "external_source_read_authority": "blocked_until_source_access_evidence",
        },
        "pipelines": sorted(
            pipelines,
            key=lambda item: (-item["confidence"], item["id"]),
        ),
        "external_sources": external_sources,
        "review_queue": review_queue,
        "mermaid": _mermaid_graph(pipelines, external_sources),
        "summary": _summary(pipelines, external_sources, review_queue),
        "parser_observations": _parser_observations(
            pipelines,
            external_sources,
            review_queue,
        ),
    }


def write_google_sheets_table_io_pipelines_package(
    *,
    out_dir: Path,
    access_preflight_path: Path,
    live_manifest_path: Path,
    live_view_formula_profile_path: Path,
    live_block_candidates_path: Path,
    bounded_window_sample_path: Path,
    live_block_candidate_tuning_path: Path,
    table_io_pipelines: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    table_io_path = out_dir / "live-table-io-pipelines.json"
    table_io_path.write_text(
        json.dumps(table_io_pipelines, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    access_preflight = _read_json(access_preflight_path)
    manifest = _read_json(live_manifest_path)
    view_formula_profile = _read_json(live_view_formula_profile_path)
    block_candidates = _read_json(live_block_candidates_path)
    bounded_sample = _read_json(bounded_window_sample_path)
    tuning = _read_json(live_block_candidate_tuning_path)
    (out_dir / "index.html").write_text(
        render_live_manifest_html(
            access_preflight=access_preflight,
            manifest=manifest,
            live_view_formula_profile=view_formula_profile,
            live_block_candidates=block_candidates,
            live_bounded_window_sample=bounded_sample,
            live_block_candidate_tuning=tuning,
            live_table_io_pipelines=table_io_pipelines,
        ),
        encoding="utf-8",
    )


def _pipeline_from_edge(
    *,
    edge: dict[str, Any],
    sheet_index: dict[str, Any],
    sampled_index: dict[str, list[dict[str, Any]]],
    signature_index: dict[tuple[str, str | None], list[dict[str, Any]]],
    source_url_candidates: list[dict[str, Any]],
    error_annotations: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    output_ref = _output_ref(edge, sheet_index, sampled_index)
    input_ref = _input_ref(edge, sheet_index, sampled_index, source_url_candidates)
    transform_ref = _transform_ref(edge, signature_index)
    review_flags = _review_flags(
        edge=edge,
        input_ref=input_ref,
        output_ref=output_ref,
        transform_ref=transform_ref,
        source_url_candidates=source_url_candidates,
        error_annotations=error_annotations,
    )
    pipeline = {
        "id": f"pipeline_{_slug(edge['source_sheet'])}_{_slug(edge['target_kind'])}_{_slug(edge.get('target_sheet') or edge['target_kind'])}",
        "type": "google_sheets_table_io_pipeline",
        "status": "candidate",
        "role": _pipeline_role(edge, input_ref, output_ref, transform_ref),
        "input_refs": [input_ref],
        "output_refs": [output_ref],
        "transform_refs": [transform_ref],
        "evidence_refs": [edge["id"], *transform_ref["signature_group_ids"]],
        "confidence": 0.0,
        "review_flags": review_flags,
        "notes": _pipeline_notes(edge, review_flags),
    }
    pipeline["confidence"] = _pipeline_confidence(pipeline, edge)
    return pipeline


def _sheet_index(block_candidates: dict[str, Any]) -> dict[str, Any]:
    sheets = {sheet["name"]: sheet for sheet in block_candidates.get("sheets", [])}
    blocks_by_id = {}
    regions_by_id = {}
    for sheet in sheets.values():
        for block in sheet.get("blocks", []):
            blocks_by_id[block["id"]] = block
        for region in sheet.get("cell_regions", []):
            regions_by_id[region["id"]] = region
    return {
        "sheets": sheets,
        "blocks_by_id": blocks_by_id,
        "regions_by_id": regions_by_id,
    }


def _sampled_index(tuning: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_sheet: dict[str, list[dict[str, Any]]] = {}
    for region in tuning.get("sampled_regions", []):
        by_sheet.setdefault(region["sheet"], []).append(region)
    for regions in by_sheet.values():
        regions.sort(
            key=lambda item: (
                _sampled_region_rank(item),
                item["bounds"]["start_row"],
                item["bounds"]["start_column"],
            )
        )
    return by_sheet


def _source_url_candidates(tuning: dict[str, Any]) -> list[dict[str, Any]]:
    regions_by_id = {item["id"]: item for item in tuning.get("sampled_regions", [])}
    candidates = []
    for action in tuning.get("tuning_actions", []):
        if action["type"] != "external_source_url_candidate":
            continue
        evidence_id = (action.get("evidence_refs") or [""])[0]
        region = regions_by_id.get(evidence_id, {})
        urls = _urls_from_preview(region.get("preview", []))
        candidates.append(
            {
                "id": f"source_url_{_slug(action['sheet'])}_{_slug(action['target_range'])}",
                "sheet": action["sheet"],
                "range": action["target_range"],
                "spreadsheet_url": urls[0] if urls else None,
                "spreadsheet_id": _spreadsheet_id_from_url(urls[0]) if urls else None,
                "evidence_refs": action.get("evidence_refs", []),
                "status": action["status"],
            }
        )
    return candidates


def _error_annotations(tuning: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_sheet: dict[str, list[dict[str, Any]]] = {}
    for action in tuning.get("tuning_actions", []):
        if action["type"] == "formula_error_annotation":
            by_sheet.setdefault(action["sheet"], []).append(action)
    return by_sheet


def _signature_index(formula_profile: dict[str, Any]) -> dict[tuple[str, str | None], list[dict[str, Any]]]:
    index: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
    for group in formula_profile.get("signature_groups", []):
        for source_sheet in group.get("source_sheets", []):
            targets = group.get("reference_sheets") or [None]
            for target_sheet in targets:
                index.setdefault((source_sheet, target_sheet), []).append(group)
    for groups in index.values():
        groups.sort(key=lambda item: (-item["formula_count"], item["id"]))
    return index


def _output_ref(
    edge: dict[str, Any],
    sheet_index: dict[str, Any],
    sampled_index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    source_sheet = edge["source_sheet"]
    sampled = _first_sampled_formula_region(sampled_index.get(source_sheet, []))
    if sampled:
        return _sampled_ref(sampled, role="output")
    sheet = sheet_index["sheets"].get(source_sheet, {})
    block = _preferred_block(
        sheet,
        preferred_types=("formula_region_candidate", "table_candidate", "object_surface"),
    )
    if block:
        return _block_ref(block, role="output")
    return {
        "id": f"sheet:{source_sheet}",
        "kind": "sheet_surface",
        "role": "output",
        "sheet": source_sheet,
        "range": None,
        "block_id": None,
        "region_id": None,
        "bounds": None,
        "label": source_sheet,
        "authority": "formula_text_dependency_candidate",
    }


def _input_ref(
    edge: dict[str, Any],
    sheet_index: dict[str, Any],
    sampled_index: dict[str, list[dict[str, Any]]],
    source_url_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    if edge["target_kind"] == "external_importrange":
        source = source_url_candidates[0] if source_url_candidates else {}
        return {
            "id": source.get("id") or f"external:{edge['id']}",
            "kind": "external_importrange_source",
            "role": "input",
            "sheet": None,
            "range": _first(edge.get("sample_target_ranges")),
            "block_id": None,
            "region_id": None,
            "bounds": None,
            "label": source.get("spreadsheet_id") or "unresolved IMPORTRANGE source",
            "authority": "blocked_until_source_access_evidence",
            "source_spreadsheet_id": source.get("spreadsheet_id"),
            "source_spreadsheet_url": source.get("spreadsheet_url"),
        }

    target_sheet = edge.get("target_sheet")
    sampled = _first_sampled_input_region(sampled_index.get(target_sheet or "", []))
    if sampled:
        return _sampled_ref(sampled, role="input")
    sheet = sheet_index["sheets"].get(target_sheet or "", {})
    block = _preferred_block(
        sheet,
        preferred_types=("table_candidate", "support_surface", "formula_region_candidate"),
    )
    if block:
        return _block_ref(block, role="input")
    return {
        "id": f"range:{target_sheet or edge['target_kind']}:{_first(edge.get('sample_target_ranges')) or 'unknown'}",
        "kind": "sheet_range",
        "role": "input",
        "sheet": target_sheet,
        "range": _first(edge.get("sample_target_ranges")),
        "block_id": None,
        "region_id": None,
        "bounds": None,
        "label": target_sheet or edge["target_kind"],
        "authority": "formula_text_dependency_candidate",
    }


def _transform_ref(
    edge: dict[str, Any],
    signature_index: dict[tuple[str, str | None], list[dict[str, Any]]],
) -> dict[str, Any]:
    groups = signature_index.get(
        (edge["source_sheet"], edge.get("target_sheet")),
        [],
    )
    if not groups and edge["target_kind"] == "external_importrange":
        groups = [
            group
            for key, values in signature_index.items()
            if key[0] == edge["source_sheet"]
            for group in values
            if "importrange" in group.get("classifications", [])
        ]
    return {
        "id": f"transform_{_slug(edge['id'])}",
        "kind": "formula_dependency_edge",
        "dependency_edge_id": edge["id"],
        "target_kind": edge["target_kind"],
        "formula_count": edge.get("formula_count", 0),
        "sample_formula_cells": edge.get("sample_formula_cells", [])[:12],
        "sample_target_ranges": edge.get("sample_target_ranges", [])[:12],
        "classifications": edge.get("classifications", []),
        "signature_group_ids": [item["id"] for item in groups[:8]],
        "repeated_formula_family": any(item.get("formula_count", 0) >= 3 for item in groups),
        "authority": edge.get("authority", "formula_text_dependency_candidate"),
    }


def _preferred_block(
    sheet: dict[str, Any],
    *,
    preferred_types: tuple[str, ...],
) -> dict[str, Any] | None:
    blocks = sheet.get("blocks", [])
    for block_type in preferred_types:
        typed = [block for block in blocks if block["type"] == block_type]
        if typed:
            return max(typed, key=lambda item: item.get("confidence", 0))
    return None


def _first_sampled_input_region(regions: list[dict[str, Any]]) -> dict[str, Any] | None:
    for subtype in (
        "sampled_external_source_region",
        "sampled_table_region",
        "sampled_display_region",
        "sampled_formula_region",
    ):
        for region in regions:
            if region["subtype"] == subtype:
                return region
    return None


def _first_sampled_formula_region(regions: list[dict[str, Any]]) -> dict[str, Any] | None:
    for region in regions:
        if region["operation"] == "inspect.formula_window" and region["metrics"].get("formula_cell_count", 0):
            return region
    return None


def _sampled_region_rank(region: dict[str, Any]) -> int:
    subtype_order = {
        "sampled_external_source_region": 0,
        "sampled_table_region": 1,
        "sampled_formula_region": 2,
        "sampled_display_region": 3,
    }
    return subtype_order.get(region["subtype"], 9)


def _block_ref(block: dict[str, Any], *, role: str) -> dict[str, Any]:
    return {
        "id": block["id"],
        "kind": block["type"],
        "role": role,
        "sheet": block["sheet"],
        "range": block["bounds"]["a1_range"],
        "block_id": block["id"],
        "region_id": None,
        "bounds": block["bounds"],
        "label": block.get("label") or block["id"],
        "authority": "block_candidate",
    }


def _sampled_ref(region: dict[str, Any], *, role: str) -> dict[str, Any]:
    return {
        "id": region["id"],
        "kind": region["subtype"],
        "role": role,
        "sheet": region["sheet"],
        "range": region["bounds"]["a1_range"],
        "block_id": None,
        "region_id": region["id"],
        "bounds": region["bounds"],
        "label": region["subtype"],
        "authority": "bounded_source_evidence",
    }


def _review_flags(
    *,
    edge: dict[str, Any],
    input_ref: dict[str, Any],
    output_ref: dict[str, Any],
    transform_ref: dict[str, Any],
    source_url_candidates: list[dict[str, Any]],
    error_annotations: dict[str, list[dict[str, Any]]],
) -> list[str]:
    flags = ["formula_result_not_established"]
    if edge["target_kind"] == "same_sheet_range":
        flags.append("same_sheet_dataflow")
    if edge["target_kind"] == "cross_sheet_range":
        flags.append("cross_sheet_dataflow")
    if edge["target_kind"] == "external_importrange":
        flags.extend(["external_source_dependency", "source_allowlist_required"])
        if source_url_candidates:
            flags.append("source_url_candidate_available")
        else:
            flags.append("source_url_unresolved")
    if transform_ref["repeated_formula_family"]:
        flags.append("repeated_formula_family")
    if input_ref["authority"] == "bounded_source_evidence":
        flags.append("sampled_input_confirmed")
    if input_ref["kind"] in {"support_surface", "sheet_range"}:
        flags.append("input_region_unresolved")
    for sheet in (input_ref.get("sheet"), output_ref.get("sheet")):
        if sheet and error_annotations.get(sheet):
            flags.append("formula_error_observed")
    return sorted(set(flags))


def _pipeline_role(
    edge: dict[str, Any],
    input_ref: dict[str, Any],
    output_ref: dict[str, Any],
    transform_ref: dict[str, Any],
) -> str:
    if edge["target_kind"] == "external_importrange":
        return "source_ingestion"
    if output_ref.get("sheet") == "FC_DATA":
        return "input_staging"
    if edge["target_kind"] == "cross_sheet_range" and input_ref.get("sheet") == "FC_DATA":
        return "report"
    if transform_ref["repeated_formula_family"] and edge["target_kind"] == "same_sheet_range":
        return "calculation"
    if edge["target_kind"] == "cross_sheet_range":
        return "bridge"
    return "calculation"


def _pipeline_confidence(pipeline: dict[str, Any], edge: dict[str, Any]) -> float:
    confidence = 0.48
    if edge.get("target_status") == "known_sheet":
        confidence += 0.12
    if edge.get("formula_count", 0) >= 10:
        confidence += 0.1
    if "sampled_input_confirmed" in pipeline["review_flags"]:
        confidence += 0.08
    if "repeated_formula_family" in pipeline["review_flags"]:
        confidence += 0.06
    if "source_allowlist_required" in pipeline["review_flags"]:
        confidence -= 0.08
    if "formula_error_observed" in pipeline["review_flags"]:
        confidence -= 0.04
    if "input_region_unresolved" in pipeline["review_flags"]:
        confidence -= 0.06
    return round(max(0.0, min(confidence, 0.9)), 4)


def _pipeline_notes(edge: dict[str, Any], review_flags: list[str]) -> list[str]:
    notes = [
        "Formula text dependency is projected to table-level I/O candidate; formula result is not authority."
    ]
    if "source_allowlist_required" in review_flags:
        notes.append("IMPORTRANGE source read is blocked until source ACL and source access evidence are verified.")
    if "formula_error_observed" in review_flags:
        notes.append("Displayed formula errors were observed in bounded samples.")
    if edge.get("sample_target_ranges"):
        notes.append("Sample target ranges: " + ", ".join(edge["sample_target_ranges"][:4]))
    return notes


def _external_sources(
    *,
    formula_profile: dict[str, Any],
    source_url_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    url_candidate = source_url_candidates[0] if source_url_candidates else {}
    sources = []
    for dependency in formula_profile.get("external_dependencies", []):
        sources.append(
            {
                "id": dependency["id"],
                "formula_sheet": dependency["formula_sheet"],
                "formula_cell": dependency["formula_cell"],
                "source_argument": dependency["source_argument"],
                "range_argument": dependency["range_argument"],
                "source_resolution_status": dependency["source_resolution_status"],
                "candidate_source_spreadsheet_id": url_candidate.get("spreadsheet_id"),
                "candidate_source_spreadsheet_url": url_candidate.get("spreadsheet_url"),
                "required_evidence": dependency["required_evidence"],
                "status": "blocked_until_source_access_evidence",
                "evidence_refs": [dependency["id"], *url_candidate.get("evidence_refs", [])],
            }
        )
    return sources


def _review_queue(
    *,
    pipelines: list[dict[str, Any]],
    external_sources: list[dict[str, Any]],
    tuning: dict[str, Any],
) -> list[dict[str, Any]]:
    queue = []
    if external_sources:
        queue.append(
            {
                "id": "review_external_importrange_source_authority",
                "type": "permission_or_authority_blocker",
                "severity": "high",
                "message": "Resolve source spreadsheet ID, Google ACL, and source access evidence before reading IMPORTRANGE source data.",
                "evidence_refs": [item["id"] for item in external_sources],
                "status": "requires_human_or_source_access_policy_evidence_action",
            }
        )
    if any("formula_error_observed" in item["review_flags"] for item in pipelines):
        queue.append(
            {
                "id": "review_formula_error_surfaces",
                "type": "formula_result_authority_gap",
                "severity": "high",
                "message": "Displayed #REF! or formula errors must be reconciled before treating pipeline outputs as calculated values.",
                "evidence_refs": [
                    action["id"]
                    for action in tuning.get("tuning_actions", [])
                    if action["type"] == "formula_error_annotation"
                ],
                "status": "requires_formula_result_review",
            }
        )
    remaining_count = len(tuning.get("remaining_read_queue", []))
    if remaining_count:
        queue.append(
            {
                "id": "review_remaining_bounded_read_queue",
                "type": "coverage_gap",
                "severity": "medium",
                "message": f"{remaining_count} bounded read candidates remain unsampled; pipeline coverage is partial.",
                "evidence_refs": [item["id"] for item in tuning.get("remaining_read_queue", [])[:12]],
                "status": "pending_bounded_sampling",
            }
        )
    return queue


def _summary(
    pipelines: list[dict[str, Any]],
    external_sources: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
) -> dict[str, int | str]:
    role_counts = Counter(item["role"] for item in pipelines)
    flag_counts = Counter(flag for item in pipelines for flag in item["review_flags"])
    return {
        "pipeline_count": len(pipelines),
        "source_ingestion_pipeline_count": role_counts["source_ingestion"],
        "input_staging_pipeline_count": role_counts["input_staging"],
        "report_pipeline_count": role_counts["report"],
        "bridge_pipeline_count": role_counts["bridge"],
        "calculation_pipeline_count": role_counts["calculation"],
        "cross_sheet_pipeline_count": flag_counts["cross_sheet_dataflow"],
        "same_sheet_pipeline_count": flag_counts["same_sheet_dataflow"],
        "external_source_pipeline_count": flag_counts["external_source_dependency"],
        "sampled_input_confirmed_pipeline_count": flag_counts["sampled_input_confirmed"],
        "formula_error_pipeline_count": flag_counts["formula_error_observed"],
        "review_queue_count": len(review_queue),
        "external_source_count": len(external_sources),
        "pipeline_status": "candidate_projected_not_accepted",
    }


def _parser_observations(
    pipelines: list[dict[str, Any]],
    external_sources: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Table I/O pipelines are deterministic projections over formula text, block candidates, and bounded samples; they are not accepted graph claims.",
        },
        {
            "level": "warning",
            "message": "Formula-result authority remains unestablished for every projected pipeline.",
        },
    ]
    if external_sources:
        observations.append(
            {
                "level": "warning",
                "message": "IMPORTRANGE source data is not read in this stage; source ACL and source access evidence are explicit blockers.",
            }
        )
    if review_queue:
        observations.append(
            {
                "level": "warning",
                "message": f"{len(review_queue)} review items must be resolved before promoting pipelines into accepted graph claims.",
            }
        )
    if not pipelines:
        observations.append(
            {
                "level": "warning",
                "message": "No formula dependency edges were available to project into table I/O pipelines.",
            }
        )
    return observations


def _mermaid_graph(
    pipelines: list[dict[str, Any]],
    external_sources: list[dict[str, Any]],
) -> str:
    lines = ["flowchart LR"]
    node_labels: dict[str, str] = {}
    for pipeline in sorted(pipelines, key=lambda item: (-item["confidence"], item["id"]))[:32]:
        input_ref = pipeline["input_refs"][0]
        output_ref = pipeline["output_refs"][0]
        input_node = _node_id(input_ref)
        output_node = _node_id(output_ref)
        node_labels[input_node] = _node_label(input_ref)
        node_labels[output_node] = _node_label(output_ref)
        edge_label = f"{pipeline['role']} / {pipeline['transform_refs'][0]['formula_count']} formulas"
        lines.append(f"  {input_node} -->|{_mermaid_escape(edge_label)}| {output_node}")
    for source in external_sources:
        source_node = _slug(source["candidate_source_spreadsheet_id"] or source["id"])
        fc_node = _slug(f"sheet:FC_DATA")
        node_labels[source_node] = "external source (blocked)"
        node_labels.setdefault(fc_node, "FC_DATA")
        lines.append(f"  {source_node} -. allowlist required .-> {fc_node}")
    return "\n".join(
        [
            lines[0],
            *(
                f'  {node_id}["{_mermaid_escape(label)}"]'
                for node_id, label in sorted(node_labels.items())
            ),
            *lines[1:],
        ]
    )


def _node_id(ref: dict[str, Any]) -> str:
    if ref.get("sheet"):
        return _slug(f"sheet:{ref['sheet']}")
    return _slug(ref["id"])


def _node_label(ref: dict[str, Any]) -> str:
    parts = [ref.get("sheet") or ref.get("label") or ref["id"]]
    if ref.get("range"):
        parts.append(ref["range"])
    return " ".join(str(part) for part in parts if part)


def _urls_from_preview(preview: list[str]) -> list[str]:
    urls = []
    for line in preview:
        urls.extend(re.findall(r"https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]+/[^\s|]*", line))
    return urls


def _spreadsheet_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def _first(values: list[Any] | None) -> Any:
    return values[0] if values else None


def _slug(value: Any) -> str:
    text = str(value or "none")
    text = re.sub(r"[^A-Za-z0-9가-힣]+", "_", text).strip("_").lower()
    return text or "none"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def _mermaid_escape(value: Any) -> str:
    return str(value).replace('"', "'").replace("\n", " ")


def render_google_sheets_table_io_pipelines_section(table_io: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in table_io["summary"].items()
    )
    pipeline_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['role'])}</td>"
        f"<td>{_esc(item['input_refs'][0]['label'])}<br><code>{_esc(item['input_refs'][0].get('range'))}</code></td>"
        f"<td>{_esc(item['output_refs'][0]['label'])}<br><code>{_esc(item['output_refs'][0].get('range'))}</code></td>"
        f"<td>{_esc(item['transform_refs'][0]['formula_count'])}</td>"
        f"<td>{_esc(item['confidence'])}</td>"
        f"<td>{_esc(', '.join(item['review_flags']))}</td>"
        "</tr>"
        for item in table_io["pipelines"][:60]
    )
    source_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['formula_sheet'])}!{_esc(item['formula_cell'])}</td>"
        f"<td>{_esc(item['candidate_source_spreadsheet_id'])}</td>"
        f"<td><code>{_esc(item['range_argument'])}</code></td>"
        f"<td>{_esc(item['status'])}</td>"
        "</tr>"
        for item in table_io["external_sources"]
    )
    if not source_rows:
        source_rows = '<tr><td colspan="4">No external source dependencies detected.</td></tr>'
    review_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['severity'])}</td>"
        f"<td>{_esc(item['type'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        "</tr>"
        for item in table_io["review_queue"]
    )
    if not review_rows:
        review_rows = '<tr><td colspan="4">No review blockers emitted.</td></tr>'
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in table_io["parser_observations"]
    )
    return f"""
  <h2>Live Table I/O Pipelines</h2>
  <section class="grid">{metrics}</section>
  <h2>Pipeline Mermaid</h2>
  <section class="panel"><pre class="mermaid">{_esc(table_io["mermaid"])}</pre></section>
  <h2>Pipeline Candidates</h2>
  <section class="panel"><table><thead><tr><th>Role</th><th>Input</th><th>Output</th><th>Formula Count</th><th>Confidence</th><th>Review Flags</th></tr></thead><tbody>{pipeline_rows}</tbody></table></section>
  <h2>External Source Blockers</h2>
  <section class="panel"><table><thead><tr><th>Formula</th><th>Candidate Source ID</th><th>Range</th><th>Status</th></tr></thead><tbody>{source_rows}</tbody></table></section>
  <h2>Pipeline Review Queue</h2>
  <section class="panel"><table><thead><tr><th>Severity</th><th>Type</th><th>Message</th><th>Status</th></tr></thead><tbody>{review_rows}</tbody></table></section>
  <h2>Pipeline Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, securityLevel: 'loose' }});
  </script>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Project Google Sheets formula/block evidence into table-level I/O pipeline candidates."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--access-preflight", type=Path, required=True)
    parser.add_argument("--live-manifest", type=Path, required=True)
    parser.add_argument("--live-view-formula-profile", type=Path, required=True)
    parser.add_argument("--live-block-candidates", type=Path, required=True)
    parser.add_argument("--bounded-window-sample", type=Path, required=True)
    parser.add_argument("--live-block-candidate-tuning", type=Path, required=True)
    args = parser.parse_args()

    table_io = build_google_sheets_table_io_pipelines(
        live_block_candidates_path=args.live_block_candidates,
        live_view_formula_profile_path=args.live_view_formula_profile,
        live_block_candidate_tuning_path=args.live_block_candidate_tuning,
    )
    write_google_sheets_table_io_pipelines_package(
        out_dir=args.out_dir,
        access_preflight_path=args.access_preflight,
        live_manifest_path=args.live_manifest,
        live_view_formula_profile_path=args.live_view_formula_profile,
        live_block_candidates_path=args.live_block_candidates,
        bounded_window_sample_path=args.bounded_window_sample,
        live_block_candidate_tuning_path=args.live_block_candidate_tuning,
        table_io_pipelines=table_io,
    )


if __name__ == "__main__":
    main()
