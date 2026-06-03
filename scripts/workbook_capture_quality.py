from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl.utils import range_boundaries

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised only when Pillow is unavailable.
    Image = None  # type: ignore[assignment]

SCHEMA_VERSION = "0.1"

MIN_HEIGHT_PX_FAIL = 50
MIN_HEIGHT_PX_WARN = 120
MIN_PIXELS_PER_ROW_FAIL = 4.0
MIN_PIXELS_PER_ROW_WARN = 8.0
MIN_PIXELS_PER_COLUMN_FAIL = 4.0
MIN_PIXELS_PER_COLUMN_WARN = 8.0
ASPECT_RATIO_FAIL = 25.0
ASPECT_RATIO_WARN = 12.0
WIDE_CAPTURE_WIDTH_WARN = 2200
WIDE_CAPTURE_COLUMN_WARN = 35
VISIBLE_PIXEL_RATIO_FAIL = 0.002
VISIBLE_PIXEL_RATIO_WARN = 0.01


def build_capture_quality(render_captures_path: Path) -> dict[str, Any]:
    render_captures_path = render_captures_path.expanduser().resolve()
    render_captures = _read_json(render_captures_path)
    results = [
        _quality_result(capture)
        for capture in render_captures.get("captures", [])
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "render_captures": str(render_captures_path),
        },
        "method": {
            "name": "deterministic_png_capture_quality",
            "thresholds": {
                "min_height_px_fail": MIN_HEIGHT_PX_FAIL,
                "min_height_px_warn": MIN_HEIGHT_PX_WARN,
                "min_pixels_per_row_fail": MIN_PIXELS_PER_ROW_FAIL,
                "min_pixels_per_row_warn": MIN_PIXELS_PER_ROW_WARN,
                "min_pixels_per_column_fail": MIN_PIXELS_PER_COLUMN_FAIL,
                "min_pixels_per_column_warn": MIN_PIXELS_PER_COLUMN_WARN,
                "aspect_ratio_fail": ASPECT_RATIO_FAIL,
                "aspect_ratio_warn": ASPECT_RATIO_WARN,
                "wide_capture_width_warn": WIDE_CAPTURE_WIDTH_WARN,
                "wide_capture_column_warn": WIDE_CAPTURE_COLUMN_WARN,
                "visible_pixel_ratio_fail": VISIBLE_PIXEL_RATIO_FAIL,
                "visible_pixel_ratio_warn": VISIBLE_PIXEL_RATIO_WARN,
            },
        },
        "quality_results": results,
        "summary": _summary(results),
        "parser_observations": [
            {
                "level": "info",
                "message": "Capture quality checks score PNG usability for downstream visual gates. They do not accept or reject semantic claims.",
            }
        ],
    }


def _quality_result(capture: dict[str, Any]) -> dict[str, Any]:
    output = capture.get("output") or {}
    capture_window = capture.get("capture_window") or {}
    range_text = capture_window.get("range") or capture.get("requested_range")
    png_path = output.get("png_path") or ""
    dimensions = {
        "width": output.get("png_width"),
        "height": output.get("png_height"),
        "size_bytes": output.get("png_size_bytes"),
    }
    range_shape = _range_shape(range_text)
    metrics = _base_metrics(dimensions, range_shape)
    image_metrics = _image_metrics(Path(png_path)) if png_path else {}
    metrics.update(image_metrics)
    checks = _checks(capture, png_path, dimensions, range_shape, metrics)
    status = _status(capture, checks)
    recommendations = _recommendations(status, checks)
    return {
        "id": f"quality_{capture.get('id')}",
        "type": "capture_quality_result",
        "status": status,
        "capture_id": capture.get("id"),
        "target_id": capture.get("target_id"),
        "sheet": capture.get("sheet"),
        "requested_range": capture.get("requested_range"),
        "capture_window_range": range_text,
        "png_path": png_path,
        "dimensions": dimensions,
        "range_shape": range_shape,
        "metrics": metrics,
        "checks": checks,
        "recommendations": recommendations,
        "evidence_refs": [capture.get("id")] if capture.get("id") else [],
        "notes": _notes(status, checks),
    }


def _range_shape(range_text: str | None) -> dict[str, Any]:
    if not range_text:
        return {
            "status": "not_available",
            "min_row": None,
            "min_column": None,
            "max_row": None,
            "max_column": None,
            "row_count": None,
            "column_count": None,
        }
    try:
        min_col, min_row, max_col, max_row = range_boundaries(range_text)
    except ValueError:
        return {
            "status": "parse_failed",
            "min_row": None,
            "min_column": None,
            "max_row": None,
            "max_column": None,
            "row_count": None,
            "column_count": None,
        }
    return {
        "status": "parsed",
        "min_row": min_row,
        "min_column": min_col,
        "max_row": max_row,
        "max_column": max_col,
        "row_count": max_row - min_row + 1,
        "column_count": max_col - min_col + 1,
    }


