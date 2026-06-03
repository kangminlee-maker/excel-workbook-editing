from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"


def build_google_sheets_carry_forward_review_packet(*, out_dir: Path) -> dict[str, Any]:
    out_dir = out_dir.expanduser().resolve()
    manifest = _read_json(out_dir / "live-manifest.json")
    grouping = _read_json(out_dir / "live-document-item-grouping-checkpoint.json")
    version = _read_json(out_dir / "live-version-breakpoint-detection.json")
    formula = _read_json(out_dir / "live-formula-result-authority-checkpoint.json")
    semantic_gate = _read_json(out_dir / "live-semantic-gate-iteration.json")

    lanes = [
        _grouping_lane(grouping),
        _formula_lane(formula),
        _metric_lane(semantic_gate),
        _version_lane(version),
    ]
    decision_items = [item for lane in lanes for item in lane["decision_items"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": manifest["source"]["spreadsheet_id"],
            "spreadsheet_url": manifest["source"].get("spreadsheet_url"),
            "title": manifest["source"]["title"],
            "source_artifacts": {
                "live_document_item_grouping_checkpoint": "live-document-item-grouping-checkpoint.json",
                "live_version_breakpoint_detection": "live-version-breakpoint-detection.json",
                "live_formula_result_authority_checkpoint": "live-formula-result-authority-checkpoint.json",
                "live_semantic_gate_iteration": "live-semantic-gate-iteration.json",
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "packet_status": "review_packet_only",
            "parser_truth": "no_new_parser_claims",
            "shared_ontology_updates": 0,
        },
        "method": {
            "name": "connected_sheets_carry_forward_review_packet",
            "authority": "review_packet_from_existing_carry_forward_artifacts",
            "decision_policy": (
                "Group carry-forward queues into reviewer decision lanes. "
                "Do not accept grouping, formula, version, metric, semantic, or shared ontology claims."
            ),
        },
        "review_lanes": lanes,
        "decision_items": decision_items,
        "suggested_review_order": [
            "formula_authority",
            "document_item_grouping",
            "metric_equivalence",
            "version_breakpoints",
        ],
        "summary": _summary(lanes, decision_items),
        "parser_observations": _parser_observations(lanes),
    }


def write_google_sheets_carry_forward_review_packet_package(
    *,
    out_dir: Path,
    packet: dict[str, Any],
) -> None:
    out_dir = out_dir.expanduser().resolve()
    (out_dir / "live-carry-forward-review-packet.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
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
            live_version_breakpoint_detection=_optional_json(out_dir / "live-version-breakpoint-detection.json"),
            live_semantic_gate_iteration=_optional_json(out_dir / "live-semantic-gate-iteration.json"),
            live_carry_forward_review_packet=packet,
        ),
        encoding="utf-8",
    )


def _grouping_lane(grouping: dict[str, Any]) -> dict[str, Any]:
    review_items = [
        item
        for item in grouping["document_items"]
        if item["status"] == "review_required"
    ]
    orphan_items = grouping["orphan_surfaces"]
    decision_items = [
        _decision_item(
            id_="grouping_review_section_groups",
            lane="document_item_grouping",
            priority="high",
            status="pending_human_review",
            question="Which section/text/table groupings should be accepted, split, or rejected before semantic storage?",
            impact="Accepted groups become the structural units consumed by semantic iteration.",
            recommended_next_action="Review representative section groups first, then decide whether ordering-only groups need visual capture or can stay review-required.",
            evidence_refs=["live-document-item-grouping-checkpoint.json"],
            sample_items=[
                _compact_grouping_item(item)
                for item in review_items
                if item["item_kind"] == "section_with_child_blocks"
            ][:15],
            total_item_count=sum(1 for item in review_items if item["item_kind"] == "section_with_child_blocks"),
        ),
        _decision_item(
            id_="grouping_review_formula_pipeline_groups",
            lane="document_item_grouping",
            priority="high",
            status="blocked_by_formula_authority",
            question="Which FC_DATA-dependent formula pipeline groups can be accepted after formula-result authority is resolved?",
            impact="These groups should not become semantic report surfaces until output authority is available.",
            recommended_next_action="Resolve formula-result authority first; then re-run grouping acceptance for blocked pipeline groups.",
            evidence_refs=["live-document-item-grouping-checkpoint.json", "live-formula-result-authority-checkpoint.json"],
            sample_items=[
                _compact_grouping_item(item)
                for item in review_items
                if item["item_kind"] == "formula_dataflow_pipeline_group"
            ][:15],
            total_item_count=sum(1 for item in review_items if item["item_kind"] == "formula_dataflow_pipeline_group"),
        ),
        _decision_item(
            id_="grouping_review_object_anchors",
            lane="document_item_grouping",
            priority="medium",
            status="pending_anchor_resolution",
            question="Which chart/image/object surfaces belong to which table or section?",
            impact="Object anchors can change human-perceived document hierarchy.",
            recommended_next_action="Resolve precise object anchors/source ranges or leave coarse object surfaces orphaned.",
            evidence_refs=["live-document-item-grouping-checkpoint.json", "live-manifest.json"],
            sample_items=[_compact_orphan_item(item) for item in orphan_items[:15]],
            total_item_count=len(orphan_items),
        ),
    ]
    return _lane(
        id_="lane_document_item_grouping",
        title="Document Item Grouping",
        priority="high",
        status="review_required",
        description="Structural grouping exists, but only formula/dataflow-backed groups are accepted.",
        decision_items=decision_items,
    )


