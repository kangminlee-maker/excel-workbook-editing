from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"
APPLESCRIPT_PATH = Path(__file__).with_name("excel_copy_ranges_png.applescript")
MAC_EXCEL_CONTAINER_DOCUMENTS = (
    Path.home() / "Library/Containers/com.microsoft.Excel/Data/Documents"
)
DEFAULT_SANDBOX_SUBDIR = "excel_workbook_editing_capture"


class RenderCaptureError(RuntimeError):
    """Raised when Excel render capture cannot complete."""


def run_render_capture(
    workbook_path: Path,
    cross_validation_plan_path: Path,
    output_dir: Path,
    *,
    batch: str = "recommended",
    target_ids: list[str] | None = None,
    limit: int | None = None,
    timeout: int = 900,
) -> dict[str, Any]:
    _ensure_platform_helper()
    workbook_path = workbook_path.expanduser().resolve()
    cross_validation_plan_path = cross_validation_plan_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not workbook_path.exists():
        raise FileNotFoundError(f"missing workbook: {workbook_path}")
    plan = _read_json(cross_validation_plan_path)
    targets = _select_targets(plan, batch=batch, target_ids=target_ids, limit=limit)
    output_dir.mkdir(parents=True, exist_ok=True)
    captures_dir = output_dir / "captures"
    captures_dir.mkdir(parents=True, exist_ok=True)

    png_paths = {
        target["id"]: captures_dir / f"{_capture_file_stem(index, target)}.png"
        for index, target in enumerate(targets, 1)
    }

    observations: list[dict[str, str]] = []
    excel_results: dict[str, dict[str, str]] = {}
    with _sandboxed_workbook(workbook_path) as sandbox_workbook:
        targets_tsv = output_dir / "capture-targets.tsv"
        _write_targets_tsv(targets_tsv, targets, png_paths)
        excel_results = _run_excel_png_capture(
            sandbox_workbook,
            targets_tsv,
            targets,
            timeout=timeout,
            observations=observations,
        )

    captures = []
    for target in targets:
        target_id = target["id"]
        png_path = png_paths[target_id]
        result = excel_results.get(target_id) or {
            "status": "error",
            "message": "Excel export did not return a status for this target.",
        }
        capture = _capture_record(
            target,
            png_path,
            result,
            observations=observations,
        )
        captures.append(capture)

    gate_results = [
        gate_result
        for capture in captures
        for gate_result in capture.get("gate_results", [])
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_artifacts": {
            "cross_validation_plan": str(cross_validation_plan_path),
        },
        "source_workbook": {
            "path": str(workbook_path),
            "file_name": workbook_path.name,
            "size_bytes": workbook_path.stat().st_size,
            "sha256": _sha256(workbook_path),
        },
        "method": {
            "engine": "Microsoft Excel",
            "capture_method": "range_copy_picture_png",
            "helper": str(APPLESCRIPT_PATH),
            "sandbox_copy": True,
            "png_export_settings": {
                "appearance": "screen",
                "format": "picture",
            },
        },
        "selected_target_ids": [target["id"] for target in targets],
        "captures": captures,
        "gate_results": gate_results,
        "summary": _summary(captures, gate_results),
        "parser_observations": observations,
    }


