from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"

DOMAIN_ROLE_BY_FILE = {
    "domain_scope.md": "scope_definition",
    "concepts.md": "concept_dictionary",
    "logic_rules.md": "logic_rule_set",
    "structure_spec.md": "structure_specification",
    "dependency_rules.md": "dependency_rule_set",
    "conciseness_rules.md": "concept_economy_rule_set",
    "competency_qs.md": "competency_question_set",
    "extension_cases.md": "extension_case_set",
}


def build_domain_source_model(
    *,
    evidence_package_path: Path,
    document_ontology_mapping_path: Path,
    action_contracts_path: Path,
    general_domain_root: Path | None = None,
    local_domain_root: Path | None = None,
) -> dict[str, Any]:
    evidence_package_path = evidence_package_path.expanduser().resolve()
    document_ontology_mapping_path = document_ontology_mapping_path.expanduser().resolve()
    action_contracts_path = action_contracts_path.expanduser().resolve()
    evidence_package = _read_json(evidence_package_path)
    document_mapping = _read_json(document_ontology_mapping_path)
    action_contracts = _read_json(action_contracts_path)

    general_sources = _general_domain_sources(
        evidence_package,
        general_domain_root=general_domain_root,
    )
    local_sources = _local_domain_sources(local_domain_root)
    local_boundaries = _local_domain_boundaries(
        evidence_package,
        local_sources=local_sources,
    )
    readiness = _semantic_readiness(
        general_sources=general_sources,
        local_sources=local_sources,
        local_boundaries=local_boundaries,
        action_contracts=action_contracts,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "evidence_package": str(evidence_package_path),
            "document_ontology_mapping": str(document_ontology_mapping_path),
            "action_contracts": str(action_contracts_path),
            "general_domain_root": str(_domain_root(general_sources)) if general_sources else None,
            "local_domain_root": str(local_domain_root.expanduser().resolve()) if local_domain_root else None,
        },
        "method": {
            "name": "deterministic_domain_source_model",
            "authority": "domain_source_inventory_not_semantic_claim_generation",
            "decision_policy": (
                "Represent reusable general-domain sources and boundary-scoped local-domain "
                "sources separately before semantic ontology proposal generation. Domain sources "
                "can constrain proposals but cannot replace workbook evidence."
            ),
        },
        "domain_layers": {
            "general_domain_sources": general_sources,
            "local_domain_sources": local_sources,
            "local_domain_boundaries": local_boundaries,
        },
        "governance_rules": _governance_rules(),
        "semantic_readiness": readiness,
        "review_queue": _review_queue(readiness, local_boundaries, action_contracts),
        "summary": _summary(general_sources, local_sources, local_boundaries, readiness),
        "parser_observations": _parser_observations(general_sources, local_sources, readiness, document_mapping),
    }


def _general_domain_sources(
    evidence_package: dict[str, Any],
    *,
    general_domain_root: Path | None,
) -> list[dict[str, Any]]:
    refs = list(evidence_package.get("domain_knowledge_refs") or [])
    if not refs and general_domain_root:
        root = general_domain_root.expanduser().resolve()
        refs = [
            {
                "id": f"general_domain:accounting-kr/{path.name}",
                "layer": "general_domain",
                "path": str(path),
                "scope": "current_sample_workbook",
                "status": "available",
            }
            for path in sorted(root.glob("*.md"))
        ]
    sources = []
    for ref in refs:
        path = Path(ref.get("path", "")).expanduser().resolve()
        file_name = path.name
        domain_id = _domain_id_from_ref(ref.get("id") or "", path)
        source = {
            "id": ref.get("id") or f"general_domain:{domain_id}/{file_name}",
            "layer": "general_domain",
            "domain_id": domain_id,
            "document_role": DOMAIN_ROLE_BY_FILE.get(file_name, "domain_document"),
            "path": str(path),
            "file_name": file_name,
            "status": "available" if path.exists() else "missing",
            "scope": ref.get("scope") or "current_sample_workbook",
            "applicability": "reusable_general_domain_constraint",
            "size_bytes": path.stat().st_size if path.exists() else None,
            "sha256": _sha256(path) if path.exists() else None,
            "heading_samples": _heading_samples(path) if path.exists() else [],
            "evidence_refs": [ref.get("id") or f"general_domain:{domain_id}/{file_name}"],
        }
        sources.append(source)
    return sorted(sources, key=lambda item: (item["domain_id"], item["file_name"]))


def _local_domain_sources(local_domain_root: Path | None) -> list[dict[str, Any]]:
    if local_domain_root is None:
        return []
    root = local_domain_root.expanduser().resolve()
    if not root.exists():
        return []
    sources = []
    for path in sorted(root.glob("*.md")):
        sources.append(
            {
                "id": f"local_domain:{path.stem}",
                "layer": "local_domain",
                "boundary_id": "local_boundary:explicit",
                "document_role": "local_policy_or_vocabulary",
                "path": str(path),
                "file_name": path.name,
                "status": "available",
                "scope": "explicit_local_boundary",
                "applicability": "boundary_scoped_constraint",
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "heading_samples": _heading_samples(path),
                "evidence_refs": [f"local_domain:{path.stem}"],
            }
        )
    return sources


