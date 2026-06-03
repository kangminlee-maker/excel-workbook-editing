from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_document_ontology_mapping import build_document_ontology_mapping  # noqa: E402


class WorkbookDocumentOntologyMappingTest(unittest.TestCase):
    def test_maps_evidence_package_to_document_structure_ontology(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            evidence_path = _write_fixture(root)

            mapping = build_document_ontology_mapping(evidence_path)

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "workbook-document-ontology-mapping.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(mapping)

        self.assertFalse(mapping["ontology"]["generated_semantic_ontology"])
        self.assertEqual(mapping["method"]["ontology_use"], "document_structure_ontology_application")
        self.assertGreaterEqual(mapping["summary"]["sheet_node_count"], 1)
        self.assertGreaterEqual(mapping["summary"]["block_node_count"], 2)
        self.assertEqual(mapping["summary"]["data_view_count"], 2)

        nodes = {node["id"]: node for node in mapping["nodes"]}
        self.assertEqual(nodes["block:pivot_block"]["status"], "accepted")
        self.assertEqual(nodes["region:region_summary"]["status"], "accepted")
        self.assertEqual(nodes["pipeline:pipeline_unresolved"]["status"], "review_required")

        data_views = {view["id"]: view for view in mapping["data_views"]}
        self.assertEqual(data_views["data_view:pipeline_pivot"]["view_kind"], "pivot_report_view")
        self.assertEqual(data_views["data_view:pipeline_pivot"]["status"], "accepted")
        self.assertEqual(
            data_views["data_view:pipeline_unresolved"]["status"],
            "review_required",
        )

        relation_node_ids = set(nodes)
        for relation in mapping["relations"]:
            self.assertIn(relation["from"], relation_node_ids)
            self.assertIn(relation["to"], relation_node_ids)
        self.assertTrue(
            any(relation["type"] == "derived_from" for relation in mapping["relations"])
        )


def _write_fixture(root: Path) -> Path:
    paths = {
        "block_candidates": root / "block-candidates.json",
        "table_io_pipelines": root / "table-io-pipelines.json",
        "gate_execution": root / "gate-execution.json",
        "boundary_decisions": root / "boundary-decisions.json",
        "pipeline_role_validation": root / "pipeline-role-validation.json",
        "coordinate_normalization": root / "coordinate-normalization.json",
        "visual_features": root / "visual-features.json",
    }
    for name, path in paths.items():
        path.write_text(json.dumps(_artifact(name), ensure_ascii=False), encoding="utf-8")

    evidence_path = root / "evidence-package.json"
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "package_kind": "artifact_assembled_workbook_understanding",
                "source": {
                    "path": str(root / "source.xlsx"),
                    "file_name": "source.xlsx",
                    "sha256": "0" * 64,
                },
                "source_artifacts": {
                    name: str(path)
                    for name, path in paths.items()
                },
                "sheets": [
                    {
                        "name": "Report",
                        "index": 0,
                        "sheet_state": "visible",
                        "dimensions": "A1:D20",
                        "grid_bounds": {
                            "min_row": 1,
                            "min_column": 1,
                            "max_row": 20,
                            "max_column": 4,
                        },
                        "freeze_panes": None,
                        "auto_filter_ref": None,
                    }
                ],
                "review_queue": [
                    {
                        "id": "role_validation_pipeline_unresolved",
                        "kind": "pipeline_role_validation",
                        "status": "review_required",
                        "reason": "unresolved_input_region",
                        "sheet": "Report",
                        "range": "C1:D5",
                        "evidence_refs": ["pipeline_unresolved"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return evidence_path


def _artifact(name: str) -> dict:
    if name == "block_candidates":
        return {
            "sheets": [
                {
                    "name": "Report",
                    "blocks": [
                        _block("row_band_1", "row_band", "A1:D20"),
                        _block("pivot_block", "pivot_table", "A1:B5"),
                    ],
                    "cell_regions": [
                        _region("region_raw", "row_band_1", "A1:B20"),
                        _region("region_summary", "row_band_1", "C1:D5"),
                    ],
                    "relations": [
                        {
                            "id": "rel_region_summary_region_raw",
                            "type": "formula_references",
                            "from": "region_summary",
                            "to": "region_raw",
                            "reason": "Fixture relation",
                            "confidence": 0.8,
                            "evidence_refs": ["formula_group"],
                        }
                    ],
                }
            ]
        }
    if name == "table_io_pipelines":
        return {
            "pipelines": [
                {
                    "id": "pipeline_pivot",
                    "status": "candidate",
                    "role": "report",
                    "output_ref": _ref("pivot_block", "pivot_table", "Report", "A1:B5", None, "pivot_block"),
                    "input_refs": [_ref("region_raw", "cell_region", "Report", "A1:B20", "region_raw", "row_band_1")],
                    "transform_refs": [
                        {
                            "id": "pivot_transform",
                            "kind": "pivot_cache",
                            "relation_type": "derived_from_pivot_cache_source",
                            "evidence": ["pivot_cache_source"],
                        }
                    ],
                    "evidence_refs": ["pivot_relation"],
                    "review_flags": ["pivot_cache_dependency"],
                },
                {
                    "id": "pipeline_unresolved",
                    "status": "candidate",
                    "role": "transform",
                    "output_ref": _ref("region_summary", "cell_region", "Report", "C1:D5", "region_summary", "row_band_1"),
                    "input_refs": [_ref("unmapped_range", "workbook_range", "Report", "Z1:Z5", None, None)],
                    "transform_refs": [
                        {
                            "id": "formula_transform",
                            "kind": "formula_signature_group",
                            "formula_signature": "A1+1",
                            "formula_cell_count": 2,
                            "evidence": ["formula_group"],
                        }
                    ],
                    "evidence_refs": ["formula_relation"],
                    "review_flags": ["unresolved_input_region"],
                },
            ]
        }
    if name == "gate_execution":
        return {
            "gate_results": [
                {
                    "id": "gate_region_summary",
                    "status": "accepted",
                    "target_id": "target_region_summary",
                    "deterministic_inputs": ["pipeline_unresolved"],
                    "evidence_refs": ["region_summary"],
                }
            ]
        }
    if name == "boundary_decisions":
        return {
            "boundary_decisions": [
                {
                    "id": "boundary_region_summary",
                    "type": "document_boundary_decision",
                    "status": "accepted",
                    "decision": "create_graph_boundary",
                    "reason": "blank_column_boundary",
                    "boundary_kind": "split_boundary",
                    "graph_effect": "graph_boundary_created",
                    "related_region_ids": ["region_summary"],
                    "evidence_refs": ["split_candidate"],
                }
            ]
        }
    if name == "pipeline_role_validation":
        return {
            "role_validations": [
                _role_validation("pipeline_pivot", "accepted", "pivot_block", None, "pivot_table", "report"),
                _role_validation("pipeline_unresolved", "review_required", "region_summary", "region_summary", "cell_region", "transform"),
            ]
        }
    if name == "coordinate_normalization":
        return {
            "coordinate_mappings": [
                {
                    "id": "coord_region_summary",
                    "target_id": "target_region_summary",
                    "status": "normalized_visible_range",
                }
            ]
        }
    if name == "visual_features":
        return {
            "feature_results": [
                {
                    "id": "features_region_summary",
                    "status": "detected",
                    "mapping_id": "coord_region_summary",
                    "capture_id": "capture_region_summary",
                    "target_id": "target_region_summary",
                    "sheet": "Report",
                    "cell_range": "C1:D5",
                    "quality_status": "usable",
                    "normalization_status": "normalized_visible_range",
                    "view_state_classification": "no_material_view_state_signal",
                    "layout_signals": ["grid_or_table_line_structure"],
                    "evidence_refs": ["coord_region_summary"],
                }
            ]
        }
    raise AssertionError(f"unknown artifact {name}")


def _block(block_id: str, block_type: str, range_text: str) -> dict:
    start, end = range_text.split(":")
    return {
        "id": block_id,
        "type": block_type,
        "subtype": block_type,
        "label": block_id,
        "bounds": {
            "start_cell": start,
            "end_cell": end,
        },
        "metrics": {},
        "evidence": ["manifest"],
        "confidence": 1.0,
    }


def _region(region_id: str, parent_id: str, range_text: str) -> dict:
    start, end = range_text.split(":")
    return {
        "id": region_id,
        "type": "cell_region",
        "subtype": "table_region_candidate",
        "parent_seed_block_id": parent_id,
        "label": region_id,
        "bounds": {
            "start_cell": start,
            "end_cell": end,
        },
        "metrics": {},
        "evidence": ["readonly_sample.windows"],
        "confidence": 0.8,
    }


def _ref(
    ref_id: str,
    kind: str,
    sheet: str,
    range_text: str,
    region_id: str | None,
    block_id: str | None,
) -> dict:
    return {
        "id": ref_id,
        "kind": kind,
        "sheet": sheet,
        "range": range_text,
        "region_id": region_id,
        "block_id": block_id,
    }


def _role_validation(
    pipeline_id: str,
    status: str,
    output_id: str,
    region_id: str | None,
    kind: str,
    role: str,
) -> dict:
    return {
        "id": f"role_validation_{pipeline_id}",
        "pipeline_id": pipeline_id,
        "status": status,
        "reason": "fixture",
        "validated_role": role if status == "accepted" else None,
        "output_ref": {
            "id": output_id,
            "kind": kind,
            "sheet": "Report",
            "range": "A1:B5",
            "block_id": output_id if kind == "pivot_table" else "row_band_1",
            "region_id": region_id,
        },
        "evidence_refs": [pipeline_id],
    }


if __name__ == "__main__":
    unittest.main()
