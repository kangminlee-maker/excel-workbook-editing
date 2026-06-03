from __future__ import annotations

import argparse
import html
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_document_item_grouping_checkpoint(
    *,
    out_dir: Path,
) -> dict[str, Any]:
    out_dir = out_dir.expanduser().resolve()
    manifest = _read_json(out_dir / "live-manifest.json")
    block_candidates = _read_json(out_dir / "live-block-candidates.json")
    table_io = _read_json(out_dir / "live-table-io-pipelines.json")
    formula_authority = _read_json(out_dir / "live-formula-result-authority-checkpoint.json")

    blocks_by_id = _blocks_by_id(block_candidates)
    pipelines_by_id = {item["id"]: item for item in table_io.get("pipelines", [])}
    pipeline_authority_by_id = {
        item["pipeline_id"]: item
        for item in formula_authority.get("pipeline_authority_results", [])
    }

    section_items = _section_document_items(block_candidates, blocks_by_id)
    pipeline_items = _pipeline_document_items(
        pipelines_by_id=pipelines_by_id,
        pipeline_authority_by_id=pipeline_authority_by_id,
    )
    document_items = [*pipeline_items, *section_items]
    orphan_surfaces = _orphan_object_surfaces(block_candidates)
    relations = _document_item_relations(document_items)
    gate_results = _grouping_gate_results(document_items, orphan_surfaces)

    checkpoint = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": manifest["source"]["spreadsheet_id"],
            "spreadsheet_url": manifest["source"].get("spreadsheet_url"),
            "title": manifest["source"]["title"],
            "source_artifacts": {
                "live_block_candidates": "live-block-candidates.json",
                "live_table_io_pipelines": "live-table-io-pipelines.json",
                "live_formula_result_authority_checkpoint": "live-formula-result-authority-checkpoint.json",
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "checkpoint_status": "completed",
            "grouping_truth": "structural_grouping_checkpoint_no_business_semantics",
            "shared_ontology_updates": 0,
        },
        "method": {
            "name": "connected_sheets_document_item_grouping_checkpoint",
            "authority": "deterministic_structural_grouping_gates",
            "decision_policy": (
                "Accept only groupings with formula/dataflow and formula-result authority. "
                "Keep ordering-only section groups and coarse object surfaces review-required."
            ),
        },
        "evidence_inputs": {
            "block_count": block_candidates["summary"]["block_count"],
            "candidate_relation_count": block_candidates["summary"]["relation_count"],
            "object_surface_count": block_candidates["summary"]["object_surface_count"],
            "pipeline_authority_result_count": len(formula_authority.get("pipeline_authority_results", [])),
        },
        "document_items": document_items,
        "document_item_relations": relations,
        "grouping_gate_results": gate_results,
        "orphan_surfaces": orphan_surfaces,
        "follow_up_actions": _follow_up_actions(orphan_surfaces, section_items),
        "summary": _summary(document_items, relations, gate_results, orphan_surfaces),
        "parser_observations": _parser_observations(document_items, orphan_surfaces),
    }
    return checkpoint


