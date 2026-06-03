from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"


def build_process_redesign_review(
    *,
    process_ledger_path: Path,
    tasklist_path: Path,
    design_doc_path: Path,
    agents_path: Path,
    implementation_map_path: Path,
    artifact_dir: Path,
) -> dict[str, Any]:
    process_ledger_path = process_ledger_path.expanduser().resolve()
    tasklist_path = tasklist_path.expanduser().resolve()
    design_doc_path = design_doc_path.expanduser().resolve()
    agents_path = agents_path.expanduser().resolve()
    implementation_map_path = implementation_map_path.expanduser().resolve()
    artifact_dir = artifact_dir.expanduser().resolve()

    ledger_entries = _read_ledger(process_ledger_path)
    tasklist_text = tasklist_path.read_text(encoding="utf-8")
    tasklist_stages = _tasklist_stages(tasklist_text)
    artifact_inventory = _artifact_inventory(artifact_dir)
    doc_inventory = _doc_inventory(
        [tasklist_path, design_doc_path, agents_path, implementation_map_path]
    )
    final_signals = _final_signals(artifact_inventory)
    stage_reviews = _stage_reviews(tasklist_stages)
    recommended_pipeline = _recommended_pipeline()
    redesign_decisions = _redesign_decisions(final_signals)
    open_evidence_gaps = _open_evidence_gaps(final_signals)
    next_iteration_plan = _next_iteration_plan()

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_materials": {
            "process_ledger": str(process_ledger_path),
            "tasklist": str(tasklist_path),
            "design_doc": str(design_doc_path),
            "agents": str(agents_path),
            "implementation_map": str(implementation_map_path),
            "artifact_dir": str(artifact_dir),
            "session_log_source": "process_ledger_jsonl",
            "artifact_inventory": artifact_inventory,
            "document_inventory": doc_inventory,
        },
        "method": {
            "name": "deterministic_process_redesign_review",
            "authority": "process_recommendation_not_parser_truth",
            "decision_policy": (
                "Use process ledger entries, tasklist stages, generated artifacts, final summaries, "
                "and active design documents to recommend which stages should be kept, merged, "
                "reordered, turned into loops, or held as review-only gates."
            ),
        },
        "final_assessment": _final_assessment(final_signals),
        "stage_reviews": stage_reviews,
        "recommended_pipeline": recommended_pipeline,
        "redesign_decisions": redesign_decisions,
        "open_evidence_gaps": open_evidence_gaps,
        "next_iteration_plan": next_iteration_plan,
        "summary": _summary(
            ledger_entries=ledger_entries,
            tasklist_stages=tasklist_stages,
            artifact_inventory=artifact_inventory,
            stage_reviews=stage_reviews,
            recommended_pipeline=recommended_pipeline,
            redesign_decisions=redesign_decisions,
            open_evidence_gaps=open_evidence_gaps,
        ),
        "parser_observations": _parser_observations(
            ledger_entries=ledger_entries,
            artifact_inventory=artifact_inventory,
            open_evidence_gaps=open_evidence_gaps,
        ),
    }


def _tasklist_stages(tasklist_text: str) -> list[dict[str, Any]]:
    stages = []
    for line in tasklist_text.splitlines():
        match = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if not match:
            continue
        stage_number, stage, status, done_when = match.groups()
        stages.append(
            {
                "stage_number": int(stage_number),
                "stage": stage.strip(),
                "status": status.strip(),
                "current_output": done_when.strip(),
            }
        )
    return stages


def _read_ledger(path: Path) -> list[dict[str, Any]]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def _artifact_inventory(artifact_dir: Path) -> list[dict[str, Any]]:
    inventory = []
    for path in sorted(artifact_dir.rglob("*")):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        rel = path.relative_to(artifact_dir).as_posix()
        item: dict[str, Any] = {
            "path": rel,
            "size_bytes": path.stat().st_size,
            "kind": path.suffix.lstrip(".") or "unknown",
        }
        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                item["json_status"] = "invalid"
            else:
                item["json_status"] = "valid"
                if isinstance(data, dict):
                    item["summary"] = data.get("summary", {})
                    item["method_name"] = data.get("method", {}).get("name")
        elif path.suffix == ".jsonl":
            with path.open(encoding="utf-8") as handle:
                item["line_count"] = sum(1 for _ in handle)
        inventory.append(item)
    return inventory