def _select_targets(
    plan: dict[str, Any],
    *,
    batch: str,
    target_ids: list[str] | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    targets = plan.get("capture_targets", [])
    target_by_id = {target["id"]: target for target in targets}
    if target_ids:
        selected = [target_by_id[target_id] for target_id in target_ids if target_id in target_by_id]
    elif batch == "recommended":
        selected = [
            target_by_id[target_id]
            for target_id in plan.get("recommended_first_batch_target_ids", [])
            if target_id in target_by_id
        ]
    elif batch == "high":
        selected = [target for target in targets if target.get("priority") == "high"]
    elif batch == "all":
        selected = list(targets)
    else:
        raise ValueError(f"unknown batch: {batch}")
    if limit is not None:
        selected = selected[:limit]
    return selected


def _ensure_platform_helper() -> None:
    if platform.system() != "Darwin":
        raise RenderCaptureError(
            "Microsoft Excel render capture is currently implemented for macOS only."
        )
    if not APPLESCRIPT_PATH.exists():
        raise FileNotFoundError(f"missing AppleScript helper: {APPLESCRIPT_PATH}")
    if shutil.which("osascript") is None:
        raise RenderCaptureError("osascript is not available.")


def _sandbox_root() -> Path:
    override = os.environ.get("EXCEL_RENDER_CAPTURE_SANDBOX_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if MAC_EXCEL_CONTAINER_DOCUMENTS.exists():
        return MAC_EXCEL_CONTAINER_DOCUMENTS / DEFAULT_SANDBOX_SUBDIR
    raise RenderCaptureError(
        "Microsoft Excel sandbox container not found. Open Microsoft Excel once, then retry capture."
    )


class _sandboxed_workbook:
    def __init__(self, workbook_path: Path) -> None:
        self.workbook_path = workbook_path
        self.tmpdir: tempfile.TemporaryDirectory[str] | None = None
        self.copy_path: Path | None = None

    def __enter__(self) -> Path:
        root = _sandbox_root()
        root.mkdir(parents=True, exist_ok=True)
        self.tmpdir = tempfile.TemporaryDirectory(prefix="run_", dir=str(root))
        self.copy_path = Path(self.tmpdir.name) / self.workbook_path.name
        shutil.copy2(self.workbook_path, self.copy_path)
        return self.copy_path

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.tmpdir is not None:
            self.tmpdir.cleanup()


def _write_targets_tsv(
    path: Path,
    targets: list[dict[str, Any]],
    png_paths: dict[str, Path],
) -> None:
    lines = []
    for target in targets:
        capture_window = target.get("capture_window") or {}
        sheet = capture_window.get("sheet") or target.get("sheet")
        range_text = capture_window.get("range") or target.get("range")
        if not sheet or not range_text:
            continue
        lines.append(
            "\t".join(
                [
                    target["id"],
                    str(sheet),
                    str(range_text),
                    str(png_paths[target["id"]]),
                ]
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_excel_png_capture(
    sandbox_workbook: Path,
    targets_tsv: Path,
    targets: list[dict[str, Any]],
    *,
    timeout: int,
    observations: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    cmd = [
        "/usr/bin/osascript",
        str(APPLESCRIPT_PATH),
        str(sandbox_workbook),
        str(targets_tsv),
    ]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        observations.append(
            {
                "level": "error",
                "message": "Excel render capture timed out. Close modal Excel dialogs and retry.",
            }
        )
        return _failed_results(targets, "Excel render capture timed out.")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        observations.append(
            {
                "level": "error",
                "message": f"Excel render capture failed: {detail}",
            }
        )
        return _failed_results(targets, detail or "Excel render capture failed.")

    return _parse_excel_results(result.stdout)


def _parse_excel_results(output: str) -> dict[str, dict[str, str]]:
    results: dict[str, dict[str, str]] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        target_id, status, message = parts
        results[target_id] = {"status": status, "message": message}
    return results


def _failed_results(targets: list[dict[str, Any]], message: str) -> dict[str, dict[str, str]]:
    return {
        target["id"]: {"status": "error", "message": message}
        for target in targets
    }


def _capture_record(
    target: dict[str, Any],
    png_path: Path,
    result: dict[str, str],
    *,
    observations: list[dict[str, str]],
) -> dict[str, Any]:
    status = "capture_failed"
    output = {
        "pdf_path": None,
        "png_path": str(png_path),
        "pdf_size_bytes": None,
        "png_size_bytes": None,
        "png_width": None,
        "png_height": None,
    }
    if result.get("status") == "captured" and png_path.exists():
        status = "captured"
        output["png_size_bytes"] = png_path.stat().st_size
        width, height = _png_dimensions(png_path)
        output["png_width"] = width
        output["png_height"] = height
    capture_window = target.get("capture_window") or {}
    gate_status = "captured_pending_review" if status == "captured" else "capture_failed"
    gate_results = [
        {
            "id": f"result_{_slug(gate.get('id', 'gate'))}",
            "type": "visual_formula_gate_result",
            "capture_id": f"capture_{_slug(target['id'])}",
            "target_id": target["id"],
            "gate_check_id": gate.get("id"),
            "gate_type": gate.get("gate_type"),
            "status": gate_status,
            "evidence_refs": [f"capture_{_slug(target['id'])}"],
            "notes": (
                "Excel range PNG capture exists; visual semantic pass/fail still requires bbox normalization or reviewer confirmation."
                if status == "captured"
                else result.get("message", "Capture failed.")
            ),
        }
        for gate in target.get("gate_checks", [])
    ]
    return {
        "id": f"capture_{_slug(target['id'])}",
        "type": "render_capture",
        "status": status,
        "target_id": target["id"],
        "sheet": capture_window.get("sheet") or target.get("sheet"),
        "requested_range": target.get("range"),
        "capture_window": capture_window,
        "target_ref": target.get("target_ref"),
        "output": output,
        "coordinate_map": {
            "status": "range_image_only" if status == "captured" else "not_available",
            "cell_range": capture_window.get("range"),
            "capture_bbox": (
                {
                    "x": 0,
                    "y": 0,
                    "width": output["png_width"],
                    "height": output["png_height"],
                }
                if output["png_width"] and output["png_height"]
                else None
            ),
        },
        "gate_results": gate_results,
        "parser_observations": [
            {
                "level": "info" if status == "captured" else "error",
                "message": result.get("message", ""),
            }
        ],
    }


def _png_dimensions(path: Path) -> tuple[int | None, int | None]:
    with path.open("rb") as handle:
        signature = handle.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            return None, None
        length = handle.read(4)
        chunk_type = handle.read(4)
        if len(length) != 4 or chunk_type != b"IHDR":
            return None, None
        data = handle.read(8)
        if len(data) != 8:
            return None, None
        return struct.unpack(">II", data)


def _summary(
    captures: list[dict[str, Any]],
    gate_results: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "selected_target_count": len(captures),
        "captured_count": sum(1 for capture in captures if capture["status"] == "captured"),
        "failed_count": sum(1 for capture in captures if capture["status"] != "captured"),
        "png_count": sum(
            1 for capture in captures if capture.get("output", {}).get("png_size_bytes")
        ),
        "gate_result_count": len(gate_results),
        "captured_pending_review_gate_count": sum(
            1 for gate in gate_results if gate["status"] == "captured_pending_review"
        ),
        "capture_failed_gate_count": sum(
            1 for gate in gate_results if gate["status"] == "capture_failed"
        ),
    }


def _capture_file_stem(index: int, target: dict[str, Any]) -> str:
    digest = hashlib.sha1(target["id"].encode("utf-8")).hexdigest()[:10]
    return f"capture_{index:03d}_{digest}"


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower()


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
        description="Capture workbook target ranges through Microsoft Excel copy-picture PNG export."
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("cross_validation_plan", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        help="JSON output path. Defaults to <output-dir>/render-captures.json.",
    )
    parser.add_argument(
        "--batch",
        choices=["recommended", "high", "all"],
        default="recommended",
    )
    parser.add_argument("--target-id", action="append", dest="target_ids")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    output_path = args.output or args.output_dir / "render-captures.json"
    package = run_render_capture(
        args.workbook,
        args.cross_validation_plan,
        args.output_dir,
        batch=args.batch,
        target_ids=args.target_ids,
        limit=args.limit,
        timeout=args.timeout,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(package["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
