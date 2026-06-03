from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"


def build_action_contracts(
    document_ontology_mapping_path: Path,
    evidence_package_path: Path | None = None,
) -> dict[str, Any]:
    document_ontology_mapping_path = document_ontology_mapping_path.expanduser().resolve()
    mapping = _read_json(document_ontology_mapping_path)
    evidence_package_resolved = _resolve_evidence_package_path(
        document_ontology_mapping_path,
        mapping,
        evidence_package_path,
    )
    evidence_package = _read_json(evidence_package_resolved)

    contracts = []
    for view in mapping.get("data_views", []):
        contracts.append(_data_view_contract(view))
    for item in mapping.get("review_queue", []):
        contracts.append(_review_item_contract(item))
    contracts = sorted(
        contracts,
        key=lambda item: (
            _priority_order(item["priority"]),
            item["action_type"],
            item["id"],
        ),
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "document_ontology_mapping": str(document_ontology_mapping_path),
            "evidence_package": str(evidence_package_resolved),
        },
        "method": {
            "name": "deterministic_action_contract_layer",
            "authority": "action_contract_projection_not_claim_acceptance",
            "decision_policy": (
                "Convert ontology statuses and review reasons into deterministic next-action "
                "contracts. These contracts say what to do next; they do not accept new "
                "document or semantic claims by themselves."
            ),
        },
        "action_contracts": contracts,
        "summary": _summary(contracts),
        "parser_observations": _parser_observations(contracts, evidence_package),
    }


def _data_view_contract(view: dict[str, Any]) -> dict[str, Any]:
    status = view.get("status")
    reason = (view.get("properties") or {}).get("reason")
    if status == "accepted":
        return {
            "id": f"action_contract:{view['id']}",
            "type": "action_contract",
            "action_status": "ready",
            "priority": "low",
            "action_type": "consume_as_structural_data_view",
            "action_owner": "downstream_parser",
            "target": _target(
                target_kind="data_view",
                data_view_id=view["id"],
                node_id=view.get("output_node_id"),
                sheet=view.get("sheet"),
                range_text=view.get("range"),
            ),
            "trigger": {
                "source_status": status,
                "reason": reason,
                "source_kind": "data_view",
            },
            "required_evidence": [
                "data_view.evidence_refs",
                "pipeline_role_validation",
                "table_io_pipeline",
            ],
            "deterministic_gate": "data_view_evidence_trace_gate",
            "completion_condition": "Data view retains evidence refs and may be consumed by validated document graph assembly.",
            "completion_effect": "eligible_for_validated_document_graph",
            "evidence_refs": view.get("evidence_refs", []),
            "source_artifact_refs": view.get("source_artifact_refs", []),
        }
    return _contract_from_reason(
        contract_id=f"action_contract:{view['id']}",
        source_kind="data_view",
        reason=reason or "review_required",
        target=_target(
            target_kind="data_view",
            data_view_id=view["id"],
            node_id=view.get("output_node_id"),
            sheet=view.get("sheet"),
            range_text=view.get("range"),
        ),
        evidence_refs=view.get("evidence_refs", []),
        source_artifact_refs=view.get("source_artifact_refs", []),
    )


def _review_item_contract(item: dict[str, Any]) -> dict[str, Any]:
    reason = item.get("reason") or "review_required"
    return _contract_from_reason(
        contract_id=f"action_contract:{item['id']}",
        source_kind=item.get("kind") or "review_item",
        reason=reason,
        target=_target(
            target_kind=item.get("kind") or "review_item",
            review_item_id=item["id"],
            node_id=item.get("target_node_id"),
            sheet=item.get("sheet"),
            range_text=item.get("range"),
        ),
        evidence_refs=item.get("evidence_refs", []),
        source_artifact_refs=["document_ontology_mapping", "evidence_package"],
    )


def _contract_from_reason(
    *,
    contract_id: str,
    source_kind: str,
    reason: str,
    target: dict[str, Any],
    evidence_refs: list[str],
    source_artifact_refs: list[str],
) -> dict[str, Any]:
    spec = _action_spec(reason)
    return {
        "id": contract_id,
        "type": "action_contract",
        "action_status": spec["action_status"],
        "priority": spec["priority"],
        "action_type": spec["action_type"],
        "action_owner": spec["action_owner"],
        "target": target,
        "trigger": {
            "source_status": "review_required",
            "reason": reason,
            "source_kind": source_kind,
        },
        "required_evidence": spec["required_evidence"],
        "deterministic_gate": spec["deterministic_gate"],
        "completion_condition": spec["completion_condition"],
        "completion_effect": spec["completion_effect"],
        "evidence_refs": sorted(set(str(ref) for ref in evidence_refs if ref)),
        "source_artifact_refs": sorted(set(str(ref) for ref in source_artifact_refs if ref)),
    }