def _base_metrics(
    dimensions: dict[str, Any],
    range_shape: dict[str, Any],
) -> dict[str, Any]:
    width = dimensions.get("width")
    height = dimensions.get("height")
    rows = range_shape.get("row_count")
    columns = range_shape.get("column_count")
    aspect_ratio = None
    if width and height:
        aspect_ratio = round(max(width / height, height / width), 4)
    return {
        "aspect_ratio": aspect_ratio,
        "pixels_per_row": round(height / rows, 4) if height and rows else None,
        "pixels_per_column": round(width / columns, 4) if width and columns else None,
        "visible_pixel_ratio": None,
        "alpha_coverage_ratio": None,
    }


def _image_metrics(path: Path) -> dict[str, Any]:
    if Image is None:
        return {
            "visible_pixel_ratio": None,
            "alpha_coverage_ratio": None,
        }
    if not path.exists():
        return {
            "visible_pixel_ratio": None,
            "alpha_coverage_ratio": None,
        }
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        max_width = 400
        if rgba.width > max_width:
            height = max(1, int(rgba.height * (max_width / rgba.width)))
            rgba = rgba.resize((max_width, height))
        pixel_source = getattr(rgba, "get_flattened_data", rgba.getdata)
        pixels = list(pixel_source())
    if not pixels:
        return {
            "visible_pixel_ratio": 0.0,
            "alpha_coverage_ratio": 0.0,
        }
    opaque = 0
    visible = 0
    for red, green, blue, alpha in pixels:
        if alpha <= 10:
            continue
        opaque += 1
        if not (red >= 245 and green >= 245 and blue >= 245):
            visible += 1
    total = len(pixels)
    return {
        "visible_pixel_ratio": round(visible / total, 6),
        "alpha_coverage_ratio": round(opaque / total, 6),
    }


def _checks(
    capture: dict[str, Any],
    png_path: str,
    dimensions: dict[str, Any],
    range_shape: dict[str, Any],
    metrics: dict[str, Any],
) -> list[dict[str, str]]:
    checks = [
        _check(
            "capture_status",
            "pass" if capture.get("status") == "captured" else "fail",
            f"Render capture status is {capture.get('status')}.",
        )
    ]
    path = Path(png_path) if png_path else None
    checks.append(
        _check(
            "png_file_exists",
            "pass" if path and path.exists() else "fail",
            f"PNG file {'exists' if path and path.exists() else 'is missing'}: {png_path}",
        )
    )
    width = dimensions.get("width")
    height = dimensions.get("height")
    checks.append(
        _check(
            "dimensions_available",
            "pass" if width and height else "fail",
            f"PNG dimensions are {width} x {height}.",
        )
    )
    checks.append(
        _threshold_check(
            "height_readability",
            height,
            fail_below=MIN_HEIGHT_PX_FAIL,
            warn_below=MIN_HEIGHT_PX_WARN,
            unit="px",
            message="Capture image height should be large enough for visual review.",
        )
    )
    checks.append(
        _threshold_check(
            "pixels_per_row",
            metrics.get("pixels_per_row"),
            fail_below=MIN_PIXELS_PER_ROW_FAIL,
            warn_below=MIN_PIXELS_PER_ROW_WARN,
            unit="px/row",
            message="Rows should have enough rendered height for visual gates.",
        )
    )
    checks.append(
        _threshold_check(
            "pixels_per_column",
            metrics.get("pixels_per_column"),
            fail_below=MIN_PIXELS_PER_COLUMN_FAIL,
            warn_below=MIN_PIXELS_PER_COLUMN_WARN,
            unit="px/column",
            message="Columns should have enough rendered width for visual gates.",
        )
    )
    aspect_ratio = metrics.get("aspect_ratio")
    if aspect_ratio is None:
        checks.append(_check("aspect_ratio", "skipped", "Aspect ratio is unavailable."))
    elif aspect_ratio >= ASPECT_RATIO_FAIL:
        checks.append(
            _check(
                "aspect_ratio",
                "fail",
                f"Aspect ratio {aspect_ratio} exceeds fail threshold {ASPECT_RATIO_FAIL}.",
            )
        )
    elif aspect_ratio >= ASPECT_RATIO_WARN:
        checks.append(
            _check(
                "aspect_ratio",
                "warning",
                f"Aspect ratio {aspect_ratio} exceeds warning threshold {ASPECT_RATIO_WARN}.",
            )
        )
    else:
        checks.append(
            _check("aspect_ratio", "pass", f"Aspect ratio {aspect_ratio} is reviewable.")
        )
    visible = metrics.get("visible_pixel_ratio")
    if visible is None:
        checks.append(
            _check("visible_content", "skipped", "Visible pixel ratio is unavailable.")
        )
    elif visible < VISIBLE_PIXEL_RATIO_FAIL:
        checks.append(
            _check(
                "visible_content",
                "fail",
                f"Visible pixel ratio {visible} is below fail threshold {VISIBLE_PIXEL_RATIO_FAIL}.",
            )
        )
    elif visible < VISIBLE_PIXEL_RATIO_WARN:
        checks.append(
            _check(
                "visible_content",
                "warning",
                f"Visible pixel ratio {visible} is below warning threshold {VISIBLE_PIXEL_RATIO_WARN}.",
            )
        )
    else:
        checks.append(
            _check(
                "visible_content",
                "pass",
                f"Visible pixel ratio {visible} is above blank-image thresholds.",
            )
        )
    columns = range_shape.get("column_count")
    if width and columns and (width >= WIDE_CAPTURE_WIDTH_WARN or columns >= WIDE_CAPTURE_COLUMN_WARN):
        checks.append(
            _check(
                "wide_capture",
                "warning",
                f"Capture spans {columns} columns at {width}px; tiling may improve reviewability.",
            )
        )
    else:
        checks.append(
            _check("wide_capture", "pass", "Capture width does not require tiling by default.")
        )
    return checks


