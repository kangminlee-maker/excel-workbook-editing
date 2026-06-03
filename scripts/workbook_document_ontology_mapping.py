from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"


def build_document_ontology_mapping(evidence_package_path: Path) -> dict[str, Any]:
    evidence_package_path = evidence_package_path.expanduser().resolve()
    evidence_package = _read_json(evidence_package_path)
    source_artifacts = _source_artifacts(evidence_package_path, evidence_package)
    block_candidates = _read_json(source_artifacts["block_candidates"])
    table_io_pipelines = _read_json(source_artifacts["table_io_pipelines"])
    gate_execution = _read_json(source_artifacts["gate_execution"])
    boundary_decisions = _read_json(source_artifacts["boundary_decisions"])
    pipeline_role_validation = _read_json(source_artifacts["pipeline_role_validation"])
    coordinate_normalization = _read_json(source_artifacts["coordinate_normalization"])
    visual_features = _read_json(source_artifacts["visual_features"])

    status_index = _build_status_index(
        gate_execution=gate_execution,
        boundary_decisions=boundary_decisions,
        pipeline_role_validation=pipeline_role_validation,
    )
    builder = _MappingBuilder(status_index=status_index)
    builder.add_workbook_and_sheets(evidence_package)
    builder.add_blocks_and_regions(block_candidates)
    builder.add_boundary_decisions(boundary_decisions)
    builder.add_visual_evidence(coordinate_normalization, visual_features)
    builder.add_pipelines(table_io_pipelines, pipeline_role_validation)
    builder.add_candidate_relations(block_candidates)
    review_queue = _ontology_review_queue(evidence_package, builder.original_to_node_id)

    nodes = sorted(builder.nodes.values(), key=lambda item: item["id"])
    relations = sorted(builder.relations.values(), key=lambda item: item["id"])
    data_views = sorted(builder.data_views.values(), key=lambda item: item["id"])
    _assert_no_dangling_relations(nodes, relations)
    _assert_evidence_refs(nodes, relations, data_views)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "evidence_package": str(evidence_package_path),
            **{name: str(path) for name, path in sorted(source_artifacts.items())},
        },
        "method": {
            "name": "deterministic_document_ontology_mapping",
            "authority": "evidence_package_projection_not_semantic_generation",
            "ontology_use": "document_structure_ontology_application",
            "decision_policy": (
                "Apply the document-structure ontology to deterministic evidence. "
                "Do not create semantic ontology concepts, and do not turn LLM-style "
                "interpretation into final truth."
            ),
        },
        "ontology": {
            "id": "document_structure_ontology_v0",
            "layer": "document_structure",
            "application_mode": "reuse_existing_ontology",
            "generated_semantic_ontology": False,
            "node_types": [
                "workbook",
                "sheet",
                "document_block",
                "cell_region",
                "data_pipeline",
                "transform_step",
                "range_ref",
                "visual_evidence",
                "review_item",
            ],
            "relation_types": [
                "contains",
                "has_region",
                "has_boundary_decision",
                "has_visual_evidence",
                "has_pipeline_output",
                "has_pipeline_input",
                "has_pipeline_transform",
                "derived_from",
                "candidate_relation",
                "requires_review",
            ],
        },
        "nodes": nodes,
        "relations": relations,
        "data_views": data_views,
        "review_queue": review_queue,
        "summary": _summary(nodes, relations, data_views, review_queue),
        "parser_observations": _parser_observations(nodes, relations, data_views, review_queue),
    }


