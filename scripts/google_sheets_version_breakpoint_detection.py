from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_version_breakpoint_detection(*, out_dir: Path) -> dict[str, Any]:
    out_dir = out_dir.expanduser().resolve()
    manifest = _read_json(out_dir / "live-manifest.json")
    block_candidates = _read_json(out_dir / "live-block-candidates.json")
    formula_profile = _read_json(out_dir / "live-view-formula-profile.json")
    blocker_update = _read_json(out_dir / "live-blocker-resolution-update.json")
    grouping = _read_json(out_dir / "live-document-item-grouping-checkpoint.json")

    sheet_stats = _sheet_stats(manifest, block_candidates, formula_profile, grouping)
    period_order = [sheet["name"] for sheet in manifest["workbook"]["sheets"] if _is_period_tab(sheet["name"])]
    version_groups = _version_groups(
        blocker_update["lineage_observations"].get("version_group_candidates", []),
        period_order,
        sheet_stats,
    )
    breakpoints = _breakpoints(
        blocker_update["lineage_observations"].get("version_breakpoint_candidates", []),
        sheet_stats,
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": manifest["source"]["spreadsheet_id"],
            "spreadsheet_url": manifest["source"].get("spreadsheet_url"),
            "title": manifest["source"]["title"],
            "source_artifacts": {
                "live_manifest": "live-manifest.json",
                "live_block_candidates": "live-block-candidates.json",
                "live_view_formula_profile": "live-view-formula-profile.json",
                "live_blocker_resolution_update": "live-blocker-resolution-update.json",
                "live_document_item_grouping_checkpoint": "live-document-item-grouping-checkpoint.json",
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "detection_status": "completed",
            "version_truth": "structural_version_candidates_no_semantic_promotion",
            "shared_ontology_updates": 0,
        },
        "method": {
            "name": "connected_sheets_version_breakpoint_detection",
            "authority": "deterministic_layout_formula_grouping_drift",
            "decision_policy": (
                "Use column-count groups as seeds, then attach block, formula-signature, "
                "and grouping-layout drift before repeated-family semantic evidence is used."
            ),
        },
        "sheet_stats": [sheet_stats[name] for name in period_order if name in sheet_stats],
        "version_groups": version_groups,
        "version_breakpoints": breakpoints,
        "follow_up_actions": _follow_up_actions(breakpoints),
        "summary": _summary(version_groups, breakpoints),
        "parser_observations": _parser_observations(version_groups, breakpoints),
    }
    return result


def write_google_sheets_version_breakpoint_detection_package(
    *,
    out_dir: Path,
    detection: dict[str, Any],
) -> None:
    out_dir = out_dir.expanduser().resolve()
    (out_dir / "live-version-breakpoint-detection.json").write_text(
        json.dumps(detection, ensure_ascii=False, indent=2) + "\n",
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
            live_document_item_grouping_checkpoint=_optional_json(out_dir / "live-document-item-grouping-checkpoint.json"),
            live_version_breakpoint_detection=detection,
        ),
        encoding="utf-8",
    )