def write_google_sheets_document_item_grouping_checkpoint_package(
    *,
    out_dir: Path,
    checkpoint: dict[str, Any],
) -> None:
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "live-document-item-grouping-checkpoint.json").write_text(
        json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "index.html").write_text(
        render_live_manifest_html(
            access_preflight=_read_json(out_dir / "access-preflight.json"),
            manifest=_read_json(out_dir / "live-manifest.json"),
            live_view_formula_profile=_optional_json(out_dir / "live-view-formula-profile.json"),
            live_block_candidates=_optional_json(out_dir / "live-block-candidates.json"),
            live_bounded_window_sample=_optional_json(out_dir / "live-bounded-window-sample.json"),
            live_block_candidate_tuning=_optional_json(out_dir / "live-block-candidate-tuning.json"),
            live_table_io_pipelines=_optional_json(out_dir / "live-table-io-pipelines.json"),
            live_cross_validation_plan=_optional_json(out_dir / "live-cross-validation-plan.json"),
            live_validation_batch_execution=_optional_json(out_dir / "live-validation-batch-execution.json"),
            live_gate_execution=_optional_json(out_dir / "live-gate-execution.json"),
            live_evidence_package=_optional_json(out_dir / "live-evidence-package.json"),
            live_document_ontology_mapping=_optional_json(out_dir / "live-document-ontology-mapping.json"),
            live_action_contracts=_optional_json(out_dir / "live-action-contracts.json"),
            live_domain_source_model=_optional_json(out_dir / "live-domain-source-model.json"),
            live_semantic_proposals=_optional_json(out_dir / "live-semantic-proposals.json"),
            live_semantic_proposal_validation=_optional_json(out_dir / "live-semantic-proposal-validation.json"),
            live_validated_document_graph=_optional_json(out_dir / "live-validated-document-graph.json"),
            live_data_view_projection=_optional_json(out_dir / "live-data-view-projection.json"),
            live_local_semantic_candidates=_optional_json(out_dir / "live-local-semantic-candidates.json"),
            live_shared_ontology_alignment_review=_optional_json(out_dir / "live-shared-ontology-alignment-review.json"),
            live_process_redesign_review=_optional_json(out_dir / "live-process-redesign-review.json"),
            live_blocker_resolution_update=_optional_json(out_dir / "live-blocker-resolution-update.json"),
            live_formula_result_authority_checkpoint=_optional_json(out_dir / "live-formula-result-authority-checkpoint.json"),
            live_document_item_grouping_checkpoint=checkpoint,
        ),
        encoding="utf-8",
    )