class _MappingBuilder:
    def __init__(self, *, status_index: dict[str, dict[str, str]]) -> None:
        self.status_index = status_index
        self.nodes: dict[str, dict[str, Any]] = {}
        self.relations: dict[str, dict[str, Any]] = {}
        self.data_views: dict[str, dict[str, Any]] = {}
        self.original_to_node_id: dict[str, str] = {}
        self.workbook_id = "workbook:source"

    def add_workbook_and_sheets(self, evidence_package: dict[str, Any]) -> None:
        source = evidence_package.get("source", {})
        self._add_node(
            {
                "id": self.workbook_id,
                "type": "workbook",
                "ontology_class": "WorkbookDocument",
                "label": source.get("file_name") or "Workbook",
                "status": "accepted",
                "sheet": None,
                "range": None,
                "properties": {
                    "source_path": source.get("path"),
                    "sha256": source.get("sha256"),
                    "package_kind": evidence_package.get("package_kind"),
                },
                "evidence_refs": ["evidence_package.source", "manifest.workbook"],
                "source_artifact_refs": ["evidence_package", "manifest"],
            }
        )
        for sheet in evidence_package.get("sheets", []):
            sheet_id = _node_id("sheet", sheet["name"])
            self.original_to_node_id[sheet["name"]] = sheet_id
            self._add_node(
                {
                    "id": sheet_id,
                    "type": "sheet",
                    "ontology_class": "WorksheetSurface",
                    "label": sheet["name"],
                    "status": "accepted",
                    "sheet": sheet["name"],
                    "range": sheet.get("dimensions"),
                    "properties": {
                        "index": sheet.get("index"),
                        "sheet_state": sheet.get("sheet_state"),
                        "grid_bounds": sheet.get("grid_bounds"),
                        "freeze_panes": sheet.get("freeze_panes"),
                        "auto_filter_ref": sheet.get("auto_filter_ref"),
                    },
                    "evidence_refs": [f"sheet:{sheet['name']}", "evidence_package.sheets"],
                    "source_artifact_refs": ["evidence_package", "manifest", "view_state_preflight"],
                }
            )
            self._add_relation(
                {
                    "id": _relation_id("contains", self.workbook_id, sheet_id),
                    "type": "contains",
                    "from": self.workbook_id,
                    "to": sheet_id,
                    "status": "accepted",
                    "properties": {"container": "workbook"},
                    "evidence_refs": ["manifest.workbook.sheets"],
                    "source_artifact_refs": ["manifest", "evidence_package"],
                }
            )

    def add_blocks_and_regions(self, block_candidates: dict[str, Any]) -> None:
        for sheet in block_candidates.get("sheets", []):
            sheet_id = _node_id("sheet", sheet["name"])
            for block in sheet.get("blocks", []):
                block_id = _node_id("block", block["id"])
                self.original_to_node_id[block["id"]] = block_id
                status = self._object_status(block["id"], fallback=_block_default_status(block))
                self._add_node(
                    {
                        "id": block_id,
                        "type": "document_block",
                        "ontology_class": _block_ontology_class(block),
                        "label": block.get("label") or block["id"],
                        "status": status,
                        "sheet": sheet["name"],
                        "range": _bounds_to_range(block.get("bounds")),
                        "properties": {
                            "candidate_type": block.get("type"),
                            "subtype": block.get("subtype"),
                            "bounds": block.get("bounds"),
                            "metrics": block.get("metrics", {}),
                            "confidence": block.get("confidence"),
                        },
                        "evidence_refs": _evidence_refs(block, ["block_candidates.blocks"]),
                        "source_artifact_refs": ["block_candidates"],
                    }
                )
                self._add_relation(
                    {
                        "id": _relation_id("contains", sheet_id, block_id),
                        "type": "contains",
                        "from": sheet_id,
                        "to": block_id,
                        "status": status,
                        "properties": {"container": "sheet"},
                        "evidence_refs": _evidence_refs(block, ["block_candidates.blocks"]),
                        "source_artifact_refs": ["block_candidates"],
                    }
                )
            for region in sheet.get("cell_regions", []):
                region_id = _node_id("region", region["id"])
                self.original_to_node_id[region["id"]] = region_id
                parent_id = region.get("parent_seed_block_id")
                status = self._object_status(region["id"], fallback="candidate")
                self._add_node(
                    {
                        "id": region_id,
                        "type": "cell_region",
                        "ontology_class": _region_ontology_class(region),
                        "label": region.get("label") or region["id"],
                        "status": status,
                        "sheet": sheet["name"],
                        "range": _bounds_to_range(region.get("bounds")),
                        "properties": {
                            "subtype": region.get("subtype"),
                            "parent_seed_block_id": parent_id,
                            "bounds": region.get("bounds"),
                            "metrics": region.get("metrics", {}),
                            "confidence": region.get("confidence"),
                        },
                        "evidence_refs": _evidence_refs(region, ["block_candidates.cell_regions"]),
                        "source_artifact_refs": ["block_candidates", "readonly_sample"],
                    }
                )
                self._add_relation(
                    {
                        "id": _relation_id("contains", sheet_id, region_id),
                        "type": "contains",
                        "from": sheet_id,
                        "to": region_id,
                        "status": status,
                        "properties": {"container": "sheet"},
                        "evidence_refs": _evidence_refs(region, ["block_candidates.cell_regions"]),
                        "source_artifact_refs": ["block_candidates"],
                    }
                )
                if parent_id:
                    parent_node_id = self.original_to_node_id.get(parent_id)
                    if parent_node_id:
                        self._add_relation(
                            {
                                "id": _relation_id("has_region", parent_node_id, region_id),
                                "type": "has_region",
                                "from": parent_node_id,
                                "to": region_id,
                                "status": status,
                                "properties": {"parent_seed_block_id": parent_id},
                                "evidence_refs": _evidence_refs(region, ["row_oriented_seed", "column_segmentation"]),
                                "source_artifact_refs": ["block_candidates"],
                            }
                        )

    def add_boundary_decisions(self, boundary_decisions: dict[str, Any]) -> None:
        for decision in boundary_decisions.get("boundary_decisions", []):
            for region_id in decision.get("related_region_ids", []):
                node_id = self.original_to_node_id.get(region_id)
                if not node_id:
                    continue
                self._add_relation(
                    {
                        "id": _relation_id("has_boundary_decision", node_id, decision["id"]),
                        "type": "has_boundary_decision",
                        "from": node_id,
                        "to": self._ensure_review_or_decision_node(decision),
                        "status": decision.get("status") or "review_required",
                        "properties": {
                            "decision": decision.get("decision"),
                            "reason": decision.get("reason"),
                            "boundary_kind": decision.get("boundary_kind"),
                            "graph_effect": decision.get("graph_effect"),
                        },
                        "evidence_refs": _evidence_refs(decision, [decision["id"]]),
                        "source_artifact_refs": ["boundary_decisions"],
                    }
                )

    def add_visual_evidence(
        self,
        coordinate_normalization: dict[str, Any],
        visual_features: dict[str, Any],
    ) -> None:
        mapping_by_target = {
            mapping.get("target_id"): mapping
            for mapping in coordinate_normalization.get("coordinate_mappings", [])
        }
        for feature in visual_features.get("feature_results", []):
            visual_id = _node_id("visual", feature["id"])
            target_original_id = _target_to_original_id(feature.get("target_id"))
            target_node_id = self.original_to_node_id.get(target_original_id or "")
            mapping = mapping_by_target.get(feature.get("target_id")) or {}
            status = _visual_status(feature)
            self._add_node(
                {
                    "id": visual_id,
                    "type": "visual_evidence",
                    "ontology_class": "RenderedVisualEvidence",
                    "label": feature.get("capture_id") or feature["id"],
                    "status": status,
                    "sheet": feature.get("sheet"),
                    "range": feature.get("cell_range"),
                    "properties": {
                        "feature_status": feature.get("status"),
                        "quality_status": feature.get("quality_status"),
                        "normalization_status": feature.get("normalization_status"),
                        "view_state_classification": feature.get("view_state_classification"),
                        "layout_signals": feature.get("layout_signals", []),
                        "png_path": feature.get("png_path"),
                        "mapping_status": mapping.get("status"),
                    },
                    "evidence_refs": _evidence_refs(feature, [feature["id"]]),
                    "source_artifact_refs": ["visual_features", "coordinate_normalization", "render_captures"],
                }
            )
            if target_node_id:
                self._add_relation(
                    {
                        "id": _relation_id("has_visual_evidence", target_node_id, visual_id),
                        "type": "has_visual_evidence",
                        "from": target_node_id,
                        "to": visual_id,
                        "status": status,
                        "properties": {
                            "target_id": feature.get("target_id"),
                            "mapping_id": feature.get("mapping_id"),
                        },
                        "evidence_refs": _evidence_refs(feature, [feature["id"]]),
                        "source_artifact_refs": ["visual_features", "coordinate_normalization"],
                    }
                )

    def add_pipelines(
        self,
        table_io_pipelines: dict[str, Any],
        pipeline_role_validation: dict[str, Any],
    ) -> None:
        validation_by_pipeline = {
            validation["pipeline_id"]: validation
            for validation in pipeline_role_validation.get("role_validations", [])
        }
        for pipeline in table_io_pipelines.get("pipelines", []):
            validation = validation_by_pipeline.get(pipeline["id"], {})
            status = validation.get("status") or pipeline.get("status") or "candidate"
            pipeline_node_id = _node_id("pipeline", pipeline["id"])
            self.original_to_node_id[pipeline["id"]] = pipeline_node_id
            self._add_node(
                {
                    "id": pipeline_node_id,
                    "type": "data_pipeline",
                    "ontology_class": "WorkbookDataPipeline",
                    "label": pipeline["id"],
                    "status": status,
                    "sheet": pipeline.get("output_ref", {}).get("sheet"),
                    "range": pipeline.get("output_ref", {}).get("range"),
                    "properties": {
                        "asserted_role": pipeline.get("role"),
                        "validated_role": validation.get("validated_role"),
                        "reason": validation.get("reason"),
                        "confidence": validation.get("confidence", pipeline.get("confidence")),
                        "review_flags": pipeline.get("review_flags", []),
                    },
                    "evidence_refs": _pipeline_evidence_refs(pipeline, validation),
                    "source_artifact_refs": ["table_io_pipelines", "pipeline_role_validation"],
                }
            )
            output_node_id = self._ensure_ref_node(pipeline.get("output_ref", {}), status)
            self._add_relation(
                {
                    "id": _relation_id("has_pipeline_output", pipeline_node_id, output_node_id),
                    "type": "has_pipeline_output",
                    "from": pipeline_node_id,
                    "to": output_node_id,
                    "status": status,
                    "properties": {"role": validation.get("validated_role") or pipeline.get("role")},
                    "evidence_refs": _pipeline_evidence_refs(pipeline, validation),
                    "source_artifact_refs": ["table_io_pipelines", "pipeline_role_validation"],
                }
            )
            input_node_ids = []
            for ref in pipeline.get("input_refs", []):
                input_node_id = self._ensure_ref_node(ref, status)
                input_node_ids.append(input_node_id)
                self._add_relation(
                    {
                        "id": _relation_id("has_pipeline_input", pipeline_node_id, input_node_id),
                        "type": "has_pipeline_input",
                        "from": pipeline_node_id,
                        "to": input_node_id,
                        "status": status,
                        "properties": {"input_kind": ref.get("kind")},
                        "evidence_refs": _pipeline_evidence_refs(pipeline, validation),
                        "source_artifact_refs": ["table_io_pipelines"],
                    }
                )
                self._add_relation(
                    {
                        "id": _relation_id("derived_from", output_node_id, input_node_id),
                        "type": "derived_from",
                        "from": output_node_id,
                        "to": input_node_id,
                        "status": status,
                        "properties": {"pipeline_id": pipeline["id"]},
                        "evidence_refs": _pipeline_evidence_refs(pipeline, validation),
                        "source_artifact_refs": ["table_io_pipelines", "pipeline_role_validation"],
                    }
                )
            transform_node_ids = []
            for transform in pipeline.get("transform_refs", []):
                transform_id = _node_id("transform", transform.get("id") or transform.get("relation_id") or pipeline["id"])
                self._add_node(
                    {
                        "id": transform_id,
                        "type": "transform_step",
                        "ontology_class": "WorkbookTransformStep",
                        "label": transform.get("kind") or transform_id,
                        "status": status,
                        "sheet": pipeline.get("output_ref", {}).get("sheet"),
                        "range": pipeline.get("output_ref", {}).get("range"),
                        "properties": {
                            "kind": transform.get("kind"),
                            "relation_type": transform.get("relation_type"),
                            "formula_signature": transform.get("formula_signature"),
                            "formula_cell_count": transform.get("formula_cell_count"),
                            "reference_count": transform.get("reference_count"),
                        },
                        "evidence_refs": _evidence_refs(transform, _pipeline_evidence_refs(pipeline, validation)),
                        "source_artifact_refs": ["table_io_pipelines", "formula_patterns", "manifest"],
                    }
                )
                transform_node_ids.append(transform_id)
                self._add_relation(
                    {
                        "id": _relation_id("has_pipeline_transform", pipeline_node_id, transform_id),
                        "type": "has_pipeline_transform",
                        "from": pipeline_node_id,
                        "to": transform_id,
                        "status": status,
                        "properties": {"transform_kind": transform.get("kind")},
                        "evidence_refs": _evidence_refs(transform, _pipeline_evidence_refs(pipeline, validation)),
                        "source_artifact_refs": ["table_io_pipelines", "formula_patterns", "manifest"],
                    }
                )
            self._add_data_view(pipeline, validation, output_node_id, input_node_ids, transform_node_ids)

    def add_candidate_relations(self, block_candidates: dict[str, Any]) -> None:
        for sheet in block_candidates.get("sheets", []):
            for relation in sheet.get("relations", []):
                from_id = self._ensure_relation_endpoint(relation.get("from"), sheet.get("name"))
                to_id = self._ensure_relation_endpoint(relation.get("to"), sheet.get("name"))
                if not from_id or not to_id:
                    continue
                self._add_relation(
                    {
                        "id": _relation_id("candidate_relation", from_id, to_id, relation.get("id")),
                        "type": "candidate_relation",
                        "from": from_id,
                        "to": to_id,
                        "status": "candidate",
                        "properties": {
                            "candidate_relation_id": relation.get("id"),
                            "candidate_relation_type": relation.get("type"),
                            "reason": relation.get("reason"),
                            "confidence": relation.get("confidence"),
                            "metrics": relation.get("metrics", {}),
                        },
                        "evidence_refs": _evidence_refs(relation, [relation.get("id") or "block_candidates.relations"]),
                        "source_artifact_refs": ["block_candidates", "formula_patterns"],
                    }
                )

    def _ensure_ref_node(self, ref: dict[str, Any], status: str) -> str:
        for key in ("region_id", "block_id", "id"):
            value = ref.get(key)
            if value and value in self.original_to_node_id:
                return self.original_to_node_id[value]
        raw_id = ref.get("id") or f"{ref.get('sheet')}!{ref.get('range')}"
        node_id = _node_id("range", raw_id)
        self.original_to_node_id[str(raw_id)] = node_id
        self._add_node(
            {
                "id": node_id,
                "type": "range_ref",
                "ontology_class": _range_ref_ontology_class(ref),
                "label": ref.get("label") or raw_id,
                "status": status,
                "sheet": ref.get("sheet"),
                "range": ref.get("range"),
                "properties": {
                    "kind": ref.get("kind"),
                    "workbook": ref.get("workbook"),
                    "block_id": ref.get("block_id"),
                    "region_id": ref.get("region_id"),
                    "bounds": ref.get("bounds"),
                },
                "evidence_refs": [str(raw_id), "table_io_pipelines.refs"],
                "source_artifact_refs": ["table_io_pipelines"],
            }
        )
        return node_id

    def _ensure_relation_endpoint(self, endpoint: Any, sheet_name: str | None) -> str | None:
        if endpoint is None:
            return None
        endpoint_text = str(endpoint)
        if endpoint_text in self.original_to_node_id:
            return self.original_to_node_id[endpoint_text]
        if endpoint_text.startswith("range:"):
            node_id = _node_id("range", endpoint_text)
            if node_id not in self.nodes:
                self._add_node(
                    {
                        "id": node_id,
                        "type": "range_ref",
                        "ontology_class": "WorkbookRangeReference",
                        "label": endpoint_text.removeprefix("range:"),
                        "status": "candidate",
                        "sheet": _sheet_from_range_ref(endpoint_text) or sheet_name,
                        "range": _range_from_range_ref(endpoint_text),
                        "properties": {"kind": "workbook_range"},
                        "evidence_refs": [endpoint_text, "block_candidates.relations"],
                        "source_artifact_refs": ["block_candidates", "formula_patterns"],
                    }
                )
            return node_id
        return None

    def _ensure_review_or_decision_node(self, item: dict[str, Any]) -> str:
        node_id = _node_id("review", item["id"])
        if node_id not in self.nodes:
            self._add_node(
                {
                    "id": node_id,
                    "type": "review_item",
                    "ontology_class": "DocumentReviewItem",
                    "label": item.get("reason") or item["id"],
                    "status": item.get("status") or "review_required",
                    "sheet": item.get("sheet"),
                    "range": item.get("range"),
                    "properties": {
                        "item_id": item["id"],
                        "item_type": item.get("type"),
                        "reason": item.get("reason"),
                        "decision": item.get("decision"),
                    },
                    "evidence_refs": _evidence_refs(item, [item["id"]]),
                    "source_artifact_refs": ["boundary_decisions"],
                }
            )
        return node_id

    def _object_status(self, original_id: str, *, fallback: str) -> str:
        if original_id in self.status_index["accepted"]:
            return "accepted"
        if original_id in self.status_index["review_required"]:
            return "review_required"
        if original_id in self.status_index["rejected"]:
            return "rejected"
        return fallback

    def _add_node(self, node: dict[str, Any]) -> None:
        existing = self.nodes.get(node["id"])
        if existing is None:
            self.nodes[node["id"]] = node
            return
        existing["status"] = _merge_status(existing.get("status"), node.get("status"))
        existing["evidence_refs"] = sorted(
            set(existing.get("evidence_refs", [])) | set(node.get("evidence_refs", []))
        )
        existing["source_artifact_refs"] = sorted(
            set(existing.get("source_artifact_refs", []))
            | set(node.get("source_artifact_refs", []))
        )

    def _add_relation(self, relation: dict[str, Any]) -> None:
        existing = self.relations.get(relation["id"])
        if existing is None:
            self.relations[relation["id"]] = relation
            return
        existing["status"] = _merge_status(existing.get("status"), relation.get("status"))
        existing["evidence_refs"] = sorted(
            set(existing.get("evidence_refs", [])) | set(relation.get("evidence_refs", []))
        )
        existing["source_artifact_refs"] = sorted(
            set(existing.get("source_artifact_refs", []))
            | set(relation.get("source_artifact_refs", []))
        )

    def _add_data_view(
        self,
        pipeline: dict[str, Any],
        validation: dict[str, Any],
        output_node_id: str,
        input_node_ids: list[str],
        transform_node_ids: list[str],
    ) -> None:
        view_kind = _data_view_kind(pipeline, validation)
        status = validation.get("status") or pipeline.get("status") or "candidate"
        self.data_views[f"data_view:{pipeline['id']}"] = {
            "id": f"data_view:{pipeline['id']}",
            "type": "data_view",
            "view_kind": view_kind,
            "status": status,
            "role": validation.get("validated_role") or pipeline.get("role"),
            "pipeline_node_id": _node_id("pipeline", pipeline["id"]),
            "output_node_id": output_node_id,
            "input_node_ids": sorted(set(input_node_ids)),
            "transform_node_ids": sorted(set(transform_node_ids)),
            "sheet": pipeline.get("output_ref", {}).get("sheet"),
            "range": pipeline.get("output_ref", {}).get("range"),
            "properties": {
                "reason": validation.get("reason"),
                "confidence": validation.get("confidence", pipeline.get("confidence")),
                "review_flags": pipeline.get("review_flags", []),
                "input_ref_count": len(pipeline.get("input_refs", [])),
                "transform_ref_count": len(pipeline.get("transform_refs", [])),
            },
            "evidence_refs": _pipeline_evidence_refs(pipeline, validation),
            "source_artifact_refs": ["table_io_pipelines", "pipeline_role_validation"],
        }