def _action_spec(reason: str) -> dict[str, Any]:
    if reason == "unresolved_input_region":
        return {
            "action_status": "open",
            "priority": "high",
            "action_type": "resolve_input_region_ownership",
            "action_owner": "deterministic_parser",
            "required_evidence": [
                "formula_relation_group",
                "candidate_input_range",
                "owning_cell_region_or_new_region",
                "boundary_decision",
            ],
            "deterministic_gate": "input_region_ownership_gate",
            "completion_condition": "Candidate input range is mapped to an owning region or retained as an explicit external/unresolved source.",
            "completion_effect": "promote_or_reject_data_view_after_role_validation",
        }
    if reason == "capture_required":
        return {
            "action_status": "open",
            "priority": "medium",
            "action_type": "acquire_render_capture",
            "action_owner": "excel_capture",
            "required_evidence": [
                "excel_range_png",
                "capture_quality_result",
                "coordinate_mapping",
                "visual_feature_result",
            ],
            "deterministic_gate": "render_capture_availability_gate",
            "completion_condition": "Target range has usable or explicitly reviewable render capture evidence.",
            "completion_effect": "rerun_visual_gate_execution",
        }
    if reason == "capture_quality_review_required":
        return {
            "action_status": "open",
            "priority": "high",
            "action_type": "recapture_or_tile_range",
            "action_owner": "excel_capture",
            "required_evidence": [
                "recapture_candidate",
                "tiling_plan_or_expanded_window",
                "capture_quality_result",
            ],
            "deterministic_gate": "capture_quality_gate",
            "completion_condition": "Capture quality becomes usable or remains explicitly quarantined with reason.",
            "completion_effect": "rerun_coordinate_normalization",
        }
    if reason == "view_state_blocked":
        return {
            "action_status": "blocked",
            "priority": "high",
            "action_type": "reconcile_view_state_authority",
            "action_owner": "human_review",
            "required_evidence": [
                "view_state_preflight",
                "visible_state_capture",
                "structural_data_evidence",
                "optional_diagnostic_reveal_capture",
            ],
            "deterministic_gate": "view_state_authority_gate",
            "completion_condition": "Visible-state authority and structural-data authority are explicitly separated for the target.",
            "completion_effect": "allow_structural_claims_without_visual_absence_claims",
        }
    if reason == "view_state_warning":
        return {
            "action_status": "open",
            "priority": "medium",
            "action_type": "review_view_state_warning",
            "action_owner": "human_review",
            "required_evidence": [
                "view_state_profile",
                "capture_quality_result",
                "visual_feature_result",
            ],
            "deterministic_gate": "view_state_warning_gate",
            "completion_condition": "Reviewer or deterministic rule confirms whether visible capture is sufficient despite view-state warning.",
            "completion_effect": "accept_or_quarantine_visual_evidence",
        }
    if reason == "style_only_boundary_needs_correlated_evidence":
        return {
            "action_status": "open",
            "priority": "low",
            "action_type": "corroborate_boundary_evidence",
            "action_owner": "human_review",
            "required_evidence": [
                "visual_feature_result",
                "formula_locality_signal",
                "header_or_blank_gap_signal",
                "boundary_decision",
            ],
            "deterministic_gate": "boundary_acceptance_gate",
            "completion_condition": "Boundary has correlated evidence or remains review-only without creating graph boundary.",
            "completion_effect": "promote_boundary_or_keep_review_item",
        }
    if reason == "merged_title_boundary_needs_semantic_review":
        return {
            "action_status": "open",
            "priority": "medium",
            "action_type": "review_title_hierarchy",
            "action_owner": "human_review",
            "required_evidence": [
                "merged_range",
                "nearby_cell_regions",
                "visual_feature_result",
                "document_hierarchy_candidate",
            ],
            "deterministic_gate": "title_hierarchy_review_gate",
            "completion_condition": "Merged/title block is accepted as hierarchy parent, caption, or non-structural decoration.",
            "completion_effect": "update_document_hierarchy_candidate",
        }
    return {
        "action_status": "open",
        "priority": "medium",
        "action_type": "review_unknown_issue",
        "action_owner": "human_review",
        "required_evidence": ["source_evidence_refs", "review_note"],
        "deterministic_gate": "manual_review_gate",
        "completion_condition": "Reviewer classifies the issue into a known action type or records a new process decision.",
        "completion_effect": "update_action_contract_taxonomy",
    }