def _formula_lane(formula: dict[str, Any]) -> dict[str, Any]:
    blocked_ranges = [
        item
        for item in formula["range_authority_results"]
        if item["status"] == "blocked"
    ]
    blocked_pipelines = [
        item
        for item in formula["pipeline_authority_results"]
        if item["status"] == "blocked"
    ]
    decision_items = [
        _decision_item(
            id_="formula_review_fc_data_errors",
            lane="formula_authority",
            priority="high",
            status="blocked",
            question="Should FC_DATA effective errors be treated as source data defects, expected blanks/errors, or blockers for all downstream reports?",
            impact="This determines whether FC_DATA-dependent report surfaces can be accepted or must remain blocked.",
            recommended_next_action="Inspect current/source FC_DATA error cells and decide whether they are acceptable diagnostics or data defects to reconcile.",
            evidence_refs=["live-formula-result-authority-checkpoint.json", "source-fc-data-grid-formula-window.json"],
            sample_items=[_compact_range_result(item) for item in blocked_ranges],
            total_item_count=len(blocked_ranges),
        ),
        _decision_item(
            id_="formula_review_report_output_probes",
            lane="formula_authority",
            priority="high",
            status="blocked",
            question="Which blocked report output ranges should receive targeted effective-value probes next?",
            impact="Targeted probes can move report pipelines from blocked to accepted/review-required formula authority.",
            recommended_next_action="Probe representative FC_DATA-dependent report outputs by version group before probing every tab.",
            evidence_refs=["live-formula-result-authority-checkpoint.json", "live-version-breakpoint-detection.json"],
            sample_items=[_compact_pipeline_result(item) for item in blocked_pipelines[:20]],
            total_item_count=len(blocked_pipelines),
        ),
    ]
    return _lane(
        id_="lane_formula_authority",
        title="Formula Result Authority",
        priority="high",
        status="blocked",
        description="FC_DATA and FC_DATA-dependent report outputs remain the strongest blockers.",
        decision_items=decision_items,
    )


def _metric_lane(semantic_gate: dict[str, Any]) -> dict[str, Any]:
    checks = semantic_gate["metric_equivalence_checks"]
    decision_items = [
        _decision_item(
            id_=f"metric_review_{check['visible_label_bucket']}",
            lane="metric_equivalence",
            priority="high",
            status="review_required",
            question=f"Can visible {check['visible_label_bucket']} surfaces be treated as the same 결제액 metric, or should they be scoped variants?",
            impact="This prevents 매출/순매출/결제액 labels from collapsing into one misleading ontology concept.",
            recommended_next_action="Compare basis, refund treatment, period axis, filters, aggregation, lineage, role, and formula authority.",
            evidence_refs=check["evidence_refs"],
            sample_items=check["sample_surfaces"],
            total_item_count=check["surface_count"],
        )
        for check in checks
    ]
    return _lane(
        id_="lane_metric_equivalence",
        title="Metric Equivalence",
        priority="high",
        status="review_required",
        description="Visible metric labels need scoped equivalence decisions before semantic storage.",
        decision_items=decision_items,
    )


