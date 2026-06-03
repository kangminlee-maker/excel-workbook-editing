from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4


DEFAULT_PACKAGE_ROOT = Path("review-packages/sheets-bridge/native-host")
FORBIDDEN_KEY_PARTS = {
    "authorization",
    "bearer",
    "cookie",
    "credential",
    "id_token",
    "access_token",
    "refresh_token",
    "oauth_token",
    "private_key",
    "service_account_key",
    "client_secret",
    "jwt",
    "token",
}
FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9_./+\-=]{8,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"\bya29\.[A-Za-z0-9_\-.]+\b"),
)


class ReviewPackageError(ValueError):
    """Raised when a snapshot cannot be safely persisted."""


def write_inspection_package(
    *,
    message: dict[str, Any],
    package_root: Path | str = DEFAULT_PACKAGE_ROOT,
    now: datetime | None = None,
) -> dict[str, Any]:
    request_id = _safe_request_id(message.get("request_id"))
    payload = _require_object(message.get("payload"), "payload")
    snapshot = _require_object(payload.get("snapshot"), "payload.snapshot")
    if snapshot.get("ok") is False or isinstance(snapshot.get("error"), dict):
        raise ReviewPackageError("denied or failed broker responses are not persisted")

    _reject_credential_material(snapshot)

    created_at = (now or datetime.now(timezone.utc)).isoformat()
    package_dir = Path(package_root) / created_at[:10] / request_id
    package_dir.mkdir(parents=True, exist_ok=False)

    snapshot_path = package_dir / "snapshot.json"
    manifest_path = package_dir / "manifest.json"
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = _snapshot_summary(snapshot)
    manifest = {
        "schema_version": "1.0",
        "artifact_kind": "sheets_bridge_review_package",
        "request_id": request_id,
        "created_at": created_at,
        "source": "chrome_native_messaging",
        "artifacts": [
            {
                "kind": "inspection_snapshot",
                "path": str(snapshot_path.resolve()),
                "summary": summary,
            }
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "artifact_path": str(manifest_path.resolve()),
        "package_dir": str(package_dir.resolve()),
        "snapshot_path": str(snapshot_path.resolve()),
        "summary": summary,
    }


def _reject_credential_material(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ReviewPackageError(f"non-string key at {path}")
            normalized = key.lower().replace("-", "_")
            if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
                raise ReviewPackageError(f"credential-like key rejected at {path}.{key}")
            _reject_credential_material(item, f"{path}.{key}")
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_credential_material(item, f"{path}[{index}]")
        return

    if isinstance(value, str):
        for pattern in FORBIDDEN_VALUE_PATTERNS:
            if pattern.search(value):
                raise ReviewPackageError(f"credential-like value rejected at {path}")


def _snapshot_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    tabs = snapshot.get("tabs")
    return {
        "spreadsheet_id": _safe_string(snapshot.get("spreadsheet_id")),
        "title": _safe_string(snapshot.get("title")),
        "tab_count": len(tabs) if isinstance(tabs, list) else 0,
        "captured_at": _safe_string(snapshot.get("captured_at")),
    }


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewPackageError(f"{label} must be an object")
    return value


def _safe_request_id(value: Any) -> str:
    if isinstance(value, str) and value:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
        if safe:
            return safe[:120]
    return f"native-{uuid4()}"


def _safe_string(value: Any) -> str:
    return value if isinstance(value, str) else ""
