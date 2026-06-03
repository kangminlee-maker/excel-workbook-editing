from __future__ import annotations

import argparse
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google_sheets_live_manifest import render_live_manifest_html


SCHEMA_VERSION = "0.1"
SOURCE_SPREADSHEET_ID = "1CPfJoD6VlChrev00xmagW6qJ2x7eNoJnlQeKe9AMYrs"
SOURCE_SPREADSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1CPfJoD6VlChrev00xmagW6qJ2x7eNoJnlQeKe9AMYrs/edit"
)


def build_google_sheets_blocker_resolution_update(
    *,
    out_dir: Path,
    fc_data_source_url: str,
    formula_result_authority: str,
    local_boundary: str,
    repeated_workbook_family: str,
    reporting_basis: str,
) -> dict[str, Any]:
    out_dir = out_dir.expanduser().resolve()
    metadata = _read_json(out_dir / "source-fc-data-broker-metadata.json")
    values_window = _read_json(out_dir / "source-fc-data-values-window.json")
    formula_window = _read_json(out_dir / "source-fc-data-formula-window.json")

    metadata_payload = _payload(metadata)
    values_payload = _payload(values_window)
    formula_payload = _payload(formula_window)
    tabs = metadata_payload.get("tabs", [])
    fc_data_tab = next((tab for tab in tabs if tab.get("title") == "FC_DATA"), {})
    version_groups, version_breakpoints = _version_breakpoint_candidates(tabs)
    nested_imports = _nested_importrange_dependencies(formula_payload)
    displayed_errors = _displayed_error_samples(values_payload)

    status_items = [
        {
            "id": "direct_fc_data_source_authority",
            "status": "resolved",
            "meaning": "사용자가 제공한 FC_DATA 원본 spreadsheet을 broker read-only smoke로 직접 검증했다.",
            "evidence_refs": [
                "source-fc-data-broker-metadata.json",
                "source-fc-data-values-window.json",
                "source-fc-data-formula-window.json",
            ],
        },
        {
            "id": "nested_importrange_lineage_authority",
            "status": "follow_up_required",
            "meaning": "FC_DATA 내부 IMPORTRANGE가 다시 다른 원본/range를 가리키므로 full raw lineage 추적 시 별도 권한 확인이 필요하다.",
            "evidence_refs": ["source-fc-data-formula-window.json"],
        },
        {
            "id": "formula_result_authority",
            "status": "open",
            "meaning": "표시값과 수식 텍스트는 확인했지만 결과값 authority는 대상 range별 검산이 필요하다.",
            "evidence_refs": [
                "source-fc-data-values-window.json",
                "source-fc-data-formula-window.json",
            ],
        },
        {
            "id": "local_boundary",
            "status": "resolved_by_user",
            "meaning": "local semantic ontology boundary는 전사레벨 현황 보고 문서로 해석한다.",
            "evidence_refs": ["user_feedback:2026-06-02"],
        },
        {
            "id": "repeated_workbook_family_evidence",
            "status": "partially_resolved_version_detection_required",
            "meaning": "모든 period 탭은 반복문서이나 포맷 업데이트와 부서 재구성에 따른 version breakpoint를 먼저 나눠야 한다.",
            "evidence_refs": ["source-fc-data-broker-metadata.json"],
        },
        {
            "id": "reporting_basis",
            "status": "resolved_by_user",
            "meaning": "이 문서는 K-IFRS 매출 계산서가 아니라 cash-basis 결제액/운영 현황 보고 문서로 해석한다.",
            "evidence_refs": ["user_feedback:2026-06-02"],
        },
    ]

    next_actions = [
        {
            "id": "rerun_authority_aware_stages",
            "action": "Stage 42-50 계열 산출물을 이 resolution update를 입력으로 다시 생성한다.",
            "done_when": "source/local-boundary/reporting-basis blocker 표현이 최신 상태로 반영되고, 미해결 항목만 carry-forward 된다.",
        },
        {
            "id": "formula_result_authority_checkpoint",
            "action": "accepted output range와 FC_DATA 핵심 range를 FORMATTED_VALUE, UNFORMATTED_VALUE, FORMULA 관점에서 대조하고 error 상태를 분류한다.",
            "done_when": "formula-result authority가 range별 accepted/review_required/blocked 상태로 분리된다.",
        },
        {
            "id": "version_breakpoint_detection",
            "action": "period 탭을 column count, header band, formula signature, 조직/부서 label 변화로 clustering한다.",
            "done_when": "반복 workbook-family evidence가 version별 before/after 그룹으로 분리된다.",
        },
        {
            "id": "semantic_rebasis_to_cash_basis",
            "action": "K-IFRS/K-GAAP 매출 의미를 공식 산출 basis로 쓰지 않고 cash-basis payment/status reporting 의미로 재라벨링한다.",
            "done_when": "semantic proposal과 shared alignment review가 cash-basis reporting을 기준으로 blocker와 candidate를 설명한다.",
        },
        {
            "id": "nested_importrange_lineage_follow_up",
            "action": "full raw lineage가 필요하면 FC_DATA 내부 IMPORTRANGE의 source argument와 import range를 별도 source authority 대상으로 승격한다.",
            "done_when": "중첩 원본 spreadsheet/range 접근 여부가 별도 gate 결과로 기록된다.",
        },
    ]

    resolved_count = len(
        [item for item in status_items if item["status"] in {"resolved", "resolved_by_user"}]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "live_inspection_dir": str(out_dir),
            "source_spreadsheet_id": metadata_payload.get("spreadsheet_id", SOURCE_SPREADSHEET_ID),
            "source_spreadsheet_url": fc_data_source_url,
            "source_title": metadata_payload.get("title", ""),
            "source_artifacts": {
                "metadata": "source-fc-data-broker-metadata.json",
                "values_window": "source-fc-data-values-window.json",
                "formula_window": "source-fc-data-formula-window.json",
            },
        },
        "authority": {
            "update_status": "blocker_resolution_recorded",
            "parser_truth": "no_new_parser_claims_until_rerun",
            "shared_ontology_updates": 0,
        },
        "method": {
            "name": "connected_sheets_blocker_resolution_update",
            "authority": "user_feedback_plus_broker_smoke_evidence",
            "decision_policy": (
                "Record resolved and still-open blockers after human feedback and broker source smoke. "
                "Do not silently mutate prior semantic or shared-alignment truth; later stages must rerun "
                "against this update."
            ),
        },
        "user_inputs": {
            "fc_data_source_url": fc_data_source_url,
            "formula_result_authority": formula_result_authority,
            "local_boundary": local_boundary,
            "repeated_workbook_family": repeated_workbook_family,
            "reporting_basis": reporting_basis,
        },
        "source_smoke": {
            "metadata": {
                "ok": bool(metadata.get("ok")),
                "title": metadata_payload.get("title", ""),
                "tab_count": len(tabs),
                "hidden_tab_count": len([tab for tab in tabs if tab.get("hidden")]),
                "fc_data": {
                    "present": bool(fc_data_tab),
                    "sheet_id": fc_data_tab.get("sheet_id"),
                    "row_count": fc_data_tab.get("row_count"),
                    "column_count": fc_data_tab.get("column_count"),
                },
                "policy": _policy_summary(metadata_payload),
            },
            "values_window": _window_smoke(values_window, values_payload),
            "formula_window": _window_smoke(formula_window, formula_payload),
        },
        "lineage_observations": {
            "nested_importrange_dependencies": nested_imports,
            "displayed_error_samples": displayed_errors,
            "version_group_candidates": version_groups,
            "version_breakpoint_candidates": version_breakpoints,
        },
        "blocker_status": status_items,
        "next_actions": next_actions,
        "summary": {
            "resolved_blocker_count": resolved_count,
            "open_blocker_count": len([item for item in status_items if item["status"] == "open"]),
            "follow_up_blocker_count": len(
                [item for item in status_items if "required" in item["status"]]
            ),
            "version_group_candidate_count": len(version_groups),
            "version_breakpoint_candidate_count": len(version_breakpoints),
            "nested_importrange_count": len(nested_imports),
            "displayed_error_sample_count": len(displayed_errors),
            "shared_ontology_update_count": 0,
        },
        "parser_observations": [
            {
                "level": "info",
                "message": "Direct FC_DATA source authority is verified by broker metadata, values-window, and formula-window smoke.",
            },
            {
                "level": "warning",
                "message": "Formula-result authority remains range-specific and requires targeted validation before numeric semantic acceptance.",
            },
            {
                "level": "warning",
                "message": "Cash-basis payment/status reporting must replace K-IFRS or GAAP revenue as the interpretation basis for this document.",
            },
        ],
    }