def _target(
    *,
    target_kind: str,
    sheet: Any,
    range_text: Any,
    node_id: Any = None,
    data_view_id: Any = None,
    review_item_id: Any = None,
) -> dict[str, Any]:
    return {
        "target_kind": target_kind,
        "node_id": node_id,
        "data_view_id": data_view_id,
        "review_item_id": review_item_id,
        "sheet": sheet,
        "range": range_text,
    }


def _summary(contracts: list[dict[str, Any]]) -> dict[str, int]:
    statuses = Counter(contract["action_status"] for contract in contracts)
    priorities = Counter(contract["priority"] for contract in contracts)
    owners = Counter(contract["action_owner"] for contract in contracts)
    actions = Counter(contract["action_type"] for contract in contracts)
    return {
        "action_contract_count": len(contracts),
        "ready_count": statuses.get("ready", 0),
        "open_count": statuses.get("open", 0),
        "blocked_count": statuses.get("blocked", 0),
        "high_priority_count": priorities.get("high", 0),
        "medium_priority_count": priorities.get("medium", 0),
        "low_priority_count": priorities.get("low", 0),
        "data_view_contract_count": sum(
            1
            for contract in contracts
            if contract.get("target", {}).get("target_kind") == "data_view"
        ),
        "review_item_contract_count": sum(
            1
            for contract in contracts
            if contract.get("target", {}).get("target_kind") != "data_view"
        ),
        "excel_capture_owner_count": owners.get("excel_capture", 0),
        "human_review_owner_count": owners.get("human_review", 0),
        "deterministic_parser_owner_count": owners.get("deterministic_parser", 0),
        "downstream_parser_owner_count": owners.get("downstream_parser", 0),
        "resolve_input_region_ownership_count": actions.get("resolve_input_region_ownership", 0),
        "acquire_render_capture_count": actions.get("acquire_render_capture", 0),
        "recapture_or_tile_range_count": actions.get("recapture_or_tile_range", 0),
        "reconcile_view_state_authority_count": actions.get("reconcile_view_state_authority", 0),
        "corroborate_boundary_evidence_count": actions.get("corroborate_boundary_evidence", 0),
    }


def _parser_observations(
    contracts: list[dict[str, Any]],
    evidence_package: dict[str, Any],
) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": "Action contracts make the document ontology actionable without accepting new structural or semantic claims.",
        },
        {
            "level": "info",
            "message": "Accepted data views are marked ready for downstream graph assembly; review-required items receive explicit next-action contracts.",
        },
    ]
    blocked_count = sum(1 for contract in contracts if contract["action_status"] == "blocked")
    if blocked_count:
        observations.append(
            {
                "level": "warning",
                "message": f"{blocked_count} contracts are blocked by view-state authority separation and require review before visual absence claims are allowed.",
            }
        )
    if evidence_package.get("domain_knowledge_refs"):
        observations.append(
            {
                "level": "info",
                "message": "Domain refs remain unused in action contract generation; they are reserved for later semantic ontology stages.",
            }
        )
    return observations


def _resolve_evidence_package_path(
    document_ontology_mapping_path: Path,
    mapping: dict[str, Any],
    evidence_package_path: Path | None,
) -> Path:
    if evidence_package_path is not None:
        path = evidence_package_path.expanduser()
    else:
        path = Path(mapping.get("source_artifacts", {}).get("evidence_package", ""))
    if not path.is_absolute():
        path = document_ontology_mapping_path.parent / path
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"missing evidence package: {path}")
    return path


def _priority_order(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 99)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic action contracts from a document ontology mapping."
    )
    parser.add_argument("--document-ontology-mapping", type=Path, required=True)
    parser.add_argument("--evidence-package", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    contracts = build_action_contracts(
        args.document_ontology_mapping,
        evidence_package_path=args.evidence_package,
    )
    payload = json.dumps(contracts, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