def _section_document_items(
    block_candidates: dict[str, Any],
    blocks_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    child_ids_by_heading: dict[str, list[str]] = defaultdict(list)
    confidence_by_heading: dict[str, list[float]] = defaultdict(list)
    relation_ids_by_heading: dict[str, list[str]] = defaultdict(list)
    for sheet in block_candidates.get("sheets", []):
        for relation in sheet.get("relations", []):
            if relation.get("type") != "section_contains_block_candidate":
                continue
            child_ids_by_heading[relation["from"]].append(relation["to"])
            confidence_by_heading[relation["from"]].append(float(relation.get("confidence", 0)))
            relation_ids_by_heading[relation["from"]].append(relation["id"])

    items = []
    for heading_id, child_ids in sorted(child_ids_by_heading.items()):
        heading = blocks_by_id.get(heading_id)
        if not heading:
            continue
        members = [heading, *[blocks_by_id[item] for item in child_ids if item in blocks_by_id]]
        item_id = f"doc_item_section_{_slug(heading_id)}"
        item = {
            "id": item_id,
            "type": "document_item_group",
            "status": "review_required",
            "item_kind": "section_with_child_blocks",
            "sheet": heading["sheet"],
            "bounds": _union_bounds([item.get("bounds") for item in members]),
            "label": heading.get("label", heading_id),
            "member_blocks": [_member_block(item) for item in members],
            "member_surfaces": [],
            "evidence_scores": {
                "spatial_text_ordering": round(_avg(confidence_by_heading[heading_id]), 3),
                "member_type_diversity": len({item.get("type") for item in members}),
                "formula_dataflow_support": 0,
                "object_anchor_support": 0,
            },
            "review_reasons": [
                "section_grouping_uses_ordering_evidence_only",
                "needs_visual_or_user_confirmation_before_semantic_storage",
            ],
            "evidence_refs": relation_ids_by_heading[heading_id],
        }
        items.append(item)
    return items


def _pipeline_document_items(
    *,
    pipelines_by_id: dict[str, dict[str, Any]],
    pipeline_authority_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    items = []
    for pipeline_id, authority in sorted(pipeline_authority_by_id.items()):
        pipeline = pipelines_by_id.get(pipeline_id)
        if not pipeline:
            continue
        input_refs = pipeline.get("input_refs", [])
        output_refs = pipeline.get("output_refs", [])
        surfaces = [
            *[_member_surface(ref, "input") for ref in input_refs],
            *[_member_surface(ref, "output") for ref in output_refs],
        ]
        status = "accepted" if authority["status"] == "accepted" else "review_required"
        review_reasons = []
        if status != "accepted":
            review_reasons.extend(authority.get("blockers", []))
            review_reasons.append("pipeline_grouping_needs_formula_result_or_lineage_resolution")
        item = {
            "id": f"doc_item_pipeline_{_slug(pipeline_id)}",
            "type": "document_item_group",
            "status": status,
            "item_kind": "formula_dataflow_pipeline_group",
            "sheet": authority.get("sheet") or _first_sheet(surfaces),
            "bounds": _union_bounds([_parse_a1_bounds(ref.get("range")) for ref in [*input_refs, *output_refs]]),
            "label": pipeline.get("label") or authority.get("range") or pipeline_id,
            "member_blocks": [],
            "member_surfaces": surfaces,
            "evidence_scores": {
                "spatial_text_ordering": 0,
                "member_type_diversity": len({surface["surface_kind"] for surface in surfaces}),
                "formula_dataflow_support": 1,
                "formula_result_authority": 1 if authority["status"] == "accepted" else 0,
                "object_anchor_support": 0,
            },
            "review_reasons": review_reasons,
            "evidence_refs": [pipeline_id, authority["id"], *pipeline.get("evidence_refs", [])],
        }
        items.append(item)
    return items


def _orphan_object_surfaces(block_candidates: dict[str, Any]) -> list[dict[str, Any]]:
    surfaces = []
    for sheet in block_candidates.get("sheets", []):
        for block in sheet.get("blocks", []):
            if block.get("type") != "object_surface":
                continue
            surfaces.append(
                {
                    "id": f"orphan_{_slug(block['id'])}",
                    "type": "orphan_surface",
                    "status": "review_required",
                    "surface_kind": "object_surface",
                    "sheet": block["sheet"],
                    "bounds": block.get("bounds"),
                    "label": block.get("label", block["id"]),
                    "reason": "object_surface_is_coarse_profile_window_without_precise_chart_or_image_anchor",
                    "evidence_refs": block.get("evidence", []),
                }
            )
    return surfaces


def _document_item_relations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relations = []
    accepted_pipeline_items = [item for item in items if item["item_kind"] == "formula_dataflow_pipeline_group"]
    for item in accepted_pipeline_items:
        status = item["status"]
        relations.append(
            {
                "id": f"rel_{item['id']}_formula_feeds_visible_output",
                "type": "document_item_relation",
                "status": status,
                "relation_type": "formula_feeds_visible_output",
                "from": item["id"],
                "to": item["id"],
                "evidence_refs": item["evidence_refs"],
                "review_reasons": item["review_reasons"],
            }
        )
    return relations


def _grouping_gate_results(
    document_items: list[dict[str, Any]],
    orphan_surfaces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []
    for item in document_items:
        if item["item_kind"] == "formula_dataflow_pipeline_group":
            results.append(
                {
                    "id": f"gate_{item['id']}_formula_dataflow",
                    "type": "document_item_grouping_gate",
                    "gate_type": "formula_dataflow_gate",
                    "target_id": item["id"],
                    "status": item["status"],
                    "message": (
                        "Formula/dataflow and formula-result authority support this document item grouping."
                        if item["status"] == "accepted"
                        else "Formula/dataflow grouping is plausible, but blockers remain."
                    ),
                    "evidence_refs": item["evidence_refs"],
                }
            )
        else:
            results.append(
                {
                    "id": f"gate_{item['id']}_section_ordering",
                    "type": "document_item_grouping_gate",
                    "gate_type": "section_ordering_gate",
                    "target_id": item["id"],
                    "status": "review_required",
                    "message": "Section contains relation uses ordering evidence only and needs visual/user confirmation.",
                    "evidence_refs": item["evidence_refs"],
                }
            )
    for surface in orphan_surfaces:
        results.append(
            {
                "id": f"gate_{surface['id']}_object_anchor",
                "type": "document_item_grouping_gate",
                "gate_type": "object_anchor_gate",
                "target_id": surface["id"],
                "status": "review_required",
                "message": "Object surface lacks precise anchor/source range evidence for grouping.",
                "evidence_refs": surface["evidence_refs"],
            }
        )
    return results


def _follow_up_actions(orphan_surfaces: list[dict[str, Any]], section_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": "resolve_object_anchors",
            "priority": "high" if orphan_surfaces else "low",
            "action": "Resolve chart/image/object anchors and source ranges before grouping object surfaces with tables.",
            "done_when": "Object surfaces are attached to specific document items or explicitly left orphaned.",
        },
        {
            "id": "review_section_groupings",
            "priority": "medium" if section_items else "low",
            "action": "Review section-with-child-block groups in HTML before semantic storage.",
            "done_when": "Ordering-only section groupings are accepted, split, or rejected by visual/data/formula evidence.",
        },
    ]


def _summary(
    document_items: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    gate_results: list[dict[str, Any]],
    orphan_surfaces: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "document_item_count": len(document_items),
        "accepted_document_item_count": sum(1 for item in document_items if item["status"] == "accepted"),
        "review_required_document_item_count": sum(1 for item in document_items if item["status"] == "review_required"),
        "pipeline_group_count": sum(1 for item in document_items if item["item_kind"] == "formula_dataflow_pipeline_group"),
        "section_group_count": sum(1 for item in document_items if item["item_kind"] == "section_with_child_blocks"),
        "document_item_relation_count": len(relations),
        "accepted_relation_count": sum(1 for item in relations if item["status"] == "accepted"),
        "grouping_gate_count": len(gate_results),
        "accepted_grouping_gate_count": sum(1 for item in gate_results if item["status"] == "accepted"),
        "review_required_grouping_gate_count": sum(1 for item in gate_results if item["status"] == "review_required"),
        "orphan_surface_count": len(orphan_surfaces),
        "shared_ontology_update_count": 0,
        "checkpoint_status": "completed_no_business_semantics",
    }


def _parser_observations(
    document_items: list[dict[str, Any]],
    orphan_surfaces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Document item grouping is structural only and does not assign business semantics.",
        }
    ]
    accepted = sum(1 for item in document_items if item["status"] == "accepted")
    if accepted:
        observations.append(
            {
                "level": "info",
                "message": f"{accepted} formula/dataflow-backed document item groups are accepted.",
            }
        )
    if orphan_surfaces:
        observations.append(
            {
                "level": "warning",
                "message": f"{len(orphan_surfaces)} object surfaces need precise anchor/source-range resolution.",
            }
        )
    observations.append(
        {
            "level": "warning",
            "message": "Ordering-only section groupings remain review-required before semantic storage.",
        }
    )
    return observations


def render_google_sheets_document_item_grouping_checkpoint_section(
    checkpoint: dict[str, Any],
) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in checkpoint["summary"].items()
    )
    item_rows = "".join(
        "<tr>"
        f"<td>{_pill(item['status'], _tone(item['status']))}</td>"
        f"<td>{_esc(item['item_kind'])}</td>"
        f"<td>{_esc(item.get('sheet'))}</td>"
        f"<td>{_esc(_a1(item.get('bounds')))}</td>"
        f"<td>{_esc(item['label'])}</td>"
        f"<td>{_esc(len(item.get('member_blocks', [])) + len(item.get('member_surfaces', [])))}</td>"
        f"<td>{_esc(', '.join(item['review_reasons'][:3]))}</td>"
        "</tr>"
        for item in checkpoint["document_items"][:80]
    )
    gate_rows = "".join(
        "<tr>"
        f"<td>{_pill(item['status'], _tone(item['status']))}</td>"
        f"<td>{_esc(item['gate_type'])}</td>"
        f"<td>{_esc(item['target_id'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in checkpoint["grouping_gate_results"][:100]
    )
    orphan_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['sheet'])}</td>"
        f"<td>{_esc(_a1(item['bounds']))}</td>"
        f"<td>{_esc(item['label'])}</td>"
        f"<td>{_esc(item['reason'])}</td>"
        "</tr>"
        for item in checkpoint["orphan_surfaces"][:80]
    )
    if not orphan_rows:
        orphan_rows = '<tr><td colspan="4">No orphan object surfaces.</td></tr>'
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in checkpoint["parser_observations"]
    )
    return f"""
  <h2>Live Document Item Grouping Checkpoint</h2>
  <section class="grid">{metrics}</section>
  <h2>Document Item Groups</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Kind</th><th>Sheet</th><th>Range</th><th>Label</th><th>Members</th><th>Review Reasons</th></tr></thead><tbody>{item_rows}</tbody></table></section>
  <h2>Grouping Gates</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Gate</th><th>Target</th><th>Message</th></tr></thead><tbody>{gate_rows}</tbody></table></section>
  <h2>Orphan Object Surfaces</h2>
  <section class="panel"><table><thead><tr><th>Sheet</th><th>Range</th><th>Label</th><th>Reason</th></tr></thead><tbody>{orphan_rows}</tbody></table></section>
  <h2>Grouping Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def _blocks_by_id(block_candidates: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        block["id"]: block
        for sheet in block_candidates.get("sheets", [])
        for block in sheet.get("blocks", [])
    }


def _member_block(block: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": block["id"],
        "block_type": block.get("type"),
        "sheet": block.get("sheet"),
        "bounds": block.get("bounds"),
        "label": block.get("label", block["id"]),
    }


def _member_surface(ref: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "id": ref.get("id") or f"{role}_{_slug(ref.get('sheet'))}_{_slug(ref.get('range'))}",
        "surface_kind": ref.get("kind", "range_surface"),
        "role": role,
        "sheet": ref.get("sheet"),
        "range": ref.get("range"),
        "label": ref.get("label") or ref.get("range") or role,
        "authority": ref.get("authority", "pipeline_ref"),
    }


def _first_sheet(surfaces: list[dict[str, Any]]) -> str | None:
    for surface in surfaces:
        if surface.get("sheet"):
            return surface["sheet"]
    return None


def _parse_a1_bounds(a1_range: str | None) -> dict[str, Any] | None:
    if not a1_range:
        return None
    parts = a1_range.split(":")
    start = _cell_to_rc(parts[0])
    end = _cell_to_rc(parts[-1])
    if not start or not end:
        return None
    return {
        "start_row": min(start[0], end[0]),
        "end_row": max(start[0], end[0]),
        "start_column": min(start[1], end[1]),
        "end_column": max(start[1], end[1]),
        "a1_range": a1_range,
    }


def _cell_to_rc(cell: str) -> tuple[int, int] | None:
    match = re.match(r"^\$?([A-Za-z]+)\$?(\d+)$", str(cell).strip())
    if not match:
        return None
    col = 0
    for char in match.group(1).upper():
        col = col * 26 + ord(char) - ord("A") + 1
    return int(match.group(2)), col


def _union_bounds(bounds_list: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    valid = [item for item in bounds_list if item]
    if not valid:
        return None
    start_row = min(item["start_row"] for item in valid)
    end_row = max(item["end_row"] for item in valid)
    start_column = min(item["start_column"] for item in valid)
    end_column = max(item["end_column"] for item in valid)
    return {
        "start_row": start_row,
        "end_row": end_row,
        "start_column": start_column,
        "end_column": end_column,
        "a1_range": f"{_column_name(start_column)}{start_row}:{_column_name(end_column)}{end_row}",
    }


def _column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result or "A"


def _a1(bounds: dict[str, Any] | None) -> str:
    if not bounds:
        return ""
    return str(bounds.get("a1_range") or "")


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0


def _slug(value: Any) -> str:
    text = str(value or "none")
    text = re.sub(r"[^A-Za-z0-9가-힣]+", "_", text).strip("_").lower()
    return text or "none"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_json(path: Path) -> dict[str, Any] | None:
    return _read_json(path) if path.exists() else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape("" if value is None else str(value))


def _pill(label: str, tone: str) -> str:
    return f'<span class="pill {tone}">{_esc(label)}</span>'


def _tone(status: str) -> str:
    if status == "accepted":
        return "ok"
    if status in {"blocked", "rejected"}:
        return "bad"
    return "warn"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build document item grouping checkpoint for connected Google Sheets."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    checkpoint = build_google_sheets_document_item_grouping_checkpoint(out_dir=args.out_dir)
    write_google_sheets_document_item_grouping_checkpoint_package(
        out_dir=args.out_dir,
        checkpoint=checkpoint,
    )


if __name__ == "__main__":
    main()