def _local_domain_boundaries(
    evidence_package: dict[str, Any],
    *,
    local_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source = evidence_package.get("source", {})
    sha = str(source.get("sha256") or "")[:12] or "unknown"
    explicit = bool(local_sources)
    return [
        {
            "id": f"local_boundary:workbook_sample:{sha}",
            "layer": "local_domain",
            "boundary_kind": "workbook_sample_boundary",
            "label": source.get("file_name") or "Current workbook sample",
            "status": "available" if explicit else "review_required",
            "scope": (
                "explicit_local_boundary"
                if explicit
                else "current_workbook_only_until_boundary_confirmed"
            ),
            "source_anchor": {
                "workbook_path": source.get("path"),
                "workbook_sha256": source.get("sha256"),
                "workbook_file_name": source.get("file_name"),
            },
            "local_source_ids": [source["id"] for source in local_sources],
            "required_confirmation": [] if explicit else [
                "organization_or_project_boundary",
                "local_policy_or_vocabulary_sources",
                "applicability_period_or_workbook_family",
            ],
            "evidence_refs": ["evidence_package.source"],
        }
    ]


def _semantic_readiness(
    *,
    general_sources: list[dict[str, Any]],
    local_sources: list[dict[str, Any]],
    local_boundaries: list[dict[str, Any]],
    action_contracts: dict[str, Any],
) -> dict[str, Any]:
    action_summary = action_contracts.get("summary", {})
    general_ready = any(source.get("status") == "available" for source in general_sources)
    local_boundary_confirmed = all(
        boundary.get("status") == "available" for boundary in local_boundaries
    )
    structural_open = int(action_summary.get("open_count") or 0)
    structural_blocked = int(action_summary.get("blocked_count") or 0)
    high_priority = int(action_summary.get("high_priority_count") or 0)
    if not general_ready:
        status = "blocked_missing_general_domain"
    elif not local_boundary_confirmed:
        status = "proposal_only_local_boundary_pending"
    elif structural_blocked or high_priority:
        status = "proposal_only_structural_actions_pending"
    else:
        status = "ready_for_semantic_proposals"
    return {
        "status": status,
        "general_domain_ready": general_ready,
        "local_boundary_confirmed": local_boundary_confirmed,
        "local_domain_source_count": len(local_sources),
        "semantic_proposal_mode": (
            "proposal_only_with_boundary_warning"
            if not local_boundary_confirmed
            else "proposal_with_explicit_boundary"
        ),
        "shared_ontology_promotion_allowed": False,
        "shared_ontology_promotion_condition": (
            "Requires explicit local boundary, repeated workbook-pair evidence, conflict checks, "
            "and human review."
        ),
        "structural_action_summary": {
            "open_count": structural_open,
            "blocked_count": structural_blocked,
            "high_priority_count": high_priority,
            "ready_count": int(action_summary.get("ready_count") or 0),
        },
        "blocking_factors": _blocking_factors(
            general_ready=general_ready,
            local_boundary_confirmed=local_boundary_confirmed,
            structural_blocked=structural_blocked,
            high_priority=high_priority,
        ),
    }


def _blocking_factors(
    *,
    general_ready: bool,
    local_boundary_confirmed: bool,
    structural_blocked: int,
    high_priority: int,
) -> list[str]:
    factors = []
    if not general_ready:
        factors.append("general_domain_source_missing")
    if not local_boundary_confirmed:
        factors.append("local_domain_boundary_not_confirmed")
    if structural_blocked:
        factors.append("blocked_action_contracts")
    if high_priority:
        factors.append("high_priority_structural_actions")
    return factors


def _governance_rules() -> list[dict[str, Any]]:
    return [
        {
            "id": "domain_source_rule:workbook_evidence_required",
            "rule": "Domain knowledge may constrain semantic proposals but cannot replace workbook evidence.",
            "applies_to": ["general_domain", "local_domain"],
        },
        {
            "id": "domain_source_rule:local_scope_required",
            "rule": "Local-domain concepts require a declared organization/project/team/tenant/workbook-family boundary before acceptance.",
            "applies_to": ["local_domain"],
        },
        {
            "id": "domain_source_rule:no_shared_promotion_from_single_workbook",
            "rule": "A single workbook may create local semantic candidates but cannot promote them to shared ontology without workbook-pair or workbook-family evidence.",
            "applies_to": ["shared_ontology_alignment"],
        },
        {
            "id": "domain_source_rule:general_alignment_not_identity",
            "rule": "A local term aligned to a general-domain concept is not identical to the general concept unless deterministic evidence and review approve that mapping.",
            "applies_to": ["general_domain", "local_domain"],
        },
    ]


def _review_queue(
    readiness: dict[str, Any],
    local_boundaries: list[dict[str, Any]],
    action_contracts: dict[str, Any],
) -> list[dict[str, Any]]:
    queue = []
    for boundary in local_boundaries:
        if boundary.get("status") == "review_required":
            queue.append(
                {
                    "id": f"review:{boundary['id']}:confirm_boundary",
                    "kind": "local_domain_boundary",
                    "priority": "high",
                    "reason": "local_domain_boundary_not_confirmed",
                    "target_id": boundary["id"],
                    "required_action": "confirm_or_define_local_boundary",
                    "evidence_refs": boundary.get("evidence_refs", []),
                }
            )
    for factor in readiness.get("blocking_factors", []):
        if factor in {"blocked_action_contracts", "high_priority_structural_actions"}:
            queue.append(
                {
                    "id": f"review:semantic_readiness:{factor}",
                    "kind": "semantic_readiness",
                    "priority": "medium",
                    "reason": factor,
                    "target_id": "semantic_readiness",
                    "required_action": "resolve_or_accept_action_contract_risk_before_semantic_acceptance",
                    "evidence_refs": ["action_contracts.summary"],
                }
            )
    summary = action_contracts.get("summary", {})
    if summary.get("open_count"):
        queue.append(
            {
                "id": "review:action_contracts:open_items",
                "kind": "action_contract_summary",
                "priority": "low",
                "reason": "open_action_contracts_remain",
                "target_id": "action_contracts.summary",
                "required_action": "use_action_contracts_as_operational_queue",
                "evidence_refs": ["action_contracts.summary"],
            }
        )
    return queue


def _summary(
    general_sources: list[dict[str, Any]],
    local_sources: list[dict[str, Any]],
    local_boundaries: list[dict[str, Any]],
    readiness: dict[str, Any],
) -> dict[str, int]:
    return {
        "general_domain_source_count": len(general_sources),
        "available_general_domain_source_count": sum(
            1 for source in general_sources if source.get("status") == "available"
        ),
        "local_domain_source_count": len(local_sources),
        "available_local_domain_source_count": sum(
            1 for source in local_sources if source.get("status") == "available"
        ),
        "local_domain_boundary_count": len(local_boundaries),
        "confirmed_local_domain_boundary_count": sum(
            1 for boundary in local_boundaries if boundary.get("status") == "available"
        ),
        "review_required_local_domain_boundary_count": sum(
            1 for boundary in local_boundaries if boundary.get("status") == "review_required"
        ),
        "semantic_blocking_factor_count": len(readiness.get("blocking_factors", [])),
    }


def _parser_observations(
    general_sources: list[dict[str, Any]],
    local_sources: list[dict[str, Any]],
    readiness: dict[str, Any],
    document_mapping: dict[str, Any],
) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": "Domain source model inventories evidence sources only; it does not generate semantic ontology concepts.",
        },
        {
            "level": "info",
            "message": f"{len(general_sources)} general-domain sources are available for later semantic proposal constraints.",
        },
    ]
    if not local_sources:
        observations.append(
            {
                "level": "warning",
                "message": "No explicit local-domain policy or vocabulary source was supplied; local semantic candidates must remain boundary-pending.",
            }
        )
    if readiness.get("blocking_factors"):
        observations.append(
            {
                "level": "warning",
                "message": "Semantic proposal readiness has blocking or warning factors: "
                + ", ".join(readiness["blocking_factors"]),
            }
        )
    if document_mapping.get("summary", {}).get("review_queue_count"):
        observations.append(
            {
                "level": "info",
                "message": "Document ontology review queue remains separate from domain source readiness.",
            }
        )
    return observations


