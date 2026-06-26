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


def build_google_sheets_domain_source_model(
    *,
    live_action_contracts_path: Path,
    live_evidence_package_path: Path,
    general_domain_dir: Path | None = None,
    blocker_resolution_update_path: Path | None = None,
    formula_result_authority_checkpoint_path: Path | None = None,
) -> dict[str, Any]:
    live_action_contracts_path = live_action_contracts_path.expanduser().resolve()
    live_evidence_package_path = live_evidence_package_path.expanduser().resolve()
    contracts = _read_json(live_action_contracts_path)
    evidence = _read_json(live_evidence_package_path)
    blocker_update = _optional_json(blocker_resolution_update_path)
    formula_checkpoint = _optional_json(formula_result_authority_checkpoint_path)
    general_sources = _general_sources(general_domain_dir)
    unavailable_sources = _unavailable_sources(evidence, contracts, blocker_update, formula_checkpoint)
    local_boundary = _local_boundary(evidence, blocker_update)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": evidence["source"]["spreadsheet_id"],
            "spreadsheet_url": evidence["source"].get("spreadsheet_url"),
            "title": evidence["source"]["title"],
            "source_artifacts": {
                "live_action_contracts": str(live_action_contracts_path),
                "live_evidence_package": str(live_evidence_package_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "model_status": "domain_source_model_only",
            "semantic_proposal_generation": "not_performed",
            "general_domain_authority": "available_as_reference_only" if general_sources else "not_selected",
            "local_domain_authority": "boundary_confirmed" if local_boundary["boundary_status"] == "confirmed" else "boundary_not_confirmed",
        },
        "general_domain_sources": general_sources,
        "local_domain_boundary": local_boundary,
        "unavailable_sources": unavailable_sources,
        "semantic_readiness": _semantic_readiness(general_sources, local_boundary, unavailable_sources),
        "summary": _summary(general_sources, unavailable_sources, local_boundary),
        "parser_observations": _parser_observations(unavailable_sources, local_boundary),
    }


def write_google_sheets_domain_source_model_package(
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
    domain_source_model: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "live-domain-source-model.json"
    model_path.write_text(
        json.dumps(domain_source_model, ensure_ascii=False, indent=2) + "\n",
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
    action_contracts = _read_json(live_action_contracts_path)
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
            live_domain_source_model=domain_source_model,
        ),
        encoding="utf-8",
    )


def _general_sources(domain_dir: Path | None) -> list[dict[str, Any]]:
    if domain_dir is None:
        return []
    domain_dir = domain_dir.expanduser().resolve()
    if not domain_dir.exists():
        return []
    sources = []
    for path in sorted(domain_dir.glob("*.md")):
        sources.append(
            {
                "id": f"general_{_slug(path.stem)}",
                "layer": "general_domain",
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "status": "available",
                "applicability": _applicability(path.name),
                "authority": "reference_only_not_workbook_truth",
            }
        )
    return sources


def _applicability(filename: str) -> list[str]:
    if filename in {"domain_scope.md", "concepts.md", "competency_qs.md", "logic_rules.md"}:
        return ["accounting_principles", "k_ifrs", "revenue_recognition"]
    if filename in {"dependency_rules.md", "structure_spec.md"}:
        return ["ontology_constraints", "dependency_rules"]
    return ["ontology_hygiene"]