def _source_artifacts(
    evidence_package_path: Path,
    evidence_package: dict[str, Any],
) -> dict[str, Path]:
    required = [
        "block_candidates",
        "table_io_pipelines",
        "gate_execution",
        "boundary_decisions",
        "pipeline_role_validation",
        "coordinate_normalization",
        "visual_features",
    ]
    source_artifacts = evidence_package.get("source_artifacts") or {}
    resolved: dict[str, Path] = {}
    for name in required:
        if name not in source_artifacts:
            raise ValueError(f"evidence package is missing source artifact: {name}")
    for name, path_text in source_artifacts.items():
        path = Path(path_text).expanduser()
        if not path.is_absolute():
            path = evidence_package_path.parent / path
        resolved[name] = path.resolve()
        if not resolved[name].exists():
            raise FileNotFoundError(f"missing source artifact {name}: {resolved[name]}")
    for name in required:
        if name not in resolved:
            raise ValueError(f"evidence package is missing source artifact: {name}")
    return resolved


def _build_status_index(
    *,
    gate_execution: dict[str, Any],
    boundary_decisions: dict[str, Any],
    pipeline_role_validation: dict[str, Any],
) -> dict[str, dict[str, str]]:
    status_index: dict[str, dict[str, str]] = {
        "accepted": {},
        "review_required": {},
        "rejected": {},
    }
    for result in gate_execution.get("gate_results", []):
        _index_status_refs(status_index, result, result.get("status"))
        target_original_id = _target_to_original_id(result.get("target_id"))
        if target_original_id:
            status_index[result.get("status", "review_required")][target_original_id] = result["id"]
    for decision in boundary_decisions.get("boundary_decisions", []):
        status = decision.get("status", "review_required")
        for region_id in decision.get("related_region_ids", []):
            status_index[status][region_id] = decision["id"]
    for validation in pipeline_role_validation.get("role_validations", []):
        status = validation.get("status", "review_required")
        output_ref = validation.get("output_ref", {})
        for key in ("id", "block_id", "region_id"):
            value = output_ref.get(key)
            if value:
                status_index[status][value] = validation["id"]
        status_index[status][validation["pipeline_id"]] = validation["id"]
    return status_index