def _sheet_stats(
    manifest: dict[str, Any],
    block_candidates: dict[str, Any],
    formula_profile: dict[str, Any],
    grouping: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    block_summary = {sheet["name"]: sheet.get("summary", {}) for sheet in block_candidates.get("sheets", [])}
    grouping_counts: dict[str, Counter] = defaultdict(Counter)
    for item in grouping.get("document_items", []):
        if item.get("sheet"):
            grouping_counts[item["sheet"]][item["status"]] += 1
            grouping_counts[item["sheet"]][item["item_kind"]] += 1
    signature_ids_by_sheet: dict[str, set[str]] = defaultdict(set)
    for sig in formula_profile.get("signature_groups", []):
        for sheet_name in sig.get("source_sheets", []):
            signature_ids_by_sheet[sheet_name].add(sig["id"])
    stats = {}
    for sheet in manifest["workbook"]["sheets"]:
        name = sheet["name"]
        summary = block_summary.get(name, {})
        stats[name] = {
            "sheet": name,
            "index": sheet["index"],
            "column_count": sheet["dimensions"]["column_count"],
            "row_count": sheet["dimensions"]["row_count"],
            "state": sheet["state"],
            "table_candidate_count": int(summary.get("table_candidate_count", 0)),
            "section_heading_count": int(summary.get("section_heading_count", 0)),
            "formula_region_candidate_count": int(summary.get("formula_region_candidate_count", 0)),
            "object_surface_count": int(summary.get("object_surface_count", 0)),
            "accepted_group_count": int(grouping_counts[name]["accepted"]),
            "review_required_group_count": int(grouping_counts[name]["review_required"]),
            "pipeline_group_count": int(grouping_counts[name]["formula_dataflow_pipeline_group"]),
            "section_group_count": int(grouping_counts[name]["section_with_child_blocks"]),
            "formula_signature_group_count": len(signature_ids_by_sheet[name]),
            "formula_signature_ids": sorted(signature_ids_by_sheet[name]),
        }
    return stats


def _version_groups(
    seeds: list[dict[str, Any]],
    period_order: list[str],
    sheet_stats: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    position = {name: index for index, name in enumerate(period_order)}
    groups = []
    for seed in seeds:
        newest = seed["newest_tab"]
        oldest = seed["oldest_tab"]
        if newest not in position or oldest not in position:
            member_tabs = [name for name, stat in sheet_stats.items() if stat["column_count"] == seed["column_count"] and _is_period_tab(name)]
        else:
            start, end = sorted([position[newest], position[oldest]])
            member_tabs = period_order[start : end + 1]
        stats = [sheet_stats[name] for name in member_tabs if name in sheet_stats]
        signature_counts = {stat["formula_signature_group_count"] for stat in stats}
        section_counts = {stat["section_heading_count"] for stat in stats}
        grouping_counts = {stat["section_group_count"] + stat["pipeline_group_count"] for stat in stats}
        review_reasons = []
        if len(signature_counts) > 1:
            review_reasons.append("formula_signature_count_drift_within_group")
        if len(section_counts) > 1:
            review_reasons.append("section_count_drift_within_group")
        if len(grouping_counts) > 1:
            review_reasons.append("document_grouping_count_drift_within_group")
        groups.append(
            {
                "id": seed["id"],
                "type": "version_group",
                "status": "review_required" if review_reasons else "accepted",
                "newest_tab": newest,
                "oldest_tab": oldest,
                "member_tabs": member_tabs,
                "column_count": seed["column_count"],
                "evidence": {
                    "formula_signature_group_counts": sorted(signature_counts),
                    "section_heading_counts": sorted(section_counts),
                    "document_grouping_counts": sorted(grouping_counts),
                },
                "review_reasons": review_reasons,
                "evidence_refs": ["live-blocker-resolution-update.json", "live-document-item-grouping-checkpoint.json"],
            }
        )
    return groups


def _breakpoints(
    seeds: list[dict[str, Any]],
    sheet_stats: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []
    for seed in seeds:
        newer = sheet_stats.get(seed["newer_tab"], {})
        older = sheet_stats.get(seed["older_tab"], {})
        drift = _drift(newer, older)
        strong_signals = [
            key
            for key in [
                "column_count_delta",
                "table_candidate_count_delta",
                "section_heading_count_delta",
                "formula_signature_group_count_delta",
                "document_grouping_count_delta",
            ]
            if abs(drift.get(key, 0)) > 0
        ]
        status = "accepted" if len(strong_signals) >= 2 or abs(drift["column_count_delta"]) >= 2 else "review_required"
        review_reasons = [] if status == "accepted" else ["column_count_only_breakpoint_needs_layout_or_formula_confirmation"]
        results.append(
            {
                "id": seed["id"],
                "type": "version_breakpoint",
                "status": status,
                "newer_tab": seed["newer_tab"],
                "older_tab": seed["older_tab"],
                "drift": drift,
                "strong_signals": strong_signals,
                "review_reasons": review_reasons,
                "evidence_refs": ["live-blocker-resolution-update.json", "live-block-candidates.json", "live-document-item-grouping-checkpoint.json"],
            }
        )
    return results


def _drift(newer: dict[str, Any], older: dict[str, Any]) -> dict[str, Any]:
    newer_sigs = set(newer.get("formula_signature_ids", []))
    older_sigs = set(older.get("formula_signature_ids", []))
    union = newer_sigs | older_sigs
    intersection = newer_sigs & older_sigs
    grouping_newer = newer.get("section_group_count", 0) + newer.get("pipeline_group_count", 0)
    grouping_older = older.get("section_group_count", 0) + older.get("pipeline_group_count", 0)
    return {
        "column_count_delta": int(newer.get("column_count", 0)) - int(older.get("column_count", 0)),
        "table_candidate_count_delta": int(newer.get("table_candidate_count", 0)) - int(older.get("table_candidate_count", 0)),
        "section_heading_count_delta": int(newer.get("section_heading_count", 0)) - int(older.get("section_heading_count", 0)),
        "formula_signature_group_count_delta": int(newer.get("formula_signature_group_count", 0)) - int(older.get("formula_signature_group_count", 0)),
        "document_grouping_count_delta": grouping_newer - grouping_older,
        "formula_signature_jaccard": round(len(intersection) / len(union), 3) if union else 1,
    }


def _follow_up_actions(breakpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    review_required = sum(1 for item in breakpoints if item["status"] == "review_required")
    return [
        {
            "id": "review_weak_version_breakpoints",
            "priority": "medium" if review_required else "low",
            "action": "Review breakpoints supported only by weak layout drift before using them for semantic promotion evidence.",
            "done_when": "Each review-required breakpoint is accepted, merged with a neighboring version group, or rejected.",
        }
    ]


def _summary(groups: list[dict[str, Any]], breakpoints: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version_group_count": len(groups),
        "accepted_version_group_count": sum(1 for item in groups if item["status"] == "accepted"),
        "review_required_version_group_count": sum(1 for item in groups if item["status"] == "review_required"),
        "version_breakpoint_count": len(breakpoints),
        "accepted_version_breakpoint_count": sum(1 for item in breakpoints if item["status"] == "accepted"),
        "review_required_version_breakpoint_count": sum(1 for item in breakpoints if item["status"] == "review_required"),
        "shared_ontology_update_count": 0,
        "detection_status": "completed_no_semantic_promotion",
    }


def _parser_observations(groups: list[dict[str, Any]], breakpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "level": "info",
            "message": "Version detection is structural evidence only and does not promote semantic concepts.",
        },
        {
            "level": "info",
            "message": f"{sum(1 for item in breakpoints if item['status'] == 'accepted')} breakpoints have multi-signal structural drift.",
        },
        {
            "level": "warning",
            "message": f"{sum(1 for item in groups if item['status'] == 'review_required')} version groups still contain intra-group drift.",
        },
    ]


def render_google_sheets_version_breakpoint_detection_section(detection: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in detection["summary"].items()
    )
    group_rows = "".join(
        "<tr>"
        f"<td>{_pill(item['status'], _tone(item['status']))}</td>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['newest_tab'])} - {_esc(item['oldest_tab'])}</td>"
        f"<td>{_esc(item['column_count'])}</td>"
        f"<td>{_esc(len(item['member_tabs']))}</td>"
        f"<td>{_esc(', '.join(item['review_reasons']))}</td>"
        "</tr>"
        for item in detection["version_groups"]
    )
    breakpoint_rows = "".join(
        "<tr>"
        f"<td>{_pill(item['status'], _tone(item['status']))}</td>"
        f"<td>{_esc(item['newer_tab'])} -> {_esc(item['older_tab'])}</td>"
        f"<td>{_esc(item['drift']['column_count_delta'])}</td>"
        f"<td>{_esc(', '.join(item['strong_signals']))}</td>"
        f"<td>{_esc(', '.join(item['review_reasons']))}</td>"
        "</tr>"
        for item in detection["version_breakpoints"]
    )
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in detection["parser_observations"]
    )
    return f"""
  <h2>Live Version Breakpoint Detection</h2>
  <section class="grid">{metrics}</section>
  <h2>Version Groups</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>ID</th><th>Tabs</th><th>Columns</th><th>Members</th><th>Review Reasons</th></tr></thead><tbody>{group_rows}</tbody></table></section>
  <h2>Version Breakpoints</h2>
  <section class="panel"><table><thead><tr><th>Status</th><th>Transition</th><th>Column Delta</th><th>Strong Signals</th><th>Review Reasons</th></tr></thead><tbody>{breakpoint_rows}</tbody></table></section>
  <h2>Version Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def _is_period_tab(name: str) -> bool:
    return bool(re.match(r"^\d{2}_\d{4}$", name))


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
    if status == "blocked":
        return "bad"
    return "warn"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect version breakpoints for connected Google Sheets period tabs."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    detection = build_google_sheets_version_breakpoint_detection(out_dir=args.out_dir)
    write_google_sheets_version_breakpoint_detection_package(
        out_dir=args.out_dir,
        detection=detection,
    )


if __name__ == "__main__":
    main()
