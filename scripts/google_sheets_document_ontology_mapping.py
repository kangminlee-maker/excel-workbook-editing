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


def build_google_sheets_document_ontology_mapping(
    *,
    live_evidence_package_path: Path,
) -> dict[str, Any]:
    live_evidence_package_path = live_evidence_package_path.expanduser().resolve()
    evidence = _read_json(live_evidence_package_path)
    nodes = _nodes(evidence)
    relations = _relations(evidence, nodes)
    review_items = _review_items(evidence)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": evidence["source"]["spreadsheet_id"],
            "spreadsheet_url": evidence["source"].get("spreadsheet_url"),
            "title": evidence["source"]["title"],
            "source_artifacts": {
                "live_evidence_package": str(live_evidence_package_path),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "mapping_status": "document_structure_ontology_mapping_only",
            "semantic_ontology_generation": "not_performed",
            "formula_result_authority": "not_established",
            "source_spreadsheet_read_authority": "blocked_until_source_access_evidence",
        },
        "ontology": {
            "namespace": "document_structure",
            "nodes": nodes,
            "relations": relations,
            "review_items": review_items,
        },
        "summary": _summary(nodes, relations, review_items),
        "parser_observations": _parser_observations(review_items),
    }


def write_google_sheets_document_ontology_mapping_package(
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
    document_ontology_mapping: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping_path = out_dir / "live-document-ontology-mapping.json"
    mapping_path.write_text(
        json.dumps(document_ontology_mapping, ensure_ascii=False, indent=2) + "\n",
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
            live_document_ontology_mapping=document_ontology_mapping,
        ),
        encoding="utf-8",
    )


def _nodes(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [
        {
            "id": "node_workbook",
            "type": "workbook_document",
            "status": "accepted",
            "label": evidence["source"]["title"],
            "properties": evidence["workbook_facts"],
            "evidence_refs": ["live-evidence-package.json"],
        },
        {
            "id": "node_accepted_evidence_body",
            "type": "accepted_evidence_body",
            "status": "accepted",
            "label": "Accepted deterministic evidence",
            "properties": {
                "accepted_gate_count": evidence["summary"]["accepted_gate_count"],
                "accepted_target_count": evidence["summary"]["accepted_target_count"],
            },
            "evidence_refs": ["accepted_evidence"],
        },
    ]
    for pipeline in evidence["accepted_evidence"]["pipelines"]:
        nodes.append(
            {
                "id": f"node_pipeline_{_slug(pipeline['id'])}",
                "type": "calculation_pipeline",
                "status": "accepted",
                "label": pipeline["output_refs"][0]["label"],
                "properties": {
                    "pipeline_id": pipeline["id"],
                    "role": pipeline["role"],
                    "confidence": pipeline["confidence"],
                    "input_label": pipeline["input_refs"][0]["label"],
                    "output_label": pipeline["output_refs"][0]["label"],
                },
                "evidence_refs": [pipeline["id"]],
            }
        )
    for item in evidence["review_queue"]:
        nodes.append(
            {
                "id": f"node_review_{_slug(item['id'])}",
                "type": "review_queue_item",
                "status": "review_required",
                "label": item["type"],
                "properties": {
                    "severity": item["severity"],
                    "message": item["message"],
                    "status": item["status"],
                },
                "evidence_refs": item.get("evidence_refs", []),
            }
        )
    return nodes


def _relations(evidence: dict[str, Any], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relations = [
        {
            "id": "rel_workbook_has_accepted_evidence",
            "type": "has_evidence_body",
            "from": "node_workbook",
            "to": "node_accepted_evidence_body",
            "status": "accepted",
            "evidence_refs": ["live-evidence-package.json"],
        }
    ]
    for node in nodes:
        if node["type"] == "calculation_pipeline":
            relations.append(
                {
                    "id": f"rel_accepted_evidence_contains_{node['id']}",
                    "type": "contains_accepted_pipeline",
                    "from": "node_accepted_evidence_body",
                    "to": node["id"],
                    "status": "accepted",
                    "evidence_refs": node["evidence_refs"],
                }
            )
        if node["type"] == "review_queue_item":
            relations.append(
                {
                    "id": f"rel_workbook_has_review_{node['id']}",
                    "type": "has_review_item",
                    "from": "node_workbook",
                    "to": node["id"],
                    "status": "review_required",
                    "evidence_refs": node["evidence_refs"],
                }
            )
    return relations


def _review_items(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "type": item["type"],
            "severity": item["severity"],
            "status": item["status"],
            "message": item["message"],
            "evidence_refs": item.get("evidence_refs", []),
        }
        for item in evidence["review_queue"]
    ]


def _summary(
    nodes: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    review_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "node_count": len(nodes),
        "accepted_node_count": sum(1 for item in nodes if item["status"] == "accepted"),
        "review_required_node_count": sum(1 for item in nodes if item["status"] == "review_required"),
        "relation_count": len(relations),
        "accepted_relation_count": sum(1 for item in relations if item["status"] == "accepted"),
        "review_required_relation_count": sum(1 for item in relations if item["status"] == "review_required"),
        "review_item_count": len(review_items),
        "semantic_concept_count": 0,
        "mapping_status": "document_structure_ontology_mapping_only",
    }


def _parser_observations(review_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": "Document ontology mapping uses the document-structure ontology only; semantic ontology generation is not performed.",
        }
    ]
    if review_items:
        observations.append(
            {
                "level": "warning",
                "message": f"{len(review_items)} review items are carried forward as review-required ontology nodes.",
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


def render_google_sheets_document_ontology_mapping_section(mapping: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in mapping["summary"].items()
    )
    node_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['type'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(item['label'])}</td>"
        f"<td><code>{_esc(item['id'])}</code></td>"
        "</tr>"
        for item in mapping["ontology"]["nodes"][:80]
    )
    relation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['type'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td><code>{_esc(item['from'])}</code></td>"
        f"<td><code>{_esc(item['to'])}</code></td>"
        "</tr>"
        for item in mapping["ontology"]["relations"][:80]
    )
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        "</tr>"
        for item in mapping["parser_observations"]
    )
    return f"""
  <h2>Live Document Ontology Mapping</h2>
  <section class="grid">{metrics}</section>
  <h2>Ontology Nodes</h2>
  <section class="panel"><table><thead><tr><th>Type</th><th>Status</th><th>Label</th><th>ID</th></tr></thead><tbody>{node_rows}</tbody></table></section>
  <h2>Ontology Relations</h2>
  <section class="panel"><table><thead><tr><th>Type</th><th>Status</th><th>From</th><th>To</th></tr></thead><tbody>{relation_rows}</tbody></table></section>
  <h2>Ontology Mapping Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Map connected Google Sheets evidence package to document-structure ontology."
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
    args = parser.parse_args()

    mapping = build_google_sheets_document_ontology_mapping(
        live_evidence_package_path=args.live_evidence_package,
    )
    write_google_sheets_document_ontology_mapping_package(
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
        document_ontology_mapping=mapping,
    )


if __name__ == "__main__":
    main()