def _index_status_refs(
    status_index: dict[str, dict[str, str]],
    item: dict[str, Any],
    status: str | None,
) -> None:
    if status not in status_index:
        return
    item_id = item.get("id")
    for ref in item.get("evidence_refs", []) + item.get("deterministic_inputs", []):
        if isinstance(ref, str):
            status_index[status][ref] = item_id


def _ontology_review_queue(
    evidence_package: dict[str, Any],
    original_to_node_id: dict[str, str],
) -> list[dict[str, Any]]:
    queue = []
    for item in evidence_package.get("review_queue", []):
        target_id = (
            original_to_node_id.get(item.get("id") or "")
            or original_to_node_id.get(_target_to_original_id(item.get("id")) or "")
        )
        queue.append(
            {
                "id": item["id"],
                "kind": item.get("kind"),
                "status": item.get("status") or "review_required",
                "reason": item.get("reason"),
                "sheet": item.get("sheet"),
                "range": item.get("range"),
                "target_node_id": target_id,
                "evidence_refs": item.get("evidence_refs", []),
            }
        )
    return queue


def _block_default_status(block: dict[str, Any]) -> str:
    if block.get("type") in {"image", "pivot_table"}:
        return "accepted"
    return "candidate"


def _block_ontology_class(block: dict[str, Any]) -> str:
    block_type = block.get("type")
    if block_type == "image":
        return "ImageBlock"
    if block_type == "pivot_table":
        return "PivotTableBlock"
    if block_type == "row_band":
        return "RowBandBlock"
    return "DocumentBlock"