def _doc_inventory(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "line_count": len(path.read_text(encoding="utf-8").splitlines()),
        }
        for path in paths
    ]


def _final_signals(artifact_inventory: list[dict[str, Any]]) -> dict[str, Any]:
    by_path = {item["path"]: item for item in artifact_inventory}

    def summary(name: str) -> dict[str, Any]:
        return by_path.get(name, {}).get("summary", {})

    gate = summary("mbp-2026-02-gate-execution.json")
    boundary = summary("mbp-2026-02-boundary-decisions.json")
    roles = summary("mbp-2026-02-pipeline-role-validation.json")
    actions = summary("mbp-2026-02-action-contracts.json")
    proposal_validation = summary("mbp-2026-02-llm-proposal-validation.json")
    graph = summary("mbp-2026-02-validated-document-graph.json")
    projection = summary("mbp-2026-02-data-view-projection.json")
    local = summary("mbp-2026-02-local-semantic-candidates.json")
    shared = summary("mbp-2026-02-shared-ontology-alignment-review.json")
    view_state = summary("mbp-2026-02-view-state-profile.json")

    return {
        "gate_summary": gate,
        "boundary_summary": boundary,
        "pipeline_role_summary": roles,
        "action_contract_summary": actions,
        "proposal_validation_summary": proposal_validation,
        "validated_graph_summary": graph,
        "data_view_projection_summary": projection,
        "local_semantic_candidate_summary": local,
        "shared_alignment_summary": shared,
        "view_state_summary": view_state,
        "accepted_gate_count": gate.get("accepted_count", 0),
        "review_required_gate_count": gate.get("review_required_count", 0),
        "accepted_pipeline_role_count": roles.get("accepted_count", 0),
        "open_action_contract_count": actions.get("open_count", 0),
        "blocked_action_contract_count": actions.get("blocked_count", 0),
        "accepted_proposal_count": proposal_validation.get("accepted_count", 0),
        "proposal_review_required_count": proposal_validation.get(
            "requires_human_review_count", 0
        ),
        "quarantined_proposal_count": proposal_validation.get("quarantined_count", 0),
        "data_view_projection_count": projection.get("data_view_projection_count", 0),
        "local_candidate_count": local.get("local_semantic_candidate_count", 0),
        "shared_promoted_count": shared.get("promoted_count", 0),
        "shared_blocked_count": shared.get("blocked_alignment_count", 0),
        "basis_review_required_count": shared.get("basis_review_required_count", 0),
        "formula_result_validation_required_count": shared.get(
            "formula_result_validation_required_count", 0
        ),
        "semantic_label_pending_count": shared.get("semantic_label_pending_count", 0),
        "view_state_blocked_or_warning_count": (
            view_state.get("view_state_explained_failure_count", 0)
            + view_state.get("view_state_warning_count", 0)
        ),
        "graph_node_count": graph.get("graph_node_count", 0),
        "graph_relation_count": graph.get("graph_relation_count", 0),
    }


