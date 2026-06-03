from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_workbook_understanding_viewer import build_viewer  # noqa: E402


class WorkbookUnderstandingViewerTest(unittest.TestCase):
    def test_builds_static_html_viewer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest_path = root / "manifest.json"
            sample_path = root / "sample.json"
            candidates_path = root / "candidates.json"
            table_io_path = root / "table-io.json"
            cross_validation_path = root / "cross-validation.json"
            render_captures_path = root / "render-captures.json"
            capture_quality_path = root / "capture-quality.json"
            recapture_candidate_plan_path = root / "recapture-candidates.json"
            recapture_candidate_captures_path = root / "recapture-captures.json"
            recapture_candidate_quality_path = root / "recapture-quality.json"
            view_state_preflight_path = root / "view-state-preflight.json"
            view_state_profile_path = root / "view-state-profile.json"
            coordinate_normalization_path = root / "coordinate-normalization.json"
            visual_features_path = root / "visual-features.json"
            gate_execution_path = root / "gate-execution.json"
            shared_alignment_path = root / "shared-alignment.json"
            process_redesign_path = root / "process-redesign.json"
            onto_seed_summary_path = root / "onto-seed-summary.json"
            output_path = root / "index.html"
            manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
            sample_path.write_text(json.dumps(_sample()), encoding="utf-8")
            candidates_path.write_text(json.dumps(_candidates()), encoding="utf-8")
            table_io_path.write_text(json.dumps(_table_io_pipelines()), encoding="utf-8")
            cross_validation_path.write_text(
                json.dumps(_cross_validation_plan()),
                encoding="utf-8",
            )
            render_captures_path.write_text(
                json.dumps(_render_captures(root)),
                encoding="utf-8",
            )
            capture_quality_path.write_text(
                json.dumps(_capture_quality(root)),
                encoding="utf-8",
            )
            recapture_candidate_plan_path.write_text(
                json.dumps(_recapture_candidate_plan()),
                encoding="utf-8",
            )
            recapture_candidate_captures_path.write_text(
                json.dumps(_render_captures(root)),
                encoding="utf-8",
            )
            recapture_candidate_quality_path.write_text(
                json.dumps(_capture_quality(root)),
                encoding="utf-8",
            )
            view_state_preflight_path.write_text(
                json.dumps(_view_state_profile()),
                encoding="utf-8",
            )
            view_state_profile_path.write_text(
                json.dumps(_view_state_profile()),
                encoding="utf-8",
            )
            coordinate_normalization_path.write_text(
                json.dumps(_coordinate_normalization()),
                encoding="utf-8",
            )
            visual_features_path.write_text(
                json.dumps(_visual_features()),
                encoding="utf-8",
            )
            gate_execution_path.write_text(
                json.dumps(_gate_execution()),
                encoding="utf-8",
            )
            shared_alignment_path.write_text(
                json.dumps(_shared_alignment_review()),
                encoding="utf-8",
            )
            process_redesign_path.write_text(
                json.dumps(_process_redesign_review()),
                encoding="utf-8",
            )
            onto_seed_summary_path.write_text(
                json.dumps(_onto_seed_summary()),
                encoding="utf-8",
            )

            build_viewer(
                manifest_path,
                sample_path,
                candidates_path,
                output_path,
                table_io_pipelines_path=table_io_path,
                cross_validation_plan_path=cross_validation_path,
                render_captures_path=render_captures_path,
                capture_quality_path=capture_quality_path,
                recapture_candidate_plan_path=recapture_candidate_plan_path,
                recapture_candidate_captures_path=recapture_candidate_captures_path,
                recapture_candidate_quality_path=recapture_candidate_quality_path,
                view_state_preflight_path=view_state_preflight_path,
                view_state_profile_path=view_state_profile_path,
                coordinate_normalization_path=coordinate_normalization_path,
                visual_features_path=visual_features_path,
                gate_execution_path=gate_execution_path,
                shared_ontology_alignment_review_path=shared_alignment_path,
                process_redesign_review_path=process_redesign_path,
                onto_reconstruct_seed_min_summary_path=onto_seed_summary_path,
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Workbook Understanding Viewer", html)
        self.assertIn("Fast ZIP/XML Manifest", html)
        self.assertIn("Read-only Targeted Row Sampling", html)
        self.assertIn("Document Block Candidates", html)
        self.assertIn("Table I/O Pipelines", html)
        self.assertIn("Data Input/Output Pipeline Graph", html)
        self.assertIn("flowchart LR", html)
        self.assertIn("summary/formula_signature_group", html)
        self.assertIn("Cross-Validation Plan", html)
        self.assertIn("Render Captures", html)
        self.assertIn("Capture Quality", html)
        self.assertIn("recapture_with_tiling", html)
        self.assertIn("Recapture Candidates", html)
        self.assertIn("visible_row_context", html)
        self.assertIn("Recapture Candidate Results", html)
        self.assertIn("View-State Preflight", html)
        self.assertIn("Hidden Row / View-State", html)
        self.assertIn("filtered_or_hidden_rows_explain_capture_failure", html)
        self.assertIn("Coordinate Normalization", html)
        self.assertIn("normalized_visible_range", html)
        self.assertIn("Visual Feature Detection", html)
        self.assertIn("grid_or_table_line_structure", html)
        self.assertIn("Cross-Validation Gate Execution", html)
        self.assertIn("deterministic_visual_evidence_available", html)
        self.assertIn("Shared Ontology Alignment / Human Review", html)
        self.assertIn("review_only_no_shared_promotion", html)
        self.assertIn("gaap_ifrs_basis_mapping_required", html)
        self.assertIn("Process Redesign Review", html)
        self.assertIn("process_redesign_review_completed", html)
        self.assertIn("Onto Seed Prompt / Timeout Mitigation", html)
        self.assertIn("not action-ready", html)
        self.assertIn("metric equivalence unresolved", html)
        self.assertIn("Visual Map", html)


def _manifest() -> dict:
    return {
        "source": {"file_name": "sample.xlsx", "path": "/tmp/sample.xlsx"},
        "summary": {"sheet_count": 1, "package_media_count": 1},
        "parser_observations": [],
        "workbook": {
            "sheets": [
                {
                    "index": 0,
                    "name": "Sheet1",
                    "dimension": "A1:E5",
                    "detail_status": "scanned",
                    "entry_size_bytes": 100,
                    "counts": {"cell_elements": 4, "formula_elements": 1},
                    "drawing_objects": [{"id": "image1"}],
                }
            ]
        },
    }


def _sample() -> dict:
    return {
        "summary": {"sheet_count": 1, "sampled_row_count": 2},
        "sheets": [
            {
                "name": "Sheet1",
                "max_row": 5,
                "max_column": 5,
                "sample_seconds": 0.01,
                "windows": [
                    {
                        "start_row": 1,
                        "end_row": 2,
                        "non_empty_cell_count": 2,
                        "formula_cell_count": 1,
                        "rows": [
                            {
                                "row": 1,
                                "non_empty_count": 1,
                                "formula_count": 0,
                                "cells": [
                                    {
                                        "value_preview": "Header",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }


def _candidates() -> dict:
    return {
        "summary": {
            "sheet_count": 1,
            "block_count": 2,
            "image_block_count": 1,
            "row_band_count": 1,
            "relation_count": 1,
        },
        "sheets": [
            {
                "name": "Sheet1",
                "blocks": [
                    {
                        "id": "img",
                        "type": "image",
                        "subtype": "image_anchor",
                        "label": "Picture",
                        "bounds": {
                            "start_row": 1,
                            "end_row": 3,
                            "start_column": 3,
                            "end_column": 5,
                        },
                        "confidence": 1,
                        "preview": ["Picture"],
                    },
                    {
                        "id": "band",
                        "type": "row_band",
                        "subtype": "table_candidate",
                        "label": "Header",
                        "bounds": {
                            "start_row": 1,
                            "end_row": 2,
                            "start_column": 1,
                            "end_column": 2,
                        },
                        "confidence": 0.7,
                        "preview": ["R1: Header"],
                    },
                ],
                "relations": [
                    {
                        "type": "adjacent_left_of",
                        "from": "band",
                        "to": "img",
                        "confidence": 0.8,
                        "reason": "near",
                    }
                ],
            }
        ],
    }


def _table_io_pipelines() -> dict:
    return {
        "summary": {
            "pipeline_count": 1,
            "formula_pipeline_count": 1,
            "pivot_pipeline_count": 0,
            "external_dependency_pipeline_count": 0,
            "unresolved_input_pipeline_count": 0,
            "summary_role_count": 1,
            "bridge_role_count": 0,
            "report_role_count": 0,
        },
        "pipelines": [
            {
                "id": "pipeline_summary",
                "type": "table_io_pipeline",
                "status": "candidate",
                "role": "summary",
                "output_ref": {
                    "id": "band",
                    "kind": "row_band",
                    "workbook": None,
                    "sheet": "Sheet1",
                    "range": "A1:B2",
                    "block_id": "band",
                    "region_id": None,
                    "bounds": {
                        "min_row": 1,
                        "min_column": 1,
                        "max_row": 2,
                        "max_column": 2,
                    },
                    "label": "Summary",
                },
                "input_refs": [
                    {
                        "id": "raw",
                        "kind": "cell_region",
                        "workbook": None,
                        "sheet": "Raw",
                        "range": "A1:B10",
                        "block_id": "raw",
                        "region_id": "raw",
                        "bounds": {
                            "min_row": 1,
                            "min_column": 1,
                            "max_row": 10,
                            "max_column": 2,
                        },
                        "label": "Raw Detail",
                    }
                ],
                "transform_refs": [
                    {
                        "id": "group1",
                        "kind": "formula_signature_group",
                        "relation_group_id": "group1",
                        "relation_id": None,
                        "relation_type": "formula_references",
                        "formula_signature": "SUMIFS(Raw!$B:$B,Raw!$A:$A,A1)",
                        "formula_cell_count": 2,
                        "reference_count": 1,
                        "evidence": ["formula_signature_group"],
                    }
                ],
                "evidence_refs": ["group1"],
                "confidence": 0.7,
                "review_flags": [],
            }
        ],
    }


def _cross_validation_plan() -> dict:
    return {
        "summary": {
            "capture_target_count": 1,
            "high_priority_count": 1,
            "medium_priority_count": 0,
            "low_priority_count": 0,
            "sheet_count": 1,
            "pipeline_target_count": 1,
            "pivot_report_target_count": 0,
            "unresolved_input_target_count": 1,
            "boundary_target_count": 0,
            "image_hierarchy_target_count": 0,
            "gate_check_count": 1,
            "recommended_first_batch_count": 1,
        },
        "recommended_first_batch_target_ids": ["target_summary"],
        "capture_targets": [
            {
                "id": "target_summary",
                "type": "visual_formula_validation_target",
                "target_type": "pipeline_output",
                "status": "candidate",
                "priority": "high",
                "score": 90,
                "sheet": "Sheet1",
                "range": "A1:B2",
                "bounds": {
                    "min_row": 1,
                    "min_column": 1,
                    "max_row": 2,
                    "max_column": 2,
                },
                "capture_window": {
                    "sheet": "Sheet1",
                    "range": "A1:C4",
                    "bounds": {
                        "min_row": 1,
                        "min_column": 1,
                        "max_row": 4,
                        "max_column": 3,
                    },
                    "authority": "excel_render_capture",
                    "coordinate_systems": [
                        "cell_range",
                        "grid_coordinate",
                        "capture_bbox",
                    ],
                },
                "target_ref": {
                    "id": "band",
                    "kind": "row_band",
                    "workbook": None,
                    "sheet": "Sheet1",
                    "range": "A1:B2",
                    "block_id": "band",
                    "region_id": None,
                    "bounds": {
                        "min_row": 1,
                        "min_column": 1,
                        "max_row": 2,
                        "max_column": 2,
                    },
                    "label": "Summary",
                },
                "related_pipeline_ids": ["pipeline_summary"],
                "related_block_ids": ["band"],
                "related_region_ids": [],
                "related_boundary_gate_ids": [],
                "reasons": ["unresolved_input_region"],
                "gate_checks": [
                    {
                        "id": "gate_target_summary_unresolved",
                        "type": "visual_formula_gate_check",
                        "target_id": "target_summary",
                        "gate_type": "unresolved_input_region_resolution",
                        "status": "pending_capture",
                        "deterministic_inputs": ["pipeline_summary"],
                        "pass_conditions": ["input is mapped"],
                        "failure_signals": ["input remains unmapped"],
                    }
                ],
                "review_questions": ["input owner?"],
                "evidence_refs": ["pipeline_summary"],
            }
        ],
    }


def _render_captures(root: Path) -> dict:
    image_path = root / "captures" / "capture.png"
    image_path.parent.mkdir(exist_ok=True)
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89"
    )
    return {
        "summary": {
            "selected_target_count": 1,
            "captured_count": 1,
            "failed_count": 0,
            "png_count": 1,
            "gate_result_count": 1,
            "captured_pending_review_gate_count": 1,
            "capture_failed_gate_count": 0,
        },
        "captures": [
            {
                "id": "capture_target_summary",
                "type": "render_capture",
                "status": "captured",
                "target_id": "target_summary",
                "sheet": "Sheet1",
                "requested_range": "A1:B2",
                "capture_window": {"sheet": "Sheet1", "range": "A1:C4"},
                "target_ref": {"id": "band"},
                "output": {
                    "pdf_path": None,
                    "png_path": str(image_path),
                    "pdf_size_bytes": None,
                    "png_size_bytes": 32,
                    "png_width": 1,
                    "png_height": 1,
                },
                "coordinate_map": {
                    "status": "range_image_only",
                    "cell_range": "A1:C4",
                    "capture_bbox": {"x": 0, "y": 0, "width": 1, "height": 1},
                },
                "gate_results": [
                    {
                        "id": "result_gate",
                        "type": "visual_formula_gate_result",
                        "capture_id": "capture_target_summary",
                        "target_id": "target_summary",
                        "gate_check_id": "gate",
                        "gate_type": "boundary_confirmation",
                        "status": "captured_pending_review",
                        "evidence_refs": ["capture_target_summary"],
                        "notes": "Captured.",
                    }
                ],
                "parser_observations": [],
            }
        ],
    }


def _capture_quality(root: Path) -> dict:
    image_path = root / "captures" / "capture.png"
    return {
        "schema_version": "0.1",
        "generated_at": "2026-06-01T00:00:00Z",
        "source_artifacts": {"render_captures": "/tmp/render-captures.json"},
        "method": {
            "name": "deterministic_png_capture_quality",
            "thresholds": {"min_height_px_fail": 50},
        },
        "quality_results": [
            {
                "id": "quality_capture_target_summary",
                "type": "capture_quality_result",
                "status": "recapture_required",
                "capture_id": "capture_target_summary",
                "target_id": "target_summary",
                "sheet": "Sheet1",
                "requested_range": "A1:B2",
                "capture_window_range": "A1:C4",
                "png_path": str(image_path),
                "dimensions": {
                    "width": 1,
                    "height": 1,
                    "size_bytes": 32,
                },
                "range_shape": {
                    "status": "parsed",
                    "min_row": 1,
                    "min_column": 1,
                    "max_row": 4,
                    "max_column": 3,
                    "row_count": 4,
                    "column_count": 3,
                },
                "metrics": {
                    "aspect_ratio": 1,
                    "pixels_per_row": 0.25,
                    "pixels_per_column": 0.33,
                    "visible_pixel_ratio": 0.5,
                    "alpha_coverage_ratio": 1,
                },
                "checks": [
                    {
                        "id": "pixels_per_row",
                        "type": "capture_quality_check",
                        "status": "fail",
                        "severity": "error",
                        "message": "Rows need more pixels.",
                    }
                ],
                "recommendations": ["recapture_with_tiling"],
                "evidence_refs": ["capture_target_summary"],
                "notes": "recapture_required: pixels_per_row",
            }
        ],
        "summary": {
            "capture_count": 1,
            "evaluated_count": 1,
            "usable_count": 0,
            "review_required_count": 0,
            "recapture_required_count": 1,
            "capture_failed_count": 0,
            "too_thin_count": 1,
            "low_row_pixels_count": 1,
            "extreme_aspect_count": 0,
            "low_visible_content_count": 0,
            "tiling_recommended_count": 1,
            "expanded_window_recommended_count": 0,
        },
        "parser_observations": [],
    }


def _recapture_candidate_plan() -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-06-01T00:00:00Z",
        "source_artifacts": {
            "render_captures": "/tmp/render-captures.json",
            "capture_quality": "/tmp/capture-quality.json",
        },
        "method": {
            "name": "recapture_candidate_generation",
            "max_columns_per_tile": 18,
            "visible_context_rows": 80,
            "expanded_context_rows": 80,
            "authority": "candidate_generation_not_final_selection",
        },
        "candidate_groups": [
            {
                "source_capture_id": "capture_target_summary",
                "source_quality_result_id": "quality_capture_target_summary",
                "source_quality_status": "recapture_required",
                "sheet": "Sheet1",
                "source_range": "A1:C4",
                "recommendations": ["recapture_with_visible_row_context"],
                "candidate_target_ids": ["candidate_summary_visible"],
            }
        ],
        "capture_targets": [
            {
                "id": "candidate_summary_visible",
                "type": "visual_formula_validation_target",
                "target_type": "recapture_candidate",
                "status": "candidate",
                "priority": "high",
                "score": 95,
                "sheet": "Sheet1",
                "range": "A5:C84",
                "bounds": {
                    "min_row": 5,
                    "min_column": 1,
                    "max_row": 84,
                    "max_column": 3,
                },
                "capture_window": {
                    "sheet": "Sheet1",
                    "range": "A5:C84",
                    "bounds": {
                        "min_row": 5,
                        "min_column": 1,
                        "max_row": 84,
                        "max_column": 3,
                    },
                    "authority": "excel_render_capture",
                    "coordinate_systems": [
                        "cell_range",
                        "grid_coordinate",
                        "capture_bbox",
                    ],
                },
                "target_ref": {"id": "band"},
                "source_capture_id": "capture_target_summary",
                "source_quality_result_id": "quality_capture_target_summary",
                "source_quality_status": "recapture_required",
                "candidate_strategy": "visible_row_context",
                "candidate_rationale": "Shift to likely visible rows.",
                "tile_index": 1,
                "tile_count": 1,
                "related_pipeline_ids": [],
                "related_block_ids": [],
                "related_region_ids": [],
                "related_boundary_gate_ids": [],
                "reasons": ["recapture_required"],
                "gate_checks": [],
                "review_questions": ["better?"],
                "evidence_refs": ["capture_target_summary"],
            }
        ],
        "recommended_first_batch_target_ids": ["candidate_summary_visible"],
        "summary": {
            "source_capture_count": 1,
            "candidate_target_count": 1,
            "high_priority_count": 1,
            "medium_priority_count": 0,
            "same_window_control_count": 0,
            "expanded_row_context_count": 0,
            "visible_row_context_count": 1,
            "visible_row_context_tile_count": 0,
            "column_tile_count": 0,
            "sheet_count": 1,
            "gate_check_count": 0,
            "recommended_first_batch_count": 1,
        },
        "parser_observations": [],
    }


def _view_state_profile() -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-06-01T00:00:00Z",
        "source_artifacts": {
            "manifest": "/tmp/manifest.json",
            "capture_quality_files": ["/tmp/capture-quality.json"],
        },
        "source": {"path": "/tmp/sample.xlsx", "file_name": "sample.xlsx"},
        "limits": {"max_sheet_xml_bytes": 100000000},
        "method": {
            "name": "deterministic_workbook_view_state_profile",
            "authority": "workbook_xml_view_state_evidence_not_semantic_truth",
            "decision_boundary": "hidden rows explain render behavior only",
        },
        "sheets": [
            {
                "name": "Sheet1",
                "entry": "xl/worksheets/sheet1.xml",
                "sheet_state": "visible",
                "dimension": "A1:C10",
                "dimension_bounds": {
                    "min_row": 1,
                    "min_column": 1,
                    "max_row": 10,
                    "max_column": 3,
                },
                "detail_status": "scanned",
                "entry_size_bytes": 100,
                "sheet_pr": {"filterMode": "1"},
                "outline_pr": {},
                "sheet_format_pr": {},
                "sheet_views": [],
                "panes": [],
                "selections": [],
                "auto_filters": [
                    {
                        "ref": "A1:C10",
                        "bounds": {
                            "min_row": 1,
                            "min_column": 1,
                            "max_row": 10,
                            "max_column": 3,
                        },
                    }
                ],
                "sort_states": [],
                "hidden_row_spans": [
                    {
                        "start_row": 2,
                        "end_row": 5,
                        "row_count": 4,
                        "hidden_count": 4,
                        "zero_height_count": 0,
                        "collapsed_count": 0,
                        "max_outline_level": 0,
                        "min_height": None,
                        "max_height": None,
                    }
                ],
                "zero_height_row_spans": [],
                "outline_row_spans": [],
                "collapsed_row_spans": [],
                "hidden_column_spans": [],
                "zero_width_column_spans": [],
                "outline_column_spans": [],
                "collapsed_column_spans": [],
                "summary": {
                    "hidden_row_count": 4,
                    "zero_height_row_count": 0,
                    "outline_row_count": 0,
                    "collapsed_row_count": 0,
                    "hidden_column_count": 0,
                    "outline_column_count": 0,
                    "auto_filter_count": 1,
                    "frozen_pane_count": 0,
                },
                "parser_observations": [],
            }
        ],
        "capture_window_analyses": [
            {
                "id": "view_state_quality_capture",
                "type": "view_state_capture_window_analysis",
                "capture_quality_file": "capture-quality.json",
                "quality_result_id": "quality_capture",
                "capture_id": "capture_target_summary",
                "target_id": "target_summary",
                "quality_status": "recapture_required",
                "sheet": "Sheet1",
                "range": "A1:C5",
                "bounds": {
                    "min_row": 1,
                    "min_column": 1,
                    "max_row": 5,
                    "max_column": 3,
                },
                "row_state_summary": {
                    "row_count": 5,
                    "hidden_row_count": 4,
                    "zero_height_row_count": 0,
                    "outline_row_count": 0,
                    "collapsed_row_count": 0,
                    "visible_row_count": 1,
                    "hidden_row_ratio": 0.8,
                    "hidden_spans": [
                        {
                            "start_row": 2,
                            "end_row": 5,
                            "row_count": 4,
                            "hidden_count": 4,
                            "zero_height_count": 0,
                            "collapsed_count": 0,
                            "max_outline_level": 0,
                            "min_height": None,
                            "max_height": None,
                        }
                    ],
                    "zero_height_spans": [],
                    "outline_spans": [],
                    "collapsed_spans": [],
                },
                "column_state_summary": {
                    "column_count": 3,
                    "hidden_column_count": 0,
                    "zero_width_column_count": 0,
                    "outline_column_count": 0,
                    "collapsed_column_count": 0,
                    "visible_column_count": 3,
                    "hidden_column_ratio": 0,
                    "hidden_spans": [],
                    "zero_width_spans": [],
                    "outline_spans": [],
                    "collapsed_spans": [],
                },
                "filter_overlap": [
                    {
                        "ref": "A1:C10",
                        "bounds": {
                            "min_row": 1,
                            "min_column": 1,
                            "max_row": 10,
                            "max_column": 3,
                        },
                        "intersection": {
                            "min_row": 1,
                            "min_column": 1,
                            "max_row": 5,
                            "max_column": 3,
                        },
                    }
                ],
                "sheet_view_signals": {
                    "filter_mode": True,
                    "auto_filter_count": 1,
                    "frozen_pane_count": 0,
                    "sheet_view_top_left_cells": [],
                },
                "classification": "filtered_or_hidden_rows_explain_capture_failure",
                "authority_decision": "separate_visible_render_authority_from_structural_data_authority",
                "recommended_next_action": "add_non_authoritative_unhide_or_clear_filter_diagnostic_before_coordinate_normalization",
                "evidence_refs": ["quality_capture", "capture_target_summary"],
            }
        ],
        "gate_results": [],
        "summary": {
            "sheet_count": 1,
            "scanned_sheet_count": 1,
            "sheet_with_filter_mode_count": 1,
            "sheet_with_hidden_rows_count": 1,
            "hidden_row_count": 4,
            "hidden_column_count": 0,
            "capture_window_analysis_count": 1,
            "view_state_explained_count": 1,
            "view_state_affects_count": 0,
            "unexplained_by_view_state_count": 0,
            "non_authoritative_unhide_diagnostic_count": 1,
        },
        "parser_observations": [],
    }


def _coordinate_normalization() -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-06-01T00:00:00Z",
        "source_artifacts": {
            "render_capture_files": ["/tmp/render.json"],
            "capture_quality_files": ["/tmp/quality.json"],
            "view_state_profile": "/tmp/view-state.json",
        },
        "method": {
            "name": "deterministic_capture_range_coordinate_normalization",
            "authority": "range_to_capture_bbox_mapping_not_visual_feature_truth",
            "visible_state_policy": "Normalize captured visible-state ranges only.",
        },
        "coordinate_mappings": [
            {
                "id": "coord_quality_capture",
                "type": "coordinate_mapping",
                "status": "normalized_visible_range",
                "capture_id": "capture_target_summary",
                "target_id": "target_summary",
                "sheet": "Sheet1",
                "cell_range": "A1:C5",
                "range_bounds": {
                    "min_row": 1,
                    "min_column": 1,
                    "max_row": 5,
                    "max_column": 3,
                },
                "capture_bbox": {
                    "x": 0,
                    "y": 0,
                    "width": 300,
                    "height": 200,
                },
                "pixel_scale": {
                    "row_count": 5,
                    "column_count": 3,
                    "pixels_per_row_estimate": 40,
                    "pixels_per_column_estimate": 100,
                    "axis_model": "uniform_range_estimate",
                },
                "quality_status": "usable",
                "view_state_classification": "no_material_view_state_signal",
                "view_state_authority_decision": "continue_with_visible_render_authority",
                "render_capture_file": "render.json",
                "capture_quality_file": "quality.json",
                "normalization_notes": "Capture range is normalized.",
                "evidence_refs": ["quality_capture", "capture_target_summary"],
            }
        ],
        "gate_results": [],
        "summary": {
            "mapping_count": 1,
            "normalized_visible_range_count": 1,
            "normalized_with_view_state_warning_count": 0,
            "review_required_count": 0,
            "blocked_by_view_state_count": 0,
            "unusable_capture_count": 0,
            "not_available_count": 0,
            "passed_gate_count": 1,
            "review_gate_count": 0,
            "blocked_gate_count": 0,
        },
        "parser_observations": [],
    }


def _visual_features() -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-06-01T00:00:00Z",
        "source_artifacts": {
            "coordinate_normalization": "/tmp/coordinate.json",
            "render_capture_files": ["/tmp/render.json"],
        },
        "method": {
            "name": "deterministic_capture_visual_feature_detection",
            "authority": "capture_image_features_not_semantic_truth",
            "image_thresholds": {
                "max_analysis_dimension": 800,
                "visible_threshold": 245,
                "line_density_threshold": 0.55,
            },
        },
        "feature_results": [
            {
                "id": "features_coord_quality_capture",
                "type": "visual_feature_result",
                "status": "detected",
                "mapping_id": "coord_quality_capture",
                "capture_id": "capture_target_summary",
                "target_id": "target_summary",
                "sheet": "Sheet1",
                "cell_range": "A1:C5",
                "png_path": "/tmp/capture.png",
                "quality_status": "usable",
                "normalization_status": "normalized_visible_range",
                "view_state_classification": "no_material_view_state_signal",
                "image_metrics": {
                    "width": 300,
                    "height": 200,
                    "analysis_width": 300,
                    "analysis_height": 200,
                    "visible_pixel_ratio": 0.2,
                    "whitespace_ratio": 0.8,
                    "alpha_coverage_ratio": 1,
                    "content_bbox": {
                        "x": 0,
                        "y": 0,
                        "width": 280,
                        "height": 180,
                    },
                },
                "line_features": {
                    "horizontal_line_count": 2,
                    "vertical_line_count": 2,
                    "horizontal_line_spans": [],
                    "vertical_line_spans": [],
                },
                "color_features": {
                    "dominant_color_count": 1,
                    "dominant_colors": [{"rgb_hex": "#101010", "ratio": 1}],
                },
                "layout_signals": [
                    "visible_content_bbox",
                    "grid_or_table_line_structure",
                ],
                "feature_notes": "Visual features were detected.",
                "evidence_refs": ["coord_quality_capture"],
            }
        ],
        "gate_results": [],
        "summary": {
            "feature_result_count": 1,
            "detected_count": 1,
            "detected_with_view_state_warning_count": 0,
            "no_visible_content_detected_count": 0,
            "skipped_quality_review_count": 0,
            "skipped_view_state_blocked_count": 0,
            "skipped_unusable_count": 0,
            "not_available_count": 0,
            "grid_like_result_count": 1,
            "passed_gate_count": 1,
            "review_gate_count": 0,
            "blocked_gate_count": 0,
        },
        "parser_observations": [],
    }


def _gate_execution() -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-06-01T00:00:00Z",
        "source_artifacts": {
            "cross_validation_plan": "/tmp/plan.json",
            "visual_features": "/tmp/visual.json",
        },
        "method": {
            "name": "deterministic_cross_validation_gate_execution",
            "authority": "evidence_gate_status_not_final_document_graph_truth",
            "decision_policy": "Accept only deterministic evidence.",
        },
        "gate_results": [
            {
                "id": "result_gate_summary",
                "type": "cross_validation_gate_result",
                "gate_check_id": "gate_summary",
                "target_id": "target_summary",
                "gate_type": "formula_summary_visual_alignment",
                "status": "accepted",
                "reason": "deterministic_visual_evidence_available",
                "confidence": 0.82,
                "target_type": "pipeline_output",
                "sheet": "Sheet1",
                "range": "A1:C5",
                "feature_result_id": "features_coord_quality_capture",
                "feature_status": "detected",
                "layout_signals": [
                    "visible_content_bbox",
                    "grid_or_table_line_structure",
                ],
                "deterministic_inputs": ["pipeline_1"],
                "evidence_refs": ["gate_summary", "features_coord_quality_capture"],
                "notes": "accepted",
            }
        ],
        "summary": {
            "gate_result_count": 1,
            "accepted_count": 1,
            "rejected_count": 0,
            "review_required_count": 0,
            "capture_required_count": 0,
            "view_state_blocked_count": 0,
            "quality_review_required_count": 0,
            "object_hierarchy_review_count": 0,
        },
        "parser_observations": [],
    }


def _shared_alignment_review() -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-06-02T00:00:00Z",
        "source_artifacts": {
            "local_semantic_candidates": "/tmp/local.json",
            "domain_source_model": "/tmp/domain.json",
            "data_view_projection": "/tmp/projection.json",
        },
        "method": {
            "name": "deterministic_shared_ontology_alignment_review",
            "authority": "review_only_no_shared_promotion",
            "decision_policy": "Review only.",
        },
        "alignment_context": {
            "local_boundary_id": "local_boundary:sample",
            "local_boundary_status": "review_required",
            "local_boundary_scope": "current_workbook_only_until_boundary_confirmed",
            "local_boundary_confirmed": False,
            "local_domain_source_count": 0,
            "general_domain_source_count": 1,
            "data_view_projection_count": 1,
            "shared_ontology_target_status": "not_provided",
            "alignment_authority": "human_review_packet_only",
            "shared_promotion_preconditions": [
                {
                    "name": "local_boundary_confirmed",
                    "status": "blocked",
                    "description": "Boundary must be confirmed.",
                    "missing_action": "Confirm the local boundary.",
                }
            ],
        },
        "alignment_items": [
            {
                "id": "alignment_item:sample",
                "type": "shared_ontology_alignment_item",
                "candidate_id": "local_semantic_candidate:sample",
                "label": "K-GAAP / K-IFRS revenue surface",
                "candidate_kind": "revenue_recognition_schedule",
                "source_kind": "accepted_semantic_context",
                "alignment_status": "blocked_basis_definition_pending",
                "promotion_decision": "not_promoted",
                "proposed_shared_concept_id": None,
                "existing_shared_concept_refs": [],
                "blockers": ["gaap_ifrs_basis_mapping_required"],
                "conflict_risks": ["dual_basis_revenue_interpretation_risk"],
                "required_evidence": ["k_gaap_vs_k_ifrs_output_definition"],
                "human_review_questions": [
                    "Is this K-GAAP output or K-IFRS support?"
                ],
                "basis_review": {
                    "required": True,
                    "detected_terms": ["KGAAP", "수익인식"],
                    "reason": "Basis separation is required.",
                },
                "data_view_refs": {
                    "data_view_ids": ["data_view:sample"],
                    "sheets": ["매출"],
                },
                "observed_terms": ["*2월 KGAAP기준 매출", "수익인식"],
                "evidence_refs": ["data_view:sample"],
                "source_artifact_refs": ["local_semantic_candidates"],
            }
        ],
        "shared_ontology_updates": [],
        "review_questions": [
            {
                "id": "review_question:gaap_ifrs_basis",
                "priority": "high",
                "topic": "gaap_ifrs_basis_separation",
                "question": "How should K-GAAP output and K-IFRS surfaces be separated?",
                "blocks": ["revenue_concept_promotion"],
                "required_evidence": ["k_gaap_vs_k_ifrs_output_definition"],
            }
        ],
        "summary": {
            "alignment_item_count": 1,
            "promoted_count": 0,
            "blocked_alignment_count": 1,
            "local_boundary_blocked_count": 1,
            "local_source_blocked_count": 1,
            "semantic_label_pending_count": 0,
            "basis_review_required_count": 1,
            "formula_result_validation_required_count": 0,
            "review_question_count": 1,
            "shared_ontology_update_count": 0,
            "alignment_status_counts": {
                "blocked_basis_definition_pending": 1
            },
            "blocker_counts": {
                "gaap_ifrs_basis_mapping_required": 1
            },
            "conflict_risk_counts": {
                "dual_basis_revenue_interpretation_risk": 1
            },
            "alignment_status": "review_only_no_shared_promotion",
        },
        "parser_observations": [
            {
                "level": "warning",
                "message": "No shared ontology promotion.",
            }
        ],
    }


def _process_redesign_review() -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-06-02T00:00:00Z",
        "source_materials": {
            "process_ledger": "/tmp/process-ledger.jsonl",
            "tasklist": "/tmp/tasklist.md",
            "design_doc": "/tmp/design.md",
            "agents": "/tmp/AGENTS.md",
            "implementation_map": "/tmp/IMPLEMENTATION_MAP.html",
            "artifact_dir": "/tmp/artifacts",
            "session_log_source": "process_ledger_jsonl",
            "artifact_inventory": [],
            "document_inventory": [],
        },
        "method": {
            "name": "deterministic_process_redesign_review",
            "authority": "process_recommendation_not_parser_truth",
            "decision_policy": "Review process evidence.",
        },
        "final_assessment": {
            "status": "structural_understanding_ready_but_semantic_promotion_blocked",
            "what_is_ready": ["Structure and data views are reviewable."],
            "what_is_not_ready": ["Shared ontology promotion is blocked."],
            "recommended_default_next_step": "Run the redesigned pipeline on another workbook.",
        },
        "stage_reviews": [
            {
                "id": "stage_review:01",
                "current_stage_number": 1,
                "current_stage": "Workbook view-state preflight",
                "current_status": "Done",
                "recommendation": "keep_reordered_early",
                "priority": "high",
                "proposed_group": "input_preflight",
                "rationale": ["View-state must be known early."],
                "recommended_changes": ["Keep before capture planning."],
                "completion_guard": ["Visible state is inventoried."],
            }
        ],
        "recommended_pipeline": [
            {
                "position": 0,
                "stage": "Workbook View-State Preflight",
                "source_current_stage_numbers": [1],
                "change_type": "keep_reordered_early",
                "why": "Human-visible state must be known early.",
            }
        ],
        "redesign_decisions": [
            {
                "id": "decision:view_state_preflight_first",
                "decision": "Move view-state preflight first.",
                "status": "accepted_for_next_iteration",
                "evidence": ["View state explained capture behavior."],
                "effect": "Capture planning is safer.",
            }
        ],
        "open_evidence_gaps": [
            {
                "id": "gap:formula_result_authority",
                "priority": "high",
                "gap": "Formula results need Excel validation.",
                "blocks": ["numeric_revenue_claim"],
                "required_evidence": ["excel_engine_recalculation_sample"],
            }
        ],
        "next_iteration_plan": [
            {
                "step": 1,
                "name": "Apply redesigned ordering.",
                "done_when": "Next workbook starts with preflight.",
            }
        ],
        "summary": {
            "ledger_entry_count": 1,
            "tasklist_stage_count": 1,
            "artifact_count": 1,
            "json_artifact_count": 1,
            "stage_review_count": 1,
            "high_priority_stage_review_count": 1,
            "recommended_pipeline_stage_count": 1,
            "redesign_decision_count": 1,
            "open_evidence_gap_count": 1,
            "recommendation_counts": {
                "keep_reordered_early": 1,
            },
            "review_status": "process_redesign_review_completed",
        },
        "parser_observations": [
            {
                "level": "info",
                "message": "Reviewed process evidence.",
            }
        ],
    }


def _onto_seed_summary() -> dict:
    return {
        "schema_version": 1,
        "generated_at": "2026-06-02T18:02:18+09:00",
        "stage": "onto_seed_prompt_timeout_mitigation",
        "source_packet_bytes": 802,
        "run_profile": {
            "domain_pack_used": False,
            "excluded_domain_sources": ["accounting-kr"],
            "reporting_basis": "cash_basis_payment_status_operational_reporting",
            "shared_ontology_update_count": 0,
            "miro_mcp_status": "disabled",
        },
        "mitigation": {
            "previous_candidate_count": 52,
            "previous_promoted_candidate_count": 19,
            "seed_min_candidate_count": 33,
            "seed_min_promoted_candidate_count": 6,
            "seed_timeout_ms": 480000,
        },
        "result": {
            "ontology_seed_ref": ".onto/reconstruct/session/ontology-seed.yaml",
            "ontology_seed_validation_status": "valid",
            "ontology_seed_validation_violations": 0,
            "handoff_readiness_projection": "not_ready",
            "ontology_handoff_readiness_claim": "limited",
            "stop_decision": "continue",
        },
        "metrics": {
            "semantic_claim_count": 55,
            "confirmed_claim_count": 34,
            "partial_claim_count": 5,
            "deferred_claim_count": 16,
            "competency_question_answerable_count": 5,
            "competency_question_partially_answerable_count": 3,
            "unsupported_question_count": 8,
        },
        "authority_boundary": {
            "accepted_as": "official onto-mcp direct reconstruct seed artifact",
            "not_accepted_as": ["action-ready ontology"],
            "remaining_maturation_frontier": ["metric equivalence unresolved"],
        },
    }


if __name__ == "__main__":
    unittest.main()