def _region_ontology_class(region: dict[str, Any]) -> str:
    subtype = region.get("subtype")
    if subtype == "text_or_label_region":
        return "TextRegion"
    if subtype == "pivot_table_value_region":
        return "PivotTableValueRegion"
    return "CellRegion"


def _range_ref_ontology_class(ref: dict[str, Any]) -> str:
    if ref.get("kind") == "pivot_table":
        return "PivotTableRangeReference"
    if ref.get("kind") == "cell_region":
        return "CellRegionReference"
    return "WorkbookRangeReference"


def _visual_status(feature: dict[str, Any]) -> str:
    status = feature.get("status")
    if status in {"detected", "detected_with_view_state_warning"}:
        return "accepted"
    return "review_required"


def _data_view_kind(pipeline: dict[str, Any], validation: dict[str, Any]) -> str:
    role = validation.get("validated_role") or pipeline.get("role")
    output_kind = pipeline.get("output_ref", {}).get("kind")
    transform_kinds = {item.get("kind") for item in pipeline.get("transform_refs", [])}
    if output_kind == "pivot_table" or "pivot_cache" in transform_kinds:
        return "pivot_report_view"
    if role == "summary":
        return "formula_summary_view"
    if role == "transform":
        return "formula_transform_view"
    return "table_pipeline_view"


