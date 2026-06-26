from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any, Mapping

from . import auth


REMOTE_SESSIONS_ENV = "SHEETS_BRIDGE_REMOTE_AUTH_SESSIONS_PATH"
READ_SCOPES = (auth.READONLY_SCOPE, auth.READWRITE_SCOPE)


class RemoteAuthError(RuntimeError):
    def __init__(
        self,
        *,
        status: str,
        reason: str,
        next_action: str,
        required_scopes: tuple[str, ...] = (),
        granted_scopes: tuple[str, ...] = (),
        session_id_present: bool = False,
    ) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.next_action = next_action
        self.required_scopes = required_scopes
        self.granted_scopes = granted_scopes
        self.session_id_present = session_id_present

    def to_result(self, *, tool: str = "") -> dict[str, Any]:
        return {
            "operation": "remote.auth",
            "status": self.status,
            "tool": tool,
            "reason": self.reason,
            "next_action": self.next_action,
            "required_runtime": "remote_authorized_google_sheets_session",
            "session_id_present": self.session_id_present,
            "required_scopes": list(self.required_scopes),
            "granted_scopes": list(self.granted_scopes),
            "credential_boundary": credential_boundary(),
        }


@dataclass(frozen=True)
class RemoteSession:
    session_id: str
    access_token: str
    scopes: tuple[str, ...]
    user_email: str = ""
    subject: str = ""
    authority: str = "remote_user_oauth"
    expires_at: datetime | None = None

    @property
    def expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= datetime.now(UTC))

    def sanitized_summary(self) -> dict[str, Any]:
        return {
            "mode": "remote_user_session",
            "authority": self.authority,
            "session_id_present": bool(self.session_id),
            "user_email": self.user_email,
            "subject": self.subject,
            "scopes": list(self.scopes),
            "expires_at": self.expires_at.isoformat() if self.expires_at else "",
            "expired": self.expired,
            "credential_boundary": credential_boundary(),
        }


class RemoteSessionStore:
    def get(self, session_id: str) -> RemoteSession | None:
        raise NotImplementedError

    def configured(self) -> bool:
        return False


class FileRemoteSessionStore(RemoteSessionStore):
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path).expanduser() if path else remote_sessions_path()

    def configured(self) -> bool:
        return bool(self.path and self.path.exists())

    def get(self, session_id: str) -> RemoteSession | None:
        if not session_id or not self.path or not self.path.exists():
            return None
        data = _read_json(self.path)
        raw_session = _session_record(data, session_id)
        if not raw_session:
            return None
        return _remote_session_from_record(session_id, raw_session)


def default_remote_session_store() -> RemoteSessionStore:
    return FileRemoteSessionStore()


def remote_sessions_path() -> Path | None:
    raw_path = os.environ.get(REMOTE_SESSIONS_ENV, "").strip()
    if not raw_path:
        return None
    return Path(raw_path).expanduser()


def remote_auth_status(
    headers: Mapping[str, str] | Any,
    *,
    store: RemoteSessionStore | None = None,
) -> dict[str, Any]:
    store = store or default_remote_session_store()
    session_id = session_id_from_headers(headers)
    result: dict[str, Any] = {
        "operation": "remote.auth_status",
        "configured": store.configured(),
        "authenticated": False,
        "session_id_present": bool(session_id),
        "credential_boundary": credential_boundary(),
    }
    if not session_id:
        result["status"] = "remote_auth_required"
        return result
    session = store.get(session_id)
    if not session:
        result["status"] = "remote_session_not_found"
        return result
    result.update(session.sanitized_summary())
    result["authenticated"] = not session.expired
    result["status"] = "authenticated" if not session.expired else "remote_session_expired"
    return result


