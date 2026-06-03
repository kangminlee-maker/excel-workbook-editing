from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


def build_viewer(
    manifest_path: Path,
    readonly_sample_path: Path,
    block_candidates_path: Path,
    output_path: Path,
    formula_patterns_path: Path | None = None,
    structural_style_profile_path: Path | None = None,
    table_io_pipelines_path: Path | None = None,
    cross_validation_plan_path: Path | None = None,
    render_captures_path: Path | None = None,
    capture_quality_path: Path | None = None,
    recapture_candidate_plan_path: Path | None = None,
    recapture_candidate_captures_path: Path | None = None,
    recapture_candidate_quality_path: Path | None = None,
    view_state_preflight_path: Path | None = None,
    view_state_profile_path: Path | None = None,
    coordinate_normalization_path: Path | None = None,
    visual_features_path: Path | None = None,
    gate_execution_path: Path | None = None,
    boundary_decisions_path: Path | None = None,
    pipeline_role_validation_path: Path | None = None,
    evidence_package_path: Path | None = None,
    document_ontology_mapping_path: Path | None = None,
    action_contracts_path: Path | None = None,
    domain_source_model_path: Path | None = None,
    llm_proposals_path: Path | None = None,
    llm_proposal_validation_path: Path | None = None,
    validated_document_graph_path: Path | None = None,
    data_view_projection_path: Path | None = None,
    local_semantic_candidates_path: Path | None = None,
    shared_ontology_alignment_review_path: Path | None = None,
    process_redesign_review_path: Path | None = None,
    onto_reconstruct_seed_min_summary_path: Path | None = None,
) -> None:
    manifest = _read_json(manifest_path)
    sample = _read_json(readonly_sample_path)
    candidates = _read_json(block_candidates_path)
    formula_patterns = _read_json(formula_patterns_path) if formula_patterns_path else None
    structural_style_profile = (
        _read_json(structural_style_profile_path)
        if structural_style_profile_path
        else None
    )
    table_io_pipelines = (
        _read_json(table_io_pipelines_path)
        if table_io_pipelines_path
        else None
    )
    cross_validation_plan = (
        _read_json(cross_validation_plan_path)
        if cross_validation_plan_path
        else None
    )
    render_captures = (
        _read_json(render_captures_path)
        if render_captures_path
        else None
    )
    capture_quality = (
        _read_json(capture_quality_path)
        if capture_quality_path
        else None
    )
    recapture_candidate_plan = (
        _read_json(recapture_candidate_plan_path)
        if recapture_candidate_plan_path
        else None
    )
    recapture_candidate_captures = (
        _read_json(recapture_candidate_captures_path)
        if recapture_candidate_captures_path
        else None
    )
    recapture_candidate_quality = (
        _read_json(recapture_candidate_quality_path)
        if recapture_candidate_quality_path
        else None
    )
    view_state_preflight = (
        _read_json(view_state_preflight_path)
        if view_state_preflight_path
        else None
    )
    view_state_profile = (
        _read_json(view_state_profile_path)
        if view_state_profile_path
        else None
    )
    coordinate_normalization = (
        _read_json(coordinate_normalization_path)
        if coordinate_normalization_path
        else None
    )
    visual_features = (
        _read_json(visual_features_path)
        if visual_features_path
        else None
    )
    gate_execution = (
        _read_json(gate_execution_path)
        if gate_execution_path
        else None
    )
    boundary_decisions = (
        _read_json(boundary_decisions_path)
        if boundary_decisions_path
        else None
    )
    pipeline_role_validation = (
        _read_json(pipeline_role_validation_path)
        if pipeline_role_validation_path
        else None
    )
    evidence_package = (
        _read_json(evidence_package_path)
        if evidence_package_path
        else None
    )
    document_ontology_mapping = (
        _read_json(document_ontology_mapping_path)
        if document_ontology_mapping_path
        else None
    )
    action_contracts = (
        _read_json(action_contracts_path)
        if action_contracts_path
        else None
    )
    domain_source_model = (
        _read_json(domain_source_model_path)
        if domain_source_model_path
        else None
    )
    llm_proposals = _read_json(llm_proposals_path) if llm_proposals_path else None
    llm_proposal_validation = (
        _read_json(llm_proposal_validation_path)
        if llm_proposal_validation_path
        else None
    )
    validated_document_graph = (
        _read_json(validated_document_graph_path)
        if validated_document_graph_path
        else None
    )
    data_view_projection = (
        _read_json(data_view_projection_path)
        if data_view_projection_path
        else None
    )
    local_semantic_candidates = (
        _read_json(local_semantic_candidates_path)
        if local_semantic_candidates_path
        else None
    )
    shared_ontology_alignment_review = (
        _read_json(shared_ontology_alignment_review_path)
        if shared_ontology_alignment_review_path
        else None
    )
    process_redesign_review = (
        _read_json(process_redesign_review_path)
        if process_redesign_review_path
        else None
    )
    onto_reconstruct_seed_min_summary = (
        _read_json(onto_reconstruct_seed_min_summary_path)
        if onto_reconstruct_seed_min_summary_path
        else None
    )

    html_text = _page(
        manifest=manifest,
        sample=sample,
        candidates=candidates,
        formula_patterns=formula_patterns,
        structural_style_profile=structural_style_profile,
        table_io_pipelines=table_io_pipelines,
        cross_validation_plan=cross_validation_plan,
        render_captures=render_captures,
        capture_quality=capture_quality,
        recapture_candidate_plan=recapture_candidate_plan,
        recapture_candidate_captures=recapture_candidate_captures,
        recapture_candidate_quality=recapture_candidate_quality,
        view_state_preflight=view_state_preflight,
        view_state_profile=view_state_profile,
        coordinate_normalization=coordinate_normalization,
        visual_features=visual_features,
        gate_execution=gate_execution,
        boundary_decisions=boundary_decisions,
        pipeline_role_validation=pipeline_role_validation,
        evidence_package=evidence_package,
        document_ontology_mapping=document_ontology_mapping,
        action_contracts=action_contracts,
        domain_source_model=domain_source_model,
        llm_proposals=llm_proposals,
        llm_proposal_validation=llm_proposal_validation,
        validated_document_graph=validated_document_graph,
        data_view_projection=data_view_projection,
        local_semantic_candidates=local_semantic_candidates,
        shared_ontology_alignment_review=shared_ontology_alignment_review,
        process_redesign_review=process_redesign_review,
        onto_reconstruct_seed_min_summary=onto_reconstruct_seed_min_summary,
        viewer_dir=output_path.parent.expanduser().resolve(),
        artifact_paths={
            "manifest": manifest_path.name,
            "readonly_sample": readonly_sample_path.name,
            "block_candidates": block_candidates_path.name,
            **(
                {"formula_patterns": formula_patterns_path.name}
                if formula_patterns_path
                else {}
            ),
            **(
                {"structural_style_profile": structural_style_profile_path.name}
                if structural_style_profile_path
                else {}
            ),
            **(
                {"table_io_pipelines": table_io_pipelines_path.name}
                if table_io_pipelines_path
                else {}
            ),
            **(
                {"cross_validation_plan": cross_validation_plan_path.name}
                if cross_validation_plan_path
                else {}
            ),
            **(
                {"render_captures": render_captures_path.name}
                if render_captures_path
                else {}
            ),
            **(
                {"capture_quality": capture_quality_path.name}
                if capture_quality_path
                else {}
            ),
            **(
                {"recapture_candidate_plan": recapture_candidate_plan_path.name}
                if recapture_candidate_plan_path
                else {}
            ),
            **(
                {"recapture_candidate_captures": recapture_candidate_captures_path.name}
                if recapture_candidate_captures_path
                else {}
            ),
            **(
                {"recapture_candidate_quality": recapture_candidate_quality_path.name}
                if recapture_candidate_quality_path
                else {}
            ),
            **(
                {"view_state_preflight": view_state_preflight_path.name}
                if view_state_preflight_path
                else {}
            ),
            **(
                {"view_state_profile": view_state_profile_path.name}
                if view_state_profile_path
                else {}
            ),
            **(
                {"coordinate_normalization": coordinate_normalization_path.name}
                if coordinate_normalization_path
                else {}
            ),
            **(
                {"visual_features": visual_features_path.name}
                if visual_features_path
                else {}
            ),
            **(
                {"gate_execution": gate_execution_path.name}
                if gate_execution_path
                else {}
            ),
            **(
                {"boundary_decisions": boundary_decisions_path.name}
                if boundary_decisions_path
                else {}
            ),
            **(
                {"pipeline_role_validation": pipeline_role_validation_path.name}
                if pipeline_role_validation_path
                else {}
            ),
            **(
                {"evidence_package": evidence_package_path.name}
                if evidence_package_path
                else {}
            ),
            **(
                {"document_ontology_mapping": document_ontology_mapping_path.name}
                if document_ontology_mapping_path
                else {}
            ),
            **(
                {"action_contracts": action_contracts_path.name}
                if action_contracts_path
                else {}
            ),
            **(
                {"domain_source_model": domain_source_model_path.name}
                if domain_source_model_path
                else {}
            ),
            **(
                {"llm_proposals": llm_proposals_path.name}
                if llm_proposals_path
                else {}
            ),
            **(
                {"llm_proposal_validation": llm_proposal_validation_path.name}
                if llm_proposal_validation_path
                else {}
            ),
            **(
                {"validated_document_graph": validated_document_graph_path.name}
                if validated_document_graph_path
                else {}
            ),
            **(
                {"data_view_projection": data_view_projection_path.name}
                if data_view_projection_path
                else {}
            ),
            **(
                {"local_semantic_candidates": local_semantic_candidates_path.name}
                if local_semantic_candidates_path
                else {}
            ),
            **(
                {
                    "shared_ontology_alignment_review": shared_ontology_alignment_review_path.name
                }
                if shared_ontology_alignment_review_path
                else {}
            ),
            **(
                {"process_redesign_review": process_redesign_review_path.name}
                if process_redesign_review_path
                else {}
            ),
            **(
                {
                    "onto_reconstruct_seed_min_summary": (
                        onto_reconstruct_seed_min_summary_path.name
                    )
                }
                if onto_reconstruct_seed_min_summary_path
                else {}
            ),
        },
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")


def _page(
    *,
    manifest: dict[str, Any],
    sample: dict[str, Any],
    candidates: dict[str, Any],
    formula_patterns: dict[str, Any] | None,
    structural_style_profile: dict[str, Any] | None,
    table_io_pipelines: dict[str, Any] | None,
    cross_validation_plan: dict[str, Any] | None,
    render_captures: dict[str, Any] | None,
    capture_quality: dict[str, Any] | None,
    recapture_candidate_plan: dict[str, Any] | None,
    recapture_candidate_captures: dict[str, Any] | None,
    recapture_candidate_quality: dict[str, Any] | None,
    view_state_preflight: dict[str, Any] | None,
    view_state_profile: dict[str, Any] | None,
    coordinate_normalization: dict[str, Any] | None,
    visual_features: dict[str, Any] | None,
    gate_execution: dict[str, Any] | None,
    boundary_decisions: dict[str, Any] | None,
    pipeline_role_validation: dict[str, Any] | None,
    evidence_package: dict[str, Any] | None,
    document_ontology_mapping: dict[str, Any] | None,
    action_contracts: dict[str, Any] | None,
    domain_source_model: dict[str, Any] | None,
    llm_proposals: dict[str, Any] | None,
    llm_proposal_validation: dict[str, Any] | None,
    validated_document_graph: dict[str, Any] | None,
    data_view_projection: dict[str, Any] | None,
    local_semantic_candidates: dict[str, Any] | None,
    shared_ontology_alignment_review: dict[str, Any] | None,
    process_redesign_review: dict[str, Any] | None,
    onto_reconstruct_seed_min_summary: dict[str, Any] | None,
    viewer_dir: Path,
    artifact_paths: dict[str, str],
) -> str:
    source = manifest.get("source", {})
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Workbook Understanding Viewer</title>
  <style>
    :root {{
      --ink: #17202a;
      --muted: #5c6670;
      --line: #d7dde4;
      --soft: #f5f7fa;
      --panel: #ffffff;
      --accent: #0f766e;
      --accent-2: #7c3aed;
      --warn: #b45309;
      --danger: #b91c1c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #eef2f6;
    }}
    header {{
      padding: 24px 28px 18px;
      background: #0f172a;
      color: #fff;
    }}
    header h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      font-weight: 700;
    }}
    header p {{ margin: 4px 0; color: #cbd5e1; }}
    main {{ padding: 22px 28px 40px; max-width: 1440px; margin: 0 auto; }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 18px;
    }}
    nav a {{
      color: var(--accent);
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin: 18px 0;
      overflow: hidden;
    }}
    section > h2 {{
      margin: 0;
      padding: 14px 16px;
      font-size: 18px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
    }}
    .section-body {{ padding: 16px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
	    .metric {{
	      border: 1px solid var(--line);
	      border-radius: 8px;
	      padding: 10px 12px;
	      background: var(--soft);
	      min-width: 0;
	    }}
	    .metric .label {{
	      font-size: 12px;
	      color: var(--muted);
	      margin-bottom: 4px;
	      overflow-wrap: anywhere;
	    }}
	    .metric .value {{
	      font-size: 20px;
	      font-weight: 700;
	      overflow-wrap: anywhere;
	    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0 18px;
      font-size: 13px;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 7px 8px;
      vertical-align: top;
      text-align: left;
    }}
	    th {{ background: #f1f5f9; font-weight: 700; }}
	    table.compact {{
	      font-size: 12px;
	      table-layout: fixed;
	    }}
	    table.compact th, table.compact td {{
	      overflow-wrap: anywhere;
	      word-break: break-word;
	    }}
	    .table-wrap {{
	      width: 100%;
	      overflow-x: auto;
	      margin: 10px 0 18px;
	    }}
	    .table-wrap table {{
	      margin: 0;
	    }}
	    .table-wrap.wide table {{
	      min-width: 1280px;
	    }}
	    .review-panels {{
	      display: grid;
	      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
	      gap: 14px;
	      align-items: start;
	      margin: 12px 0 18px;
	    }}
	    .review-panel {{
	      min-width: 0;
	    }}
	    .review-panel h3 {{
	      margin: 0 0 8px;
	      font-size: 15px;
	    }}
    code {{
      background: #eef2f7;
      border: 1px solid #dde4ee;
      border-radius: 4px;
      padding: 1px 4px;
      font-size: 12px;
    }}
	    .pill {{
	      display: inline-block;
	      padding: 2px 7px;
      border-radius: 999px;
      background: #e6fffb;
      color: #0f766e;
      border: 1px solid #99f6e4;
	      font-size: 12px;
	      font-weight: 700;
	    }}
	    .pill.long {{
	      border-radius: 6px;
	      white-space: normal;
	      overflow-wrap: anywhere;
	      line-height: 1.35;
	    }}
    .pill.warn {{ background: #fff7ed; color: var(--warn); border-color: #fed7aa; }}
    .pill.danger {{ background: #fef2f2; color: var(--danger); border-color: #fecaca; }}
    .stage-note {{
      border-left: 4px solid var(--accent);
      background: #f0fdfa;
      padding: 10px 12px;
      margin-bottom: 14px;
      color: #134e4a;
      font-size: 13px;
    }}
    .review-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 12px;
      margin: 12px 0 18px;
    }}
    .review-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fff;
    }}
    .review-card h3 {{
      margin: 0 0 8px;
      font-size: 15px;
    }}
    .review-card p {{
      margin: 7px 0;
      line-height: 1.5;
      font-size: 13px;
    }}
    .review-card ul {{
      margin: 8px 0 0 18px;
      padding: 0;
      font-size: 13px;
      line-height: 1.5;
    }}
    .review-example {{
      margin-top: 9px;
      padding: 8px 10px;
      border-left: 3px solid var(--accent-2);
      background: #f8fafc;
      color: #334155;
      font-size: 12px;
      line-height: 1.45;
    }}
    .decision-strip {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 8px;
      margin-top: 10px;
    }}
    .decision {{
      border: 1px solid #dbeafe;
      border-radius: 6px;
      background: #eff6ff;
      padding: 8px;
      font-size: 12px;
      line-height: 1.45;
    }}
    .gate {{
      margin-top: 10px;
      padding: 8px 10px;
      border: 1px solid #fed7aa;
      border-radius: 6px;
      background: #fff7ed;
      color: #7c2d12;
      font-size: 12px;
      line-height: 1.45;
    }}
    .flow {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 8px;
      margin: 10px 0 16px;
    }}
    .flow-step {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: var(--soft);
      font-size: 12px;
      line-height: 1.45;
    }}
    .flow-step strong {{
      display: block;
      margin-bottom: 4px;
      color: var(--ink);
      font-size: 13px;
    }}
    .block-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }}
    .block-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fff;
    }}
    .block-card h3 {{
      margin: 0 0 6px;
      font-size: 15px;
    }}
    .capture-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
      margin-top: 12px;
    }}
    .capture-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 10px;
    }}
    .capture-card img {{
      display: block;
      width: 100%;
      max-height: 320px;
      object-fit: contain;
      border: 1px solid var(--line);
      background: #fff;
    }}
    .capture-card h3 {{
      margin: 8px 0 4px;
      font-size: 14px;
    }}
    .mermaid-panel {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 12px;
      margin: 12px 0 18px;
    }}
    .mermaid-panel h3 {{
      margin: 0 0 8px;
      font-size: 15px;
    }}
    .mermaid-diagram {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafc;
      margin: 10px 0;
    }}
    .mermaid {{
      min-width: 760px;
      padding: 14px;
    }}
    .mermaid-source {{
      margin-top: 8px;
    }}
    .mermaid-source summary {{
      cursor: pointer;
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
    }}
    .mermaid-source pre {{
      margin: 8px 0 0;
      padding: 10px;
      overflow-x: auto;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 6px;
      font-size: 12px;
      line-height: 1.45;
    }}
    .preview {{
      margin-top: 8px;
      padding: 8px;
      background: #f8fafc;
      border-radius: 6px;
      color: #334155;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      white-space: pre-wrap;
    }}
    .canvas {{
      position: relative;
      min-height: 520px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background:
        linear-gradient(#edf2f7 1px, transparent 1px),
        linear-gradient(90deg, #edf2f7 1px, transparent 1px),
        #fff;
      background-size: 24px 18px;
      overflow: hidden;
    }}
    .canvas-item {{
      position: absolute;
      border: 2px solid var(--accent);
      background: rgba(15, 118, 110, 0.08);
      border-radius: 4px;
      padding: 3px 5px;
      font-size: 11px;
      overflow: hidden;
    }}
    .canvas-item.image {{
      border-color: var(--accent-2);
      background: rgba(124, 58, 237, 0.10);
    }}
    .canvas-item.row {{
      border-color: var(--accent);
    }}
    .canvas-item.pivot {{
      border-color: var(--warn);
      background: rgba(180, 83, 9, 0.12);
    }}
    .muted {{ color: var(--muted); }}
    .small {{ font-size: 12px; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    document.addEventListener("DOMContentLoaded", () => {{
      if (window.mermaid) {{
        window.mermaid.initialize({{
          startOnLoad: true,
          theme: "base",
          securityLevel: "loose",
          flowchart: {{ htmlLabels: true, curve: "basis" }}
        }});
      }}
    }});
  </script>
</head>
<body>
  <header>
    <h1>Workbook Understanding Viewer</h1>
    <p>{_esc(source.get("file_name", "Workbook"))}</p>
    <p class="small">{_esc(source.get("path", ""))}</p>
  </header>
  <main>
    <nav>
      <a href="#stage-manifest">1. Manifest</a>
      {_nav_view_state_preflight(view_state_preflight)}
      <a href="#stage-sample">2. Read-only Sample</a>
      <a href="#stage-blocks">3. Block Candidates</a>
      {_nav_formula(formula_patterns)}
      {_nav_structural_style(structural_style_profile)}
      {_nav_table_io(table_io_pipelines)}
      {_nav_cross_validation(cross_validation_plan)}
      {_nav_render_captures(render_captures)}
      {_nav_capture_quality(capture_quality)}
      {_nav_recapture_candidate_plan(recapture_candidate_plan)}
      {_nav_recapture_candidate_results(recapture_candidate_quality)}
      {_nav_view_state_profile(view_state_profile)}
      {_nav_coordinate_normalization(coordinate_normalization)}
      {_nav_visual_features(visual_features)}
      {_nav_gate_execution(gate_execution)}
      {_nav_boundary_decisions(boundary_decisions)}
      {_nav_pipeline_role_validation(pipeline_role_validation)}
      {_nav_evidence_package(evidence_package)}
      {_nav_document_ontology_mapping(document_ontology_mapping)}
      {_nav_action_contracts(action_contracts)}
      {_nav_domain_source_model(domain_source_model)}
      {_nav_llm_proposals(llm_proposals)}
      {_nav_llm_proposal_validation(llm_proposal_validation)}
      {_nav_validated_document_graph(validated_document_graph)}
      {_nav_data_view_projection(data_view_projection)}
      {_nav_local_semantic_candidates(local_semantic_candidates)}
      {_nav_shared_ontology_alignment_review(shared_ontology_alignment_review)}
      {_nav_process_redesign_review(process_redesign_review)}
      {_nav_onto_reconstruct_seed_min_summary(onto_reconstruct_seed_min_summary)}
      <a href="#visual-map">Visual Map</a>
      <a href="#review-notes">Review Notes</a>
    </nav>
    {_artifact_links(artifact_paths)}
    {_manifest_section(manifest)}
    {_view_state_preflight_section(view_state_preflight)}
    {_sample_section(sample)}
    {_blocks_section(candidates)}
    {_formula_patterns_section(formula_patterns)}
    {_structural_style_section(structural_style_profile)}
    {_table_io_pipelines_section(table_io_pipelines)}
    {_cross_validation_plan_section(cross_validation_plan)}
    {_render_captures_section(render_captures, viewer_dir)}
    {_capture_quality_section(capture_quality, viewer_dir)}
    {_recapture_candidate_plan_section(recapture_candidate_plan)}
    {_recapture_candidate_results_section(recapture_candidate_plan, recapture_candidate_captures, recapture_candidate_quality, viewer_dir)}
    {_view_state_profile_section(view_state_profile)}
    {_coordinate_normalization_section(coordinate_normalization)}
    {_visual_features_section(visual_features)}
    {_gate_execution_section(gate_execution)}
    {_boundary_decisions_section(boundary_decisions)}
    {_pipeline_role_validation_section(pipeline_role_validation)}
    {_evidence_package_section(evidence_package)}
    {_document_ontology_mapping_section(document_ontology_mapping)}
    {_action_contracts_section(action_contracts)}
    {_domain_source_model_section(domain_source_model)}
    {_llm_proposals_section(llm_proposals)}
    {_llm_proposal_validation_section(llm_proposal_validation)}
    {_validated_document_graph_section(validated_document_graph)}
    {_data_view_projection_section(data_view_projection)}
    {_local_semantic_candidates_section(local_semantic_candidates)}
    {_shared_ontology_alignment_review_section(shared_ontology_alignment_review)}
    {_process_redesign_review_section(process_redesign_review)}
    {_onto_reconstruct_seed_min_summary_section(onto_reconstruct_seed_min_summary)}
    {_visual_map_section(candidates)}
    {_review_notes_section(candidates, formula_patterns)}
  </main>
</body>
</html>
"""


def _nav_formula(formula_patterns: dict[str, Any] | None) -> str:
    if not formula_patterns:
        return ""
    return '<a href="#stage-formulas">4. Formula Patterns</a>'


def _nav_view_state_preflight(
    view_state_preflight: dict[str, Any] | None,
) -> str:
    if not view_state_preflight:
        return ""
    return '<a href="#stage-view-state-preflight">1.5. View-State Preflight</a>'


def _nav_structural_style(structural_style_profile: dict[str, Any] | None) -> str:
    if not structural_style_profile:
        return ""
    return '<a href="#stage-structural-style">5. Structural Style</a>'


def _nav_table_io(table_io_pipelines: dict[str, Any] | None) -> str:
    if not table_io_pipelines:
        return ""
    return '<a href="#stage-table-io">6. Table I/O Pipelines</a>'


def _nav_cross_validation(cross_validation_plan: dict[str, Any] | None) -> str:
    if not cross_validation_plan:
        return ""
    return '<a href="#stage-cross-validation">7. Cross-Validation Plan</a>'


def _nav_render_captures(render_captures: dict[str, Any] | None) -> str:
    if not render_captures:
        return ""
    return '<a href="#stage-render-captures">8. Render Captures</a>'


def _nav_capture_quality(capture_quality: dict[str, Any] | None) -> str:
    if not capture_quality:
        return ""
    return '<a href="#stage-capture-quality">9. Capture Quality</a>'


def _nav_recapture_candidate_plan(
    recapture_candidate_plan: dict[str, Any] | None,
) -> str:
    if not recapture_candidate_plan:
        return ""
    return '<a href="#stage-recapture-candidates">10. Recapture Candidates</a>'


def _nav_recapture_candidate_results(
    recapture_candidate_quality: dict[str, Any] | None,
) -> str:
    if not recapture_candidate_quality:
        return ""
    return '<a href="#stage-recapture-results">11. Recapture Results</a>'


def _nav_view_state_profile(
    view_state_profile: dict[str, Any] | None,
) -> str:
    if not view_state_profile:
        return ""
    return '<a href="#stage-view-state">12. View-State</a>'


def _nav_coordinate_normalization(
    coordinate_normalization: dict[str, Any] | None,
) -> str:
    if not coordinate_normalization:
        return ""
    return '<a href="#stage-coordinate-normalization">13. Coordinates</a>'


def _nav_visual_features(
    visual_features: dict[str, Any] | None,
) -> str:
    if not visual_features:
        return ""
    return '<a href="#stage-visual-features">14. Visual Features</a>'


def _nav_gate_execution(
    gate_execution: dict[str, Any] | None,
) -> str:
    if not gate_execution:
        return ""
    return '<a href="#stage-gate-execution">15. Gate Execution</a>'


def _nav_boundary_decisions(
    boundary_decisions: dict[str, Any] | None,
) -> str:
    if not boundary_decisions:
        return ""
    return '<a href="#stage-boundary-decisions">16. Boundary Decisions</a>'


def _nav_pipeline_role_validation(
    pipeline_role_validation: dict[str, Any] | None,
) -> str:
    if not pipeline_role_validation:
        return ""
    return '<a href="#stage-pipeline-role-validation">17. Pipeline Roles</a>'


def _nav_evidence_package(
    evidence_package: dict[str, Any] | None,
) -> str:
    if not evidence_package:
        return ""
    return '<a href="#stage-evidence-package">18. Evidence Package</a>'


def _nav_document_ontology_mapping(
    document_ontology_mapping: dict[str, Any] | None,
) -> str:
    if not document_ontology_mapping:
        return ""
    return '<a href="#stage-document-ontology">19. Document Ontology</a>'


def _nav_action_contracts(
    action_contracts: dict[str, Any] | None,
) -> str:
    if not action_contracts:
        return ""
    return '<a href="#stage-action-contracts">20. Action Contracts</a>'


def _nav_domain_source_model(
    domain_source_model: dict[str, Any] | None,
) -> str:
    if not domain_source_model:
        return ""
    return '<a href="#stage-domain-source-model">21. Domain Sources</a>'


def _nav_llm_proposals(
    llm_proposals: dict[str, Any] | None,
) -> str:
    if not llm_proposals:
        return ""
    return '<a href="#stage-llm-proposals">22. LLM Proposals</a>'


def _nav_llm_proposal_validation(
    llm_proposal_validation: dict[str, Any] | None,
) -> str:
    if not llm_proposal_validation:
        return ""
    return '<a href="#stage-llm-proposal-validation">23. Proposal Validation</a>'


def _nav_validated_document_graph(
    validated_document_graph: dict[str, Any] | None,
) -> str:
    if not validated_document_graph:
        return ""
    return '<a href="#stage-validated-document-graph">24. Validated Graph</a>'


def _nav_data_view_projection(
    data_view_projection: dict[str, Any] | None,
) -> str:
    if not data_view_projection:
        return ""
    return '<a href="#stage-data-view-projection">25. Data View Projection</a>'


def _nav_local_semantic_candidates(
    local_semantic_candidates: dict[str, Any] | None,
) -> str:
    if not local_semantic_candidates:
        return ""
    return '<a href="#stage-local-semantic-candidates">26. Local Semantic Candidates</a>'


def _nav_shared_ontology_alignment_review(
    shared_ontology_alignment_review: dict[str, Any] | None,
) -> str:
    if not shared_ontology_alignment_review:
        return ""
    return '<a href="#stage-shared-ontology-alignment-review">27. Shared Alignment Review</a>'


def _nav_process_redesign_review(
    process_redesign_review: dict[str, Any] | None,
) -> str:
    if not process_redesign_review:
        return ""
    return '<a href="#stage-process-redesign-review">28. Process Redesign Review</a>'


def _nav_onto_reconstruct_seed_min_summary(
    onto_reconstruct_seed_min_summary: dict[str, Any] | None,
) -> str:
    if not onto_reconstruct_seed_min_summary:
        return ""
    return '<a href="#stage-onto-seed-min">61. Onto Seed</a>'


def _artifact_links(paths: dict[str, str]) -> str:
    rows = "".join(
        f"<tr><td>{_esc(label)}</td><td><a href=\"{_esc(path)}\">{_esc(path)}</a></td></tr>"
        for label, path in paths.items()
    )
    return f"""
<section>
  <h2>Artifacts</h2>
  <div class="section-body">
    <table>
      <tr><th>Stage</th><th>JSON</th></tr>
      {rows}
    </table>
  </div>
</section>
"""


def _manifest_section(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    sheets = manifest["workbook"]["sheets"]
    rows = []
    for sheet in sheets:
        status = sheet["detail_status"]
        status_class = "warn" if status == "skipped_large_xml" else ""
        rows.append(
            "<tr>"
            f"<td>{sheet['index']}</td>"
            f"<td>{_esc(sheet['name'])}</td>"
            f"<td>{_esc(sheet.get('dimension'))}</td>"
            f"<td><span class=\"pill {status_class}\">{_esc(status)}</span></td>"
            f"<td>{_num(sheet.get('entry_size_bytes'))}</td>"
            f"<td>{_num(sheet['counts']['cell_elements'])}</td>"
            f"<td>{_num(sheet['counts']['formula_elements'])}</td>"
            f"<td>{len(sheet.get('drawing_objects', []))}</td>"
            f"<td>{len(sheet.get('pivot_tables', []))}</td>"
            "</tr>"
        )
    observations = _observations(manifest.get("parser_observations", []))
    return f"""
<section id="stage-manifest">
  <h2>1. Fast ZIP/XML Manifest</h2>
  <div class="section-body">
    <div class="stage-note">대형 workbook을 full load하기 전에 package 구조, 시트 크기, shared strings, drawing/media, pivot/external link 위험을 빠르게 확인하는 단계입니다.</div>
    {_metrics(summary)}
    {observations}
    <table>
      <tr><th>#</th><th>Sheet</th><th>Dimension</th><th>Status</th><th>XML bytes</th><th>Cells</th><th>Formulas</th><th>Images</th><th>Pivots</th></tr>
      {''.join(rows)}
    </table>
    {_pivot_cache_table(manifest)}
    {_external_link_table(manifest)}
  </div>
</section>
"""


def _pivot_cache_table(manifest: dict[str, Any]) -> str:
    caches = manifest.get("workbook", {}).get("pivot_caches", [])
    if not caches:
        return ""
    rows = []
    for cache in caches:
        source = cache.get("source") or {}
        rows.append(
            "<tr>"
            f"<td>{_esc(cache.get('cache_id'))}</td>"
            f"<td>{_esc(source.get('sheet'))}</td>"
            f"<td><code>{_esc(source.get('range'))}</code></td>"
            f"<td>{_num(cache.get('record_count'))}</td>"
            f"<td>{_num(cache.get('cache_field_count'))}</td>"
            "</tr>"
        )
    return f"""
    <h3>Pivot Caches</h3>
    <table>
      <tr><th>Cache</th><th>Source Sheet</th><th>Source Range</th><th>Records</th><th>Fields</th></tr>
      {''.join(rows)}
    </table>
    """


def _external_link_table(manifest: dict[str, Any]) -> str:
    links = manifest.get("workbook", {}).get("external_links", [])
    if not links:
        return ""
    rows = []
    for link in links:
        targets = "<br>".join(
            f"{_esc(target.get('target_mode'))}: <code>{_esc(target.get('target'))}</code>"
            for target in link.get("targets", [])
        )
        sheet_samples = ", ".join(link.get("sheet_name_samples", [])[:8])
        rows.append(
            "<tr>"
            f"<td>{_esc(link.get('entry'))}</td>"
            f"<td>{_num(link.get('sheet_name_count'))}</td>"
            f"<td>{_esc(sheet_samples)}</td>"
            f"<td>{targets}</td>"
            "</tr>"
        )
    return f"""
    <h3>External Workbook Links</h3>
    <table>
      <tr><th>Entry</th><th>Sheets</th><th>Sheet Samples</th><th>Targets</th></tr>
      {''.join(rows)}
    </table>
    """


def _sample_section(sample: dict[str, Any]) -> str:
    sheet_html = []
    for sheet in sample["sheets"]:
        windows = []
        for window in sheet["windows"]:
            rows = []
            for row in window["rows"]:
                cells = " | ".join(
                    _esc(cell["value_preview"])
                    for cell in row["cells"][:10]
                    if cell.get("value_preview") is not None
                )
                if not cells:
                    cells = "<span class=\"muted\">blank</span>"
                rows.append(
                    f"<tr><td>{row['row']}</td><td>{row['non_empty_count']}</td><td>{row['formula_count']}</td><td>{cells}</td></tr>"
                )
            windows.append(
                f"""
                <h3>Rows {window['start_row']} - {window['end_row']}</h3>
                <p class="small muted">non-empty {window['non_empty_cell_count']}, formulas {window['formula_cell_count']}</p>
                <table>
                  <tr><th>Row</th><th>Non-empty</th><th>Formulas</th><th>Preview</th></tr>
                  {''.join(rows)}
                </table>
                """
            )
        sheet_html.append(
            f"""
            <h3>{_esc(sheet['name'])}</h3>
            <p class="small muted">max row {sheet['max_row']}, max column {sheet['max_column']}, sampled in {sheet['sample_seconds']}s</p>
            {''.join(windows)}
            """
        )
    return f"""
<section id="stage-sample">
  <h2>2. Read-only Targeted Row Sampling</h2>
  <div class="section-body">
    <div class="stage-note">원본 workbook을 <code>openpyxl read_only=True</code>로 열고, 필요한 row window만 빠르게 읽은 단계입니다. 수식 셀은 계산 결과가 아니라 수식 텍스트입니다.</div>
    {_metrics(sample['summary'])}
    {''.join(sheet_html)}
  </div>
</section>
"""


def _blocks_section(candidates: dict[str, Any]) -> str:
    sheets = []
    for sheet in candidates["sheets"]:
        blocks = []
        for block in sheet["blocks"]:
            bounds = block["bounds"]
            preview = "\n".join(block.get("preview", []))
            refs = block.get("formula_references", [])
            ref_note = (
                f", formula refs {len(refs)}{_formula_reference_kind_note(refs)}"
                if refs
                else ""
            )
            blocks.append(
                f"""
                <article class="block-card">
                  <h3>{_esc(block['label'] or block['id'])}</h3>
                  <p><span class="pill">{_esc(block['type'])}</span> <span class="pill">{_esc(block['subtype'])}</span></p>
                  <p class="small muted">Rows {bounds['start_row']} - {bounds['end_row']}, Columns {bounds['start_column']} - {bounds['end_column']}, confidence {block['confidence']}{ref_note}</p>
                  <div class="preview">{_esc(preview)}</div>
                </article>
                """
            )
        rel_rows = "".join(
            f"<tr><td>{_esc(rel['type'])}</td><td>{_esc(rel['from'])}</td><td>{_esc(rel['to'])}</td><td>{rel['confidence']}</td><td>{_esc(rel['reason'])}</td></tr>"
            for rel in sheet["relations"]
        )
        relation_groups = sheet.get("relation_groups", [])
        cell_regions = sheet.get("cell_regions", [])
        split_candidates = sheet.get("cell_region_split_candidates", [])
        boundary_gate_results = sheet.get("boundary_gate_results", [])
        sheets.append(
            f"""
            <h3>{_esc(sheet['name'])}</h3>
            <div class="block-grid">{''.join(blocks)}</div>
            {_cell_regions_table(cell_regions)}
            {_cell_region_split_candidates_table(split_candidates)}
            {_boundary_gate_results_table(boundary_gate_results)}
            {_relation_groups_table(relation_groups)}
            <h3>Relations</h3>
            <table>
              <tr><th>Type</th><th>From</th><th>To</th><th>Confidence</th><th>Reason</th></tr>
              {rel_rows}
            </table>
            """
        )
    return f"""
<section id="stage-blocks">
  <h2>3. Document Block Candidates</h2>
  <div class="section-body">
    <div class="stage-note">이미지 anchor, sampled row-oriented region seed, grid proximity를 결합한 deterministic seed입니다. 현재 <code>row_band</code>는 초기 후보 타입이며, 최종 Document Graph에서는 행/열 양방향 경계와 의미 분리 근거로 2D 셀 영역을 확정해야 합니다.</div>
    {_metrics(candidates['summary'])}
    {''.join(sheets)}
  </div>
</section>
"""


def _cell_regions_table(regions: list[dict[str, Any]]) -> str:
    if not regions:
        return ""
    rows = []
    for region in regions[:60]:
        bounds = region["bounds"]
        signal_types = sorted({signal["type"] for signal in region.get("split_signals", [])})
        rows.append(
            "<tr>"
            f"<td>{_esc(region['id'])}</td>"
            f"<td>{_esc(region['parent_seed_block_id'])}</td>"
            f"<td>{_esc(region['subtype'])}</td>"
            f"<td>R{bounds['start_row']}:R{bounds['end_row']}, C{bounds['start_column']}:C{bounds['end_column']}</td>"
            f"<td>{_num(region['metrics'].get('non_empty_cell_count'))}</td>"
            f"<td>{_num(region['metrics'].get('formula_cell_count'))}</td>"
            f"<td>{_esc(', '.join(signal_types))}</td>"
            "</tr>"
        )
    omitted = len(regions) - min(len(regions), 60)
    note = (
        f"<p class=\"small muted\">Showing top 60 of {len(regions)} 2D cell regions.</p>"
        if omitted > 0
        else ""
    )
    return f"""
            <h3>2D Cell Region Candidates</h3>
            {note}
            <table>
              <tr><th>Region</th><th>Seed</th><th>Subtype</th><th>Bounds</th><th>Cells</th><th>Formulas</th><th>Split Signals</th></tr>
              {''.join(rows)}
            </table>
            """


def _cell_region_split_candidates_table(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return ""
    rows = []
    for candidate in candidates[:40]:
        rows.append(
            "<tr>"
            f"<td>{_esc(candidate['type'])}</td>"
            f"<td>{_esc(candidate['parent_seed_block_id'])}</td>"
            f"<td>{_esc(candidate.get('from_region_id'))}</td>"
            f"<td>{_esc(candidate.get('to_region_id'))}</td>"
            f"<td>{_esc(candidate.get('boundary_within_region_id'))}</td>"
            f"<td>C{candidate['boundary_after_column']} / C{candidate['boundary_before_column']}</td>"
            f"<td>{candidate['confidence']}</td>"
            f"<td>{_esc(candidate['reason'])}</td>"
            "</tr>"
        )
    omitted = len(candidates) - min(len(candidates), 40)
    note = (
        f"<p class=\"small muted\">Showing top 40 of {len(candidates)} cell-region split candidates.</p>"
        if omitted > 0
        else ""
    )
    return f"""
            <h3>Cell Region Split Candidates</h3>
            {note}
            <table>
              <tr><th>Type</th><th>Seed</th><th>Left Region</th><th>Right Region</th><th>Within Region</th><th>Boundary</th><th>Confidence</th><th>Reason</th></tr>
              {''.join(rows)}
            </table>
            """


def _boundary_gate_results_table(results: list[dict[str, Any]]) -> str:
    if not results:
        return ""
    rows = []
    for result in sorted(results, key=lambda item: item.get("score", 0), reverse=True)[:60]:
        rows.append(
            "<tr>"
            f"<td>{_esc(result['candidate_type'])}</td>"
            f"<td><span class=\"pill\">{_esc(result['status'])}</span></td>"
            f"<td>{result['score']}</td>"
            f"<td>{_esc(result['decision'])}</td>"
            f"<td>{_esc(', '.join(result.get('related_region_ids', [])))}</td>"
            f"<td>{_esc(', '.join(result.get('evidence', [])))}</td>"
            f"<td>{_esc(result['rationale'])}</td>"
            "</tr>"
        )
    omitted = len(results) - min(len(results), 60)
    note = (
        f"<p class=\"small muted\">Showing top 60 of {len(results)} boundary gate results.</p>"
        if omitted > 0
        else ""
    )
    return f"""
            <h3>Boundary Gate Results</h3>
            {note}
            <table>
              <tr><th>Candidate</th><th>Status</th><th>Score</th><th>Decision</th><th>Regions</th><th>Evidence</th><th>Rationale</th></tr>
              {''.join(rows)}
            </table>
            """


def _structural_style_section(structural_style_profile: dict[str, Any] | None) -> str:
    if not structural_style_profile:
        return ""
    sheets = []
    for sheet in structural_style_profile.get("sheets", []):
        boundaries = sheet.get("style_boundaries", [])[:30]
        boundary_rows = "".join(
            "<tr>"
            f"<td>C{boundary['left_end_column']} / C{boundary['right_start_column']}</td>"
            f"<td>{_num(boundary['row_count'])}</td>"
            f"<td>{_esc(', '.join(str(row) for row in boundary.get('sample_rows', [])))}</td>"
            f"<td>{boundary['confidence']}</td>"
            f"<td>{_esc(boundary['reason'])}</td>"
            "</tr>"
            for boundary in boundaries
        )
        merge_rows = "".join(
            "<tr>"
            f"<td><code>{_esc(item['range'])}</code></td>"
            f"<td>{_esc(_bounds_label(item.get('bounds')))}</td>"
            "</tr>"
            for item in sheet.get("merge_ranges", [])[:20]
        )
        boundary_table = (
            f"""
            <h4>Style Boundaries</h4>
            <table>
              <tr><th>Boundary</th><th>Rows</th><th>Sample Rows</th><th>Confidence</th><th>Reason</th></tr>
              {boundary_rows}
            </table>
            """
            if boundary_rows
            else ""
        )
        merge_table = (
            f"""
            <h4>Merged Ranges</h4>
            <table>
              <tr><th>Range</th><th>Bounds</th></tr>
              {merge_rows}
            </table>
            """
            if merge_rows
            else ""
        )
        sheets.append(
            f"""
            <h3>{_esc(sheet['name'])}</h3>
            {_metrics(sheet['summary'])}
            {boundary_table}
            {merge_table}
            """
        )
    return f"""
<section id="stage-structural-style">
  <h2>5. Structural Style Profile</h2>
  <div class="section-body">
    <div class="stage-note">병합 범위, 행/열 dimension, sampled cell style, 시각 스타일 경계를 추출한 deterministic evidence입니다. 스타일 차이는 split 확정이 아니라 boundary gate의 후보 근거입니다.</div>
    {_metrics(structural_style_profile['summary'])}
    {''.join(sheets)}
  </div>
</section>
"""


def _table_io_pipelines_section(table_io_pipelines: dict[str, Any] | None) -> str:
    if not table_io_pipelines:
        return ""
    pipelines = table_io_pipelines.get("pipelines", [])
    rows = []
    for pipeline in pipelines[:80]:
        role_class = "warn" if pipeline.get("role") in {"summary", "report"} else ""
        flags = ", ".join(pipeline.get("review_flags", []))
        rows.append(
            "<tr>"
            f"<td><span class=\"pill {role_class}\">{_esc(pipeline.get('role'))}</span><br><span class=\"small muted\">{_esc(pipeline.get('id'))}</span></td>"
            f"<td>{_pipeline_ref_summary(pipeline.get('output_ref') or {})}</td>"
            f"<td>{_refs_summary(pipeline.get('input_refs', []))}</td>"
            f"<td>{_transform_summary(pipeline.get('transform_refs', []))}</td>"
            f"<td>{_esc(flags)}</td>"
            f"<td>{pipeline.get('confidence')}</td>"
            "</tr>"
        )
    omitted = len(pipelines) - min(len(pipelines), 80)
    note = (
        f"<p class=\"small muted\">Showing top 80 of {len(pipelines)} table I/O pipelines.</p>"
        if omitted > 0
        else ""
    )
    return f"""
<section id="stage-table-io">
  <h2>6. Table I/O Pipelines</h2>
  <div class="section-body">
    <div class="stage-note">수식 relation group, pivot cache source, 2D cell region 후보를 표 단위 입출력 후보로 투영한 단계입니다. 시각적으로 분리된 블록도 같은 계산 pipeline이면 연결하고, pivot table은 표시값이 아니라 cache/source 설정을 transform evidence로 기록합니다.</div>
    {_metrics(table_io_pipelines['summary'])}
    {_table_io_mermaid_section(pipelines)}
    {note}
    <table>
      <tr><th>Role</th><th>Output</th><th>Inputs</th><th>Transforms</th><th>Review Flags</th><th>Confidence</th></tr>
      {''.join(rows)}
    </table>
  </div>
</section>
"""


def _table_io_mermaid_section(pipelines: list[dict[str, Any]]) -> str:
    if not pipelines:
        return ""
    overview = _sheet_level_mermaid(pipelines)
    detail, detail_count = _pipeline_detail_mermaid(pipelines)
    return f"""
    <div class="mermaid-panel">
      <h3>Data Input/Output Pipeline Graph</h3>
      <p class="small muted">상단 graph는 전체 pipeline을 sheet 단위로 집계하고, 하단 graph는 검토 우선순위가 높은 table/pivot output 후보를 개별 ref 단위로 펼친 것입니다.</p>
      <h4>Sheet-Level Overview</h4>
      <div class="mermaid-diagram"><div class="mermaid">{_esc(overview)}</div></div>
      {_mermaid_source("Sheet-Level Mermaid Source", overview)}
      <h4>Pipeline-Level Detail</h4>
      <p class="small muted">Showing {detail_count} of {len(pipelines)} pipelines in the detailed graph. 전체 후보 목록은 아래 table을 기준으로 확인합니다.</p>
      <div class="mermaid-diagram"><div class="mermaid">{_esc(detail)}</div></div>
      {_mermaid_source("Pipeline-Level Mermaid Source", detail)}
    </div>
    """


def _mermaid_source(label: str, source: str) -> str:
    return f"""
      <details class="mermaid-source">
        <summary>{_esc(label)}</summary>
        <pre>{_esc(source)}</pre>
      </details>
    """


def _sheet_level_mermaid(pipelines: list[dict[str, Any]]) -> str:
    sheet_counts: dict[str, dict[str, int]] = {}
    edge_counts: dict[tuple[str, str, str], int] = {}
    for pipeline in pipelines:
        output_ref = pipeline.get("output_ref") or {}
        output_sheet = output_ref.get("sheet") or "unknown output"
        sheet_counts.setdefault(output_sheet, {"source": 0, "output": 0})[
            "output"
        ] += 1
        input_refs = pipeline.get("input_refs") or []
        label = _pipeline_edge_label(pipeline)
        if not input_refs:
            edge_counts[("Unresolved input", output_sheet, "unresolved")] = (
                edge_counts.get(("Unresolved input", output_sheet, "unresolved"), 0) + 1
            )
            sheet_counts.setdefault("Unresolved input", {"source": 0, "output": 0})[
                "source"
            ] += 1
            continue
        for input_ref in input_refs:
            input_sheet = (
                input_ref.get("sheet")
                or input_ref.get("workbook")
                or "unknown input"
            )
            sheet_counts.setdefault(input_sheet, {"source": 0, "output": 0})[
                "source"
            ] += 1
            key = (input_sheet, output_sheet, label)
            edge_counts[key] = edge_counts.get(key, 0) + 1

    node_ids = {
        sheet: f"s{idx}"
        for idx, sheet in enumerate(sorted(sheet_counts, key=lambda value: str(value)))
    }
    lines = [
        "flowchart LR",
        "  classDef sheetNode fill:#eef2ff,stroke:#4f46e5,color:#111827;",
        "  classDef unresolvedNode fill:#fef2f2,stroke:#b91c1c,color:#111827;",
    ]
    for sheet, node_id in node_ids.items():
        counts = sheet_counts[sheet]
        label = _mermaid_label(
            f"{sheet}<br/>feeds {counts['source']} / outputs {counts['output']}"
        )
        cls = "unresolvedNode" if sheet == "Unresolved input" else "sheetNode"
        lines.append(f'  {node_id}["{label}"]:::{cls}')
    for (input_sheet, output_sheet, edge_label), count in sorted(edge_counts.items()):
        if input_sheet not in node_ids or output_sheet not in node_ids:
            continue
        label = _mermaid_edge_label(f"{edge_label} x{count}")
        lines.append(f"  {node_ids[input_sheet]} -->|{label}| {node_ids[output_sheet]}")
    return "\n".join(lines)


def _pipeline_detail_mermaid(
    pipelines: list[dict[str, Any]], limit: int = 36
) -> tuple[str, int]:
    selected = _select_detail_pipelines(pipelines, limit)
    node_ids: dict[str, str] = {}
    node_defs: dict[str, tuple[str, str]] = {}
    edges: list[tuple[str, str, str]] = []

    def get_node(ref: dict[str, Any], fallback: str, as_output: bool = False) -> str:
        key = _pipeline_ref_key(ref, fallback)
        if key not in node_ids:
            node_id = f"n{len(node_ids)}"
            node_ids[key] = node_id
            node_defs[node_id] = (
                _mermaid_ref_label(ref, fallback),
                _mermaid_ref_class(ref, as_output=as_output),
            )
        elif as_output:
            label, cls = node_defs[node_ids[key]]
            if cls == "regionNode":
                node_defs[node_ids[key]] = (label, "outputNode")
        return node_ids[key]

    unresolved_id = "unresolved_input"
    for pipeline in selected:
        output_ref = pipeline.get("output_ref") or {}
        output_node = get_node(
            output_ref,
            pipeline.get("id") or "output",
            as_output=True,
        )
        input_refs = pipeline.get("input_refs") or []
        edge_label = _pipeline_edge_label(pipeline)
        if not input_refs:
            if unresolved_id not in node_ids:
                node_ids[unresolved_id] = f"n{len(node_ids)}"
                node_defs[node_ids[unresolved_id]] = (
                    "Unresolved input<br/>needs gate review",
                    "unresolvedNode",
                )
            edges.append((node_ids[unresolved_id], output_node, edge_label))
            continue
        for input_ref in input_refs[:5]:
            input_node = get_node(input_ref, "input")
            edges.append((input_node, output_node, edge_label))

    lines = [
        "flowchart LR",
        "  classDef regionNode fill:#eef2ff,stroke:#4f46e5,color:#111827;",
        "  classDef outputNode fill:#ecfdf5,stroke:#0f766e,color:#111827;",
        "  classDef pivotNode fill:#fff7ed,stroke:#b45309,color:#111827;",
        "  classDef externalNode fill:#faf5ff,stroke:#7c3aed,color:#111827;",
        "  classDef unresolvedNode fill:#fef2f2,stroke:#b91c1c,color:#111827;",
    ]
    for node_id, (label, cls) in node_defs.items():
        lines.append(f'  {node_id}["{_mermaid_label(label)}"]:::{cls}')
    for source, target, label in edges:
        lines.append(f"  {source} -->|{_mermaid_edge_label(label)}| {target}")
    return "\n".join(lines), len(selected)


def _select_detail_pipelines(
    pipelines: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    def score(pipeline: dict[str, Any]) -> tuple[int, float, str]:
        flags = set(pipeline.get("review_flags") or [])
        transforms = pipeline.get("transform_refs") or []
        transform_kinds = {transform.get("kind") for transform in transforms}
        priority = 0
        if "unresolved_input_region" in flags:
            priority += 100
        if "pivot_cache" in transform_kinds:
            priority += 60
        if pipeline.get("role") == "summary":
            priority += 35
        elif pipeline.get("role") == "report":
            priority += 30
        elif pipeline.get("role") == "transform":
            priority += 20
        priority += min(len(pipeline.get("input_refs") or []), 5)
        return (
            priority,
            float(pipeline.get("confidence") or 0),
            str(pipeline.get("id") or ""),
        )

    sorted_pipelines = sorted(pipelines, key=score, reverse=True)
    selected: list[dict[str, Any]] = []
    per_output_sheet: dict[str, int] = {}
    for pipeline in sorted_pipelines:
        output_sheet = (pipeline.get("output_ref") or {}).get("sheet") or ""
        flags = set(pipeline.get("review_flags") or [])
        cap = 8 if "unresolved_input_region" in flags else 5
        if per_output_sheet.get(output_sheet, 0) >= cap and len(selected) < limit // 2:
            continue
        selected.append(pipeline)
        per_output_sheet[output_sheet] = per_output_sheet.get(output_sheet, 0) + 1
        if len(selected) >= limit:
            break
    if len(selected) < min(limit, len(pipelines)):
        selected_ids = {id(item) for item in selected}
        for pipeline in sorted_pipelines:
            if id(pipeline) in selected_ids:
                continue
            selected.append(pipeline)
            if len(selected) >= limit:
                break
    return selected


def _pipeline_edge_label(pipeline: dict[str, Any]) -> str:
    transforms = pipeline.get("transform_refs") or []
    kinds = [transform.get("kind") for transform in transforms if transform.get("kind")]
    if "pivot_cache" in kinds:
        transform = "pivot_cache"
    elif kinds:
        transform = str(kinds[0])
    else:
        transform = "dataflow"
    role = pipeline.get("role") or "pipeline"
    return f"{role}/{transform}"


def _pipeline_ref_key(ref: dict[str, Any], fallback: str) -> str:
    return "|".join(
        str(part or "")
        for part in (
            ref.get("id") or fallback,
            ref.get("kind"),
            ref.get("workbook"),
            ref.get("sheet"),
            ref.get("range"),
        )
    )


def _mermaid_ref_label(ref: dict[str, Any], fallback: str) -> str:
    sheet = ref.get("sheet") or ref.get("workbook") or "unknown"
    range_text = ref.get("range") or ""
    kind = ref.get("kind") or "ref"
    label = ref.get("label") or ref.get("id") or fallback
    pieces = [str(sheet)]
    if range_text:
        pieces.append(str(range_text))
    pieces.append(str(kind))
    if label and label not in pieces:
        pieces.append(_shorten(str(label), 36))
    return "<br/>".join(pieces)


def _mermaid_ref_class(ref: dict[str, Any], *, as_output: bool) -> str:
    kind = ref.get("kind")
    if kind == "pivot_table":
        return "pivotNode"
    if ref.get("workbook") and not ref.get("sheet"):
        return "externalNode"
    if kind in {"unresolved", "unknown"}:
        return "unresolvedNode"
    return "outputNode" if as_output else "regionNode"


def _mermaid_label(value: str) -> str:
    return (
        str(value)
        .replace('"', "'")
        .replace("\n", " ")
        .replace("|", "/")
    )


def _mermaid_edge_label(value: str) -> str:
    return _mermaid_label(_shorten(str(value), 40)).replace("<br/>", " ")


def _refs_summary(refs: list[dict[str, Any]]) -> str:
    if not refs:
        return "<span class=\"muted\">none</span>"
    return "<br>".join(_pipeline_ref_summary(ref) for ref in refs[:6])


def _pipeline_ref_summary(ref: dict[str, Any]) -> str:
    pieces = [f"<span class=\"pill\">{_esc(ref.get('kind'))}</span>"]
    label = ref.get("label") or ref.get("id")
    if label:
        pieces.append(_esc(label))
    workbook = ref.get("workbook")
    if workbook:
        pieces.append(f"<span class=\"small muted\">workbook: {_esc(workbook)}</span>")
    sheet = ref.get("sheet")
    range_text = ref.get("range")
    if sheet or range_text:
        pieces.append(
            f"<span class=\"small muted\">{_esc(sheet)} {('<code>' + _esc(range_text) + '</code>') if range_text else ''}</span>"
        )
    return " ".join(pieces)


def _transform_summary(transforms: list[dict[str, Any]]) -> str:
    if not transforms:
        return "<span class=\"muted\">none</span>"
    rows = []
    for transform in transforms[:6]:
        if transform.get("kind") == "pivot_cache":
            text = "pivot cache aggregation/filter"
        else:
            text = _shorten(transform.get("formula_signature") or "", 140)
        rows.append(
            f"<span class=\"pill\">{_esc(transform.get('kind'))}</span> "
            f"<span class=\"small muted\">cells {_num(transform.get('formula_cell_count'))}, refs {_num(transform.get('reference_count'))}</span>"
            f"<br><code>{_esc(text)}</code>"
        )
    return "<br>".join(rows)


def _cross_validation_plan_section(cross_validation_plan: dict[str, Any] | None) -> str:
    if not cross_validation_plan:
        return ""
    targets = cross_validation_plan.get("capture_targets", [])
    target_by_id = {target.get("id"): target for target in targets}
    first_batch_targets = [
        target_by_id[target_id]
        for target_id in cross_validation_plan.get("recommended_first_batch_target_ids", [])
        if target_id in target_by_id
    ]
    target_rows = []
    for target in targets[:80]:
        priority_class = "danger" if target.get("priority") == "high" else (
            "warn" if target.get("priority") == "medium" else ""
        )
        target_rows.append(
            "<tr>"
            f"<td><span class=\"pill {priority_class}\">{_esc(target.get('priority'))}</span><br><span class=\"small muted\">score {target.get('score')}</span></td>"
            f"<td>{_esc(target.get('sheet'))}<br><code>{_esc(target.get('range'))}</code><div class=\"small muted\">capture {_esc((target.get('capture_window') or {}).get('range'))}</div></td>"
            f"<td>{_esc(target.get('target_type'))}<br>{_pipeline_ref_summary(target.get('target_ref') or {})}</td>"
            f"<td>{_esc(', '.join(target.get('reasons', [])[:8]))}</td>"
            f"<td>{_esc(', '.join(check.get('gate_type', '') for check in target.get('gate_checks', [])[:6]))}</td>"
            f"<td>{_esc(' / '.join(target.get('review_questions', [])[:2]))}</td>"
            "</tr>"
        )
    omitted = len(targets) - min(len(targets), 80)
    note = (
        f"<p class=\"small muted\">Showing top 80 of {len(targets)} capture targets.</p>"
        if omitted > 0
        else ""
    )
    first_batch_rows = "".join(
        "<tr>"
        f"<td>{index}</td>"
        f"<td>{_esc(target.get('sheet'))}</td>"
        f"<td><code>{_esc((target.get('capture_window') or {}).get('range'))}</code></td>"
        f"<td>{_esc(target.get('target_type'))}</td>"
        f"<td>{_esc(', '.join(target.get('reasons', [])[:5]))}</td>"
        "</tr>"
        for index, target in enumerate(first_batch_targets, 1)
    )
    first_batch = (
        f"""
        <h3>Recommended First Capture Batch</h3>
        <table>
          <tr><th>#</th><th>Sheet</th><th>Capture Window</th><th>Target Type</th><th>Why</th></tr>
          {first_batch_rows}
        </table>
        """
        if first_batch_rows
        else ""
    )
    return f"""
<section id="stage-cross-validation">
  <h2>7. Cross-Validation Plan</h2>
  <div class="section-body">
    <div class="stage-note">실제 Excel render capture를 실행하기 전, 어떤 영역을 먼저 캡처하고 어떤 deterministic gate를 걸지 정한 계획입니다. 이 단계의 출력은 검증 계획이며, 아직 캡처 결과나 최종 graph claim이 아닙니다.</div>
    {_metrics(cross_validation_plan['summary'])}
    {first_batch}
    {note}
    <table>
      <tr><th>Priority</th><th>Sheet / Range</th><th>Target</th><th>Reasons</th><th>Pending Gates</th><th>Review Questions</th></tr>
      {''.join(target_rows)}
    </table>
  </div>
</section>
"""


def _render_captures_section(
    render_captures: dict[str, Any] | None,
    viewer_dir: Path,
) -> str:
    if not render_captures:
        return ""
    cards = []
    for capture in render_captures.get("captures", []):
        output = capture.get("output") or {}
        png_path = output.get("png_path")
        image_src = _relative_src(png_path, viewer_dir) if png_path else ""
        status_class = "" if capture.get("status") == "captured" else "danger"
        gate_statuses = sorted(
            {gate.get("status", "") for gate in capture.get("gate_results", [])}
        )
        image_html = (
            f"<a href=\"{_esc(image_src)}\"><img src=\"{_esc(image_src)}\" alt=\"{_esc(capture.get('target_id'))}\"></a>"
            if image_src and capture.get("status") == "captured"
            else "<div class=\"preview\">capture failed</div>"
        )
        cards.append(
            f"""
            <article class="capture-card">
              {image_html}
              <h3>{_esc(capture.get('sheet'))} <code>{_esc((capture.get('capture_window') or {}).get('range'))}</code></h3>
              <p><span class="pill {status_class}">{_esc(capture.get('status'))}</span> <span class="small muted">{_esc(capture.get('target_id'))}</span></p>
              <p class="small muted">PNG {output.get('png_width')} x {output.get('png_height')}, gates {len(capture.get('gate_results', []))}: {_esc(', '.join(gate_statuses))}</p>
            </article>
            """
        )
    return f"""
<section id="stage-render-captures">
  <h2>8. Render Captures</h2>
  <div class="section-body">
    <div class="stage-note">Excel <code>copy picture</code> 경로로 캡처한 실제 range PNG입니다. 현재 gate 결과는 capture evidence 확보 상태이며, semantic pass/fail은 다음 bbox normalization 및 리뷰 단계에서 확정합니다.</div>
    {_metrics(render_captures['summary'])}
    <div class="capture-grid">
      {''.join(cards)}
    </div>
  </div>
</section>
"""


def _capture_quality_section(
    capture_quality: dict[str, Any] | None,
    viewer_dir: Path,
) -> str:
    if not capture_quality:
        return ""
    rows = []
    for result in _sorted_quality_results(capture_quality.get("quality_results", [])):
        png_path = result.get("png_path")
        image_src = _relative_src(png_path, viewer_dir) if png_path else ""
        link = (
            f"<a href=\"{_esc(image_src)}\">PNG</a>"
            if image_src
            else "<span class=\"muted\">PNG</span>"
        )
        dimensions = result.get("dimensions") or {}
        range_shape = result.get("range_shape") or {}
        metrics = result.get("metrics") or {}
        rows.append(
            "<tr>"
            f"<td><span class=\"pill {_quality_status_class(result.get('status'))}\">{_esc(result.get('status'))}</span><br><span class=\"small muted\">{_esc(result.get('capture_id'))}</span></td>"
            f"<td>{_esc(result.get('sheet'))}<br><code>{_esc(result.get('capture_window_range'))}</code><br>{link}</td>"
            f"<td>{_num(dimensions.get('width'))} x {_num(dimensions.get('height'))}<br><span class=\"small muted\">rows {_num(range_shape.get('row_count'))}, cols {_num(range_shape.get('column_count'))}</span></td>"
            f"<td>px/row {_metric(metrics.get('pixels_per_row'))}<br>px/col {_metric(metrics.get('pixels_per_column'))}<br>aspect {_metric(metrics.get('aspect_ratio'))}</td>"
            f"<td>{_quality_checks_summary(result.get('checks', []))}</td>"
            f"<td>{_esc(', '.join(result.get('recommendations', [])))}</td>"
            "</tr>"
        )
    return f"""
<section id="stage-capture-quality">
  <h2>9. Capture Quality</h2>
  <div class="section-body">
    <div class="stage-note">캡처 PNG가 다음 visual gate에 충분한지 deterministic하게 점검한 단계입니다. 이 결과는 semantic pass/fail이 아니라, 재캡처·타일링·확대가 필요한지 판단하는 품질 gate입니다.</div>
    {_metrics(capture_quality['summary'])}
    <table>
      <tr><th>Status</th><th>Capture</th><th>Image / Range</th><th>Metrics</th><th>Flagged Checks</th><th>Recommendations</th></tr>
      {''.join(rows)}
    </table>
  </div>
</section>
"""


def _recapture_candidate_plan_section(
    recapture_candidate_plan: dict[str, Any] | None,
) -> str:
    if not recapture_candidate_plan:
        return ""
    targets_by_id = {
        target.get("id"): target
        for target in recapture_candidate_plan.get("capture_targets", [])
    }
    sections = []
    for group in recapture_candidate_plan.get("candidate_groups", []):
        rows = []
        for target_id in group.get("candidate_target_ids", []):
            target = targets_by_id.get(target_id)
            if not target:
                continue
            rows.append(
                "<tr>"
                f"<td><span class=\"pill {_recapture_priority_class(target.get('priority'))}\">{_esc(target.get('priority'))}</span><br><span class=\"small muted\">{_esc(target.get('id'))}</span></td>"
                f"<td>{_esc(target.get('candidate_strategy'))}<br><span class=\"small muted\">tile {target.get('tile_index')} / {target.get('tile_count')}</span></td>"
                f"<td>{_esc(target.get('sheet'))}<br><code>{_esc(target.get('range'))}</code></td>"
                f"<td>{_esc(_shorten(target.get('candidate_rationale') or '', 140))}</td>"
                "</tr>"
            )
        sections.append(
            f"""
            <h3>{_esc(group.get('sheet'))} <code>{_esc(group.get('source_range'))}</code></h3>
            <p><span class="pill {_quality_status_class(group.get('source_quality_status'))}">{_esc(group.get('source_quality_status'))}</span> <span class="small muted">{_esc(', '.join(group.get('recommendations', [])))}</span></p>
            <table>
              <tr><th>Priority</th><th>Candidate Strategy</th><th>Range</th><th>Rationale</th></tr>
              {''.join(rows)}
            </table>
            """
        )
    return f"""
<section id="stage-recapture-candidates">
  <h2>10. Recapture Candidates</h2>
  <div class="section-body">
    <div class="stage-note">품질 문제가 있는 capture에 대해 여러 재캡처 후보를 만든 실험 계획입니다. 이 후보들은 최종 선택이 아니라 실제 캡처와 품질 재평가를 거쳐 비교해야 합니다.</div>
    {_metrics(recapture_candidate_plan['summary'])}
    {''.join(sections)}
  </div>
</section>
"""


def _recapture_candidate_results_section(
    recapture_candidate_plan: dict[str, Any] | None,
    recapture_candidate_captures: dict[str, Any] | None,
    recapture_candidate_quality: dict[str, Any] | None,
    viewer_dir: Path,
) -> str:
    if not recapture_candidate_quality:
        return ""
    plan_targets = {
        target.get("id"): target
        for target in (recapture_candidate_plan or {}).get("capture_targets", [])
    }
    captures = {
        capture.get("id"): capture
        for capture in (recapture_candidate_captures or {}).get("captures", [])
    }
    rows = []
    for result in _sorted_quality_results(recapture_candidate_quality.get("quality_results", [])):
        capture = captures.get(result.get("capture_id"), {})
        target = plan_targets.get(result.get("target_id"), {})
        output = capture.get("output") or {}
        png_path = result.get("png_path") or output.get("png_path")
        image_src = _relative_src(png_path, viewer_dir) if png_path else ""
        image_link = (
            f"<a href=\"{_esc(image_src)}\">PNG</a>"
            if image_src
            else "<span class=\"muted\">PNG</span>"
        )
        dimensions = result.get("dimensions") or {}
        metrics = result.get("metrics") or {}
        rows.append(
            "<tr>"
            f"<td><span class=\"pill {_quality_status_class(result.get('status'))}\">{_esc(result.get('status'))}</span><br><span class=\"small muted\">{_esc(result.get('target_id'))}</span></td>"
            f"<td>{_esc(target.get('candidate_strategy'))}<br><span class=\"small muted\">source {_esc(target.get('source_capture_id'))}</span></td>"
            f"<td>{_esc(result.get('sheet'))}<br><code>{_esc(result.get('capture_window_range'))}</code><br>{image_link}</td>"
            f"<td>{_num(dimensions.get('width'))} x {_num(dimensions.get('height'))}<br>px/row {_metric(metrics.get('pixels_per_row'))}<br>aspect {_metric(metrics.get('aspect_ratio'))}</td>"
            f"<td>{_quality_checks_summary(result.get('checks', []))}</td>"
            f"<td>{_esc(', '.join(result.get('recommendations', [])))}</td>"
            "</tr>"
        )
    return f"""
<section id="stage-recapture-results">
  <h2>11. Recapture Candidate Results</h2>
  <div class="section-body">
    <div class="stage-note">재캡처 후보를 실제 Excel capture로 실행한 뒤 다시 품질 gate를 통과시킨 결과입니다. wide-range tiling과 hidden/collapsed row 문제를 분리해서 봅니다.</div>
    {_metrics(recapture_candidate_quality['summary'])}
    <table>
      <tr><th>Status</th><th>Candidate</th><th>Capture</th><th>Metrics</th><th>Flagged Checks</th><th>Recommendations</th></tr>
      {''.join(rows)}
    </table>
  </div>
</section>
"""


def _view_state_preflight_section(
    view_state_preflight: dict[str, Any] | None,
) -> str:
    if not view_state_preflight:
        return ""
    sheet_rows = _view_state_sheet_rows(view_state_preflight)
    return f"""
<section id="stage-view-state-preflight">
  <h2>1.5. View-State Preflight</h2>
  <div class="section-body">
    <div class="stage-note">원본 visible state를 유지한 채 hidden row/column, filter, outline, pane 상태를 먼저 인벤토리화합니다. 전체 reveal은 기본 입력이 아니라 필요한 경우에만 만드는 non-authoritative diagnostic projection입니다.</div>
    {_metrics(view_state_preflight['summary'])}
    <table>
      <tr><th>Sheet</th><th>Hidden Rows</th><th>Hidden Columns</th><th>Outline Columns</th><th>Filters</th></tr>
      {sheet_rows}
    </table>
  </div>
</section>
"""


def _view_state_profile_section(
    view_state_profile: dict[str, Any] | None,
) -> str:
    if not view_state_profile:
        return ""
    sheet_rows = _view_state_sheet_rows(view_state_profile)
    analysis_rows = []
    for analysis in _sorted_view_state_analyses(
        view_state_profile.get("capture_window_analyses", [])
    ):
        row_summary = analysis.get("row_state_summary") or {}
        col_summary = analysis.get("column_state_summary") or {}
        analysis_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_view_state_class(analysis.get('classification'))}\">{_esc(analysis.get('classification'))}</span><br><span class=\"small muted\">{_esc(analysis.get('quality_status'))}</span></td>"
            f"<td>{_esc(analysis.get('sheet'))}<br><code>{_esc(analysis.get('range'))}</code><br><span class=\"small muted\">{_esc(analysis.get('capture_quality_file'))}</span></td>"
            f"<td>hidden {_num(row_summary.get('hidden_row_count'))} / visible {_num(row_summary.get('visible_row_count'))}<br><span class=\"small muted\">ratio {_metric(row_summary.get('hidden_row_ratio'))}</span></td>"
            f"<td>hidden {_num(col_summary.get('hidden_column_count'))} / visible {_num(col_summary.get('visible_column_count'))}<br><span class=\"small muted\">ratio {_metric(col_summary.get('hidden_column_ratio'))}</span></td>"
            f"<td>{_esc(analysis.get('authority_decision'))}<br><span class=\"small muted\">{_esc(analysis.get('recommended_next_action'))}</span></td>"
            "</tr>"
        )
    return f"""
<section id="stage-view-state">
  <h2>12. Hidden Row / View-State</h2>
  <div class="section-body">
    <div class="stage-note">Workbook XML의 hidden row/column, autoFilter, filterMode, frozen pane, sheet view 상태를 capture quality와 대조한 결과입니다. 이 단계는 현재 Excel에서 보이는 화면의 권위와 숨겨진 구조 데이터의 권위를 분리합니다.</div>
    {_metrics(view_state_profile['summary'])}
    <h3>Sheet View-State Signals</h3>
    <table>
      <tr><th>Sheet</th><th>Hidden Rows</th><th>Hidden Columns</th><th>Outline Columns</th><th>Filters</th></tr>
      {sheet_rows}
    </table>
    <h3>Capture Window Gate Results</h3>
    <table>
      <tr><th>Classification</th><th>Capture Window</th><th>Rows</th><th>Columns</th><th>Authority / Next Action</th></tr>
      {''.join(analysis_rows)}
    </table>
  </div>
</section>
"""


def _view_state_sheet_rows(profile: dict[str, Any]) -> str:
    rows = []
    for sheet in profile.get("sheets", []):
        summary = sheet.get("summary") or {}
        if not any(
            summary.get(key, 0)
            for key in (
                "hidden_row_count",
                "hidden_column_count",
                "outline_column_count",
                "auto_filter_count",
            )
        ):
            continue
        filters = ", ".join(
            item.get("ref") or ""
            for item in sheet.get("auto_filters", [])
            if item.get("ref")
        )
        hidden_rows = _span_summary(sheet.get("hidden_row_spans", []), "row")
        hidden_cols = _span_summary(sheet.get("hidden_column_spans", []), "column")
        outline_cols = _span_summary(sheet.get("outline_column_spans", []), "column")
        rows.append(
            "<tr>"
            f"<td>{_esc(sheet.get('name'))}<br><span class=\"small muted\">{_esc(sheet.get('detail_status'))}</span></td>"
            f"<td>{_num(summary.get('hidden_row_count'))}<br><span class=\"small muted\">{hidden_rows}</span></td>"
            f"<td>{_num(summary.get('hidden_column_count'))}<br><span class=\"small muted\">{hidden_cols}</span></td>"
            f"<td>{_num(summary.get('outline_column_count'))}<br><span class=\"small muted\">{outline_cols}</span></td>"
            f"<td>filterMode {_esc(sheet.get('sheet_pr', {}).get('filterMode') or '0')}<br><span class=\"small muted\">{_esc(filters or 'none')}</span></td>"
            "</tr>"
        )
    return "".join(rows)


def _coordinate_normalization_section(
    coordinate_normalization: dict[str, Any] | None,
) -> str:
    if not coordinate_normalization:
        return ""
    rows = []
    for mapping in _sorted_coordinate_mappings(
        coordinate_normalization.get("coordinate_mappings", [])
    ):
        bbox = mapping.get("capture_bbox") or {}
        scale = mapping.get("pixel_scale") or {}
        rows.append(
            "<tr>"
            f"<td><span class=\"pill {_coordinate_status_class(mapping.get('status'))}\">{_esc(mapping.get('status'))}</span><br><span class=\"small muted\">{_esc(mapping.get('capture_id'))}</span></td>"
            f"<td>{_esc(mapping.get('sheet'))}<br><code>{_esc(mapping.get('cell_range'))}</code><br><span class=\"small muted\">{_esc(mapping.get('capture_quality_file'))}</span></td>"
            f"<td>{_num(bbox.get('width'))} x {_num(bbox.get('height'))}<br><span class=\"small muted\">px/row {_metric(scale.get('pixels_per_row_estimate'))}, px/col {_metric(scale.get('pixels_per_column_estimate'))}</span></td>"
            f"<td>{_esc(mapping.get('view_state_classification'))}<br><span class=\"small muted\">{_esc(mapping.get('view_state_authority_decision'))}</span></td>"
            f"<td>{_esc(_shorten(mapping.get('normalization_notes') or '', 160))}</td>"
            "</tr>"
        )
    return f"""
<section id="stage-coordinate-normalization">
  <h2>13. Coordinate Normalization</h2>
  <div class="section-body">
    <div class="stage-note">Capture bbox를 workbook cell range에 다시 매핑합니다. 이 단계는 range-level 좌표 근거를 만들 뿐, 내부 시각 특징이나 semantic claim을 확정하지 않습니다.</div>
    {_metrics(coordinate_normalization['summary'])}
    <table>
      <tr><th>Status</th><th>Range</th><th>Capture BBox / Scale</th><th>View-State</th><th>Notes</th></tr>
      {''.join(rows)}
    </table>
  </div>
</section>
"""


def _visual_features_section(
    visual_features: dict[str, Any] | None,
) -> str:
    if not visual_features:
        return ""
    rows = []
    for result in _sorted_visual_feature_results(
        visual_features.get("feature_results", [])
    ):
        metrics = result.get("image_metrics") or {}
        lines = result.get("line_features") or {}
        rows.append(
            "<tr>"
            f"<td><span class=\"pill {_visual_feature_status_class(result.get('status'))}\">{_esc(result.get('status'))}</span><br><span class=\"small muted\">{_esc(result.get('capture_id'))}</span></td>"
            f"<td>{_esc(result.get('sheet'))}<br><code>{_esc(result.get('cell_range'))}</code></td>"
            f"<td>visible {_metric(metrics.get('visible_pixel_ratio'))}<br><span class=\"small muted\">content {_bbox_label(metrics.get('content_bbox'))}</span></td>"
            f"<td>h {_num(lines.get('horizontal_line_count'))} / v {_num(lines.get('vertical_line_count'))}</td>"
            f"<td>{_esc(', '.join(result.get('layout_signals', [])))}</td>"
            f"<td>{_esc(_shorten(result.get('feature_notes') or '', 140))}</td>"
            "</tr>"
        )
    return f"""
<section id="stage-visual-features">
  <h2>14. Visual Feature Detection</h2>
  <div class="section-body">
    <div class="stage-note">Normalized visible captures에서 whitespace, content bbox, line 후보, dominant color, grid/table-like 신호를 deterministic하게 추출합니다. 이 단계도 semantic truth가 아니라 다음 gate의 시각 증거입니다.</div>
    {_metrics(visual_features['summary'])}
    <table>
      <tr><th>Status</th><th>Range</th><th>Content</th><th>Lines</th><th>Layout Signals</th><th>Notes</th></tr>
      {''.join(rows)}
    </table>
  </div>
</section>
"""


def _gate_execution_section(
    gate_execution: dict[str, Any] | None,
) -> str:
    if not gate_execution:
        return ""
    rows = []
    for result in _sorted_gate_execution_results(gate_execution.get("gate_results", [])):
        rows.append(
            "<tr>"
            f"<td><span class=\"pill {_gate_execution_status_class(result.get('status'))}\">{_esc(result.get('status'))}</span><br><span class=\"small muted\">{_esc(result.get('reason'))}</span></td>"
            f"<td>{_esc(result.get('gate_type'))}<br><span class=\"small muted\">{_esc(result.get('gate_check_id'))}</span></td>"
            f"<td>{_esc(result.get('sheet'))}<br><code>{_esc(result.get('range'))}</code><br><span class=\"small muted\">{_esc(result.get('target_id'))}</span></td>"
            f"<td>{_metric(result.get('confidence'))}</td>"
            f"<td>{_esc(', '.join(result.get('layout_signals', [])))}</td>"
            f"<td>{_esc(_shorten(result.get('notes') or '', 160))}</td>"
            "</tr>"
        )
    return f"""
<section id="stage-gate-execution">
  <h2>15. Cross-Validation Gate Execution</h2>
  <div class="section-body">
    <div class="stage-note">계획된 pending gate를 visual feature, capture quality, view-state 증거로 1차 실행한 결과입니다. accepted는 증거 gate 통과를 뜻하며, 아직 최종 document graph 확정은 아닙니다.</div>
    {_metrics(gate_execution['summary'])}
    <table>
      <tr><th>Status</th><th>Gate</th><th>Target</th><th>Confidence</th><th>Signals</th><th>Notes</th></tr>
      {''.join(rows)}
    </table>
  </div>
</section>
"""


def _sorted_gate_execution_results(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    order = {
        "rejected": 0,
        "review_required": 1,
        "accepted": 2,
    }
    return sorted(
        results,
        key=lambda item: (
            order.get(item.get("status"), 99),
            str(item.get("reason") or ""),
            str(item.get("gate_type") or ""),
            str(item.get("target_id") or ""),
        ),
    )


def _gate_execution_status_class(status: Any) -> str:
    if status == "rejected":
        return "danger"
    if status == "review_required":
        return "warn"
    return ""


def _boundary_decisions_section(
    boundary_decisions: dict[str, Any] | None,
) -> str:
    if not boundary_decisions:
        return ""
    rows = []
    for decision in _sorted_boundary_decisions(
        boundary_decisions.get("boundary_decisions", [])
    ):
        linked = decision.get("linked_gate_results", [])
        linked_summary = ", ".join(
            f"{item.get('link_type')}:{item.get('status')}:{item.get('reason')}"
            for item in linked[:3]
        )
        if len(linked) > 3:
            linked_summary += f", +{len(linked) - 3}"
        location = decision.get("boundary_location") or {}
        columns = ""
        if location:
            columns = (
                f"C{location.get('boundary_after_column')} / "
                f"C{location.get('boundary_before_column')}"
            )
        rows.append(
            "<tr>"
            f"<td><span class=\"pill {_gate_execution_status_class(decision.get('status'))}\">{_esc(decision.get('status'))}</span><br><span class=\"small muted\">{_esc(decision.get('reason'))}</span></td>"
            f"<td>{_esc(decision.get('candidate_type'))}<br><span class=\"small muted\">{_esc(decision.get('boundary_kind'))}</span></td>"
            f"<td>{_esc(decision.get('sheet'))}<br><code>{_esc(columns)}</code><br><span class=\"small muted\">{_esc(decision.get('source_boundary_gate_result_id'))}</span></td>"
            f"<td>{_esc(decision.get('decision'))}<br><span class=\"small muted\">{_esc(decision.get('graph_effect'))}</span></td>"
            f"<td>{_metric(decision.get('confidence'))}</td>"
            f"<td>{_esc(_shorten(linked_summary, 180))}</td>"
            "</tr>"
        )
    return f"""
<section id="stage-boundary-decisions">
  <h2>16. Boundary Acceptance / Rejection</h2>
  <div class="section-body">
    <div class="stage-note">Boundary 후보를 document graph boundary로 승격할지 결정한 결과입니다. blank-column처럼 구조적으로 강한 split만 자동 수용하고, style-only와 merged-title 근거는 review item으로 유지합니다.</div>
    {_metrics(boundary_decisions['summary'])}
    <table>
      <tr><th>Status</th><th>Candidate</th><th>Location</th><th>Decision</th><th>Confidence</th><th>Linked Gates</th></tr>
      {''.join(rows)}
    </table>
  </div>
</section>
"""


def _sorted_boundary_decisions(
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    order = {
        "rejected": 0,
        "review_required": 1,
        "accepted": 2,
    }
    return sorted(
        decisions,
        key=lambda item: (
            order.get(item.get("status"), 99),
            str(item.get("reason") or ""),
            str(item.get("sheet") or ""),
            str(item.get("source_boundary_gate_result_id") or ""),
        ),
    )


def _pipeline_role_validation_section(
    pipeline_role_validation: dict[str, Any] | None,
) -> str:
    if not pipeline_role_validation:
        return ""
    rows = []
    for validation in _sorted_pipeline_role_validations(
        pipeline_role_validation.get("role_validations", [])
    ):
        output_ref = validation.get("output_ref") or {}
        gates = validation.get("linked_gate_results", [])
        gate_summary = ", ".join(
            f"{item.get('gate_type')}:{item.get('status')}:{item.get('reason')}"
            for item in gates[:3]
        )
        if len(gates) > 3:
            gate_summary += f", +{len(gates) - 3}"
        rows.append(
            "<tr>"
            f"<td><span class=\"pill {_gate_execution_status_class(validation.get('status'))}\">{_esc(validation.get('status'))}</span><br><span class=\"small muted\">{_esc(validation.get('reason'))}</span></td>"
            f"<td>{_esc(validation.get('asserted_role'))}<br><span class=\"small muted\">{_esc(validation.get('pipeline_id'))}</span></td>"
            f"<td>{_esc(output_ref.get('sheet'))}<br><code>{_esc(output_ref.get('range'))}</code><br><span class=\"small muted\">{_esc(output_ref.get('kind'))}</span></td>"
            f"<td>{_metric(validation.get('confidence'))}</td>"
            f"<td>{_esc(', '.join(validation.get('role_evidence', [])[:8]))}</td>"
            f"<td>{_esc(_shorten(gate_summary, 180))}</td>"
            "</tr>"
        )
    return f"""
<section id="stage-pipeline-role-validation">
  <h2>17. Pipeline Role Validation</h2>
  <div class="section-body">
    <div class="stage-note">수식 signature, pivot cache, input/output refs, boundary decision, gate 결과를 결합해 pipeline role을 검증합니다. 시각 capture가 부족한 pivot report도 pivot cache authority가 있으면 role 자체는 수용하고, input region이 불명확하면 review로 남깁니다.</div>
    {_metrics(pipeline_role_validation['summary'])}
    <table>
      <tr><th>Status</th><th>Role / Pipeline</th><th>Output</th><th>Confidence</th><th>Evidence</th><th>Linked Gates</th></tr>
      {''.join(rows)}
    </table>
  </div>
</section>
"""


def _sorted_pipeline_role_validations(
    validations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    order = {
        "rejected": 0,
        "review_required": 1,
        "accepted": 2,
    }
    return sorted(
        validations,
        key=lambda item: (
            order.get(item.get("status"), 99),
            str(item.get("reason") or ""),
            str(item.get("asserted_role") or ""),
            str(item.get("pipeline_id") or ""),
        ),
    )


def _evidence_package_section(
    evidence_package: dict[str, Any] | None,
) -> str:
    if not evidence_package:
        return ""
    inventory_rows = []
    for item in evidence_package.get("artifact_inventory", []):
        summary = item.get("summary") or {}
        summary_text = ", ".join(
            f"{key}={value}"
            for key, value in list(summary.items())[:5]
        )
        inventory_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('id'))}</td>"
            f"<td><code>{_esc(Path(item.get('path') or '').name)}</code></td>"
            f"<td>{_esc(_shorten(summary_text, 160))}</td>"
            "</tr>"
        )
    layer_rows = []
    for name, layer in evidence_package.get("evidence_layers", {}).items():
        layer_rows.append(
            "<tr>"
            f"<td>{_esc(name)}</td>"
            f"<td><span class=\"pill {_evidence_layer_status_class(layer.get('status'))}\">{_esc(layer.get('status'))}</span></td>"
            f"<td>{_esc(layer.get('detail'))}</td>"
            "</tr>"
        )
    review_rows = []
    for item in evidence_package.get("review_queue", [])[:40]:
        review_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('kind'))}<br><span class=\"small muted\">{_esc(item.get('id'))}</span></td>"
            f"<td>{_esc(item.get('reason'))}</td>"
            f"<td>{_esc(item.get('sheet'))}<br><code>{_esc(item.get('range'))}</code></td>"
            "</tr>"
        )
    domain_rows = []
    for item in evidence_package.get("domain_knowledge_refs", []):
        domain_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('layer'))}</td>"
            f"<td>{_esc(item.get('id'))}</td>"
            f"<td><code>{_esc(Path(item.get('path') or '').name)}</code></td>"
            "</tr>"
        )
    return f"""
<section id="stage-evidence-package">
  <h2>18. Workbook Evidence Package</h2>
  <div class="section-body">
    <div class="stage-note">앞선 deterministic artifact들을 하나의 parser input authority로 묶은 패키지입니다. 원본 workbook을 다시 열어 추론하지 않고, 각 claim이 어떤 artifact와 decision에 기대는지 추적할 수 있게 합니다.</div>
    {_metrics(evidence_package['summary'])}
    <h3>Evidence Layers</h3>
    <table>
      <tr><th>Layer</th><th>Status</th><th>Detail</th></tr>
      {''.join(layer_rows)}
    </table>
    <h3>Artifact Inventory</h3>
    <table>
      <tr><th>Artifact</th><th>File</th><th>Summary</th></tr>
      {''.join(inventory_rows)}
    </table>
    <h3>Review Queue</h3>
    <table>
      <tr><th>Item</th><th>Reason</th><th>Target</th></tr>
      {''.join(review_rows)}
    </table>
    <p class="small muted">Showing top 40 of {len(evidence_package.get('review_queue', []))} review queue items.</p>
    <h3>Domain Evidence Refs</h3>
    <table>
      <tr><th>Layer</th><th>Ref</th><th>File</th></tr>
      {''.join(domain_rows)}
    </table>
  </div>
</section>
"""


def _document_ontology_mapping_section(
    document_ontology_mapping: dict[str, Any] | None,
) -> str:
    if not document_ontology_mapping:
        return ""
    nodes = document_ontology_mapping.get("nodes", [])
    relations = document_ontology_mapping.get("relations", [])
    data_views = document_ontology_mapping.get("data_views", [])
    class_rows = []
    node_class_counts = Counter(
        (node.get("type"), node.get("ontology_class"), node.get("status"))
        for node in nodes
    )
    for (node_type, ontology_class, status), count in node_class_counts.most_common(30):
        class_rows.append(
            "<tr>"
            f"<td>{_esc(node_type)}</td>"
            f"<td>{_esc(ontology_class)}</td>"
            f"<td><span class=\"pill {_gate_execution_status_class(status)}\">{_esc(status)}</span></td>"
            f"<td>{_num(count)}</td>"
            "</tr>"
        )
    relation_rows = []
    relation_counts = Counter(
        (relation.get("type"), relation.get("status"))
        for relation in relations
    )
    for (relation_type, status), count in relation_counts.most_common(24):
        relation_rows.append(
            "<tr>"
            f"<td>{_esc(relation_type)}</td>"
            f"<td><span class=\"pill {_gate_execution_status_class(status)}\">{_esc(status)}</span></td>"
            f"<td>{_num(count)}</td>"
            "</tr>"
        )
    data_view_rows = []
    for view in _sorted_document_data_views(data_views):
        data_view_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_gate_execution_status_class(view.get('status'))}\">{_esc(view.get('status'))}</span><br><span class=\"small muted\">{_esc(view.get('view_kind'))}</span></td>"
            f"<td>{_esc(view.get('role'))}<br><span class=\"small muted\">{_esc(view.get('id'))}</span></td>"
            f"<td>{_esc(view.get('sheet'))}<br><code>{_esc(view.get('range'))}</code></td>"
            f"<td>{len(view.get('input_node_ids', []))}</td>"
            f"<td>{len(view.get('transform_node_ids', []))}</td>"
            f"<td>{_metric((view.get('properties') or {}).get('confidence'))}</td>"
            f"<td>{_esc(_shorten((view.get('properties') or {}).get('reason') or '', 80))}</td>"
            "</tr>"
        )
    review_rows = []
    for item in document_ontology_mapping.get("review_queue", [])[:40]:
        review_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('kind'))}<br><span class=\"small muted\">{_esc(item.get('id'))}</span></td>"
            f"<td>{_esc(item.get('reason'))}</td>"
            f"<td>{_esc(item.get('sheet'))}<br><code>{_esc(item.get('range'))}</code></td>"
            f"<td>{_esc(item.get('target_node_id'))}</td>"
            "</tr>"
        )
    graph = _document_ontology_mermaid(document_ontology_mapping)
    return f"""
<section id="stage-document-ontology">
  <h2>19. Document Ontology Mapping</h2>
  <div class="section-body">
    <div class="stage-note">Evidence Package를 문서구조 온톨로지에 적용한 deterministic projection입니다. 이 단계는 sheet, block, region, pipeline, visual evidence, review item을 구조화하지만 의미 기반 ontology concept은 생성하지 않습니다.</div>
    {_metrics(document_ontology_mapping['summary'])}
    <div class="mermaid-panel">
      <h3>Ontology Data View Graph</h3>
      <p class="small muted">Accepted/review-required data view를 sheet 단위 흐름으로 집계한 graph입니다. 세부 입출력은 아래 data view table과 JSON artifact가 authority입니다.</p>
      <div class="mermaid-diagram"><div class="mermaid">{_esc(graph)}</div></div>
      {_mermaid_source("Document Ontology Mermaid Source", graph)}
    </div>
    <h3>Node Class Summary</h3>
    <table>
      <tr><th>Node Type</th><th>Ontology Class</th><th>Status</th><th>Count</th></tr>
      {''.join(class_rows)}
    </table>
    <h3>Relation Summary</h3>
    <table>
      <tr><th>Relation</th><th>Status</th><th>Count</th></tr>
      {''.join(relation_rows)}
    </table>
    <h3>Data Views</h3>
    <table>
      <tr><th>Status / Kind</th><th>Role / View</th><th>Output</th><th>Inputs</th><th>Transforms</th><th>Confidence</th><th>Reason</th></tr>
      {''.join(data_view_rows)}
    </table>
    <h3>Review Queue</h3>
    <table>
      <tr><th>Item</th><th>Reason</th><th>Target</th><th>Mapped Node</th></tr>
      {''.join(review_rows)}
    </table>
    <p class="small muted">Showing top 40 of {len(document_ontology_mapping.get('review_queue', []))} review queue items.</p>
  </div>
</section>
"""


def _sorted_document_data_views(data_views: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {
        "rejected": 0,
        "review_required": 1,
        "candidate": 2,
        "accepted": 3,
    }
    return sorted(
        data_views,
        key=lambda item: (
            order.get(item.get("status"), 99),
            str(item.get("view_kind") or ""),
            str(item.get("sheet") or ""),
            str(item.get("id") or ""),
        ),
    )


def _document_ontology_mermaid(document_ontology_mapping: dict[str, Any]) -> str:
    nodes_by_id = {
        node["id"]: node
        for node in document_ontology_mapping.get("nodes", [])
    }
    sheet_counts: dict[str, dict[str, int]] = {}
    edge_counts: dict[tuple[str, str, str], int] = {}
    for view in document_ontology_mapping.get("data_views", []):
        output_node = nodes_by_id.get(view.get("output_node_id"), {})
        output_sheet = output_node.get("sheet") or view.get("sheet") or "unknown output"
        sheet_counts.setdefault(output_sheet, {"source": 0, "output": 0})["output"] += 1
        input_node_ids = view.get("input_node_ids") or []
        edge_label = f"{view.get('view_kind')}:{view.get('status')}"
        if not input_node_ids:
            input_sheet = "Unresolved input"
            sheet_counts.setdefault(input_sheet, {"source": 0, "output": 0})["source"] += 1
            edge_counts[(input_sheet, output_sheet, edge_label)] = (
                edge_counts.get((input_sheet, output_sheet, edge_label), 0) + 1
            )
            continue
        for input_node_id in input_node_ids:
            input_node = nodes_by_id.get(input_node_id, {})
            input_sheet = input_node.get("sheet") or "unknown input"
            sheet_counts.setdefault(input_sheet, {"source": 0, "output": 0})["source"] += 1
            edge_counts[(input_sheet, output_sheet, edge_label)] = (
                edge_counts.get((input_sheet, output_sheet, edge_label), 0) + 1
            )
    node_ids = {
        sheet: f"o{index}"
        for index, sheet in enumerate(sorted(sheet_counts, key=lambda value: str(value)))
    }
    lines = [
        "flowchart LR",
        "  classDef sheetNode fill:#eef2ff,stroke:#4f46e5,color:#111827;",
        "  classDef reviewNode fill:#fef2f2,stroke:#b91c1c,color:#111827;",
    ]
    for sheet, node_id in node_ids.items():
        counts = sheet_counts[sheet]
        cls = "reviewNode" if sheet == "Unresolved input" else "sheetNode"
        label = _mermaid_label(
            f"{sheet}<br/>feeds {counts['source']} / outputs {counts['output']}"
        )
        lines.append(f'  {node_id}["{label}"]:::{cls}')
    for (input_sheet, output_sheet, edge_label), count in sorted(edge_counts.items()):
        if input_sheet not in node_ids or output_sheet not in node_ids:
            continue
        label = _mermaid_edge_label(f"{edge_label} x{count}")
        lines.append(f"  {node_ids[input_sheet]} -->|{label}| {node_ids[output_sheet]}")
    return "\n".join(lines)


def _action_contracts_section(
    action_contracts: dict[str, Any] | None,
) -> str:
    if not action_contracts:
        return ""
    contracts = action_contracts.get("action_contracts", [])
    action_rows = []
    action_counts = Counter(
        (
            contract.get("priority"),
            contract.get("action_status"),
            contract.get("action_type"),
            contract.get("action_owner"),
        )
        for contract in contracts
    )
    for (priority, status, action_type, owner), count in action_counts.most_common(30):
        action_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_action_priority_class(priority)}\">{_esc(priority)}</span></td>"
            f"<td><span class=\"pill {_action_status_class(status)}\">{_esc(status)}</span></td>"
            f"<td>{_esc(action_type)}</td>"
            f"<td>{_esc(owner)}</td>"
            f"<td>{_num(count)}</td>"
            "</tr>"
        )
    detail_rows = []
    for contract in _sorted_action_contracts(contracts)[:80]:
        target = contract.get("target") or {}
        trigger = contract.get("trigger") or {}
        detail_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_action_priority_class(contract.get('priority'))}\">{_esc(contract.get('priority'))}</span><br><span class=\"small muted\">{_esc(contract.get('action_status'))}</span></td>"
            f"<td>{_esc(contract.get('action_type'))}<br><span class=\"small muted\">{_esc(contract.get('action_owner'))}</span></td>"
            f"<td>{_esc(trigger.get('reason'))}<br><span class=\"small muted\">{_esc(trigger.get('source_kind'))}</span></td>"
            f"<td>{_esc(target.get('sheet'))}<br><code>{_esc(target.get('range'))}</code><br><span class=\"small muted\">{_esc(target.get('data_view_id') or target.get('review_item_id') or target.get('node_id'))}</span></td>"
            f"<td>{_esc(_shorten(contract.get('deterministic_gate'), 64))}</td>"
            f"<td>{_esc(_shorten(contract.get('completion_effect'), 80))}</td>"
            "</tr>"
        )
    graph = _action_contract_mermaid(action_contracts)
    return f"""
<section id="stage-action-contracts">
  <h2>20. Action Contract Layer</h2>
  <div class="section-body">
    <div class="stage-note">Document ontology의 상태를 다음 실행 단위로 바꾼 deterministic action layer입니다. 이 단계는 새 claim을 accept하지 않고, 각 accepted/review-required 항목에 owner, required evidence, gate, completion condition을 붙입니다.</div>
    {_metrics(action_contracts['summary'])}
    <div class="mermaid-panel">
      <h3>Action Flow</h3>
      <p class="small muted">상태별 action type을 집계한 graph입니다. high priority와 blocked 항목은 다음 튜닝/리뷰의 우선순위입니다.</p>
      <div class="mermaid-diagram"><div class="mermaid">{_esc(graph)}</div></div>
      {_mermaid_source("Action Contract Mermaid Source", graph)}
    </div>
    <h3>Action Summary</h3>
    <table>
      <tr><th>Priority</th><th>Status</th><th>Action</th><th>Owner</th><th>Count</th></tr>
      {''.join(action_rows)}
    </table>
    <h3>Action Contracts</h3>
    <table>
      <tr><th>Priority / Status</th><th>Action / Owner</th><th>Trigger</th><th>Target</th><th>Gate</th><th>Effect</th></tr>
      {''.join(detail_rows)}
    </table>
    <p class="small muted">Showing top 80 of {len(contracts)} action contracts.</p>
  </div>
</section>
"""


def _sorted_action_contracts(contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        contracts,
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}.get(item.get("priority"), 99),
            {"blocked": 0, "open": 1, "ready": 2}.get(item.get("action_status"), 99),
            str(item.get("action_type") or ""),
            str(item.get("id") or ""),
        ),
    )


def _action_contract_mermaid(action_contracts: dict[str, Any]) -> str:
    counts = Counter(
        (
            contract.get("action_status") or "unknown",
            contract.get("action_type") or "unknown_action",
            contract.get("action_owner") or "unknown_owner",
        )
        for contract in action_contracts.get("action_contracts", [])
    )
    status_ids: dict[str, str] = {}
    action_ids: dict[str, str] = {}
    owner_ids: dict[str, str] = {}
    lines = [
        "flowchart LR",
        "  classDef ready fill:#ecfdf5,stroke:#0f766e,color:#111827;",
        "  classDef open fill:#fff7ed,stroke:#b45309,color:#111827;",
        "  classDef blocked fill:#fef2f2,stroke:#b91c1c,color:#111827;",
        "  classDef action fill:#eef2ff,stroke:#4f46e5,color:#111827;",
        "  classDef owner fill:#f8fafc,stroke:#64748b,color:#111827;",
    ]

    def node_id(pool: dict[str, str], prefix: str, key: str) -> str:
        if key not in pool:
            pool[key] = f"{prefix}{len(pool)}"
        return pool[key]

    for (status, action_type, owner), count in sorted(counts.items()):
        status_id = node_id(status_ids, "s", status)
        action_id = node_id(action_ids, "a", action_type)
        owner_id = node_id(owner_ids, "o", owner)
        lines.append(f'  {status_id}["{_mermaid_label(status)}"]:::{status}')
        lines.append(f'  {action_id}["{_mermaid_label(action_type)}"]:::action')
        lines.append(f'  {owner_id}["{_mermaid_label(owner)}"]:::owner')
        lines.append(
            f"  {status_id} -->|{_mermaid_edge_label(str(count))}| {action_id}"
        )
        lines.append(f"  {action_id} --> {owner_id}")
    return "\n".join(dict.fromkeys(lines))


def _action_status_class(status: Any) -> str:
    if status == "blocked":
        return "danger"
    if status == "open":
        return "warn"
    return ""


def _action_priority_class(priority: Any) -> str:
    if priority == "high":
        return "danger"
    if priority == "medium":
        return "warn"
    return ""


def _domain_source_model_section(
    domain_source_model: dict[str, Any] | None,
) -> str:
    if not domain_source_model:
        return ""
    readiness = domain_source_model.get("semantic_readiness", {})
    general_sources = domain_source_model.get("domain_layers", {}).get(
        "general_domain_sources", []
    )
    local_sources = domain_source_model.get("domain_layers", {}).get(
        "local_domain_sources", []
    )
    local_boundaries = domain_source_model.get("domain_layers", {}).get(
        "local_domain_boundaries", []
    )
    general_rows = []
    for source in general_sources:
        general_rows.append(
            "<tr>"
            f"<td>{_esc(source.get('file_name'))}<br><span class=\"small muted\">{_esc(source.get('document_role'))}</span></td>"
            f"<td><span class=\"pill {_domain_status_class(source.get('status'))}\">{_esc(source.get('status'))}</span></td>"
            f"<td>{_num(source.get('size_bytes'))}</td>"
            f"<td>{_esc(_shorten(' / '.join(source.get('heading_samples', [])[:3]), 180))}</td>"
            "</tr>"
        )
    boundary_rows = []
    for boundary in local_boundaries:
        boundary_rows.append(
            "<tr>"
            f"<td>{_esc(boundary.get('label'))}<br><span class=\"small muted\">{_esc(boundary.get('id'))}</span></td>"
            f"<td><span class=\"pill {_domain_status_class(boundary.get('status'))}\">{_esc(boundary.get('status'))}</span></td>"
            f"<td>{_esc(boundary.get('scope'))}</td>"
            f"<td>{_esc(', '.join(boundary.get('required_confirmation', [])))}</td>"
            "</tr>"
        )
    local_rows = []
    for source in local_sources:
        local_rows.append(
            "<tr>"
            f"<td>{_esc(source.get('file_name'))}</td>"
            f"<td>{_esc(source.get('document_role'))}</td>"
            f"<td><span class=\"pill {_domain_status_class(source.get('status'))}\">{_esc(source.get('status'))}</span></td>"
            "</tr>"
        )
    if not local_rows:
        local_rows.append(
            '<tr><td colspan="3" class="muted">No explicit local-domain source supplied yet.</td></tr>'
        )
    governance_rows = []
    for rule in domain_source_model.get("governance_rules", []):
        governance_rows.append(
            "<tr>"
            f"<td>{_esc(rule.get('id'))}</td>"
            f"<td>{_esc(rule.get('rule'))}</td>"
            f"<td>{_esc(', '.join(rule.get('applies_to', [])))}</td>"
            "</tr>"
        )
    review_rows = []
    for item in domain_source_model.get("review_queue", []):
        review_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_action_priority_class(item.get('priority'))}\">{_esc(item.get('priority'))}</span><br><span class=\"small muted\">{_esc(item.get('kind'))}</span></td>"
            f"<td>{_esc(item.get('reason'))}</td>"
            f"<td>{_esc(item.get('required_action'))}</td>"
            f"<td>{_esc(item.get('target_id'))}</td>"
            "</tr>"
        )
    return f"""
<section id="stage-domain-source-model">
  <h2>21. Domain Knowledge Source Model</h2>
  <div class="section-body">
    <div class="stage-note">의미 온톨로지를 생성하기 전에 general-domain evidence와 boundary-scoped local-domain evidence를 분리한 모델입니다. 현재 단계는 domain source inventory이며, semantic concept을 생성하지 않습니다.</div>
    {_metrics(domain_source_model['summary'])}
    <h3>Semantic Readiness</h3>
    <table>
      <tr><th>Status</th><th>Proposal Mode</th><th>General Ready</th><th>Local Boundary</th><th>Blocking Factors</th></tr>
      <tr>
        <td><span class="pill {_domain_readiness_class(readiness.get('status'))}">{_esc(readiness.get('status'))}</span></td>
        <td>{_esc(readiness.get('semantic_proposal_mode'))}</td>
        <td>{_esc(readiness.get('general_domain_ready'))}</td>
        <td>{_esc(readiness.get('local_boundary_confirmed'))}</td>
        <td>{_esc(', '.join(readiness.get('blocking_factors', [])))}</td>
      </tr>
    </table>
    <h3>General-Domain Sources</h3>
    <table>
      <tr><th>Source</th><th>Status</th><th>Bytes</th><th>Heading Samples</th></tr>
      {''.join(general_rows)}
    </table>
    <h3>Local-Domain Boundaries</h3>
    <table>
      <tr><th>Boundary</th><th>Status</th><th>Scope</th><th>Required Confirmation</th></tr>
      {''.join(boundary_rows)}
    </table>
    <h3>Local-Domain Sources</h3>
    <table>
      <tr><th>Source</th><th>Role</th><th>Status</th></tr>
      {''.join(local_rows)}
    </table>
    <h3>Governance Rules</h3>
    <table>
      <tr><th>Rule</th><th>Meaning</th><th>Applies To</th></tr>
      {''.join(governance_rows)}
    </table>
    <h3>Domain Review Queue</h3>
    <table>
      <tr><th>Priority / Kind</th><th>Reason</th><th>Required Action</th><th>Target</th></tr>
      {''.join(review_rows)}
    </table>
  </div>
</section>
"""


def _llm_proposals_section(
    llm_proposals: dict[str, Any] | None,
) -> str:
    if not llm_proposals:
        return ""
    context = llm_proposals.get("proposal_context", {})
    readiness = context.get("semantic_readiness", {})
    concept_rows = []
    for proposal in llm_proposals.get("semantic_concept_proposals", []):
        concept_rows.append(
            "<tr>"
            f"<td>{_esc(proposal.get('label'))}<br><span class=\"small muted\">{_esc(proposal.get('concept_kind'))}</span></td>"
            f"<td>{_esc(', '.join(proposal.get('matched_sheets', [])))}</td>"
            f"<td>{_esc(proposal.get('scope'))}</td>"
            f"<td>{_esc(proposal.get('confidence'))}</td>"
            f"<td>{_esc(', '.join(proposal.get('review_flags', [])))}</td>"
            "</tr>"
        )
    relation_rows = []
    for proposal in llm_proposals.get("semantic_relation_proposals", []):
        relation_rows.append(
            "<tr>"
            f"<td>{_esc(proposal.get('from_sheet'))} → {_esc(proposal.get('to_sheet'))}</td>"
            f"<td>{_esc(proposal.get('relation_type'))}</td>"
            f"<td>{_num(len(proposal.get('pipeline_ids', [])))}</td>"
            f"<td>{_esc(', '.join(proposal.get('required_gates', [])))}</td>"
            "</tr>"
        )
    alias_rows = []
    for proposal in llm_proposals.get("alias_proposals", [])[:40]:
        alias_rows.append(
            "<tr>"
            f"<td>{_esc(proposal.get('alias'))}</td>"
            f"<td>{_esc(_shorten(proposal.get('canonical_concept_id', ''), 96))}</td>"
            f"<td>{_esc(proposal.get('alias_scope'))}</td>"
            f"<td>{_esc(proposal.get('confidence'))}</td>"
            "</tr>"
        )
    note_rows = []
    for note in llm_proposals.get("ambiguity_notes", []):
        note_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_action_priority_class(note.get('severity'))}\">{_esc(note.get('severity'))}</span><br><span class=\"small muted\">{_esc(note.get('topic'))}</span></td>"
            f"<td>{_esc(note.get('note'))}</td>"
            f"<td>{_esc(note.get('required_resolution'))}</td>"
            "</tr>"
        )
    gate_rows = []
    for gate, count in (llm_proposals.get("validation_plan", {}).get("gate_counts") or {}).items():
        gate_rows.append(
            "<tr>"
            f"<td>{_esc(gate)}</td>"
            f"<td>{_num(count)}</td>"
            "</tr>"
        )
    observations = _observations(llm_proposals.get("parser_observations", []))
    return f"""
<section id="stage-llm-proposals">
  <h2>22. LLM Proposal Generation</h2>
  <div class="section-body">
    <div class="stage-note">이 단계는 의미 온톨로지와 hierarchy를 확정하지 않습니다. Workbook evidence, domain source, action contract 범위 안에서 다음 deterministic gate가 검증할 proposal만 생성합니다.</div>
    {_metrics(llm_proposals['summary'])}
    {observations}
    <h3>Proposal Context</h3>
    <table>
      <tr><th>Readiness</th><th>Mode</th><th>Blocking Factors</th><th>Shared Promotion</th></tr>
      <tr>
        <td><span class="pill {_domain_readiness_class(readiness.get('status'))}">{_esc(readiness.get('status'))}</span></td>
        <td>{_esc(readiness.get('semantic_proposal_mode'))}</td>
        <td>{_esc(', '.join(readiness.get('blocking_factors', [])))}</td>
        <td>{_esc(readiness.get('shared_ontology_promotion_allowed'))}</td>
      </tr>
    </table>
    <h3>Semantic Concept Proposals</h3>
    <table>
      <tr><th>Concept</th><th>Sheets</th><th>Scope</th><th>Confidence</th><th>Review Flags</th></tr>
      {''.join(concept_rows)}
    </table>
    <h3>Semantic Relation Proposals</h3>
    <table>
      <tr><th>Flow</th><th>Relation</th><th>Pipelines</th><th>Required Gates</th></tr>
      {''.join(relation_rows)}
    </table>
    <h3>Alias Proposals <span class="small muted">(first 40)</span></h3>
    <table>
      <tr><th>Alias</th><th>Canonical Concept</th><th>Scope</th><th>Confidence</th></tr>
      {''.join(alias_rows)}
    </table>
    <h3>Ambiguity Notes</h3>
    <table>
      <tr><th>Severity / Topic</th><th>Note</th><th>Required Resolution</th></tr>
      {''.join(note_rows)}
    </table>
    <h3>Next Gate Counts</h3>
    <table>
      <tr><th>Gate</th><th>Proposal Count</th></tr>
      {''.join(gate_rows)}
    </table>
  </div>
</section>
"""


def _llm_proposal_validation_section(
    llm_proposal_validation: dict[str, Any] | None,
) -> str:
    if not llm_proposal_validation:
        return ""
    result_counts: dict[tuple[str, str], int] = {}
    for result in llm_proposal_validation.get("proposal_results", []):
        key = (result.get("proposal_type", ""), result.get("final_status", ""))
        result_counts[key] = result_counts.get(key, 0) + 1
    type_rows = []
    for (proposal_type, status), count in sorted(result_counts.items()):
        type_rows.append(
            "<tr>"
            f"<td>{_esc(proposal_type)}</td>"
            f"<td><span class=\"pill {_validation_status_class(status)}\">{_esc(status)}</span></td>"
            f"<td>{_num(count)}</td>"
            "</tr>"
        )
    gate_rows = []
    for gate, counts in llm_proposal_validation.get("gate_summary", {}).items():
        rendered = ", ".join(f"{status}: {count}" for status, count in counts.items())
        gate_rows.append(
            "<tr>"
            f"<td>{_esc(gate)}</td>"
            f"<td>{_esc(rendered)}</td>"
            "</tr>"
        )
    review_rows = []
    for item in llm_proposal_validation.get("review_queue", [])[:80]:
        review_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_validation_status_class(item.get('status'))}\">{_esc(item.get('status'))}</span><br><span class=\"small muted\">{_esc(item.get('proposal_type'))}</span></td>"
            f"<td>{_esc(_shorten(item.get('label') or item.get('proposal_id'), 120))}</td>"
            f"<td>{_esc(', '.join(item.get('blocking_gates', [])))}</td>"
            f"<td>{_esc(item.get('required_action'))}</td>"
            "</tr>"
        )
    observations = _observations(llm_proposal_validation.get("parser_observations", []))
    return f"""
<section id="stage-llm-proposal-validation">
  <h2>23. Deterministic Validation of LLM Proposals</h2>
  <div class="section-body">
    <div class="stage-note">LLM proposal을 다시 해석하지 않고 source trace, domain, local boundary, data view, coordinate, formula/pivot topology, alias conflict, confidence gate로 검증한 결과입니다. 이 단계도 최종 document graph 조립은 하지 않습니다.</div>
    {_metrics(llm_proposal_validation['summary'])}
    {observations}
    <h3>Result Counts by Proposal Type</h3>
    <table>
      <tr><th>Proposal Type</th><th>Status</th><th>Count</th></tr>
      {''.join(type_rows)}
    </table>
    <h3>Gate Summary</h3>
    <table>
      <tr><th>Gate</th><th>Status Counts</th></tr>
      {''.join(gate_rows)}
    </table>
    <h3>Review / Quarantine Queue <span class="small muted">(first 80)</span></h3>
    <table>
      <tr><th>Status / Type</th><th>Proposal</th><th>Blocking Gates</th><th>Required Action</th></tr>
      {''.join(review_rows)}
    </table>
  </div>
</section>
"""


def _validated_document_graph_section(
    validated_document_graph: dict[str, Any] | None,
) -> str:
    if not validated_document_graph:
        return ""
    graph = validated_document_graph.get("graph", {})
    carry = validated_document_graph.get("carry_forward", {})
    node_type_counts = Counter(node.get("type") for node in graph.get("nodes", []))
    relation_type_counts = Counter(relation.get("type") for relation in graph.get("relations", []))
    node_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in node_type_counts.most_common()
    )
    relation_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in relation_type_counts.most_common()
    )
    semantic_rows = []
    for node in graph.get("nodes", []):
        if node.get("type") != "semantic_concept":
            continue
        props = node.get("properties", {})
        semantic_rows.append(
            "<tr>"
            f"<td>{_esc(node.get('label'))}<br><span class=\"small muted\">{_esc(node.get('id'))}</span></td>"
            f"<td>{_esc(props.get('concept_kind'))}</td>"
            f"<td>{_esc(props.get('scope'))}</td>"
            f"<td>{_esc(', '.join(props.get('data_view_ids', [])[:4]))}</td>"
            "</tr>"
        )
    semantic_relation_rows = []
    for relation in graph.get("relations", []):
        if relation.get("type") in {"contains_semantic_concept", "pivot_cache_feeds_report", "formula_feeds_summary_or_transform"}:
            semantic_relation_rows.append(
                "<tr>"
                f"<td>{_esc(relation.get('type'))}</td>"
                f"<td>{_esc(_shorten(relation.get('from', ''), 80))}</td>"
                f"<td>{_esc(_shorten(relation.get('to', ''), 80))}</td>"
                "</tr>"
            )
    alias_rows = []
    for alias in graph.get("semantic_aliases", [])[:60]:
        alias_rows.append(
            "<tr>"
            f"<td>{_esc(alias.get('alias'))}</td>"
            f"<td>{_esc(_shorten(alias.get('canonical_concept_id', ''), 100))}</td>"
            f"<td>{_esc(alias.get('confidence'))}</td>"
            "</tr>"
        )
    filtered_rows = []
    for relation in carry.get("filtered_document_relations", []):
        filtered_rows.append(
            "<tr>"
            f"<td>{_esc(relation.get('id'))}</td>"
            f"<td>{_esc(relation.get('reason'))}</td>"
            f"<td>{_esc(relation.get('from'))} → {_esc(relation.get('to'))}</td>"
            "</tr>"
        )
    proposal_review_rows = []
    for item in carry.get("proposal_review_queue", [])[:50]:
        proposal_review_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_validation_status_class(item.get('status'))}\">{_esc(item.get('status'))}</span><br><span class=\"small muted\">{_esc(item.get('proposal_type'))}</span></td>"
            f"<td>{_esc(_shorten(item.get('label') or item.get('proposal_id'), 120))}</td>"
            f"<td>{_esc(item.get('required_action'))}</td>"
            "</tr>"
        )
    observations = _observations(validated_document_graph.get("parser_observations", []))
    return f"""
<section id="stage-validated-document-graph">
  <h2>24. Validated Document Graph</h2>
  <div class="section-body">
    <div class="stage-note">Accepted document ontology artifacts and accepted proposal validation results only are assembled into the graph body. Review-required and quarantined items are carried forward and are not promoted into graph claims.</div>
    {_metrics(validated_document_graph['summary'])}
    {observations}
    <div class="grid two">
      <div>
        <h3>Node Types</h3>
        <table><tr><th>Type</th><th>Count</th></tr>{node_rows}</table>
      </div>
      <div>
        <h3>Relation Types</h3>
        <table><tr><th>Type</th><th>Count</th></tr>{relation_rows}</table>
      </div>
    </div>
    <h3>Accepted Semantic Concepts</h3>
    <table>
      <tr><th>Concept</th><th>Kind</th><th>Scope</th><th>Data Views</th></tr>
      {''.join(semantic_rows)}
    </table>
    <h3>Accepted Semantic Relations</h3>
    <table>
      <tr><th>Relation</th><th>From</th><th>To</th></tr>
      {''.join(semantic_relation_rows)}
    </table>
    <h3>Accepted Aliases <span class="small muted">(first 60)</span></h3>
    <table>
      <tr><th>Alias</th><th>Canonical Concept</th><th>Confidence</th></tr>
      {''.join(alias_rows)}
    </table>
    <h3>Filtered Accepted Document Relations</h3>
    <table>
      <tr><th>Relation</th><th>Reason</th><th>Endpoints</th></tr>
      {''.join(filtered_rows) if filtered_rows else '<tr><td colspan="3" class="muted">None</td></tr>'}
    </table>
    <h3>Proposal Carry-Forward Queue <span class="small muted">(first 50)</span></h3>
    <table>
      <tr><th>Status / Type</th><th>Proposal</th><th>Required Action</th></tr>
      {''.join(proposal_review_rows)}
    </table>
  </div>
</section>
"""


def _data_view_projection_section(
    data_view_projection: dict[str, Any] | None,
) -> str:
    if not data_view_projection:
        return ""
    projections = data_view_projection.get("data_view_projections", [])
    objects = data_view_projection.get("document_object_projections", [])
    kind_counts = Counter(item.get("projection_kind") for item in projections)
    role_counts = Counter(item.get("role") for item in projections)
    preview_status_counts = Counter(item.get("preview", {}).get("status") for item in projections)
    object_kind_counts = Counter(item.get("object_kind") for item in objects)
    semantic_coverage = Counter(
        "semantic_context"
        if item.get("semantic_context", {}).get("semantic_concept_ids")
        else "no_semantic_context"
        for item in projections
    )
    kind_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in kind_counts.most_common()
    )
    role_rows = "".join(
        f"<tr><td>{_esc(role)}</td><td>{_num(count)}</td></tr>"
        for role, count in role_counts.most_common()
    )
    preview_rows = "".join(
        f"<tr><td>{_esc(status)}</td><td>{_num(count)}</td></tr>"
        for status, count in preview_status_counts.most_common()
    )
    object_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in object_kind_counts.most_common()
    )
    semantic_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in semantic_coverage.most_common()
    )
    projection_rows = []
    for item in projections:
        context = item.get("semantic_context", {})
        labels = ", ".join(str(value) for value in context.get("semantic_labels", []))
        warnings = ", ".join(item.get("warnings", []))
        projection_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('sheet'))}<br><span class=\"small muted\">{_esc(item.get('range'))}</span></td>"
            f"<td><span class=\"pill\">{_esc(item.get('role'))}</span><br><span class=\"small muted\">{_esc(item.get('projection_kind'))}</span></td>"
            f"<td>{_esc(_shorten(labels, 120)) if labels else '<span class=\"muted\">None</span>'}</td>"
            f"<td>{_esc(item.get('preview', {}).get('status'))}<br><span class=\"small muted\">rows {_num(item.get('metrics', {}).get('sampled_row_count', 0))}, cells {_num(item.get('metrics', {}).get('sampled_cell_count', 0))}</span></td>"
            f"<td>{_num(item.get('metrics', {}).get('formula_cell_count', 0))}</td>"
            f"<td>{_esc(_shorten(warnings, 120)) if warnings else '<span class=\"muted\">None</span>'}</td>"
            "</tr>"
        )
    preview_examples = sorted(
        projections,
        key=lambda item: (
            -int(item.get("metrics", {}).get("formula_cell_count", 0)),
            str(item.get("sheet")),
            str(item.get("range")),
        ),
    )[:8]
    preview_blocks = []
    for item in preview_examples:
        preview_blocks.append(
            "<details>"
            f"<summary>{_esc(item.get('sheet'))} { _esc(item.get('range')) } "
            f"<span class=\"small muted\">{_esc(item.get('projection_kind'))}, formulas {_num(item.get('metrics', {}).get('formula_cell_count', 0))}</span></summary>"
            f"{_projection_preview_table(item)}"
            "</details>"
        )
    observations = _observations(data_view_projection.get("parser_observations", []))
    return f"""
<section id="stage-data-view-projection">
  <h2>25. Data View Projection</h2>
  <div class="section-body">
    <div class="stage-note">Accepted data views from the validated graph are projected into reviewable surfaces for the next semantic candidate stage. Formula text remains evidence only; recalculated formula results still require the real Excel engine.</div>
    {_metrics(data_view_projection['summary'])}
    {observations}
    <div class="grid two">
      <div>
        <h3>Projection Kinds</h3>
        <table><tr><th>Kind</th><th>Count</th></tr>{kind_rows}</table>
      </div>
      <div>
        <h3>Roles</h3>
        <table><tr><th>Role</th><th>Count</th></tr>{role_rows}</table>
      </div>
      <div>
        <h3>Preview Status</h3>
        <table><tr><th>Status</th><th>Count</th></tr>{preview_rows}</table>
      </div>
      <div>
        <h3>Document Objects</h3>
        <table><tr><th>Kind</th><th>Count</th></tr>{object_rows}</table>
      </div>
      <div>
        <h3>Semantic Coverage</h3>
        <table><tr><th>Coverage</th><th>Count</th></tr>{semantic_rows}</table>
      </div>
    </div>
    <h3>Data View Projections</h3>
    <table>
      <tr><th>Sheet / Range</th><th>Role / Kind</th><th>Semantic Context</th><th>Preview</th><th>Formula Cells</th><th>Warnings</th></tr>
      {''.join(projection_rows)}
    </table>
    <h3>Preview Examples <span class="small muted">(highest formula density first)</span></h3>
    {''.join(preview_blocks)}
  </div>
</section>
"""


def _projection_preview_table(item: dict[str, Any]) -> str:
    rows = []
    for row in item.get("preview", {}).get("rows", [])[:5]:
        cell_texts = []
        for cell in row.get("cells", [])[:8]:
            value = cell.get("formula") or cell.get("value_preview")
            cell_texts.append(
                f"<code>{_esc(cell.get('cell'))}: {_esc(_shorten(str(value), 70))}</code>"
            )
        rows.append(
            "<tr>"
            f"<td>{_num(row.get('row'))}</td>"
            f"<td>{' '.join(cell_texts) if cell_texts else '<span class=\"muted\">empty sampled row</span>'}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="2" class="muted">No readonly preview rows.</td></tr>')
    return f"<table><tr><th>Row</th><th>Cells</th></tr>{''.join(rows)}</table>"


def _local_semantic_candidates_section(
    local_semantic_candidates: dict[str, Any] | None,
) -> str:
    if not local_semantic_candidates:
        return ""
    candidates = local_semantic_candidates.get("local_semantic_candidates", [])
    relations = local_semantic_candidates.get("candidate_relations", [])
    source_counts = Counter(item.get("source_kind") for item in candidates)
    status_counts = Counter(item.get("status") for item in candidates)
    promotion_counts = Counter(item.get("promotion_status") for item in candidates)
    relation_counts = Counter(item.get("type") for item in relations)
    source_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in source_counts.most_common()
    )
    status_rows = "".join(
        f"<tr><td>{_esc(status)}</td><td>{_num(count)}</td></tr>"
        for status, count in status_counts.most_common()
    )
    promotion_rows = "".join(
        f"<tr><td>{_esc(status)}</td><td>{_num(count)}</td></tr>"
        for status, count in promotion_counts.most_common()
    )
    relation_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in relation_counts.most_common()
    )
    boundary = local_semantic_candidates.get("local_boundary") or {}
    boundary_rows = "".join(
        [
            f"<tr><td>ID</td><td>{_esc(boundary.get('id'))}</td></tr>",
            f"<tr><td>Status</td><td><span class=\"pill {_local_candidate_status_class(boundary.get('status'))}\">{_esc(boundary.get('status'))}</span></td></tr>",
            f"<tr><td>Scope</td><td>{_esc(boundary.get('scope'))}</td></tr>",
        ]
    )
    candidate_rows = []
    for item in candidates:
        refs = item.get("data_view_refs", {})
        actions = ", ".join(item.get("required_actions", []))
        warnings = ", ".join(item.get("warnings", []))
        terms = ", ".join(str(term) for term in item.get("observed_terms", [])[:8])
        candidate_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('label'))}<br><span class=\"small muted\">{_esc(item.get('candidate_kind'))}</span></td>"
            f"<td><span class=\"pill {_local_candidate_status_class(item.get('status'))}\">{_esc(item.get('status'))}</span><br><span class=\"small muted\">{_esc(item.get('source_kind'))}</span></td>"
            f"<td>{_esc(item.get('promotion_status'))}</td>"
            f"<td>{_num(len(refs.get('data_view_ids', [])))} views<br><span class=\"small muted\">{_esc(', '.join(refs.get('sheets', [])[:4]))}</span></td>"
            f"<td>{_num(refs.get('formula_cell_count', 0))}</td>"
            f"<td>{_esc(_shorten(terms, 140)) if terms else '<span class=\"muted\">None</span>'}</td>"
            f"<td>{_esc(_shorten(actions, 140))}</td>"
            f"<td>{_esc(_shorten(warnings, 140)) if warnings else '<span class=\"muted\">None</span>'}</td>"
            "</tr>"
        )
    review_rows = []
    for item in local_semantic_candidates.get("review_queue", [])[:60]:
        review_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_local_candidate_status_class(item.get('priority'))}\">{_esc(item.get('priority'))}</span><br><span class=\"small muted\">{_esc(item.get('kind'))}</span></td>"
            f"<td>{_esc(item.get('reason'))}</td>"
            f"<td>{_esc(_shorten(item.get('target_id', ''), 120))}</td>"
            f"<td>{_esc(item.get('required_action'))}</td>"
            "</tr>"
        )
    observations = _observations(local_semantic_candidates.get("parser_observations", []))
    return f"""
<section id="stage-local-semantic-candidates">
  <h2>26. Local Semantic Ontology Candidates</h2>
  <div class="section-body">
    <div class="stage-note">Accepted data-view projections are converted into boundary-scoped local semantic candidates. These are candidates only: unconfirmed local boundary and missing local vocabulary sources block shared ontology promotion.</div>
    {_metrics(local_semantic_candidates['summary'])}
    {observations}
    <div class="grid two">
      <div>
        <h3>Local Boundary</h3>
        <table><tr><th>Field</th><th>Value</th></tr>{boundary_rows}</table>
      </div>
      <div>
        <h3>Source Kinds</h3>
        <table><tr><th>Kind</th><th>Count</th></tr>{source_rows}</table>
      </div>
      <div>
        <h3>Candidate Status</h3>
        <table><tr><th>Status</th><th>Count</th></tr>{status_rows}</table>
      </div>
      <div>
        <h3>Promotion Status</h3>
        <table><tr><th>Status</th><th>Count</th></tr>{promotion_rows}</table>
      </div>
      <div>
        <h3>Candidate Relations</h3>
        <table><tr><th>Relation</th><th>Count</th></tr>{relation_rows}</table>
      </div>
    </div>
    <h3>Local Semantic Candidates</h3>
    <table>
      <tr><th>Candidate</th><th>Status / Source</th><th>Promotion</th><th>Data Views</th><th>Formula Cells</th><th>Observed Terms</th><th>Required Actions</th><th>Warnings</th></tr>
      {''.join(candidate_rows)}
    </table>
    <h3>Review Queue <span class="small muted">(first 60)</span></h3>
    <table>
      <tr><th>Priority / Kind</th><th>Reason</th><th>Target</th><th>Required Action</th></tr>
      {''.join(review_rows)}
    </table>
  </div>
</section>
"""


def _shared_ontology_alignment_review_section(
    shared_ontology_alignment_review: dict[str, Any] | None,
) -> str:
    if not shared_ontology_alignment_review:
        return ""
    summary = shared_ontology_alignment_review.get("summary", {})
    scalar_summary = {
        key: value
        for key, value in summary.items()
        if key not in {"alignment_status_counts", "blocker_counts", "conflict_risk_counts"}
    }
    context = shared_ontology_alignment_review.get("alignment_context", {})
    precondition_rows = []
    for item in context.get("shared_promotion_preconditions", []):
        precondition_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('name'))}</td>"
            f"<td><span class=\"pill {_shared_alignment_status_class(item.get('status'))}\">{_esc(item.get('status'))}</span></td>"
            f"<td>{_esc(item.get('description'))}</td>"
            f"<td>{_esc(item.get('missing_action'))}</td>"
            "</tr>"
        )
    blocker_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in Counter(summary.get("blocker_counts", {})).most_common()
    )
    conflict_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in Counter(summary.get("conflict_risk_counts", {})).most_common()
    )
    status_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in Counter(summary.get("alignment_status_counts", {})).most_common()
    )
    context_rows = "".join(
        [
            f"<tr><td>Local boundary</td><td>{_esc(context.get('local_boundary_id'))}<br><span class=\"pill {_shared_alignment_status_class(context.get('local_boundary_status'))}\">{_esc(context.get('local_boundary_status'))}</span></td></tr>",
            f"<tr><td>Local scope</td><td>{_esc(context.get('local_boundary_scope'))}</td></tr>",
            f"<tr><td>Local sources</td><td>{_num(context.get('local_domain_source_count'))}</td></tr>",
            f"<tr><td>General-domain sources</td><td>{_num(context.get('general_domain_source_count'))}</td></tr>",
            f"<tr><td>Shared ontology target</td><td><span class=\"pill warn\">{_esc(context.get('shared_ontology_target_status'))}</span></td></tr>",
        ]
    )
    item_rows = []
    for item in shared_ontology_alignment_review.get("alignment_items", []):
        refs = item.get("data_view_refs", {})
        blockers = ", ".join(item.get("blockers", []))
        risks = ", ".join(item.get("conflict_risks", []))
        evidence = ", ".join(item.get("required_evidence", []))
        questions = " / ".join(item.get("human_review_questions", []))
        basis = item.get("basis_review", {})
        item_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('label'))}<br><span class=\"small muted\">{_esc(item.get('candidate_kind'))}</span></td>"
            f"<td><span class=\"pill {_shared_alignment_status_class(item.get('alignment_status'))}\">{_esc(item.get('alignment_status'))}</span><br><span class=\"small muted\">{_esc(item.get('source_kind'))}</span></td>"
            f"<td><span class=\"pill danger\">{_esc(item.get('promotion_decision'))}</span></td>"
            f"<td>{_num(len(refs.get('data_view_ids', [])))} views<br><span class=\"small muted\">{_esc(', '.join(refs.get('sheets', [])[:4]))}</span></td>"
            f"<td>{_esc(_shorten(blockers, 150))}</td>"
            f"<td>{_esc(_shorten(risks, 130))}</td>"
            f"<td>{_esc('required' if basis.get('required') else 'not_required')}<br><span class=\"small muted\">{_esc(', '.join(basis.get('detected_terms', [])[:8]))}</span></td>"
            f"<td>{_esc(_shorten(evidence, 150))}</td>"
            f"<td>{_esc(_shorten(questions, 180))}</td>"
            "</tr>"
        )
    review_rows = []
    for item in shared_ontology_alignment_review.get("review_questions", []):
        review_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_action_priority_class(item.get('priority'))}\">{_esc(item.get('priority'))}</span><br><span class=\"small muted\">{_esc(item.get('topic'))}</span></td>"
            f"<td>{_esc(item.get('question'))}</td>"
            f"<td>{_esc(', '.join(item.get('blocks', [])))}</td>"
            f"<td>{_esc(', '.join(item.get('required_evidence', [])))}</td>"
            "</tr>"
        )
    observations = _observations(
        shared_ontology_alignment_review.get("parser_observations", [])
    )
    updates = shared_ontology_alignment_review.get("shared_ontology_updates", [])
    update_note = (
        "<p class=\"muted\">No shared ontology updates were emitted. This stage is review-only until blockers are cleared.</p>"
        if not updates
        else f"<p>{_num(len(updates))} shared ontology updates were emitted.</p>"
    )
    return f"""
<section id="stage-shared-ontology-alignment-review">
  <h2>27. Shared Ontology Alignment / Human Review</h2>
  <div class="section-body">
    <div class="stage-note">Local semantic candidates are checked against shared ontology promotion prerequisites. The current sample intentionally emits no shared ontology updates because local boundary, local source, workbook-family repetition, shared target, formula authority, and human approval evidence are still missing.</div>
    {_metrics(scalar_summary)}
    {observations}
    <div class="review-panels">
      <div class="review-panel">
        <h3>Alignment Context</h3>
        <div class="table-wrap"><table class="compact"><tr><th>Field</th><th>Value</th></tr>{context_rows}</table></div>
      </div>
      <div class="review-panel">
        <h3>Alignment Status</h3>
        <div class="table-wrap"><table class="compact"><tr><th>Status</th><th>Count</th></tr>{status_rows}</table></div>
      </div>
      <div class="review-panel">
        <h3>Blockers</h3>
        <div class="table-wrap"><table class="compact"><tr><th>Blocker</th><th>Count</th></tr>{blocker_rows}</table></div>
      </div>
      <div class="review-panel">
        <h3>Conflict Risks</h3>
        <div class="table-wrap"><table class="compact"><tr><th>Risk</th><th>Count</th></tr>{conflict_rows}</table></div>
      </div>
      <div class="review-panel">
        <h3>Shared Ontology Updates</h3>
        {update_note}
      </div>
    </div>
    <h3>Preconditions</h3>
    <div class="table-wrap">
      <table class="compact">
        <tr><th>Name</th><th>Status</th><th>Description</th><th>Missing Action</th></tr>
        {''.join(precondition_rows)}
      </table>
    </div>
    <h3>Alignment Items</h3>
    <div class="table-wrap wide">
      <table class="compact">
        <tr><th>Candidate</th><th>Status / Source</th><th>Decision</th><th>Data Views</th><th>Blockers</th><th>Conflict Risks</th><th>K-GAAP / K-IFRS Basis</th><th>Required Evidence</th><th>Human Review Questions</th></tr>
        {''.join(item_rows)}
      </table>
    </div>
    <h3>Review Questions</h3>
    <div class="table-wrap">
      <table class="compact">
        <tr><th>Priority / Topic</th><th>Question</th><th>Blocks</th><th>Required Evidence</th></tr>
        {''.join(review_rows)}
      </table>
    </div>
  </div>
</section>
"""


def _process_redesign_review_section(
    process_redesign_review: dict[str, Any] | None,
) -> str:
    if not process_redesign_review:
        return ""
    summary = process_redesign_review.get("summary", {})
    scalar_summary = {
        key: value
        for key, value in summary.items()
        if key != "recommendation_counts"
    }
    final = process_redesign_review.get("final_assessment", {})
    ready_items = "".join(
        f"<li>{_esc(item)}</li>" for item in final.get("what_is_ready", [])
    )
    not_ready_items = "".join(
        f"<li>{_esc(item)}</li>" for item in final.get("what_is_not_ready", [])
    )
    decision_rows = []
    for item in process_redesign_review.get("redesign_decisions", []):
        decision_rows.append(
            "<tr>"
            f"<td>{_esc(item.get('decision'))}<br><span class=\"small muted\">{_esc(item.get('id'))}</span></td>"
            f"<td><span class=\"pill\">{_esc(item.get('status'))}</span></td>"
            f"<td>{_esc(_shorten(' / '.join(item.get('evidence', [])), 220))}</td>"
            f"<td>{_esc(item.get('effect'))}</td>"
            "</tr>"
        )
    pipeline_rows = []
    for item in process_redesign_review.get("recommended_pipeline", []):
        pipeline_rows.append(
            "<tr>"
            f"<td>{_num(item.get('position'))}</td>"
            f"<td>{_esc(item.get('stage'))}</td>"
            f"<td><span class=\"pill {_process_change_class(item.get('change_type'))}\">{_esc(item.get('change_type'))}</span></td>"
            f"<td>{_esc(', '.join(str(value) for value in item.get('source_current_stage_numbers', [])))}</td>"
            f"<td>{_esc(item.get('why'))}</td>"
            "</tr>"
        )
    stage_rows = []
    for item in process_redesign_review.get("stage_reviews", []):
        stage_rows.append(
            "<tr>"
            f"<td>{_num(item.get('current_stage_number'))}<br><span class=\"small muted\">{_esc(item.get('current_status'))}</span></td>"
            f"<td>{_esc(item.get('current_stage'))}</td>"
            f"<td><span class=\"pill {_process_change_class(item.get('recommendation'))}\">{_esc(item.get('recommendation'))}</span><br><span class=\"small muted\">{_esc(item.get('proposed_group'))}</span></td>"
            f"<td><span class=\"pill {_action_priority_class(item.get('priority'))}\">{_esc(item.get('priority'))}</span></td>"
            f"<td>{_esc(_shorten(' / '.join(item.get('rationale', [])), 220))}</td>"
            f"<td>{_esc(_shorten(' / '.join(item.get('recommended_changes', [])), 220))}</td>"
            f"<td>{_esc(_shorten(' / '.join(item.get('completion_guard', [])), 180))}</td>"
            "</tr>"
        )
    gap_rows = []
    for item in process_redesign_review.get("open_evidence_gaps", []):
        gap_rows.append(
            "<tr>"
            f"<td><span class=\"pill {_action_priority_class(item.get('priority'))}\">{_esc(item.get('priority'))}</span><br><span class=\"small muted\">{_esc(item.get('id'))}</span></td>"
            f"<td>{_esc(item.get('gap'))}</td>"
            f"<td>{_esc(', '.join(item.get('blocks', [])))}</td>"
            f"<td>{_esc(', '.join(item.get('required_evidence', [])))}</td>"
            "</tr>"
        )
    next_rows = []
    for item in process_redesign_review.get("next_iteration_plan", []):
        next_rows.append(
            "<tr>"
            f"<td>{_num(item.get('step'))}</td>"
            f"<td>{_esc(item.get('name'))}</td>"
            f"<td>{_esc(item.get('done_when'))}</td>"
            "</tr>"
        )
    recommendation_rows = "".join(
        f"<tr><td>{_esc(kind)}</td><td>{_num(count)}</td></tr>"
        for kind, count in Counter(summary.get("recommendation_counts", {})).most_common()
    )
    observations = _observations(process_redesign_review.get("parser_observations", []))
    return f"""
<section id="stage-process-redesign-review">
  <h2>28. Process Redesign Review</h2>
  <div class="section-body">
    <div class="stage-note">The process ledger, final artifacts, stage outputs, active docs, and viewer behavior are reviewed to decide which parser stages should be kept, merged, reordered, looped, or kept as review-only gates.</div>
    {_metrics(scalar_summary)}
    {observations}
    <div class="review-panels">
      <div class="review-panel">
        <h3>Final Assessment</h3>
        <p><span class="pill warn long">{_esc(final.get('status'))}</span></p>
        <p>{_esc(final.get('recommended_default_next_step'))}</p>
      </div>
      <div class="review-panel">
        <h3>What Is Ready</h3>
        <ul>{ready_items}</ul>
      </div>
      <div class="review-panel">
        <h3>What Is Not Ready</h3>
        <ul>{not_ready_items}</ul>
      </div>
      <div class="review-panel">
        <h3>Recommendation Counts</h3>
        <div class="table-wrap"><table class="compact"><tr><th>Recommendation</th><th>Count</th></tr>{recommendation_rows}</table></div>
      </div>
    </div>
    <h3>Redesign Decisions</h3>
    <div class="table-wrap">
      <table class="compact">
        <tr><th>Decision</th><th>Status</th><th>Evidence</th><th>Effect</th></tr>
        {''.join(decision_rows)}
      </table>
    </div>
    <h3>Recommended Pipeline</h3>
    <div class="table-wrap">
      <table class="compact">
        <tr><th>#</th><th>Stage</th><th>Change</th><th>Current Stage Refs</th><th>Why</th></tr>
        {''.join(pipeline_rows)}
      </table>
    </div>
    <h3>Stage Reviews</h3>
    <div class="table-wrap wide">
      <table class="compact">
        <tr><th>Current #</th><th>Current Stage</th><th>Recommendation / Group</th><th>Priority</th><th>Rationale</th><th>Recommended Changes</th><th>Completion Guard</th></tr>
        {''.join(stage_rows)}
      </table>
    </div>
    <h3>Open Evidence Gaps</h3>
    <div class="table-wrap">
      <table class="compact">
        <tr><th>Priority / ID</th><th>Gap</th><th>Blocks</th><th>Required Evidence</th></tr>
        {''.join(gap_rows)}
      </table>
    </div>
    <h3>Next Iteration Plan</h3>
    <div class="table-wrap">
      <table class="compact">
        <tr><th>Step</th><th>Name</th><th>Done When</th></tr>
        {''.join(next_rows)}
      </table>
    </div>
  </div>
</section>
"""


def _onto_reconstruct_seed_min_summary_section(
    onto_reconstruct_seed_min_summary: dict[str, Any] | None,
) -> str:
    if not onto_reconstruct_seed_min_summary:
        return ""
    run_profile = onto_reconstruct_seed_min_summary.get("run_profile", {})
    mitigation = onto_reconstruct_seed_min_summary.get("mitigation", {})
    result = onto_reconstruct_seed_min_summary.get("result", {})
    metrics = onto_reconstruct_seed_min_summary.get("metrics", {})
    authority = onto_reconstruct_seed_min_summary.get("authority_boundary", {})
    summary_metrics = {
        "source_packet_bytes": onto_reconstruct_seed_min_summary.get(
            "source_packet_bytes"
        ),
        "candidate_count": mitigation.get("seed_min_candidate_count"),
        "promoted_candidate_count": mitigation.get("seed_min_promoted_candidate_count"),
        "seed_validation": result.get("ontology_seed_validation_status"),
        "validation_violations": result.get("ontology_seed_validation_violations"),
        "handoff_projection": result.get("handoff_readiness_projection"),
        "handoff_claim": result.get("ontology_handoff_readiness_claim"),
        "shared_updates": run_profile.get("shared_ontology_update_count"),
    }
    claim_metrics = {
        "semantic_claims": metrics.get("semantic_claim_count"),
        "confirmed": metrics.get("confirmed_claim_count"),
        "partial": metrics.get("partial_claim_count"),
        "deferred": metrics.get("deferred_claim_count"),
        "answerable_cq": metrics.get("competency_question_answerable_count"),
        "partial_cq": metrics.get("competency_question_partially_answerable_count"),
        "unsupported_questions": metrics.get("unsupported_question_count"),
    }
    not_accepted_rows = "".join(
        f"<tr><td><span class=\"pill warn long\">{_esc(item)}</span></td></tr>"
        for item in authority.get("not_accepted_as", [])
    )
    frontier_rows = "".join(
        "<tr>"
        f"<td>{_esc(item)}</td>"
        "<td>Keep as maturation queue; do not promote as parser truth yet.</td>"
        "</tr>"
        for item in authority.get("remaining_maturation_frontier", [])
    )
    return f"""
<section id="stage-onto-seed-min">
  <h2>61. Onto Seed Prompt / Timeout Mitigation</h2>
  <div class="section-body">
    <div class="stage-note">Official onto-mcp direct reconstruct now produced a valid local ontology seed. The seed is accepted as local seed authority only; it is still not action-ready, writeback-ready, shared, K-IFRS/K-GAAP, or accounting-kr aligned.</div>
    {_metrics(summary_metrics)}
    {_metrics(claim_metrics)}
    <div class="review-panels">
      <div class="review-panel">
        <h3>Authority Boundary</h3>
        <p><span class="pill">{_esc(authority.get('accepted_as'))}</span></p>
        <p><strong>Seed:</strong> <code>{_esc(result.get('ontology_seed_ref'))}</code></p>
        <p><strong>Stop decision:</strong> <code>{_esc(result.get('stop_decision'))}</code></p>
      </div>
      <div class="review-panel">
        <h3>Run Profile</h3>
        <p>Domain pack used: <code>{_esc(run_profile.get('domain_pack_used'))}</code></p>
        <p>Reporting basis: <code>{_esc(run_profile.get('reporting_basis'))}</code></p>
        <p>Excluded domains: <code>{_esc(', '.join(run_profile.get('excluded_domain_sources', [])))}</code></p>
        <p>Miro MCP: <code>{_esc(run_profile.get('miro_mcp_status'))}</code></p>
      </div>
      <div class="review-panel">
        <h3>Candidate Reduction</h3>
        <p>Previous candidates: <code>{_esc(mitigation.get('previous_candidate_count'))}</code> -> <code>{_esc(mitigation.get('seed_min_candidate_count'))}</code></p>
        <p>Promoted candidates: <code>{_esc(mitigation.get('previous_promoted_candidate_count'))}</code> -> <code>{_esc(mitigation.get('seed_min_promoted_candidate_count'))}</code></p>
        <p>Seed timeout: <code>{_esc(mitigation.get('seed_timeout_ms'))}</code> ms</p>
      </div>
    </div>
    <h3>Not Accepted As</h3>
    <div class="table-wrap">
      <table class="compact">
        <tr><th>Boundary</th></tr>
        {not_accepted_rows}
      </table>
    </div>
    <h3>Maturation Frontier</h3>
    <div class="table-wrap">
      <table class="compact">
        <tr><th>Open Frontier</th><th>Current Treatment</th></tr>
        {frontier_rows}
      </table>
    </div>
  </div>
</section>
"""


def _process_change_class(status: Any) -> str:
    text = str(status or "")
    if "reorder" in text or "loop" in text or "merge" in text or "review_only" in text:
        return "warn"
    if "blocked" in text or "remove" in text:
        return "danger"
    return ""


def _shared_alignment_status_class(status: Any) -> str:
    if status in {"blocked", "not_promoted"}:
        return "danger"
    if status in {
        "review_required",
        "blocked_local_boundary_pending",
        "blocked_basis_definition_pending",
        "blocked_semantic_label_pending",
        "not_provided",
    }:
        return "warn"
    return ""


def _local_candidate_status_class(status: Any) -> str:
    if status in {"high", "review_required", "needs_semantic_interpretation"}:
        return "warn"
    if status in {"blocked", "error"}:
        return "danger"
    return ""


def _domain_status_class(status: Any) -> str:
    if status in {"missing", "review_required"}:
        return "warn"
    return ""


def _domain_readiness_class(status: Any) -> str:
    if status and str(status).startswith("blocked"):
        return "danger"
    if status and str(status).startswith("proposal_only"):
        return "warn"
    return ""


def _validation_status_class(status: Any) -> str:
    if status in {"rejected", "quarantined"}:
        return "danger"
    if status in {"requires_human_review", "warning"}:
        return "warn"
    return ""


def _evidence_layer_status_class(status: Any) -> str:
    if status in {"unavailable", "not_captured"}:
        return "danger"
    if status == "partial":
        return "warn"
    return ""


def _sorted_visual_feature_results(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    order = {
        "skipped_view_state_blocked": 0,
        "skipped_unusable": 1,
        "not_available": 2,
        "skipped_quality_review": 3,
        "no_visible_content_detected": 4,
        "detected_with_view_state_warning": 5,
        "detected": 6,
    }
    return sorted(
        results,
        key=lambda item: (
            order.get(item.get("status"), 99),
            str(item.get("sheet") or ""),
            str(item.get("cell_range") or ""),
        ),
    )


def _visual_feature_status_class(status: Any) -> str:
    if status in {"skipped_view_state_blocked", "skipped_unusable", "not_available"}:
        return "danger"
    if status in {
        "skipped_quality_review",
        "no_visible_content_detected",
        "detected_with_view_state_warning",
    }:
        return "warn"
    return ""


def _bbox_label(bbox: Any) -> str:
    if not isinstance(bbox, dict):
        return "none"
    return (
        f"{_num(bbox.get('x'))},{_num(bbox.get('y'))} "
        f"{_num(bbox.get('width'))}x{_num(bbox.get('height'))}"
    )


def _sorted_coordinate_mappings(
    mappings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    order = {
        "blocked_by_view_state": 0,
        "unusable_capture": 1,
        "not_available": 2,
        "review_required": 3,
        "normalized_with_view_state_warning": 4,
        "normalized_visible_range": 5,
    }
    return sorted(
        mappings,
        key=lambda item: (
            order.get(item.get("status"), 99),
            str(item.get("sheet") or ""),
            str(item.get("cell_range") or ""),
        ),
    )


def _coordinate_status_class(status: Any) -> str:
    if status in {"blocked_by_view_state", "unusable_capture", "not_available"}:
        return "danger"
    if status in {"review_required", "normalized_with_view_state_warning"}:
        return "warn"
    return ""


def _sorted_view_state_analyses(
    analyses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    order = {
        "all_rows_hidden_or_zero_height": 0,
        "filtered_or_hidden_rows_explain_capture_failure": 1,
        "hidden_rows_dominate_capture_window": 2,
        "filtered_rows_affect_capture_window": 3,
        "mixed_visible_hidden_rows": 4,
        "hidden_columns_affect_capture_window": 5,
        "capture_issue_without_view_state_explanation": 6,
        "no_material_view_state_signal": 7,
    }
    return sorted(
        analyses,
        key=lambda item: (
            order.get(item.get("classification"), 99),
            str(item.get("sheet") or ""),
            str(item.get("range") or ""),
        ),
    )


def _view_state_class(classification: Any) -> str:
    if classification in {
        "all_rows_hidden_or_zero_height",
        "filtered_or_hidden_rows_explain_capture_failure",
        "hidden_rows_dominate_capture_window",
        "capture_issue_without_view_state_explanation",
    }:
        return "danger"
    if classification in {
        "filtered_rows_affect_capture_window",
        "mixed_visible_hidden_rows",
        "hidden_columns_affect_capture_window",
    }:
        return "warn"
    return ""


def _span_summary(spans: list[dict[str, Any]], axis: str) -> str:
    if not spans:
        return "none"
    parts = []
    for span in spans[:3]:
        if axis == "row":
            parts.append(f"{span.get('start_row')}-{span.get('end_row')}")
        else:
            parts.append(
                f"{span.get('start_column_letter')}-{span.get('end_column_letter')}"
            )
    if len(spans) > 3:
        parts.append(f"+{len(spans) - 3}")
    return _esc(", ".join(parts))


def _recapture_priority_class(priority: Any) -> str:
    if priority == "high":
        return "danger"
    if priority == "medium":
        return "warn"
    return ""


def _sorted_quality_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {
        "capture_failed": 0,
        "recapture_required": 1,
        "review_required": 2,
        "usable": 3,
    }
    return sorted(
        results,
        key=lambda result: (
            order.get(result.get("status"), 9),
            str(result.get("sheet") or ""),
            str(result.get("capture_window_range") or ""),
        ),
    )


def _quality_status_class(status: Any) -> str:
    if status in {"capture_failed", "recapture_required"}:
        return "danger"
    if status == "review_required":
        return "warn"
    return ""


def _quality_checks_summary(checks: list[dict[str, Any]]) -> str:
    flagged = [
        check
        for check in checks
        if check.get("status") in {"fail", "warning"}
    ]
    if not flagged:
        return "<span class=\"muted\">none</span>"
    return "<br>".join(
        f"<span class=\"pill {_check_status_class(check.get('status'))}\">{_esc(check.get('status'))}</span> {_esc(check.get('id'))}: <span class=\"small muted\">{_esc(_shorten(check.get('message') or '', 90))}</span>"
        for check in flagged[:5]
    )


def _check_status_class(status: Any) -> str:
    return "danger" if status == "fail" else "warn" if status == "warning" else ""


def _metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return _num(value)


def _relation_groups_table(groups: list[dict[str, Any]]) -> str:
    if not groups:
        return ""
    sorted_groups = sorted(
        groups,
        key=lambda group: group.get("formula_cell_count", 0),
        reverse=True,
    )
    shown = sorted_groups[:40]
    rows = []
    for group in shown:
        profile = group.get("pattern_profile", {})
        profile_note = (
            f"{_esc(profile.get('structure_hint'))}, pattern formulas {_num(profile.get('formula_count'))}"
            if profile.get("matched")
            else "no profile match"
        )
        rows.append(
            "<tr>"
            f"<td>{_esc(group['source_block_id'])}</td>"
            f"<td>{_esc(group['relation_type'])}</td>"
            f"<td>{_num(group['formula_cell_count'])}</td>"
            f"<td>{_num(group['reference_count'])}</td>"
            f"<td>{_esc(group.get('target_sheet'))}<br><span class=\"small muted\">{_esc(', '.join(group.get('target_range_samples', [])))}</span></td>"
            f"<td>{_esc(_bounds_label(group.get('target_bounds_union')))}</td>"
            f"<td><code>{_esc(group['formula_signature'])}</code><div class=\"small muted\">{profile_note}</div></td>"
            "</tr>"
        )
    omitted = len(sorted_groups) - len(shown)
    omitted_note = (
        f"<p class=\"small muted\">Showing top {len(shown)} of {len(sorted_groups)} formula relation groups.</p>"
        if omitted > 0
        else ""
    )
    return f"""
            <h3>Formula Relation Groups</h3>
            {omitted_note}
            <table>
              <tr><th>Source</th><th>Relation</th><th>Formula Cells</th><th>Refs</th><th>Target Samples</th><th>Target Bounds</th><th>Signature</th></tr>
              {''.join(rows)}
            </table>
            """


def _bounds_label(bounds: dict[str, Any] | None) -> str:
    if not bounds:
        return ""
    return (
        f"R{bounds['min_row']}:R{bounds['max_row']}, "
        f"C{bounds['min_column']}:C{bounds['max_column']}"
    )


def _formula_reference_kind_note(refs: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for ref in refs:
        kind = ref.get("kind", "unknown")
        counts[kind] = counts.get(kind, 0) + 1
    if not counts:
        return ""
    return " (" + ", ".join(f"{_esc(key)} {value}" for key, value in sorted(counts.items())) + ")"


def _formula_patterns_section(formula_patterns: dict[str, Any] | None) -> str:
    if not formula_patterns:
        return ""
    sheets = []
    for sheet in formula_patterns["sheets"]:
        windows = []
        for window in sheet["windows"]:
            groups = []
            for group in window["signature_groups"][:12]:
                examples = "\n".join(group.get("formula_examples", []))
                groups.append(
                    "<tr>"
                    f"<td>{group['formula_count']}</td>"
                    f"<td>{group['row_min']}-{group['row_max']}</td>"
                    f"<td>{group['column_min']}-{group['column_max']}</td>"
                    f"<td>{_esc(', '.join(group['sample_cells']))}</td>"
                    f"<td><code>{_esc(group['signature'])}</code><div class=\"preview\">{_esc(examples)}</div></td>"
                    "</tr>"
                )
            windows.append(
                f"""
                <h3>{_esc(sheet['name'])}: Rows {window['start_row']} - {window['end_row']}</h3>
                <p><span class="pill warn">{_esc(window['structure_hint'])}</span></p>
                <p class="small muted">formulas {window['formula_count']}, signatures {window['signature_group_count']}, repeated signatures {window['repeated_signature_group_count']}</p>
                <table>
                  <tr><th>Count</th><th>Rows</th><th>Columns</th><th>Sample Cells</th><th>Signature / Examples</th></tr>
                  {''.join(groups)}
                </table>
                """
            )
        sheets.append("".join(windows))
    return f"""
<section id="stage-formulas">
  <h2>4. Formula Pattern Profile</h2>
  <div class="section-body">
    <div class="stage-note">대형 시트를 바로 표로 분할하기 전에, 수식 구조가 반복되는지 먼저 보는 deterministic profile입니다. 같은 구조의 수식은 상대 좌표 signature로 묶습니다.</div>
    {_metrics(formula_patterns['summary'])}
    {''.join(sheets)}
  </div>
</section>
"""


def _visual_map_section(candidates: dict[str, Any]) -> str:
    maps = [_sheet_visual_map(sheet) for sheet in candidates.get("sheets", [])]
    maps = [item for item in maps if item]
    if not maps:
        return ""
    return f"""
<section id="visual-map">
  <h2>Visual Map</h2>
  <div class="section-body">
    <div class="stage-note">셀 grid 기준의 상대 배치입니다. 실제 Excel 렌더 캡처가 아니며, 다음 단계에서 capture 좌표와 교차검증해야 합니다.</div>
    {''.join(maps)}
  </div>
</section>
"""


def _sheet_visual_map(sheet: dict[str, Any]) -> str:
    blocks = sheet["blocks"]
    if not blocks:
        return ""
    min_row = min(block["bounds"]["start_row"] for block in blocks)
    max_row = max(block["bounds"]["end_row"] for block in blocks)
    min_col = min(block["bounds"]["start_column"] or 1 for block in blocks)
    max_col = max(block["bounds"]["end_column"] or 1 for block in blocks)
    row_span = max(max_row - min_row + 1, 1)
    col_span = max(max_col - min_col + 1, 1)
    items = []
    for block in blocks:
        bounds = block["bounds"]
        left = ((bounds["start_column"] or min_col) - min_col) / col_span * 100
        top = (bounds["start_row"] - min_row) / row_span * 100
        width = max(((bounds["end_column"] or min_col) - (bounds["start_column"] or min_col) + 1) / col_span * 100, 5)
        height = max((bounds["end_row"] - bounds["start_row"] + 1) / row_span * 100, 4)
        if block["type"] == "image":
            cls = "image"
        elif block["type"] == "pivot_table":
            cls = "pivot"
        else:
            cls = "row"
        label = block["label"] or block["subtype"]
        items.append(
            f"<div class=\"canvas-item {cls}\" style=\"left:{left:.2f}%;top:{top:.2f}%;width:{width:.2f}%;height:{height:.2f}%\">{_esc(label)}</div>"
        )
    return f"""
    <h3>{_esc(sheet['name'])}</h3>
    <div class="canvas">{''.join(items)}</div>
"""


def _review_notes_section(
    candidates: dict[str, Any], formula_patterns: dict[str, Any] | None
) -> str:
    priority_rows = _review_priority_rows(candidates, formula_patterns)
    return f"""
<section id="review-notes">
  <h2>Review Notes</h2>
  <div class="section-body">
    <div class="stage-note">이 네 가지 질문은 LLM 해석을 바로 믿기 위한 질문이 아니라, 다음 파서 튜닝과 deterministic gate를 어디에 걸지 정하는 검수 질문입니다.</div>
    <div class="flow">
      <div class="flow-step"><strong>1. 경계</strong>사람이 보는 표/문단/요약 단위가 어떤 2D 셀 영역인지 확인합니다.</div>
      <div class="flow-step"><strong>2. 위계</strong>이미지, 텍스트, pivot, 표가 서로 설명 관계인지 단순 배치인지 봅니다.</div>
      <div class="flow-step"><strong>3. 계산 관계</strong>수식 signature, pivot cache, 외부 참조를 이용해 merge/split/link를 결정합니다.</div>
      <div class="flow-step"><strong>4. 시각 검증</strong>XML만으로 애매한 곳을 Excel render capture 대상으로 올립니다.</div>
    </div>

    <div class="review-grid">
      <div class="review-card">
        <h3>1. 2D 셀 영역 경계가 사람이 보는 표 단위와 맞나요?</h3>
        <p>최종 블록 경계는 행 구간만으로 정하면 안 됩니다. 같은 행 안에서 좌/우로 서로 다른 표가 있을 수 있고, 같은 열 안에서 위/아래 표가 빈 행 없이 붙어 있을 수도 있습니다. 현재 <code>row_band</code>는 첫 seed일 뿐이며, 이후에는 행 범위와 열 범위를 함께 가진 cell region으로 확정해야 합니다.</p>
        <div class="review-example"><strong>예시.</strong> <code>누적</code> 시트의 117개 <code>SUBTOTAL</code> 수식은 셀마다 따로 해석하기보다 하나의 summary formula band로 보는 편이 자연스럽습니다. 반대로 같은 행 구간 안에서도 A:D는 원천 데이터, F:J는 요약표처럼 헤더, 수식 출처, 스타일이 다르면 두 개의 cell region으로 나눠야 합니다.</div>
        <div class="decision-strip">
          <div class="decision"><strong>OK</strong><br>제목, 헤더, 본문, 요약이 같은 업무 단위를 설명합니다.</div>
          <div class="decision"><strong>Merge</strong><br>시각적으로 조금 떨어져도 같은 formula pattern이나 같은 pivot/source 흐름을 공유합니다.</div>
          <div class="decision"><strong>Split</strong><br>행/열이 붙어 있어도 헤더, 계산, 출처, 의미가 바뀝니다.</div>
        </div>
        <div class="gate"><strong>Gate.</strong> 빈 행/빈 열이 없다는 이유만으로 merge하지 않습니다. 반복 formula signature, pivot cache/source, 헤더 반복, 스타일 경계, 병합 셀, 외부 참조가 서로 다른 단위를 가리키면 인접해 있어도 split 후보입니다.</div>
      </div>

      <div class="review-card">
        <h3>2. 이미지 anchor와 좌측/하단 표의 관계가 맞나요?</h3>
        <p>엑셀의 이미지는 장식이 아니라 캡처, 증빙, 매뉴얼 조각, 또는 특정 표의 시각적 제목일 수 있습니다. anchor 좌표만으로 부모-자식 관계를 확정하지 않고, 주변 텍스트와 표 위치를 함께 봐야 합니다.</p>
        <div class="review-example"><strong>예시.</strong> <code>결제&amp;수수료</code> 시트에는 이미지 5개와 pivot table 14개가 함께 있습니다. 이미지 바로 아래 pivot/table이 반복된다면 <code>image explains table group</code> 후보이고, 좌측 텍스트와 나란히 있으면 설명 블록의 일부일 수 있습니다.</div>
        <div class="decision-strip">
          <div class="decision"><strong>Parent</strong><br>이미지 아래/옆 표가 이미지의 설명 대상입니다.</div>
          <div class="decision"><strong>Caption</strong><br>이미지가 텍스트 블록의 일부 또는 캡처입니다.</div>
          <div class="decision"><strong>Unrelated</strong><br>시각적으로 가깝지만 계산/문맥 관계가 없습니다.</div>
        </div>
        <div class="gate"><strong>Gate.</strong> anchor 근접성, row/column overlap, 주변 텍스트, render capture를 함께 만족할 때만 hierarchy relation을 강하게 올립니다.</div>
      </div>

      <div class="review-card">
        <h3>3. 수식/요약 블록이 별도 블록으로 나뉘어야 하나요?</h3>
        <p>수식이 있다고 모두 별도 블록은 아닙니다. 행 단위 파생 컬럼은 같은 데이터 표 안에 남고, 넓은 범위를 집계하는 요약 band나 <code>GETPIVOTDATA</code>, pivot table 출력은 별도 계산/요약 블록으로 보는 편이 안전합니다.</p>
        <div class="review-example"><strong>예시.</strong> <code>매출</code> 시트의 <code>SUMIFS</code> 반복은 <code>결제상세</code>를 참조하는 데이터 흐름 relation입니다. <code>누적</code>의 <code>SUBTOTAL</code> band는 상세 행이 아니라 요약/필터 계산 권위이므로 일반 row table과 분리 후보입니다.</div>
        <div class="decision-strip">
          <div class="decision"><strong>Keep</strong><br>본문 행마다 같은 방식으로 계산되는 파생 컬럼입니다.</div>
          <div class="decision"><strong>Split</strong><br>전체 범위 집계, subtotal, report header/footer입니다.</div>
          <div class="decision"><strong>Link</strong><br>외부 workbook, 다른 sheet, pivot cache를 참조합니다.</div>
        </div>
        <div class="gate"><strong>Gate.</strong> raw relation은 증거로 유지하고, formula signature 기반 <code>relation_groups</code>를 해석 단위로 사용합니다. pivot table은 값 표가 아니라 pivot cache/source 설정을 기준으로 검증합니다.</div>
      </div>

      <div class="review-card">
        <h3>4. 어떤 블록부터 실제 Excel render capture로 확인해야 하나요?</h3>
        <p>XML/셀 값만으로는 병합 셀, 숨김 행/열, 이미지 겹침, pivot 스타일, 사람이 보는 구획선을 충분히 알기 어렵습니다. capture는 비용이 있으므로 위험도가 높은 블록부터 순서를 정해야 합니다.</p>
        <div class="review-example"><strong>예시.</strong> <code>결제&amp;수수료</code>처럼 이미지와 pivot이 섞인 시트, <code>매출</code>처럼 pivot/table이 많은 시트, <code>누적</code>처럼 XML이 매우 큰 시트의 상단 summary band가 우선 후보입니다.</div>
        <div class="decision-strip">
          <div class="decision"><strong>High</strong><br>이미지/pivot/merged layout이 섞이고 hierarchy가 애매합니다.</div>
          <div class="decision"><strong>Medium</strong><br>수식 grouping은 명확하지만 표 경계가 애매합니다.</div>
          <div class="decision"><strong>Low</strong><br>단일 표이고 formula pattern도 안정적입니다.</div>
        </div>
        <div class="gate"><strong>Gate.</strong> capture 결과와 XML anchor/bounds가 충돌하면 visual authority를 별도 evidence로 남기고, LLM 판단은 이 evidence 안에서만 허용합니다.</div>
      </div>
    </div>

    <h3>Current Workbook Review Priority Hints</h3>
    <table>
      <tr><th>Sheet</th><th>Why first</th><th>Images</th><th>Pivots</th><th>Relation Groups</th><th>Formula Cells</th></tr>
      {priority_rows}
    </table>
  </div>
</section>
"""


def _review_priority_rows(
    candidates: dict[str, Any], formula_patterns: dict[str, Any] | None
) -> str:
    formula_counts = {}
    if formula_patterns:
        for sheet in formula_patterns.get("sheets", []):
            formula_counts[sheet.get("name")] = sheet.get("summary", {}).get(
                "formula_count", 0
            )

    rows = []
    for sheet in candidates.get("sheets", []):
        blocks = sheet.get("blocks", [])
        image_count = sum(1 for block in blocks if block.get("type") == "image")
        pivot_count = sum(1 for block in blocks if block.get("type") == "pivot_table")
        group_count = len(sheet.get("relation_groups", []))
        formula_count = formula_counts.get(sheet.get("name"), 0)
        bounds = sheet.get("dimension_bounds") or {}
        end_row = bounds.get("end_row") or bounds.get("max_row") or 0
        start_row = bounds.get("start_row") or bounds.get("min_row") or 1
        row_span = end_row - start_row + 1
        score = image_count * 5 + pivot_count * 4 + min(group_count, 40) + min(
            formula_count // 100, 30
        )
        if row_span >= 100_000:
            score += 35
        if score <= 0:
            continue
        reasons = []
        if image_count:
            reasons.append("image hierarchy")
        if pivot_count:
            reasons.append("pivot/table boundary")
        if row_span >= 100_000:
            reasons.append("large sheet boundary risk")
        if group_count >= 50:
            reasons.append("dense formula relations")
        elif group_count:
            reasons.append("formula grouping")
        if formula_count >= 1000:
            reasons.append("large formula surface")
        rows.append(
            {
                "name": sheet.get("name"),
                "score": score,
                "why": ", ".join(reasons) or "structural review",
                "images": image_count,
                "pivots": pivot_count,
                "groups": group_count,
                "formulas": formula_count,
            }
        )

    rows.sort(key=lambda item: (-item["score"], str(item["name"])))
    if not rows:
        return "<tr><td colspan=\"6\">No priority hints were produced.</td></tr>"
    return "".join(
        "<tr>"
        f"<td>{_esc(item['name'])}</td>"
        f"<td>{_esc(item['why'])}</td>"
        f"<td>{_num(item['images'])}</td>"
        f"<td>{_num(item['pivots'])}</td>"
        f"<td>{_num(item['groups'])}</td>"
        f"<td>{_num(item['formulas'])}</td>"
        "</tr>"
        for item in rows[:8]
    )


def _metrics(summary: dict[str, Any]) -> str:
    cards = []
    for key, value in summary.items():
        cards.append(
            f"<div class=\"metric\"><div class=\"label\">{_esc(key)}</div><div class=\"value\">{_esc(_num(value))}</div></div>"
        )
    return f"<div class=\"grid\">{''.join(cards)}</div>"


def _observations(observations: list[dict[str, Any]]) -> str:
    if not observations:
        return ""
    rows = []
    for item in observations:
        cls = "warn" if item["level"] == "warning" else ""
        rows.append(
            f"<tr><td><span class=\"pill {cls}\">{_esc(item['level'])}</span></td><td>{_esc(item['message'])}</td></tr>"
        )
    return f"<table><tr><th>Level</th><th>Message</th></tr>{''.join(rows)}</table>"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _num(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _shorten(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _relative_src(path_text: str, viewer_dir: Path) -> str:
    path = Path(path_text).expanduser()
    try:
        return path.resolve().relative_to(viewer_dir).as_posix()
    except ValueError:
        return path_text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a static HTML viewer for workbook understanding artifacts."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--readonly-sample", type=Path, required=True)
    parser.add_argument("--block-candidates", type=Path, required=True)
    parser.add_argument("--formula-patterns", type=Path)
    parser.add_argument("--structural-style-profile", type=Path)
    parser.add_argument("--table-io-pipelines", type=Path)
    parser.add_argument("--cross-validation-plan", type=Path)
    parser.add_argument("--render-captures", type=Path)
    parser.add_argument("--capture-quality", type=Path)
    parser.add_argument("--recapture-candidate-plan", type=Path)
    parser.add_argument("--recapture-candidate-captures", type=Path)
    parser.add_argument("--recapture-candidate-quality", type=Path)
    parser.add_argument("--view-state-preflight", type=Path)
    parser.add_argument("--view-state-profile", type=Path)
    parser.add_argument("--coordinate-normalization", type=Path)
    parser.add_argument("--visual-features", type=Path)
    parser.add_argument("--gate-execution", type=Path)
    parser.add_argument("--boundary-decisions", type=Path)
    parser.add_argument("--pipeline-role-validation", type=Path)
    parser.add_argument("--evidence-package", type=Path)
    parser.add_argument("--document-ontology-mapping", type=Path)
    parser.add_argument("--action-contracts", type=Path)
    parser.add_argument("--domain-source-model", type=Path)
    parser.add_argument("--llm-proposals", type=Path)
    parser.add_argument("--llm-proposal-validation", type=Path)
    parser.add_argument("--validated-document-graph", type=Path)
    parser.add_argument("--data-view-projection", type=Path)
    parser.add_argument("--local-semantic-candidates", type=Path)
    parser.add_argument("--shared-ontology-alignment-review", type=Path)
    parser.add_argument("--process-redesign-review", type=Path)
    parser.add_argument("--onto-reconstruct-seed-min-summary", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    build_viewer(
        args.manifest,
        args.readonly_sample,
        args.block_candidates,
        args.output,
        formula_patterns_path=args.formula_patterns,
        structural_style_profile_path=args.structural_style_profile,
        table_io_pipelines_path=args.table_io_pipelines,
        cross_validation_plan_path=args.cross_validation_plan,
        render_captures_path=args.render_captures,
        capture_quality_path=args.capture_quality,
        recapture_candidate_plan_path=args.recapture_candidate_plan,
        recapture_candidate_captures_path=args.recapture_candidate_captures,
        recapture_candidate_quality_path=args.recapture_candidate_quality,
        view_state_preflight_path=args.view_state_preflight,
        view_state_profile_path=args.view_state_profile,
        coordinate_normalization_path=args.coordinate_normalization,
        visual_features_path=args.visual_features,
        gate_execution_path=args.gate_execution,
        boundary_decisions_path=args.boundary_decisions,
        pipeline_role_validation_path=args.pipeline_role_validation,
        evidence_package_path=args.evidence_package,
        document_ontology_mapping_path=args.document_ontology_mapping,
        action_contracts_path=args.action_contracts,
        domain_source_model_path=args.domain_source_model,
        llm_proposals_path=args.llm_proposals,
        llm_proposal_validation_path=args.llm_proposal_validation,
        validated_document_graph_path=args.validated_document_graph,
        data_view_projection_path=args.data_view_projection,
        local_semantic_candidates_path=args.local_semantic_candidates,
        shared_ontology_alignment_review_path=args.shared_ontology_alignment_review,
        process_redesign_review_path=args.process_redesign_review,
        onto_reconstruct_seed_min_summary_path=args.onto_reconstruct_seed_min_summary,
    )


if __name__ == "__main__":
    main()