def write_google_sheets_blocker_resolution_update_package(
    *,
    out_dir: Path,
    update: dict[str, Any],
) -> None:
    out_dir = out_dir.expanduser().resolve()
    update_path = out_dir / "live-blocker-resolution-update.json"
    update_path.write_text(
        json.dumps(update, ensure_ascii=False, indent=2) + "\n",
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
            live_blocker_resolution_update=update,
        ),
        encoding="utf-8",
    )


def render_google_sheets_blocker_resolution_update_section(update: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in update["summary"].items()
    )
    status_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['meaning'])}</td>"
        f"<td>{_esc(', '.join(item['evidence_refs']))}</td>"
        "</tr>"
        for item in update["blocker_status"]
    )
    source = update["source_smoke"]
    source_rows = "".join(
        "<tr>"
        f"<td>{_esc(label)}</td>"
        f"<td>{_esc(value)}</td>"
        "</tr>"
        for label, value in [
            ("source title", update["source"]["source_title"]),
            ("metadata ok", source["metadata"]["ok"]),
            ("tab count", source["metadata"]["tab_count"]),
            ("FC_DATA", source["metadata"]["fc_data"]),
            ("values window", source["values_window"]),
            ("formula window", source["formula_window"]),
        ]
    )
    version_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['newer_tab'])}</td>"
        f"<td>{_esc(item['older_tab'])}</td>"
        f"<td>{_esc(item['newer_column_count'])} → {_esc(item['older_column_count'])}</td>"
        f"<td>{_esc(item['reason'])}</td>"
        "</tr>"
        for item in update["lineage_observations"]["version_breakpoint_candidates"][:24]
    )
    if not version_rows:
        version_rows = '<tr><td colspan="5">No version breakpoint candidates found.</td></tr>'
    nested_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['cell'])}</td>"
        f"<td><code>{_esc(item['formula'])}</code></td>"
        f"<td>{_esc(item['source_argument'])}</td>"
        f"<td>{_esc(item['import_range'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        "</tr>"
        for item in update["lineage_observations"]["nested_importrange_dependencies"]
    )
    if not nested_rows:
        nested_rows = '<tr><td colspan="5">No nested IMPORTRANGE dependencies found.</td></tr>'
    action_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['action'])}</td>"
        f"<td>{_esc(item['done_when'])}</td>"
        "</tr>"
        for item in update["next_actions"]
    )
    return f"""
  <h2>Live Blocker Resolution Update</h2>
  <section class="grid">{metrics}</section>
  <h2>Resolved / Open Blockers</h2>
  <section class="panel"><table><thead><tr><th>ID</th><th>Status</th><th>Meaning</th><th>Evidence</th></tr></thead><tbody>{status_rows}</tbody></table></section>
  <h2>FC_DATA Source Smoke</h2>
  <section class="panel"><table><thead><tr><th>Item</th><th>Evidence</th></tr></thead><tbody>{source_rows}</tbody></table></section>
  <h2>Nested Source Lineage</h2>
  <section class="panel"><table><thead><tr><th>Cell</th><th>Formula</th><th>Source Argument</th><th>Import Range</th><th>Status</th></tr></thead><tbody>{nested_rows}</tbody></table></section>
  <h2>Version Breakpoint Candidates</h2>
  <section class="panel"><table><thead><tr><th>ID</th><th>Newer Tab</th><th>Older Tab</th><th>Column Change</th><th>Reason</th></tr></thead><tbody>{version_rows}</tbody></table></section>
  <h2>Next Authority Actions</h2>
  <section class="panel"><table><thead><tr><th>ID</th><th>Action</th><th>Done When</th></tr></thead><tbody>{action_rows}</tbody></table></section>
"""