def require_remote_session(
    headers: Mapping[str, str] | Any,
    *,
    store: RemoteSessionStore | None = None,
    required_all: tuple[str, ...] = (),
    required_any: tuple[str, ...] = (),
) -> RemoteSession:
    store = store or default_remote_session_store()
    session_id = session_id_from_headers(headers)
    if not session_id:
        raise RemoteAuthError(
            status="remote_auth_required",
            reason="A remote Sheets operation requires an authorized remote MCP session.",
            next_action="Authorize the remote MCP session, then retry the tool call.",
            required_scopes=tuple(required_all or required_any),
            session_id_present=False,
        )
    session = store.get(session_id)
    if not session:
        raise RemoteAuthError(
            status="remote_session_not_found",
            reason="The remote session handle was not found in the approved session store.",
            next_action="Start or refresh the remote MCP session authorization.",
            required_scopes=tuple(required_all or required_any),
            session_id_present=True,
        )
    if session.expired:
        raise RemoteAuthError(
            status="remote_session_expired",
            reason="The remote session has expired.",
            next_action="Refresh or reauthorize the remote MCP session.",
            required_scopes=tuple(required_all or required_any),
            granted_scopes=session.scopes,
            session_id_present=True,
        )
    missing = tuple(scope for scope in required_all if not scope_satisfied(session.scopes, scope))
    any_ok = not required_any or any(scope_satisfied(session.scopes, scope) for scope in required_any)
    if missing or not any_ok:
        required = missing or required_any
        raise RemoteAuthError(
            status="remote_permission_denied",
            reason="The remote session does not include the scope required for this operation.",
            next_action="Reauthorize the remote MCP session with the requested access level.",
            required_scopes=tuple(required),
            granted_scopes=session.scopes,
            session_id_present=True,
        )
    return session


def session_id_from_headers(headers: Mapping[str, str] | Any) -> str:
    explicit = _header_value(headers, "X-Sheets-Bridge-Session")
    if explicit:
        return explicit
    authorization = _header_value(headers, "Authorization")
    prefix = "Bearer "
    if authorization.startswith(prefix):
        return authorization[len(prefix):].strip()
    return ""


def scope_satisfied(granted_scopes: tuple[str, ...], required_scope: str) -> bool:
    granted = set(granted_scopes)
    if required_scope == auth.READONLY_SCOPE:
        return auth.READONLY_SCOPE in granted or auth.READWRITE_SCOPE in granted
    if required_scope == auth.DRIVE_FILE_SCOPE:
        return auth.DRIVE_FILE_SCOPE in granted or auth.DRIVE_SCOPE in granted
    return required_scope in granted


def credential_boundary() -> dict[str, bool]:
    return {
        "access_token_returned": False,
        "refresh_token_returned": False,
        "raw_credentials_returned": False,
        "local_oauth_cache_visible": False,
    }


def _header_value(headers: Mapping[str, str] | Any, name: str) -> str:
    if hasattr(headers, "get"):
        value = headers.get(name) or headers.get(name.lower())
        return str(value or "").strip()
    return ""


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise RemoteAuthError(
            status="remote_session_store_invalid",
            reason="Remote session store must contain a JSON object.",
            next_action="Check the configured remote session store.",
        )
    return data


def _session_record(data: dict[str, Any], session_id: str) -> dict[str, Any]:
    sessions = data.get("sessions")
    if isinstance(sessions, dict) and isinstance(sessions.get(session_id), dict):
        return sessions[session_id]
    if isinstance(sessions, list):
        for item in sessions:
            if isinstance(item, dict) and str(item.get("session_id") or "") == session_id:
                return item
    if str(data.get("session_id") or "") == session_id:
        return data
    return {}


def _remote_session_from_record(session_id: str, record: dict[str, Any]) -> RemoteSession:
    access_token = str(record.get("access_token") or "").strip()
    if not access_token:
        raise RemoteAuthError(
            status="remote_session_invalid",
            reason="The remote session record does not contain an access token.",
            next_action="Refresh or replace the remote session record in approved storage.",
            session_id_present=True,
        )
    return RemoteSession(
        session_id=session_id,
        access_token=access_token,
        scopes=_scopes_from_record(record),
        user_email=str(record.get("user_email") or record.get("email") or ""),
        subject=str(record.get("subject") or record.get("user") or ""),
        authority=str(record.get("authority") or "remote_user_oauth"),
        expires_at=_parse_datetime(str(record.get("expires_at") or "")),
    )


def _scopes_from_record(record: dict[str, Any]) -> tuple[str, ...]:
    if isinstance(record.get("scopes"), list):
        return tuple(str(scope).strip() for scope in record["scopes"] if str(scope).strip())
    return tuple(scope.strip() for scope in str(record.get("scope") or "").split() if scope.strip())


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
