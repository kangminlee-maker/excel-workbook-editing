from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl.utils import range_boundaries

SCHEMA_VERSION = "0.1"
BLOCKING_VIEW_STATE_CLASSIFICATIONS = {
    "all_rows_hidden_or_zero_height",
    "filtered_or_hidden_rows_explain_capture_failure",
    "hidden_rows_dominate_capture_window",
}
AFFECTING_VIEW_STATE_CLASSIFICATIONS = {
    "filtered_rows_affect_capture_window",
    "mixed_visible_hidden_rows",
    "hidden_columns_affect_capture_window",
}


def build_coordinate_normalization(
    capture_specs: list[tuple[Path, Path]],
    view_state_profile_path: Path | None = None,
) -> dict[str, Any]:
    captures_by_id: dict[str, dict[str, Any]] = {}
    capture_sources_by_id: dict[str, str] = {}
    quality_results = []
    source_render_files = []
    source_quality_files = []
    for render_path, quality_path in capture_specs:
        render_path = render_path.expanduser().resolve()
        quality_path = quality_path.expanduser().resolve()
        render_captures = _read_json(render_path)
        capture_quality = _read_json(quality_path)
        source_render_files.append(str(render_path))
        source_quality_files.append(str(quality_path))
        for capture in render_captures.get("captures", []):
            capture_id = capture.get("id")
            if capture_id:
                captures_by_id[capture_id] = capture
                capture_sources_by_id[capture_id] = render_path.name
        for result in capture_quality.get("quality_results", []):
            quality_results.append(
                {
                    **result,
                    "source_capture_quality_file": quality_path.name,
                }
            )

    view_state_profile_path = (
        view_state_profile_path.expanduser().resolve()
        if view_state_profile_path
        else None
    )
    view_state_profile = _read_json(view_state_profile_path) if view_state_profile_path else None
    view_state_by_quality_id = {
        analysis.get("quality_result_id"): analysis
        for analysis in (view_state_profile or {}).get("capture_window_analyses", [])
        if analysis.get("quality_result_id")
    }

    mappings = [
        _mapping(
            result,
            captures_by_id.get(result.get("capture_id")),
            capture_sources_by_id.get(result.get("capture_id")),
            view_state_by_quality_id.get(result.get("id")),
        )
        for result in quality_results
    ]
    gate_results = [_gate_result(mapping) for mapping in mappings]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "render_capture_files": source_render_files,
            "capture_quality_files": source_quality_files,
            "view_state_profile": str(view_state_profile_path) if view_state_profile_path else None,
        },
        "method": {
            "name": "deterministic_capture_range_coordinate_normalization",
            "authority": "range_to_capture_bbox_mapping_not_visual_feature_truth",
            "visible_state_policy": (
                "Normalize only the captured visible-state range. Hidden or filtered rows remain "
                "structural data evidence, not visual absence."
            ),
        },
        "coordinate_mappings": mappings,
        "gate_results": gate_results,
        "summary": _summary(mappings, gate_results),
        "parser_observations": _parser_observations(mappings),
    }