def _domain_root(sources: list[dict[str, Any]]) -> Path | None:
    if not sources:
        return None
    return Path(sources[0]["path"]).parent


def _domain_id_from_ref(ref_id: str, path: Path) -> str:
    if ref_id.startswith("general_domain:"):
        remainder = ref_id.split(":", 1)[1]
        if "/" in remainder:
            return remainder.split("/", 1)[0]
    if path.parent.name:
        return path.parent.name
    return "unknown"


def _heading_samples(path: Path, limit: int = 8) -> list[str]:
    headings = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(stripped)
            if len(headings) >= limit:
                break
    return headings


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build domain source model for semantic ontology preparation."
    )
    parser.add_argument("--evidence-package", type=Path, required=True)
    parser.add_argument("--document-ontology-mapping", type=Path, required=True)
    parser.add_argument("--action-contracts", type=Path, required=True)
    parser.add_argument("--general-domain-root", type=Path)
    parser.add_argument("--local-domain-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    model = build_domain_source_model(
        evidence_package_path=args.evidence_package,
        document_ontology_mapping_path=args.document_ontology_mapping,
        action_contracts_path=args.action_contracts,
        general_domain_root=args.general_domain_root,
        local_domain_root=args.local_domain_root,
    )
    payload = json.dumps(model, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
