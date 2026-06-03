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


def build_google_sheets_action_contracts(
    *,
    live_document_ontology_mapping_path: Path,
) -> dict[str, Any]:
    live_document_ontology_mapping_path = live_document_ontology_mapping_path.expanduser().resolve()
    mapping = _read_json(live_document_ontology_mapping_path)
    contracts = [
        _contract_from_review_item(item)
        for item in mapping["ontology"]["review_items"]
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": mapping["source"]["spreadsheet_id"],
            "spreadsheet_url": mapping["source"].get("spreadsheet_url"),
            "title": mapping["source"]["title"],
            "source_artifacts": {
                "live_document_ontology_mapping": str(live_document_ontology_mapping_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "contract_status": "action_contract_layer_only",
            "new_graph_claims": False,
            "semantic_ontology_generation": "not_performed",
        },
        "action_contracts": contracts,
        "summary": _summary(contracts),
        "parser_observations": _parser_observations(contracts),
    }


def write_google_sheets_action_contracts_package(
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
    action_contracts: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    contracts_path = out_dir / "live-action-contracts.json"
    contracts_path.write_text(
        json.dumps(action_contracts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    access_preflight = _read_json(access_preflight_path)
    manifest = _read_json(live_manifest_path)
    view_formula_profile = _read_json(live_view_formula_profile_path)
    block_candidates = _read_json(live_block_candidates_path)
    bounded_sample = _read_json(bounded_window_sample_path)
    tuning = _read_json(live_block_candidate_tuning_path)
    table_io = _read_json(live_table_io_pipelines_path)
    cross_validation_plan = _read_json(live_cross_validation_plan_path)
    validation_batch = _read_json(live_validation_batch_execution_path)
    gate_execution = _read_json(live_gate_execution_path)
    evidence_package = _read_json(live_evidence_package_path)
    ontology_mapping = _read_json(live_document_ontology_mapping_path)
    (out_dir / "index.html").write_text(
        render_live_manifest_html(
            access_preflight=access_preflight,
            manifest=manifest,
            live_view_formula_profile=view_formula_profile,
            live_block_candidates=block_candidates,
            live_bounded_window_sample=bounded_sample,
            live_block_candidate_tuning=tuning,
            live_table_io_pipelines=table_io,
            live_cross_validation_plan=cross_validation_plan,
            live_validation_batch_execution=validation_batch,
            live_gate_execution=gate_execution,
            live_evidence_package=evidence_package,
            live_document_ontology_mapping=ontology_mapping,
            live_action_contracts=action_contracts,
        ),
        encoding="utf-8",
    )


def _contract_from_review_item(item: dict[str, Any]) -> dict[str, Any]:
    template = _template(item["type"])
    return {
        "id": f"contract_{_slug(item['id'])}",
        "type": "action_contract",
        "source_review_item_id": item["id"],
        "status": "open",
        "priority": item["severity"],
        "owner": template["owner"],
        "action": template["action"],
        "required_evidence": template["required_evidence"],
        "deterministic_gate": template["deterministic_gate"],
        "completion_condition": template["completion_condition"],
        "completion_effect": template["completion_effect"],
        "evidence_refs": item.get("evidence_refs", []),
    }


def _template(review_type: str) -> dict[str, Any]:
    if review_type == "external_source_authority_blocker":
        return {
            "owner": "sheet_owner_and_broker_policy_owner",
            "action": "Resolve IMPORTRANGE source argument, confirm Google ACL, and add source spreadsheet to broker allowlist before source reads.",
            "required_evidence": [
                "resolved source spreadsheet ID",
                "Google ACL confirmation for principal",
                "broker allowlist entry for source spreadsheet",
            ],
            "deterministic_gate": "external_source_authority",
            "completion_condition": "Source spreadsheet can be inspected through broker policy without bypassing ACL or broker controls.",
            "completion_effect": "External source dependency gates may be re-run.",
        }
    if review_type == "formula_result_authority_gap":
        return {
            "owner": "sheet_owner_or_formula_reconciliation_reviewer",
            "action": "Reconcile displayed formula errors and establish whether affected outputs are valid, expected stale states, or broken calculations.",
            "required_evidence": [
                "error cell locations",
                "formula text and display value comparison",
                "resolved upstream source/result authority",
            ],
            "deterministic_gate": "formula_error_reconciliation",
            "completion_condition": "Affected pipeline outputs can be classified as valid, invalid, or intentionally unresolved.",
            "completion_effect": "Formula-error blocked pipeline targets may be re-evaluated.",
        }
    if review_type == "coverage_gap":
        return {
            "owner": "parser_operator",
            "action": "Execute or explicitly defer remaining current-workbook bounded read candidates under broker policy.",
            "required_evidence": [
                "bounded read execution artifact or explicit deferral record",
                "policy-compliant range list",
            ],
            "deterministic_gate": "bounded_read_policy_check",
            "completion_condition": "Remaining coverage gap is reduced or accepted as a documented limitation.",
            "completion_effect": "Coverage review queue can be reduced or carried with narrower scope.",
        }
    if review_type == "blocked_deterministic_gates":
        return {
            "owner": "parser_operator",
            "action": "Re-run deterministic gates after source authority, formula-error, or coverage blockers are resolved.",
            "required_evidence": [
                "updated blocker evidence",
                "new gate execution artifact",
            ],
            "deterministic_gate": "gate_reexecution",
            "completion_condition": "Previously blocked gates move to accepted or review-required with explicit rationale.",
            "completion_effect": "Evidence package and ontology mapping can be refreshed.",
        }
    return {
        "owner": "human_reviewer",
        "action": "Review unresolved parser item and provide required evidence or an explicit deferral.",
        "required_evidence": ["human review decision"],
        "deterministic_gate": "manual_review_gate",
        "completion_condition": "Review item has a documented decision.",
        "completion_effect": "Review item can be closed, deferred, or routed to another contract.",
    }


def _summary(contracts: list[dict[str, Any]]) -> dict[str, Any]:
    owners = Counter(item["owner"] for item in contracts)
    priorities = Counter(item["priority"] for item in contracts)
    return {
        "action_contract_count": len(contracts),
        "open_contract_count": sum(1 for item in contracts if item["status"] == "open"),
        "high_priority_contract_count": priorities["high"],
        "medium_priority_contract_count": priorities["medium"],
        "sheet_owner_contract_count": owners["sheet_owner_and_broker_policy_owner"] + owners["sheet_owner_or_formula_reconciliation_reviewer"],
        "parser_operator_contract_count": owners["parser_operator"],
        "semantic_concept_count": 0,
        "contract_status": "action_contract_layer_only",
    }


def _parser_observations(contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Action contracts translate review-required ontology items into owner, action, evidence, gate, and completion criteria.",
        }
    ]
    if contracts:
        observations.append(
            {
                "level": "warning",
                "message": f"{len(contracts)} contracts remain open before graph promotion can advance.",
            }
        )
    return observations


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


def render_google_sheets_action_contracts_section(contracts: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in contracts["summary"].items()
    )
    rows = "".join(
        "<tr>"
        f"<td>{_esc(item['priority'])}</td>"
        f"<td>{_esc(item['owner'])}</td>"
        f"<td>{_esc(item['deterministic_gate'])}</td>"
        f"<td>{_esc(item['action'])}</td>"
        f"<td>{_esc(item['completion_effect'])}</td>"
        "</tr>"
        for item in contracts["action_contracts"]
    )
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in contracts["parser_observations"]
    )
    return f"""
  <h2>Live Action Contracts</h2>
  <section class="grid">{metrics}</section>
  <h2>Action Contracts</h2>
  <section class="panel"><table><thead><tr><th>Priority</th><th>Owner</th><th>Gate</th><th>Action</th><th>Completion Effect</th></tr></thead><tbody>{rows}</tbody></table></section>
  <h2>Action Contract Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build action contracts from connected Google Sheets document ontology mapping."
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
    args = parser.parse_args()

    contracts = build_google_sheets_action_contracts(
        live_document_ontology_mapping_path=args.live_document_ontology_mapping,
    )
    write_google_sheets_action_contracts_package(
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
        action_contracts=contracts,
    )


if __name__ == "__main__":
    main()