def _version_lane(version: dict[str, Any]) -> dict[str, Any]:
    review_groups = [
        item
        for item in version["version_groups"]
        if item["status"] == "review_required"
    ]
    review_breakpoints = [
        item
        for item in version["version_breakpoints"]
        if item["status"] == "review_required"
    ]
    decision_items = [
        _decision_item(
            id_="version_review_intragroup_drift",
            lane="version_breakpoints",
            priority="medium",
            status="review_required",
            question="Should review-required version groups be split further before repeated evidence is used?",
            impact="Version groups define which tabs may count as repeated-family evidence.",
            recommended_next_action="Inspect groups with formula/grouping drift and split only where layout meaning changes.",
            evidence_refs=["live-version-breakpoint-detection.json"],
            sample_items=[_compact_version_group(item) for item in review_groups],
            total_item_count=len(review_groups),
        ),
        _decision_item(
            id_="version_review_weak_breakpoints",
            lane="version_breakpoints",
            priority="medium",
            status="review_required",
            question="Are column-count-only breakpoints real format/organization version changes or noise?",
            impact="Weak breakpoints should not support shared ontology promotion until accepted.",
            recommended_next_action="Review weak breakpoints after grouping/metric decisions; merge or accept them based on visible layout changes.",
            evidence_refs=["live-version-breakpoint-detection.json"],
            sample_items=[_compact_breakpoint(item) for item in review_breakpoints[:20]],
            total_item_count=len(review_breakpoints),
        ),
    ]
    return _lane(
        id_="lane_version_breakpoints",
        title="Version Breakpoints",
        priority="medium",
        status="review_required",
        description="Most version evidence is usable, but weak breakpoints should not drive promotion yet.",
        decision_items=decision_items,
    )


def _lane(
    *,
    id_: str,
    title: str,
    priority: str,
    status: str,
    description: str,
    decision_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": id_,
        "type": "review_lane",
        "title": title,
        "priority": priority,
        "status": status,
        "description": description,
        "decision_item_count": len(decision_items),
        "total_evidence_item_count": sum(item["total_item_count"] for item in decision_items),
        "decision_items": decision_items,
    }


def _decision_item(
    *,
    id_: str,
    lane: str,
    priority: str,
    status: str,
    question: str,
    impact: str,
    recommended_next_action: str,
    evidence_refs: list[str],
    sample_items: list[dict[str, Any]],
    total_item_count: int,
) -> dict[str, Any]:
    return {
        "id": id_,
        "type": "review_decision_item",
        "lane": lane,
        "priority": priority,
        "status": status,
        "question": question,
        "impact": impact,
        "recommended_next_action": recommended_next_action,
        "total_item_count": total_item_count,
        "sample_items": sample_items,
        "evidence_refs": evidence_refs,
    }


def _summary(lanes: list[dict[str, Any]], decision_items: list[dict[str, Any]]) -> dict[str, Any]:
    priority_counts = Counter(item["priority"] for item in decision_items)
    status_counts = Counter(item["status"] for item in decision_items)
    return {
        "review_lane_count": len(lanes),
        "decision_item_count": len(decision_items),
        "high_priority_decision_item_count": priority_counts["high"],
        "medium_priority_decision_item_count": priority_counts["medium"],
        "blocked_decision_item_count": status_counts["blocked"] + status_counts["blocked_by_formula_authority"],
        "review_required_decision_item_count": status_counts["review_required"],
        "total_evidence_item_count": sum(item["total_item_count"] for item in decision_items),
        "shared_ontology_update_count": 0,
        "packet_status": "review_packet_only",
    }


def _parser_observations(lanes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "level": "info",
            "message": "Carry-forward review packet groups existing review queues and does not create parser truth.",
        },
        {
            "level": "warning",
            "message": "Formula authority and metric equivalence are high-priority blockers for semantic storage.",
        },
        {
            "level": "info",
            "message": f"{len(lanes)} review lanes are ready for human feedback in the HTML viewer.",
        },
    ]