def _payload(response: dict[str, Any]) -> dict[str, Any]:
    payload = response.get("payload")
    if isinstance(payload, dict):
        return payload
    return response


def _policy_summary(payload: dict[str, Any]) -> dict[str, Any]:
    for artifact in payload.get("artifacts", []):
        if artifact.get("kind") == "broker_policy":
            return artifact.get("summary", {})
    return {}


def _window_smoke(response: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    windows = payload.get("windows", [])
    return {
        "ok": bool(response.get("ok")),
        "operation": payload.get("operation"),
        "requested_ranges": payload.get("requested_ranges", []),
        "window_count": len(windows),
        "row_count": sum(window.get("row_count", 0) for window in windows),
        "column_count_max": max([window.get("column_count", 0) for window in windows] or [0]),
        "policy": _policy_summary(payload),
    }


def _nested_importrange_dependencies(payload: dict[str, Any]) -> list[dict[str, Any]]:
    dependencies = []
    for cell, value in _iter_window_cells(payload):
        if not isinstance(value, str) or "IMPORTRANGE" not in value.upper():
            continue
        match = re.search(r"IMPORTRANGE\(([^,]+),\s*\"([^\"]+)\"", value, re.IGNORECASE)
        dependencies.append(
            {
                "cell": cell,
                "formula": value,
                "source_argument": match.group(1).strip() if match else "",
                "import_range": match.group(2).strip() if match else "",
                "status": "requires_follow_up_if_full_raw_lineage_needed",
            }
        )
    return dependencies


def _displayed_error_samples(payload: dict[str, Any]) -> list[dict[str, Any]]:
    samples = []
    for cell, value in _iter_window_cells(payload):
        if isinstance(value, str) and value.startswith("#"):
            samples.append({"cell": cell, "displayed_value": value})
        if len(samples) >= 20:
            break
    return samples


def _version_breakpoint_candidates(
    tabs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    period_tabs = [tab for tab in tabs if re.match(r"^\d{2}_\d{4}$", str(tab.get("title", "")))]
    if not period_tabs:
        return [], []

    groups = []
    start = period_tabs[0]
    current_count = start.get("column_count")
    previous = start
    for tab in period_tabs[1:]:
        if tab.get("column_count") != current_count:
            groups.append(_version_group(start, previous, current_count))
            start = tab
            current_count = tab.get("column_count")
        previous = tab
    groups.append(_version_group(start, previous, current_count))

    breakpoints = []
    for newer, older in zip(period_tabs, period_tabs[1:]):
        if newer.get("column_count") == older.get("column_count"):
            continue
        breakpoints.append(
            {
                "id": f"breakpoint_{newer['title']}_to_{older['title']}",
                "newer_tab": newer["title"],
                "older_tab": older["title"],
                "newer_column_count": newer.get("column_count"),
                "older_column_count": older.get("column_count"),
                "reason": "adjacent period tabs have different column counts; likely format or organization version boundary candidate",
            }
        )
    return groups, breakpoints


def _version_group(start: dict[str, Any], end: dict[str, Any], column_count: Any) -> dict[str, Any]:
    return {
        "id": f"version_group_{start['title']}_through_{end['title']}",
        "newest_tab": start["title"],
        "oldest_tab": end["title"],
        "column_count": column_count,
    }


def _iter_window_cells(payload: dict[str, Any]):
    for window in payload.get("windows", []):
        sheet_name, start_row, start_col = _range_start(window.get("range", "Sheet1!A1"))
        for row_offset, row in enumerate(window.get("values", [])):
            for col_offset, value in enumerate(row):
                yield (
                    f"{sheet_name}!{_column_label(start_col + col_offset)}{start_row + row_offset}",
                    value,
                )


def _range_start(a1_range: str) -> tuple[str, int, int]:
    sheet, _, cells = a1_range.partition("!")
    start = cells.split(":", 1)[0] or "A1"
    match = re.match(r"([A-Z]+)(\d+)", start)
    if not match:
        return sheet, 1, 1
    return sheet, int(match.group(2)), _column_index(match.group(1))


def _column_index(label: str) -> int:
    index = 0
    for char in label:
        index = index * 26 + (ord(char.upper()) - ord("A") + 1)
    return index


def _column_label(index: int) -> str:
    label = ""
    while index:
        index, rem = divmod(index - 1, 26)
        label = chr(ord("A") + rem) + label
    return label or "A"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _optional_json(path: Path) -> dict[str, Any] | None:
    return _read_json(path) if path.exists() else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record connected Google Sheets blocker resolutions from user feedback and broker source smoke."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--fc-data-source-url", default=SOURCE_SPREADSHEET_URL)
    parser.add_argument("--formula-result-authority", default="requires_targeted_validation")
    parser.add_argument("--local-boundary", default="전사레벨 현황 보고 문서")
    parser.add_argument(
        "--repeated-workbook-family",
        default="모든 period 탭이 반복문서이나 포맷 업데이트와 조직/부서 재구성 지점은 version breakpoint로 분리 필요",
    )
    parser.add_argument(
        "--reporting-basis",
        default="cash basis; 결제액 기반 운영 현황 보고이며 K-IFRS/K-GAAP 매출 산출물이 아님",
    )
    args = parser.parse_args()

    update = build_google_sheets_blocker_resolution_update(
        out_dir=args.out_dir,
        fc_data_source_url=args.fc_data_source_url,
        formula_result_authority=args.formula_result_authority,
        local_boundary=args.local_boundary,
        repeated_workbook_family=args.repeated_workbook_family,
        reporting_basis=args.reporting_basis,
    )
    write_google_sheets_blocker_resolution_update_package(
        out_dir=args.out_dir,
        update=update,
    )


if __name__ == "__main__":
    main()