def _threshold_check(
    check_id: str,
    value: float | int | None,
    *,
    fail_below: float,
    warn_below: float,
    unit: str,
    message: str,
) -> dict[str, str]:
    if value is None:
        return _check(check_id, "skipped", f"{message} Value is unavailable.")
    if value < fail_below:
        return _check(
            check_id,
            "fail",
            f"{message} {value} {unit} is below fail threshold {fail_below}.",
        )
    if value < warn_below:
        return _check(
            check_id,
            "warning",
            f"{message} {value} {unit} is below warning threshold {warn_below}.",
        )
    return _check(
        check_id,
        "pass",
        f"{message} {value} {unit} is within threshold.",
    )


def _check(check_id: str, status: str, message: str) -> dict[str, str]:
    severity = "error" if status == "fail" else "warning" if status == "warning" else "info"
    return {
        "id": check_id,
        "type": "capture_quality_check",
        "status": status,
        "severity": severity,
        "message": message,
    }


def _status(capture: dict[str, Any], checks: list[dict[str, str]]) -> str:
    if capture.get("status") != "captured":
        return "capture_failed"
    if any(check["status"] == "fail" for check in checks):
        return "recapture_required"
    if any(check["status"] == "warning" for check in checks):
        return "review_required"
    return "usable"


def _recommendations(status: str, checks: list[dict[str, str]]) -> list[str]:
    check_status = {check["id"]: check["status"] for check in checks}
    recommendations = []
    if status == "capture_failed":
        recommendations.append("rerun_excel_capture")
    if check_status.get("height_readability") == "fail":
        recommendations.append("recapture_with_expanded_window_or_zoom")
    if check_status.get("pixels_per_row") == "fail":
        recommendations.append("recapture_with_visible_row_context")
    if check_status.get("wide_capture") == "warning":
        recommendations.append("recapture_with_tiling")
    if check_status.get("visible_content") == "fail":
        recommendations.append("inspect_for_blank_or_clipped_capture")
    if status == "usable":
        recommendations.append("accept_for_next_visual_gate")
    if status == "review_required" and not recommendations:
        recommendations.append("human_review_before_gate_execution")
    return sorted(set(recommendations))


def _notes(status: str, checks: list[dict[str, str]]) -> str:
    flagged = [check["id"] for check in checks if check["status"] in {"fail", "warning"}]
    if not flagged:
        return "Capture quality checks passed."
    return f"{status}: " + ", ".join(flagged)


def _summary(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "capture_count": len(results),
        "evaluated_count": sum(1 for result in results if result["status"] != "capture_failed"),
        "usable_count": sum(1 for result in results if result["status"] == "usable"),
        "review_required_count": sum(1 for result in results if result["status"] == "review_required"),
        "recapture_required_count": sum(1 for result in results if result["status"] == "recapture_required"),
        "capture_failed_count": sum(1 for result in results if result["status"] == "capture_failed"),
        "too_thin_count": _check_count(results, "height_readability", {"fail", "warning"}),
        "low_row_pixels_count": _check_count(results, "pixels_per_row", {"fail", "warning"}),
        "extreme_aspect_count": _check_count(results, "aspect_ratio", {"fail", "warning"}),
        "low_visible_content_count": _check_count(results, "visible_content", {"fail", "warning"}),
        "tiling_recommended_count": sum(
            1
            for result in results
            if "recapture_with_tiling" in result.get("recommendations", [])
        ),
        "expanded_window_recommended_count": sum(
            1
            for result in results
            if "recapture_with_expanded_window_or_zoom" in result.get("recommendations", [])
        ),
    }


def _check_count(
    results: list[dict[str, Any]],
    check_id: str,
    statuses: set[str],
) -> int:
    count = 0
    for result in results:
        for check in result.get("checks", []):
            if check.get("id") == check_id and check.get("status") in statuses:
                count += 1
                break
    return count


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate workbook render capture PNG usability for visual gates."
    )
    parser.add_argument("render_captures", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    package = build_capture_quality(args.render_captures)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(package["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
