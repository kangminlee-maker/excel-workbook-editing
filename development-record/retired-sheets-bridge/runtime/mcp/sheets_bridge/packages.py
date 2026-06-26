from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


DEFAULT_PACKAGE_ROOT = Path("review-packages/sheets-bridge/mcp")


def write_bridge_package(
    *,
    snapshot: dict[str, Any],
    package_root: Path | str = DEFAULT_PACKAGE_ROOT,
    request_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    created_at = (now or datetime.now(UTC)).isoformat()
    safe_request_id = _safe_id(request_id or snapshot.get("snapshot_id") or f"mcp-{created_at}")
    package_dir = Path(package_root) / created_at[:10] / safe_request_id
    package_dir.mkdir(parents=True, exist_ok=False)

    primary_kind = _primary_kind(snapshot)
    snapshot_path = package_dir / "snapshot.json"
    manifest_path = package_dir / "manifest.json"
    handoff_path = package_dir / "mcp-handoff.json"
    _write_json(snapshot_path, snapshot)

    handoff = {
        "schema_version": "1.0",
        "artifact_kind": "sheets_bridge_mcp_handoff",
        "request_id": safe_request_id,
        "created_at": created_at,
        "package_dir": str(package_dir.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "primary_artifact": {
            "kind": primary_kind,
            "path": str(snapshot_path.resolve()),
        },
        "mcp_prompt": f"이 Sheets Bridge 패키지를 분석해줘: {manifest_path.resolve()}",
        "analysis_boundary": [
            "Read manifest.json first.",
            "Use only sanitized local artifacts referenced by the manifest.",
            "Use only credential-free MCP outputs and review artifacts.",
            "Treat the package as a point-in-time snapshot, not as live spreadsheet authority.",
        ],
    }
    _write_json(handoff_path, handoff)

    manifest = {
        "schema_version": "1.0",
        "artifact_kind": "sheets_bridge_mcp_package",
        "request_id": safe_request_id,
        "created_at": created_at,
        "source": _package_source(snapshot),
        "artifacts": [
            {
                "kind": primary_kind,
                "path": str(snapshot_path.resolve()),
                "summary": _snapshot_summary(snapshot),
            },
            {
                "kind": "mcp_handoff",
                "path": str(handoff_path.resolve()),
                "summary": {
                    "manifest_path": str(manifest_path.resolve()),
                    "mcp_prompt": handoff["mcp_prompt"],
                },
            },
        ],
    }
    _write_json(manifest_path, manifest)
    return {
        "package_dir": str(package_dir.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "snapshot_path": str(snapshot_path.resolve()),
        "mcp_handoff_path": str(handoff_path.resolve()),
        "summary": _snapshot_summary(snapshot),
    }


def write_inspection_package(
    *,
    snapshot: dict[str, Any],
    package_root: Path | str = DEFAULT_PACKAGE_ROOT,
    request_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    return write_bridge_package(
        snapshot=snapshot,
        package_root=package_root,
        request_id=request_id,
        now=now,
    )


def _snapshot_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    windows = snapshot.get("windows") if isinstance(snapshot.get("windows"), list) else []
    tabs = snapshot.get("tabs") if isinstance(snapshot.get("tabs"), list) else []
    return {
        "operation": snapshot.get("operation", ""),
        "spreadsheet_id": snapshot.get("spreadsheet_id", ""),
        "title": snapshot.get("title", ""),
        "tab_count": len(tabs),
        "window_count": len(windows),
        "requested_ranges": snapshot.get("requested_ranges", []),
    }


def _primary_kind(snapshot: dict[str, Any]) -> str:
    operation = str(snapshot.get("operation", ""))
    if operation.startswith("apply."):
        return "apply_result"
    if operation.startswith("rollback."):
        return "rollback_result"
    return "inspection_snapshot"


def _package_source(snapshot: dict[str, Any]) -> str:
    for artifact in snapshot.get("artifacts", []) or []:
        if not isinstance(artifact, dict):
            continue
        summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
        if summary.get("mode") == "remote_user_session":
            return "remote_mcp_user_session"
    return "mcp_user_oauth"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_id(value: object) -> str:
    raw = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(value))
    return raw[:120] or "mcp-package"