def _local_boundary(
    evidence: dict[str, Any],
    blocker_update: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if blocker_update:
        return {
            "layer": "local_domain",
            "boundary_label": blocker_update["user_inputs"]["local_boundary"],
            "boundary_status": "confirmed",
            "available_local_evidence": [
                "user-confirmed local boundary",
                "user-confirmed reporting basis",
                "accepted calculation pipeline labels",
                "workbook facts",
                "review queue items",
            ],
            "missing_local_evidence": [
                "boundary-scoped glossary or policy document",
                "reviewed metric-equivalence decisions for repeated labels",
            ],
            "reporting_basis": blocker_update["user_inputs"]["reporting_basis"],
            "promotion_policy": "local_candidates_only_until_repeated_evidence_metric_gates_and_human_review_are_confirmed",
        }
    return {
        "layer": "local_domain",
        "boundary_label": evidence["source"]["title"],
        "boundary_status": "review_required",
        "available_local_evidence": [
            "accepted calculation pipeline labels",
            "workbook facts",
            "review queue items",
        ],
        "missing_local_evidence": [
            "organization/project/team boundary confirmation",
            "source spreadsheet authority",
            "formula-result authority for FC_DATA-dependent report pipelines",
        ],
        "promotion_policy": "local_candidates_only_until_boundary_and_repeated_evidence_are_confirmed",
    }


def _unavailable_sources(
    evidence: dict[str, Any],
    contracts: dict[str, Any],
    blocker_update: dict[str, Any] | None,
    formula_checkpoint: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    unavailable = []
    source_resolved = bool(
        blocker_update
        and blocker_update.get("source_smoke", {}).get("metadata", {}).get("ok")
    )
    if evidence["summary"]["source_spreadsheet_read_count"] == 0 and not source_resolved:
        unavailable.append(
            {
                "id": "unavailable_external_importrange_source",
                "type": "source_spreadsheet",
                "status": "blocked",
                "reason": "source ACL and source access evidence not confirmed",
                "related_contract_ids": [
                    item["id"]
                    for item in contracts["action_contracts"]
                    if item["deterministic_gate"] == "external_source_authority"
                ],
            }
        )
    elif blocker_update and blocker_update.get("lineage_observations", {}).get("nested_importrange_dependencies"):
        unavailable.append(
            {
                "id": "follow_up_nested_importrange_lineage",
                "type": "source_lineage",
                "status": "review_required",
                "reason": "direct FC_DATA source is readable, but nested IMPORTRANGE lineage remains follow-up if full raw lineage is needed",
                "related_contract_ids": [],
            }
        )
    blocked_pipeline_count = 0
    if formula_checkpoint:
        blocked_pipeline_count = formula_checkpoint["summary"].get("blocked_pipeline_result_count", 0)
    formula_unresolved = (
        evidence["authority"]["formula_result_authority"] == "not_established"
        and not formula_checkpoint
    ) or blocked_pipeline_count > 0
    if formula_unresolved:
        unavailable.append(
            {
                "id": "unavailable_formula_result_authority_for_report_pipelines",
                "type": "formula_result",
                "status": "blocked",
                "reason": (
                    f"{blocked_pipeline_count} pipeline outputs remain blocked by formula-result/error authority"
                    if formula_checkpoint
                    else "formula recalculation/result authority not established"
                ),
                "related_contract_ids": [
                    item["id"]
                    for item in contracts["action_contracts"]
                    if item["deterministic_gate"] == "formula_error_reconciliation"
                ],
            }
        )
    return unavailable


def _semantic_readiness(
    general_sources: list[dict[str, Any]],
    local_boundary: dict[str, Any],
    unavailable_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "general_domain_available": bool(general_sources),
        "local_boundary_confirmed": local_boundary["boundary_status"] == "confirmed",
        "unavailable_source_count": len(unavailable_sources),
        "semantic_proposal_scope": (
            "cash_basis_operational_reporting_local_candidates"
            if local_boundary["boundary_status"] == "confirmed"
            else "limited_document_evidence_only"
        ),
        "shared_ontology_promotion_status": "blocked",
        "blocked_reason": "shared promotion requires repeated evidence, metric-equivalence gates, source lineage checks, and human approval",
    }


def _summary(
    general_sources: list[dict[str, Any]],
    unavailable_sources: list[dict[str, Any]],
    local_boundary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "general_domain_source_count": len(general_sources),
        "available_general_domain_source_count": sum(1 for item in general_sources if item["status"] == "available"),
        "unavailable_source_count": len(unavailable_sources),
        "local_boundary_confirmed": local_boundary["boundary_status"] == "confirmed",
        "semantic_proposal_generation": "not_performed",
        "shared_ontology_promotion_status": "blocked",
    }


def _parser_observations(
    unavailable_sources: list[dict[str, Any]],
    local_boundary: dict[str, Any],
) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Domain source model separates general-domain references from local-boundary evidence before semantic proposals.",
        }
    ]
    if local_boundary["boundary_status"] != "confirmed":
        observations.append(
            {
                "level": "warning",
                "message": "Local domain boundary is not confirmed; local semantic candidates must remain boundary-scoped and review-required.",
            }
        )
    if unavailable_sources:
        observations.append(
            {
                "level": "warning",
                "message": f"{len(unavailable_sources)} source authorities are unavailable for semantic promotion.",
            }
        )
    return observations


def _slug(value: Any) -> str:
    text = str(value or "none")
    text = re.sub(r"[^A-Za-z0-9가-힣]+", "_", text).strip("_").lower()
    return text or "none"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_json(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    path = path.expanduser().resolve()
    return _read_json(path) if path.exists() else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def render_google_sheets_domain_source_model_section(model: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in model["summary"].items()
    )
    source_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(', '.join(item['applicability']))}</td>"
        f"<td><code>{_esc(item['path'])}</code></td>"
        "</tr>"
        for item in model["general_domain_sources"]
    )
    if not source_rows:
        source_rows = '<tr><td colspan="4">No general-domain sources selected.</td></tr>'
    unavailable_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['type'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['reason'])}</td>"
        "</tr>"
        for item in model["unavailable_sources"]
    )
    if not unavailable_rows:
        unavailable_rows = '<tr><td colspan="3">No unavailable sources.</td></tr>'
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in model["parser_observations"]
    )
    return f"""
  <h2>Live Domain Source Model</h2>
  <section class="grid">{metrics}</section>
  <h2>General Domain Sources</h2>
  <section class="panel"><table><thead><tr><th>ID</th><th>Status</th><th>Applicability</th><th>Path</th></tr></thead><tbody>{source_rows}</tbody></table></section>
  <h2>Local Boundary</h2>
  <section class="panel"><pre><code>{_esc(model["local_domain_boundary"])}</code></pre></section>
  <h2>Unavailable Sources</h2>
  <section class="panel"><table><thead><tr><th>Type</th><th>Status</th><th>Reason</th></tr></thead><tbody>{unavailable_rows}</tbody></table></section>
  <h2>Domain Source Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build domain source model for connected Google Sheets semantic preparation."
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
    parser.add_argument("--general-domain-dir", type=Path, default=None)
    parser.add_argument("--blocker-resolution-update", type=Path, default=None)
    parser.add_argument("--formula-result-authority-checkpoint", type=Path, default=None)
    args = parser.parse_args()

    model = build_google_sheets_domain_source_model(
        live_action_contracts_path=args.live_action_contracts,
        live_evidence_package_path=args.live_evidence_package,
        general_domain_dir=args.general_domain_dir,
        blocker_resolution_update_path=args.blocker_resolution_update,
        formula_result_authority_checkpoint_path=args.formula_result_authority_checkpoint,
    )
    write_google_sheets_domain_source_model_package(
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
        domain_source_model=model,
    )


if __name__ == "__main__":
    main()
