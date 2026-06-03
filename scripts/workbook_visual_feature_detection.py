from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]

SCHEMA_VERSION = "0.1"
DETECTABLE_MAPPING_STATUSES = {
    "normalized_visible_range",
    "normalized_with_view_state_warning",
}
MAX_ANALYSIS_DIMENSION = 800
VISIBLE_THRESHOLD = 245
LINE_DENSITY_THRESHOLD = 0.55


def build_visual_feature_detection(
    coordinate_normalization_path: Path,
) -> dict[str, Any]:
    coordinate_normalization_path = coordinate_normalization_path.expanduser().resolve()
    coordinate_normalization = _read_json(coordinate_normalization_path)
    capture_by_id = _capture_lookup(coordinate_normalization)
    feature_results = [
        _feature_result(mapping, capture_by_id.get(mapping.get("capture_id")))
        for mapping in coordinate_normalization.get("coordinate_mappings", [])
    ]
    gate_results = [_gate_result(result) for result in feature_results]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "coordinate_normalization": str(coordinate_normalization_path),
            "render_capture_files": coordinate_normalization.get("source_artifacts", {}).get(
                "render_capture_files",
                [],
            ),
        },
        "method": {
            "name": "deterministic_capture_visual_feature_detection",
            "authority": "capture_image_features_not_semantic_truth",
            "image_thresholds": {
                "max_analysis_dimension": MAX_ANALYSIS_DIMENSION,
                "visible_threshold": VISIBLE_THRESHOLD,
                "line_density_threshold": LINE_DENSITY_THRESHOLD,
            },
        },
        "feature_results": feature_results,
        "gate_results": gate_results,
        "summary": _summary(feature_results, gate_results),
        "parser_observations": _parser_observations(feature_results),
    }