def render_google_sheets_carry_forward_review_packet_section(packet: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in packet["summary"].items()
    )
    lane_rows = "".join(
        "<tr>"
        f"<td>{_pill(lane['priority'], _priority_tone(lane['priority']))}</td>"
        f"<td>{_pill(lane['status'], _tone(lane['status']))}</td>"
        f"<td>{_esc(lane['title'])}</td>"
        f"<td>{_esc(lane['decision_item_count'])}</td>"
        f"<td>{_esc(lane['total_evidence_item_count'])}</td>"
        f"<td>{_esc(lane['description'])}</td>"
        "</tr>"
        for lane in packet["review_lanes"]
    )
    decision_rows = "".join(
        "<tr>"
        f"<td>{_pill(item['priority'], _priority_tone(item['priority']))}</td>"
        f"<td>{_pill(item['status'], _tone(item['status']))}</td>"
        f"<td>{_esc(item['lane'])}</td>"
        f"<td>{_esc(item['question'])}</td>"
        f"<td>{_esc(item['total_item_count'])}</td>"
        f"<td>{_esc(item['recommended_next_action'])}</td>"
        "</tr>"
        for item in packet["decision_items"]
    )
    sample_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['lane'])}</td>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td><code>{_esc(item['sample_items'][:5])}</code></td>"
        "</tr>"
        for item in packet["decision_items"]
    )
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in packet["parser_observations"]
    )
    return f"""
  <h2>Live Carry-forward Review Packet</h2>
  <section class="grid">{metrics}</section>
  <h2>Review Lanes</h2>
  <section class="panel"><table><thead><tr><th>Priority</th><th>Status</th><th>Lane</th><th>Decision Items</th><th>Evidence Items</th><th>Description</th></tr></thead><tbody>{lane_rows}</tbody></table></section>
  <h2>Review Decision Items</h2>
  <section class="panel"><table><thead><tr><th>Priority</th><th>Status</th><th>Lane</th><th>Question</th><th>Items</th><th>Recommended Next Action</th></tr></thead><tbody>{decision_rows}</tbody></table></section>
  <h2>Decision Samples</h2>
  <section class="panel"><table><thead><tr><th>Lane</th><th>Decision</th><th>Sample Items</th></tr></thead><tbody>{sample_rows}</tbody></table></section>
  <h2>Carry-forward Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def _compact_grouping_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "kind": item["item_kind"],
        "sheet": item.get("sheet"),
        "range": (item.get("bounds") or {}).get("a1_range"),
        "label": item.get("label"),
        "review_reasons": item.get("review_reasons", [])[:3],
    }


def _compact_orphan_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "sheet": item.get("sheet"),
        "range": (item.get("bounds") or {}).get("a1_range"),
        "label": item.get("label"),
        "reason": item.get("reason"),
    }


def _compact_range_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "source_kind": item.get("source_kind"),
        "sheet": item.get("sheet"),
        "range": item.get("range"),
        "blockers": item.get("blockers", []),
        "error_samples": item.get("error_samples", [])[:5],
    }


def _compact_pipeline_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["pipeline_id"],
        "role": item.get("role"),
        "sheet": item.get("sheet"),
        "range": item.get("range"),
        "authority_basis": item.get("authority_basis"),
        "blockers": item.get("blockers", []),
    }


def _compact_version_group(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "tabs": f"{item['newest_tab']} - {item['oldest_tab']}",
        "member_count": len(item.get("member_tabs", [])),
        "review_reasons": item.get("review_reasons", []),
        "evidence": item.get("evidence", {}),
    }


def _compact_breakpoint(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "transition": f"{item['newer_tab']} -> {item['older_tab']}",
        "drift": item.get("drift", {}),
        "review_reasons": item.get("review_reasons", []),
    }


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
    if "blocked" in status:
        return "bad"
    if status in {"accepted", "complete"}:
        return "ok"
    return "warn"


def _priority_tone(priority: str) -> str:
    if priority == "high":
        return "bad"
    if priority == "medium":
        return "warn"
    return "ok"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build carry-forward review packet for connected Google Sheets."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    packet = build_google_sheets_carry_forward_review_packet(out_dir=args.out_dir)
    write_google_sheets_carry_forward_review_packet_package(
        out_dir=args.out_dir,
        packet=packet,
    )


if __name__ == "__main__":
    main()