def _stage_reviews(tasklist_stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reviews = []
    for stage in tasklist_stages:
        number = stage["stage_number"]
        recommendation, priority, group, rationale, changes = _stage_recommendation(
            number
        )
        reviews.append(
            {
                "id": f"stage_review:{number:02d}",
                "current_stage_number": number,
                "current_stage": stage["stage"],
                "current_status": stage["status"],
                "recommendation": recommendation,
                "priority": priority,
                "proposed_group": group,
                "rationale": rationale,
                "recommended_changes": changes,
                "completion_guard": _completion_guard(number),
            }
        )
    return reviews


def _stage_recommendation(
    stage_number: int,
) -> tuple[str, str, str, list[str], list[str]]:
    if stage_number == 1:
        return (
            "keep_reordered_early",
            "high",
            "input_preflight",
            [
                "Hidden rows, filters, outline state, and view offsets affected later capture behavior.",
                "The process already corrected this by adding early view-state preflight.",
            ],
            [
                "Keep this immediately after fast manifest and before sampling/capture planning.",
                "Do not reveal hidden content by default; preserve source-visible authority.",
            ],
        )
    if stage_number in {4, 5}:
        return (
            "merge_as_region_candidate_generation",
            "medium",
            "region_candidate_model",
            [
                "Row-band seeds were useful but insufficient because row and column boundaries can both split tables.",
                "2D cell regions are the durable object; row bands should remain only early seeds.",
            ],
            [
                "Merge initial block candidates and 2D segmentation into one region-candidate stage with substeps.",
                "Retain row-band evidence as a seed property, not the final unit.",
            ],
        )
    if stage_number == 6:
        return (
            "keep_before_boundary_decisions",
            "high",
            "region_candidate_model",
            [
                "Style and merged-cell evidence materially improves split/merge boundary ranking.",
            ],
            [
                "Run structural style profiling before final split/merge boundary gates.",
            ],
        )
    if stage_number == 9:
        return (
            "move_to_review_package_layer",
            "low",
            "human_review_surface",
            [
                "Mermaid pipeline visualization is valuable for review but does not create parser truth.",
            ],
            [
                "Keep as a generated review surface attached to pipeline extraction rather than a core parser stage.",
            ],
        )
    if stage_number in {11, 12, 13, 14, 15, 16}:
        return (
            "turn_into_visual_evidence_loop",
            "high",
            "visual_evidence_loop",
            [
                "Capture, quality checks, recapture, view-state reconciliation, coordinate normalization, and visual features form an iterative evidence loop.",
                "Recapture experiments improved some wide-range captures but did not resolve hidden/filter authority cases.",
            ],
            [
                "Represent as a loop with explicit exit criteria instead of a strictly linear chain.",
                "Keep reveal/clear-filter variants diagnostic and non-authoritative.",
            ],
        )
    if stage_number in {17, 18, 19}:
        return (
            "keep_as_decision_layer",
            "high",
            "deterministic_decision_layer",
            [
                "Gate, boundary, and role decisions must remain separate from raw evidence extraction.",
            ],
            [
                "Keep accepted/review/rejected statuses distinct from final graph claims.",
                "Let formula and pivot authority support role labels even when visual evidence remains partial.",
            ],
        )
    if stage_number in {20, 21, 22}:
        return (
            "keep_as_authority_and_action_layers",
            "high",
            "evidence_and_action_layer",
            [
                "Evidence package, document ontology mapping, and action contracts made open review items traceable and actionable.",
            ],
            [
                "Keep document-structure ontology utilization separate from semantic ontology generation.",
                "Keep action contracts as the handoff surface for unresolved claims.",
            ],
        )
    if stage_number in {23, 24, 25}:
        return (
            "keep_with_proposal_boundary",
            "high",
            "semantic_proposal_layer",
            [
                "General-domain sources helped LLM proposal grounding, while deterministic validation quarantined local-boundary-sensitive claims.",
            ],
            [
                "Keep LLM output proposal-only.",
                "Require deterministic source, domain, conflict, formula/pivot topology, and local-boundary gates before graph membership.",
            ],
        )
    if stage_number in {26, 27, 28, 29}:
        return (
            "keep_as_projection_and_review_layers",
            "high",
            "graph_projection_and_semantic_review",
            [
                "Validated graph, data views, local candidates, and shared alignment separated accepted structure from semantic review queues.",
            ],
            [
                "Do not promote local candidates to shared ontology until boundary/source/repetition/conflict/formula/human gates pass.",
                "Add explicit K-GAAP/K-IFRS basis review for revenue candidates.",
            ],
        )
    if stage_number == 30:
        return (
            "keep_continuous",
            "high",
            "process_governance",
            [
                "The ledger exposed ordering mistakes, useful loops, and visual-review failures.",
            ],
            [
                "Run after each sample workbook and before locking the next process version.",
            ],
        )
    return (
        "keep",
        "medium",
        "core_pipeline",
        ["The stage produced reusable evidence for downstream parser decisions."],
        ["Keep the stage with current authority boundaries."],
    )


def _completion_guard(stage_number: int) -> list[str]:
    guards = {
        1: [
            "Hidden/filter/outline/pane state is inventoried before capture planning.",
            "Source-visible authority is preserved.",
        ],
        3: [
            "Formula references, external workbook references, pivot cache sources, and repeated formula signatures are indexed.",
        ],
        9: ["Visualization is present but cannot become parser truth."],
        13: ["Recapture candidates are accepted only after capture quality comparison."],
        22: ["Each action has owner, required evidence, gate, and completion effect."],
        25: ["LLM proposals have deterministic outcomes and rejected/quarantined queues."],
        29: ["Shared ontology updates remain zero while promotion blockers remain."],
        30: ["Review recommendations are written to artifact, docs, viewer, and ledger."],
    }
    return guards.get(stage_number, ["Output artifact exists and is schema-validated when a schema exists."])


def _recommended_pipeline() -> list[dict[str, Any]]:
    rows = [
        (0, "Fast ZIP/XML Manifest", [0], "keep", "Large-file and package risk preflight."),
        (1, "Workbook View-State Preflight", [1], "keep_reordered_early", "Human-visible state must be known before sampling/capture interpretation."),
        (2, "Read-Only Targeted Sampling", [2], "keep", "Values and formula text preview without mutating source workbook."),
        (3, "Pivot / Formula / External Reference Profiling", [3], "keep", "Dataflow, pivot cache, external link, and formula pattern authority."),
        (4, "Structural Style Profile", [6], "move_earlier", "Style/merge/dimension evidence before region boundary decisions."),
        (5, "Region Candidate Generation", [4, 5], "merge", "Combine row-band seeds and 2D region segmentation into one candidate model."),
        (6, "Split / Merge Boundary Ranking", [7], "keep", "Conservative candidate ranking before acceptance."),
        (7, "Table I/O Pipeline Extraction", [8], "keep", "Table-level input/output pipeline projection over formula and pivot authority."),
        (8, "Cross-Validation Target Planning", [10], "keep", "Plan visual/formula/pipeline gates before capture."),
        (9, "Visual Evidence Acquisition Loop", [11, 12, 13, 14, 15, 16], "loop", "Capture, quality, recapture, view-state reconciliation, normalization, and visual features."),
        (10, "Visual / Data / Formula Gate Execution", [17], "keep", "Evidence statuses, not final graph claims."),
        (11, "Boundary And Pipeline Role Decisions", [18, 19], "merge_decision_layer", "Decision layer over gates, boundary candidates, formula, and pivot authority."),
        (12, "Workbook Evidence Package Assembly", [20], "keep", "Single parser input authority."),
        (13, "Document Ontology Mapping", [21], "keep", "Document-structure ontology utilization."),
        (14, "Action Contract Layer", [22], "keep", "Actionable ontology handoff for unresolved claims."),
        (15, "Domain Knowledge Source Model", [23], "keep", "Separate general-domain and local-domain evidence."),
        (16, "LLM Proposal Generation", [24], "keep_proposal_only", "Interpretation only; no acceptance."),
        (17, "Deterministic Proposal Validation", [25], "keep_gate", "Gate LLM claims before graph membership."),
        (18, "Validated Document Graph", [26], "keep", "Accepted graph plus carry-forward queues."),
        (19, "Data View Projection", [27], "keep", "Reviewer-friendly read model over accepted graph."),
        (20, "Local Semantic Candidates", [28], "keep_review_candidate", "Boundary-scoped candidates only."),
        (21, "Shared Ontology Alignment / Human Review", [29], "keep_review_only", "Promotion blocked until evidence gates pass."),
        (22, "Review Package / Viewer Layout Gate", [9], "supporting_gate", "Generated review surfaces need layout QA."),
        (23, "Process Redesign Review", [30], "continuous", "Use ledger to redesign pipeline after each sample."),
    ]
    return [
        {
            "position": position,
            "stage": stage,
            "source_current_stage_numbers": source_numbers,
            "change_type": change_type,
            "why": why,
        }
        for position, stage, source_numbers, change_type, why in rows
    ]


def _redesign_decisions(final_signals: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "decision:view_state_preflight_first",
            "decision": "Move and keep view-state preflight at the beginning.",
            "status": "accepted_for_next_iteration",
            "evidence": [
                "Hidden/filter state explained capture behavior.",
                f"view_state_blocked_or_warning_count={final_signals.get('view_state_blocked_or_warning_count')}",
            ],
            "effect": "Capture planning and visual absence claims must know visible-state authority first.",
        },
        {
            "id": "decision:region_candidates_are_2d",
            "decision": "Treat row bands as seeds and 2D cell regions as the durable boundary object.",
            "status": "accepted_for_next_iteration",
            "evidence": [
                "The user identified that column boundaries and adjacent-but-separate regions can both exist.",
            ],
            "effect": "Merge row-band and 2D segmentation implementation as one candidate model.",
        },
        {
            "id": "decision:visual_capture_is_loop",
            "decision": "Model render capture, quality, recapture, view-state reconciliation, coordinate normalization, and visual feature detection as one loop.",
            "status": "accepted_for_next_iteration",
            "evidence": [
                "Recapture improved wide-range cases but not hidden/filter cases.",
                "Visual feature detection depends on quality and view-state authority.",
            ],
            "effect": "A capture target exits the loop only when it is usable, blocked by source-visible view-state, or explicitly carried as review-required.",
        },
        {
            "id": "decision:shared_ontology_review_only",
            "decision": "Keep shared ontology alignment review-only until promotion prerequisites pass.",
            "status": "accepted_for_next_iteration",
            "evidence": [
                f"shared_promoted_count={final_signals.get('shared_promoted_count')}",
                f"shared_blocked_count={final_signals.get('shared_blocked_count')}",
            ],
            "effect": "No shared ontology write path should run for this sample yet.",
        },
        {
            "id": "decision:formula_results_need_excel_engine",
            "decision": "Add an explicit Excel-engine recalculation gate before numeric formula-result claims.",
            "status": "accepted_for_next_iteration",
            "evidence": [
                f"formula_result_validation_required_count={final_signals.get('formula_result_validation_required_count')}",
            ],
            "effect": "Formula text remains evidence only until recalculated through Microsoft Excel or an approved equivalent authority.",
        },
        {
            "id": "decision:viewer_layout_gate",
            "decision": "Add a lightweight viewer layout gate for dense review sections.",
            "status": "accepted_for_next_iteration",
            "evidence": [
                "Stage 27 shared alignment section required a layout repair after user review.",
            ],
            "effect": "Generated HTML review surfaces must be checked for overflow and overlap.",
        },
    ]