def _target_to_original_id(target_id: Any) -> str | None:
    if not isinstance(target_id, str):
        return None
    if target_id.startswith("target_"):
        return target_id.removeprefix("target_")
    return None


def _sheet_from_range_ref(range_ref: str) -> str | None:
    if not range_ref.startswith("range:") or "!" not in range_ref:
        return None
    return range_ref.removeprefix("range:").split("!", 1)[0]


def _range_from_range_ref(range_ref: str) -> str | None:
    if not range_ref.startswith("range:") or "!" not in range_ref:
        return None
    return range_ref.split("!", 1)[1]


def _bounds_to_range(bounds: dict[str, Any] | None) -> str | None:
    if not bounds:
        return None
    start = bounds.get("start_cell")
    end = bounds.get("end_cell")
    if start and end:
        return f"{start}:{end}"
    return None


def _pipeline_evidence_refs(
    pipeline: dict[str, Any],
    validation: dict[str, Any],
) -> list[str]:
    refs = set(pipeline.get("evidence_refs", []))
    refs.add(pipeline["id"])
    refs.update(validation.get("evidence_refs", []))
    if validation.get("id"):
        refs.add(validation["id"])
    return sorted(str(ref) for ref in refs if ref)


def _evidence_refs(item: dict[str, Any], fallback: list[str]) -> list[str]:
    refs = set(str(ref) for ref in item.get("evidence_refs", []) if ref)
    for ref in item.get("evidence", []):
        if ref:
            refs.add(str(ref))
    for ref in fallback:
        if ref:
            refs.add(str(ref))
    if item.get("id"):
        refs.add(str(item["id"]))
    return sorted(refs)