def _mapping(
    quality_result: dict[str, Any],
    capture: dict[str, Any] | None,
    render_source_name: str | None,
    view_state_analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    range_text = quality_result.get("capture_window_range") or quality_result.get("requested_range")
    bounds = _bounds_from_range(range_text)
    capture_bbox = ((capture or {}).get("coordinate_map") or {}).get("capture_bbox")
    if capture_bbox is None:
        capture_bbox = _capture_bbox_from_quality(quality_result)
    status = _normalization_status(quality_result, capture, capture_bbox, view_state_analysis)
    row_count = bounds["max_row"] - bounds["min_row"] + 1 if bounds else None
    column_count = bounds["max_column"] - bounds["min_column"] + 1 if bounds else None
    pixel_scale = _pixel_scale(capture_bbox, row_count, column_count)
    return {
        "id": f"coord_{quality_result.get('id')}",
        "type": "coordinate_mapping",
        "status": status,
        "capture_id": quality_result.get("capture_id"),
        "target_id": quality_result.get("target_id"),
        "sheet": quality_result.get("sheet"),
        "cell_range": range_text,
        "range_bounds": bounds,
        "capture_bbox": capture_bbox,
        "pixel_scale": pixel_scale,
        "quality_status": quality_result.get("status"),
        "view_state_classification": (
            view_state_analysis.get("classification")
            if view_state_analysis
            else "not_evaluated"
        ),
        "view_state_authority_decision": (
            view_state_analysis.get("authority_decision")
            if view_state_analysis
            else "not_evaluated"
        ),
        "render_capture_file": render_source_name,
        "capture_quality_file": quality_result.get("source_capture_quality_file"),
        "normalization_notes": _normalization_notes(
            quality_result,
            status,
            view_state_analysis,
        ),
        "evidence_refs": [
            item
            for item in [
                quality_result.get("id"),
                quality_result.get("capture_id"),
                (view_state_analysis or {}).get("id"),
            ]
            if item
        ],
    }


def _normalization_status(
    quality_result: dict[str, Any],
    capture: dict[str, Any] | None,
    capture_bbox: dict[str, Any] | None,
    view_state_analysis: dict[str, Any] | None,
) -> str:
    if not capture or capture.get("status") != "captured" or not capture_bbox:
        return "not_available"
    classification = (view_state_analysis or {}).get("classification")
    if classification in BLOCKING_VIEW_STATE_CLASSIFICATIONS:
        return "blocked_by_view_state"
    quality_status = quality_result.get("status")
    if quality_status == "usable":
        if classification in AFFECTING_VIEW_STATE_CLASSIFICATIONS:
            return "normalized_with_view_state_warning"
        return "normalized_visible_range"
    if quality_status == "review_required":
        return "review_required"
    return "unusable_capture"


def _capture_bbox_from_quality(
    quality_result: dict[str, Any],
) -> dict[str, int] | None:
    dimensions = quality_result.get("dimensions") or {}
    width = dimensions.get("width")
    height = dimensions.get("height")
    if not width or not height:
        return None
    return {
        "x": 0,
        "y": 0,
        "width": width,
        "height": height,
    }


def _pixel_scale(
    capture_bbox: dict[str, Any] | None,
    row_count: int | None,
    column_count: int | None,
) -> dict[str, Any]:
    width = (capture_bbox or {}).get("width")
    height = (capture_bbox or {}).get("height")
    return {
        "row_count": row_count,
        "column_count": column_count,
        "pixels_per_row_estimate": (
            round(height / row_count, 6)
            if height and row_count
            else None
        ),
        "pixels_per_column_estimate": (
            round(width / column_count, 6)
            if width and column_count
            else None
        ),
        "axis_model": "uniform_range_estimate",
    }


def _normalization_notes(
    quality_result: dict[str, Any],
    status: str,
    view_state_analysis: dict[str, Any] | None,
) -> str:
    if status == "normalized_visible_range":
        return "Capture range is normalized as a visible-state bbox estimate."
    if status == "normalized_with_view_state_warning":
        return "Capture is usable but view-state affects part of the mapped range."
    if status == "blocked_by_view_state":
        return "Visible-state capture is dominated by hidden or filtered rows; preserve structural data separately and use only diagnostic reveal captures if needed."
    if status == "review_required":
        return "Capture has a bbox but quality checks require review before downstream visual gates trust it."
    if status == "unusable_capture":
        return f"Capture quality status is {quality_result.get('status')}."
    if view_state_analysis:
        return f"View-state classification: {view_state_analysis.get('classification')}."
    return "Coordinate mapping is not available."


def _gate_result(mapping: dict[str, Any]) -> dict[str, Any]:
    status = {
        "normalized_visible_range": "passed",
        "normalized_with_view_state_warning": "review_required",
        "review_required": "review_required",
        "blocked_by_view_state": "blocked",
        "unusable_capture": "blocked",
        "not_available": "blocked",
    }[mapping["status"]]
    return {
        "id": f"gate_{mapping['id']}",
        "type": "coordinate_normalization_gate_result",
        "mapping_id": mapping["id"],
        "capture_id": mapping.get("capture_id"),
        "target_id": mapping.get("target_id"),
        "gate_type": "range_capture_bbox_mapping",
        "status": status,
        "normalization_status": mapping["status"],
        "evidence_refs": mapping["evidence_refs"],
        "notes": mapping["normalization_notes"],
    }


def _summary(
    mappings: list[dict[str, Any]],
    gate_results: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "mapping_count": len(mappings),
        "normalized_visible_range_count": _count_status(mappings, "normalized_visible_range"),
        "normalized_with_view_state_warning_count": _count_status(
            mappings,
            "normalized_with_view_state_warning",
        ),
        "review_required_count": _count_status(mappings, "review_required"),
        "blocked_by_view_state_count": _count_status(mappings, "blocked_by_view_state"),
        "unusable_capture_count": _count_status(mappings, "unusable_capture"),
        "not_available_count": _count_status(mappings, "not_available"),
        "passed_gate_count": sum(1 for gate in gate_results if gate["status"] == "passed"),
        "review_gate_count": sum(
            1 for gate in gate_results if gate["status"] == "review_required"
        ),
        "blocked_gate_count": sum(1 for gate in gate_results if gate["status"] == "blocked"),
    }


def _count_status(mappings: list[dict[str, Any]], status: str) -> int:
    return sum(1 for mapping in mappings if mapping["status"] == status)


def _parser_observations(mappings: list[dict[str, Any]]) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": "Coordinate normalization maps capture-range bboxes back to workbook cell ranges. It does not detect internal visual features.",
        }
    ]
    blocked = _count_status(mappings, "blocked_by_view_state")
    if blocked:
        observations.append(
            {
                "level": "warning",
                "message": f"{blocked} mappings are blocked by hidden/filter view-state and should not be treated as visual absence.",
            }
        )
    return observations


def _bounds_from_range(value: str | None) -> dict[str, int] | None:
    if not value:
        return None
    try:
        min_col, min_row, max_col, max_row = range_boundaries(value)
    except ValueError:
        return None
    return {
        "min_row": min_row,
        "min_column": min_col,
        "max_row": max_row,
        "max_column": max_col,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _capture_spec(value: str) -> tuple[Path, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("capture spec must be RENDER_JSON=QUALITY_JSON")
    render, quality = value.split("=", 1)
    return Path(render), Path(quality)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize Excel capture bboxes back to workbook cell ranges."
    )
    parser.add_argument(
        "--capture",
        action="append",
        type=_capture_spec,
        required=True,
        help="Pair render captures and capture quality as RENDER_JSON=QUALITY_JSON.",
    )
    parser.add_argument("--view-state-profile", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = build_coordinate_normalization(
        args.capture,
        view_state_profile_path=args.view_state_profile,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(package, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(package["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