def _open_evidence_gaps(final_signals: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "gap:local_boundary",
            "priority": "high",
            "gap": "Local domain boundary is not confirmed.",
            "blocks": ["local_semantic_truth_acceptance", "shared_ontology_promotion"],
            "required_evidence": ["confirmed_organization_or_project_boundary"],
        },
        {
            "id": "gap:local_sources",
            "priority": "high",
            "gap": "No local policy, glossary, or owner-approved vocabulary source is available.",
            "blocks": ["local_candidate_acceptance", "shared_ontology_promotion"],
            "required_evidence": ["local_policy_or_vocabulary_source"],
        },
        {
            "id": "gap:semantic_labels",
            "priority": "high",
            "gap": f"{final_signals.get('semantic_label_pending_count')} accepted data-view surfaces need semantic labels.",
            "blocks": ["candidate_alignment", "shared_ontology_promotion"],
            "required_evidence": ["human_confirmed_semantic_label"],
        },
        {
            "id": "gap:gaap_ifrs_basis",
            "priority": "high",
            "gap": f"{final_signals.get('basis_review_required_count')} candidates need K-GAAP/K-IFRS basis separation.",
            "blocks": ["official_ifrs_revenue_claim", "revenue_concept_promotion"],
            "required_evidence": [
                "k_gaap_vs_k_ifrs_output_definition",
                "official_ifrs_revenue_aggregation_definition",
            ],
        },
        {
            "id": "gap:formula_result_authority",
            "priority": "high",
            "gap": f"{final_signals.get('formula_result_validation_required_count')} candidates need Excel-engine formula-result validation.",
            "blocks": ["numeric_revenue_claim", "formula_based_shared_promotion"],
            "required_evidence": ["excel_engine_recalculation_sample"],
        },
        {
            "id": "gap:workbook_family_repetition",
            "priority": "medium",
            "gap": "No repeated workbook-pair or workbook-family evidence has been supplied.",
            "blocks": ["shared_ontology_promotion"],
            "required_evidence": ["workbook_family_or_pair_repetition_evidence"],
        },
        {
            "id": "gap:remaining_visual_review",
            "priority": "medium",
            "gap": f"{final_signals.get('review_required_gate_count')} gate results remain review-required.",
            "blocks": ["full_automation_claim"],
            "required_evidence": ["additional_capture_or_human_review"],
        },
    ]