def _node_id(kind: str, raw_id: Any) -> str:
    return f"{kind}:{raw_id}"


def _relation_id(relation_type: str, from_id: Any, to_id: Any, extra: Any | None = None) -> str:
    parts = [relation_type, str(from_id), str(to_id)]
    if extra:
        parts.append(str(extra))
    return "rel:" + "|".join(parts)


def _merge_status(current: str | None, new: str | None) -> str:
    order = {
        "rejected": 4,
        "review_required": 3,
        "accepted": 2,
        "candidate": 1,
        None: 0,
    }
    return current if order.get(current, 0) >= order.get(new, 0) else str(new)


def _assert_no_dangling_relations(
    nodes: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> None:
    node_ids = {node["id"] for node in nodes}
    dangling = [
        relation["id"]
        for relation in relations
        if relation["from"] not in node_ids or relation["to"] not in node_ids
    ]
    if dangling:
        raise ValueError(f"document ontology mapping has dangling relations: {dangling[:5]}")


def _assert_evidence_refs(
    nodes: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    data_views: list[dict[str, Any]],
) -> None:
    missing = []
    for collection_name, items in (
        ("nodes", nodes),
        ("relations", relations),
        ("data_views", data_views),
    ):
        for item in items:
            if item.get("status") == "accepted" and not item.get("evidence_refs"):
                missing.append(f"{collection_name}:{item.get('id')}")
    if missing:
        raise ValueError(f"accepted ontology items are missing evidence refs: {missing[:5]}")


def _summary(
    nodes: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    data_views: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
) -> dict[str, int]:
    node_types = Counter(node["type"] for node in nodes)
    relation_types = Counter(relation["type"] for relation in relations)
    statuses = Counter(node["status"] for node in nodes)
    view_statuses = Counter(view["status"] for view in data_views)
    return {
        "node_count": len(nodes),
        "relation_count": len(relations),
        "data_view_count": len(data_views),
        "review_queue_count": len(review_queue),
        "sheet_node_count": node_types.get("sheet", 0),
        "block_node_count": node_types.get("document_block", 0),
        "cell_region_node_count": node_types.get("cell_region", 0),
        "pipeline_node_count": node_types.get("data_pipeline", 0),
        "transform_step_node_count": node_types.get("transform_step", 0),
        "visual_evidence_node_count": node_types.get("visual_evidence", 0),
        "range_ref_node_count": node_types.get("range_ref", 0),
        "accepted_node_count": statuses.get("accepted", 0),
        "review_required_node_count": statuses.get("review_required", 0),
        "candidate_node_count": statuses.get("candidate", 0),
        "accepted_data_view_count": view_statuses.get("accepted", 0),
        "review_required_data_view_count": view_statuses.get("review_required", 0),
        "contains_relation_count": relation_types.get("contains", 0),
        "derived_from_relation_count": relation_types.get("derived_from", 0),
    }


def _parser_observations(
    nodes: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    data_views: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": "Document ontology mapping is a deterministic projection over the evidence package; no semantic ontology concepts were generated.",
        },
        {
            "level": "info",
            "message": "Pivot tables remain pivot report views backed by pivot cache/source evidence, not raw data tables.",
        },
    ]
    if review_queue:
        observations.append(
            {
                "level": "warning",
                "message": f"{len(review_queue)} unresolved evidence items remain attached to ontology review items.",
            }
        )
    if any(view["status"] == "review_required" for view in data_views):
        observations.append(
            {
                "level": "warning",
                "message": "At least one data view remains review-required because its input ownership or validation evidence is incomplete.",
            }
        )
    if not relations:
        observations.append(
            {"level": "warning", "message": "No ontology relations were produced."}
        )
    return observations


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Map workbook evidence package artifacts to the document-structure ontology."
    )
    parser.add_argument("--evidence-package", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    mapping = build_document_ontology_mapping(args.evidence_package)
    payload = json.dumps(mapping, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