def _capture_lookup(
    coordinate_normalization: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    captures = {}
    for render_file in coordinate_normalization.get("source_artifacts", {}).get(
        "render_capture_files",
        [],
    ):
        path = Path(render_file)
        if not path.exists():
            continue
        render_package = _read_json(path)
        for capture in render_package.get("captures", []):
            capture_id = capture.get("id")
            if capture_id:
                captures[capture_id] = capture
    return captures


def _feature_result(
    mapping: dict[str, Any],
    capture: dict[str, Any] | None,
) -> dict[str, Any]:
    status = _feature_status(mapping, capture)
    png_path = ((capture or {}).get("output") or {}).get("png_path")
    features = _empty_features()
    if status in {"detected", "detected_with_view_state_warning"} and png_path:
        features = _image_features(Path(png_path))
        if features["image_metrics"]["content_bbox"] is None:
            status = "no_visible_content_detected"
    return {
        "id": f"features_{mapping.get('id')}",
        "type": "visual_feature_result",
        "status": status,
        "mapping_id": mapping.get("id"),
        "capture_id": mapping.get("capture_id"),
        "target_id": mapping.get("target_id"),
        "sheet": mapping.get("sheet"),
        "cell_range": mapping.get("cell_range"),
        "png_path": png_path,
        "quality_status": mapping.get("quality_status"),
        "normalization_status": mapping.get("status"),
        "view_state_classification": mapping.get("view_state_classification"),
        **features,
        "layout_signals": _layout_signals(mapping, features),
        "feature_notes": _feature_notes(status, mapping),
        "evidence_refs": [
            item
            for item in [mapping.get("id"), mapping.get("capture_id")]
            if item
        ],
    }


def _feature_status(
    mapping: dict[str, Any],
    capture: dict[str, Any] | None,
) -> str:
    status = mapping.get("status")
    if status == "blocked_by_view_state":
        return "skipped_view_state_blocked"
    if status == "review_required":
        return "skipped_quality_review"
    if status in {"unusable_capture", "not_available"}:
        return "skipped_unusable"
    if status not in DETECTABLE_MAPPING_STATUSES:
        return "skipped_unusable"
    if Image is None:
        return "not_available"
    if not capture or capture.get("status") != "captured":
        return "not_available"
    output = capture.get("output") or {}
    png_path = output.get("png_path")
    if not png_path or not Path(png_path).exists():
        return "not_available"
    if status == "normalized_with_view_state_warning":
        return "detected_with_view_state_warning"
    return "detected"


def _image_features(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        original_width, original_height = rgba.width, rgba.height
        scale = min(
            1.0,
            MAX_ANALYSIS_DIMENSION / max(1, max(original_width, original_height)),
        )
        if scale < 1.0:
            rgba = rgba.resize(
                (
                    max(1, int(original_width * scale)),
                    max(1, int(original_height * scale)),
                )
            )
        pixels = list(getattr(rgba, "get_flattened_data", rgba.getdata)())
    width, height = rgba.width, rgba.height
    visible_mask = []
    visible_count = 0
    opaque_count = 0
    color_counter: Counter[tuple[int, int, int]] = Counter()
    for red, green, blue, alpha in pixels:
        opaque = alpha > 10
        visible = opaque and not (
            red >= VISIBLE_THRESHOLD
            and green >= VISIBLE_THRESHOLD
            and blue >= VISIBLE_THRESHOLD
        )
        visible_mask.append(visible)
        if opaque:
            opaque_count += 1
        if visible:
            visible_count += 1
            color_counter[(red // 32, green // 32, blue // 32)] += 1

    total = max(1, len(pixels))
    content_bbox = _content_bbox(visible_mask, width, height, scale)
    horizontal_lines = _line_spans(visible_mask, width, height, axis="row")
    vertical_lines = _line_spans(visible_mask, width, height, axis="column")
    dominant_colors = _dominant_colors(color_counter, max(1, visible_count))
    return {
        "image_metrics": {
            "width": original_width,
            "height": original_height,
            "analysis_width": width,
            "analysis_height": height,
            "visible_pixel_ratio": round(visible_count / total, 6),
            "whitespace_ratio": round(1 - (visible_count / total), 6),
            "alpha_coverage_ratio": round(opaque_count / total, 6),
            "content_bbox": content_bbox,
        },
        "line_features": {
            "horizontal_line_count": len(horizontal_lines),
            "vertical_line_count": len(vertical_lines),
            "horizontal_line_spans": horizontal_lines[:20],
            "vertical_line_spans": vertical_lines[:20],
        },
        "color_features": {
            "dominant_color_count": len(dominant_colors),
            "dominant_colors": dominant_colors,
        },
    }


def _content_bbox(
    visible_mask: list[bool],
    width: int,
    height: int,
    scale: float,
) -> dict[str, int] | None:
    xs = []
    ys = []
    for index, visible in enumerate(visible_mask):
        if not visible:
            continue
        xs.append(index % width)
        ys.append(index // width)
    if not xs or not ys:
        return None
    inverse = 1 / scale if scale else 1
    min_x = int(min(xs) * inverse)
    min_y = int(min(ys) * inverse)
    max_x = int((max(xs) + 1) * inverse)
    max_y = int((max(ys) + 1) * inverse)
    return {
        "x": min_x,
        "y": min_y,
        "width": max(1, max_x - min_x),
        "height": max(1, max_y - min_y),
    }


def _line_spans(
    visible_mask: list[bool],
    width: int,
    height: int,
    *,
    axis: str,
) -> list[dict[str, Any]]:
    dense_indices = []
    if axis == "row":
        for y in range(height):
            start = y * width
            density = sum(1 for item in visible_mask[start:start + width] if item) / width
            if density >= LINE_DENSITY_THRESHOLD:
                dense_indices.append((y, density))
    else:
        for x in range(width):
            density = sum(
                1
                for y in range(height)
                if visible_mask[(y * width) + x]
            ) / height
            if density >= LINE_DENSITY_THRESHOLD:
                dense_indices.append((x, density))
    return _group_dense_indices(dense_indices)


def _group_dense_indices(
    dense_indices: list[tuple[int, float]],
) -> list[dict[str, Any]]:
    spans = []
    start = None
    previous = None
    densities = []
    for index, density in dense_indices:
        if start is None:
            start = index
            previous = index
            densities = [density]
            continue
        if previous is not None and index == previous + 1:
            previous = index
            densities.append(density)
            continue
        spans.append(_span(start, previous, densities))
        start = index
        previous = index
        densities = [density]
    if start is not None and previous is not None:
        spans.append(_span(start, previous, densities))
    return spans


def _span(start: int, end: int, densities: list[float]) -> dict[str, Any]:
    return {
        "start": start,
        "end": end,
        "thickness": end - start + 1,
        "max_density": round(max(densities), 6),
        "avg_density": round(sum(densities) / len(densities), 6),
    }


def _dominant_colors(
    color_counter: Counter[tuple[int, int, int]],
    visible_count: int,
) -> list[dict[str, Any]]:
    colors = []
    for (red_bucket, green_bucket, blue_bucket), count in color_counter.most_common(5):
        red = min(255, red_bucket * 32 + 16)
        green = min(255, green_bucket * 32 + 16)
        blue = min(255, blue_bucket * 32 + 16)
        colors.append(
            {
                "rgb_hex": f"#{red:02x}{green:02x}{blue:02x}",
                "ratio": round(count / visible_count, 6),
            }
        )
    return colors


def _empty_features() -> dict[str, Any]:
    return {
        "image_metrics": {
            "width": None,
            "height": None,
            "analysis_width": None,
            "analysis_height": None,
            "visible_pixel_ratio": None,
            "whitespace_ratio": None,
            "alpha_coverage_ratio": None,
            "content_bbox": None,
        },
        "line_features": {
            "horizontal_line_count": 0,
            "vertical_line_count": 0,
            "horizontal_line_spans": [],
            "vertical_line_spans": [],
        },
        "color_features": {
            "dominant_color_count": 0,
            "dominant_colors": [],
        },
    }


def _layout_signals(
    mapping: dict[str, Any],
    features: dict[str, Any],
) -> list[str]:
    signals = []
    image_metrics = features.get("image_metrics", {})
    line_features = features.get("line_features", {})
    range_bounds = mapping.get("range_bounds") or {}
    if image_metrics.get("content_bbox") is not None:
        signals.append("visible_content_bbox")
    if (image_metrics.get("visible_pixel_ratio") or 0) < 0.01:
        signals.append("sparse_visible_content")
    if (
        line_features.get("horizontal_line_count", 0) >= 2
        and line_features.get("vertical_line_count", 0) >= 2
    ):
        signals.append("grid_or_table_line_structure")
    if (range_bounds.get("max_column") or 0) - (range_bounds.get("min_column") or 0) + 1 >= 15:
        signals.append("wide_range")
    if mapping.get("status") == "normalized_with_view_state_warning":
        signals.append("view_state_warning")
    return signals


def _feature_notes(status: str, mapping: dict[str, Any]) -> str:
    if status == "detected":
        return "Visual features were detected from the normalized visible capture."
    if status == "detected_with_view_state_warning":
        return "Visual features were detected, but view-state affects part of the range."
    if status == "skipped_view_state_blocked":
        return "Skipped because hidden/filter view-state blocks visual absence claims for this capture."
    if status == "skipped_quality_review":
        return "Skipped because capture quality requires review before visual feature gates trust it."
    if status == "no_visible_content_detected":
        return "No visible content bbox was detected in the capture image."
    return f"Skipped because normalization status is {mapping.get('status')}."


def _gate_result(result: dict[str, Any]) -> dict[str, Any]:
    status = {
        "detected": "passed",
        "detected_with_view_state_warning": "review_required",
        "no_visible_content_detected": "review_required",
        "skipped_quality_review": "review_required",
        "skipped_view_state_blocked": "blocked",
        "skipped_unusable": "blocked",
        "not_available": "blocked",
    }[result["status"]]
    return {
        "id": f"gate_{result['id']}",
        "type": "visual_feature_gate_result",
        "feature_result_id": result["id"],
        "mapping_id": result.get("mapping_id"),
        "capture_id": result.get("capture_id"),
        "target_id": result.get("target_id"),
        "gate_type": "capture_visual_feature_detection",
        "status": status,
        "feature_status": result["status"],
        "evidence_refs": result["evidence_refs"],
        "notes": result["feature_notes"],
    }


def _summary(
    results: list[dict[str, Any]],
    gate_results: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "feature_result_count": len(results),
        "detected_count": _count_status(results, "detected"),
        "detected_with_view_state_warning_count": _count_status(
            results,
            "detected_with_view_state_warning",
        ),
        "no_visible_content_detected_count": _count_status(
            results,
            "no_visible_content_detected",
        ),
        "skipped_quality_review_count": _count_status(results, "skipped_quality_review"),
        "skipped_view_state_blocked_count": _count_status(
            results,
            "skipped_view_state_blocked",
        ),
        "skipped_unusable_count": _count_status(results, "skipped_unusable"),
        "not_available_count": _count_status(results, "not_available"),
        "grid_like_result_count": sum(
            1
            for result in results
            if "grid_or_table_line_structure" in result.get("layout_signals", [])
        ),
        "passed_gate_count": sum(1 for gate in gate_results if gate["status"] == "passed"),
        "review_gate_count": sum(
            1 for gate in gate_results if gate["status"] == "review_required"
        ),
        "blocked_gate_count": sum(1 for gate in gate_results if gate["status"] == "blocked"),
    }


def _count_status(results: list[dict[str, Any]], status: str) -> int:
    return sum(1 for result in results if result["status"] == status)


def _parser_observations(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    observations = [
        {
            "level": "info",
            "message": "Visual feature detection extracts deterministic image features for later gates. It does not assign document semantics.",
        }
    ]
    blocked = _count_status(results, "skipped_view_state_blocked")
    if blocked:
        observations.append(
            {
                "level": "warning",
                "message": f"{blocked} mappings were skipped because hidden/filter view-state blocks visual absence claims.",
            }
        )
    return observations


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect deterministic visual features from normalized workbook capture PNGs."
    )
    parser.add_argument("coordinate_normalization", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = build_visual_feature_detection(args.coordinate_normalization)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(package, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(package["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