def _next_iteration_plan() -> list[dict[str, Any]]:
    return [
        {
            "step": 1,
            "name": "Apply redesigned ordering to the next workbook or workbook pair.",
            "done_when": "The pipeline starts with manifest, view-state preflight, sampling, formula/pivot profiling, and style profiling before region segmentation.",
        },
        {
            "step": 2,
            "name": "Collect local-domain evidence.",
            "done_when": "A boundary and local vocabulary/policy source are attached before semantic acceptance.",
        },
        {
            "step": 3,
            "name": "Run Excel-engine formula-result validation on selected revenue outputs.",
            "done_when": "Numeric formula claims have recalculated Excel evidence or remain explicitly blocked.",
        },
        {
            "step": 4,
            "name": "Define K-GAAP/K-IFRS output basis.",
            "done_when": "Revenue surfaces are classified as K-GAAP output, K-IFRS support, or bridge with human-approved aggregation rules.",
        },
        {
            "step": 5,
            "name": "Add viewer layout QA to new dense sections.",
            "done_when": "Generated HTML sections pass desktop and mobile overflow checks.",
        },
    ]


def _final_assessment(final_signals: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "structural_understanding_ready_but_semantic_promotion_blocked",
        "what_is_ready": [
            "Workbook structure, visual evidence, formula/pivot dataflow, table I/O pipelines, document ontology mapping, actionable review items, validated graph, data views, local semantic candidates, and shared alignment blockers are represented as traceable artifacts.",
            f"{final_signals.get('data_view_projection_count')} data views are projected for review.",
            f"{final_signals.get('accepted_pipeline_role_count')} pipeline roles are accepted.",
        ],
        "what_is_not_ready": [
            "Official K-IFRS revenue output is not authoritative until output basis, aggregation rule, and Excel-engine formula results are confirmed.",
            "Shared ontology promotion is blocked because local boundary, local source, repeated workbook-family evidence, shared target checks, and human approval are missing.",
        ],
        "recommended_default_next_step": "Use the redesigned pipeline on a second workbook or source/output pair while collecting local-domain and formula-result authority evidence.",
    }


def _summary(
    *,
    ledger_entries: list[dict[str, Any]],
    tasklist_stages: list[dict[str, Any]],
    artifact_inventory: list[dict[str, Any]],
    stage_reviews: list[dict[str, Any]],
    recommended_pipeline: list[dict[str, Any]],
    redesign_decisions: list[dict[str, Any]],
    open_evidence_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    recommendation_counts = Counter(item["recommendation"] for item in stage_reviews)
    high_priority_stage_count = sum(
        1 for item in stage_reviews if item["priority"] == "high"
    )
    return {
        "ledger_entry_count": len(ledger_entries),
        "tasklist_stage_count": len(tasklist_stages),
        "artifact_count": len(artifact_inventory),
        "json_artifact_count": sum(1 for item in artifact_inventory if item["kind"] == "json"),
        "stage_review_count": len(stage_reviews),
        "high_priority_stage_review_count": high_priority_stage_count,
        "recommended_pipeline_stage_count": len(recommended_pipeline),
        "redesign_decision_count": len(redesign_decisions),
        "open_evidence_gap_count": len(open_evidence_gaps),
        "recommendation_counts": dict(recommendation_counts),
        "review_status": "process_redesign_review_completed",
    }


def _parser_observations(
    *,
    ledger_entries: list[dict[str, Any]],
    artifact_inventory: list[dict[str, Any]],
    open_evidence_gaps: list[dict[str, Any]],
) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": f"Reviewed {len(ledger_entries)} process ledger entries and {len(artifact_inventory)} generated artifacts.",
        }
    ]
    high_gaps = sum(1 for gap in open_evidence_gaps if gap["priority"] == "high")
    if high_gaps:
        observations.append(
            {
                "level": "warning",
                "message": f"{high_gaps} high-priority evidence gaps remain before semantic promotion or official numeric claims.",
            }
        )
    observations.append(
        {
            "level": "warning",
            "message": "Process recommendations are not parser truth; they must be applied and tested on the next workbook iteration.",
        }
    )
    return observations


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build process redesign review artifact from workbook-understanding outputs."
    )
    parser.add_argument("--process-ledger", type=Path, required=True)
    parser.add_argument("--tasklist", type=Path, required=True)
    parser.add_argument("--design-doc", type=Path, required=True)
    parser.add_argument("--agents", type=Path, required=True)
    parser.add_argument("--implementation-map", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    package = build_process_redesign_review(
        process_ledger_path=args.process_ledger,
        tasklist_path=args.tasklist,
        design_doc_path=args.design_doc,
        agents_path=args.agents,
        implementation_map_path=args.implementation_map,
        artifact_dir=args.artifact_dir,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
