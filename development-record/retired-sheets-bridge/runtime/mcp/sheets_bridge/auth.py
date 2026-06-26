from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
import webbrowser


READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
READWRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
DRIVE_COPY_SCOPES = (DRIVE_FILE_SCOPE, DRIVE_SCOPE)
DEFAULT_SCOPES = (READONLY_SCOPE,)
AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class OAuthConfigError(ValueError):
    """Raised when local OAuth client configuration is missing or invalid."""


class OAuthFlowError(RuntimeError):
    """Raised when an OAuth login or token refresh fails."""


@dataclass(frozen=True)
class OAuthClientConfig:
    client_id: str
    client_secret: str = ""
    scopes: tuple[str, ...] = DEFAULT_SCOPES


def default_config_dir() -> Path:
    override = os.environ.get("SHEETS_BRIDGE_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Day1" / "SheetsBridgeMcp"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Day1" / "SheetsBridgeMcp"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "day1-sheets-bridge"


def token_path(config_dir: Path | None = None) -> Path:
    return (config_dir or default_config_dir()) / "oauth-token.json"


def oauth_config_path(config_dir: Path | None = None) -> Path:
    return (config_dir or default_config_dir()) / "oauth-client.json"


def load_oauth_client_config(config_dir: Path | None = None) -> OAuthClientConfig:
    client_id = os.environ.get("SHEETS_BRIDGE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SHEETS_BRIDGE_OAUTH_CLIENT_SECRET", "").strip()
    scopes = _scopes_from_env()

    path = oauth_config_path(config_dir)
    if path.exists():
        data = _read_json(path)
        client_id = client_id or str(data.get("client_id", "")).strip()
        client_secret = client_secret or str(data.get("client_secret", "")).strip()
        if not scopes and isinstance(data.get("scopes"), list):
            scopes = tuple(str(scope) for scope in data["scopes"] if str(scope).strip())

    if not client_id:
        raise OAuthConfigError(
            "Missing OAuth client id. Set SHEETS_BRIDGE_OAUTH_CLIENT_ID or create oauth-client.json."
        )
    return OAuthClientConfig(
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes or DEFAULT_SCOPES,
    )


def auth_status(config_dir: Path | None = None) -> dict[str, Any]:
    path = token_path(config_dir)
    if not path.exists():
        return {"configured": _oauth_client_configured(config_dir), "authenticated": False}
    token = _read_json(path)
    expires_at = _parse_datetime(str(token.get("expires_at", "")))
    return {
        "configured": _oauth_client_configured(config_dir),
        "authenticated": bool(token.get("refresh_token") or token.get("access_token")),
        "expires_at": expires_at.isoformat() if expires_at else "",
        "expired": bool(expires_at and expires_at <= datetime.now(UTC)),
        "scope": token.get("scope", ""),
        "token_path": str(path),
    }


def login(
    *,
    config_dir: Path | None = None,
    open_browser: bool = True,
    token_transport=None,
) -> dict[str, Any]:
    config = load_oauth_client_config(config_dir)
    state = secrets.token_urlsafe(24)
    server = _OneShotOAuthServer(("127.0.0.1", 0), _OAuthCallbackHandler)
    redirect_uri = f"http://127.0.0.1:{server.server_port}/oauth2callback"
    auth_url = _authorization_url(config=config, redirect_uri=redirect_uri, state=state)

    if open_browser:
        webbrowser.open(auth_url)
    print(f"Open this URL to sign in:\n{auth_url}", file=sys.stderr)

    server.handle_request()
    if server.error:
        raise OAuthFlowError(server.error)
    if server.state != state:
        raise OAuthFlowError("OAuth state mismatch")
    if not server.code:
        raise OAuthFlowError("OAuth authorization code was not returned")

    token = exchange_code_for_token(
        code=server.code,
        config=config,
        redirect_uri=redirect_uri,
        token_transport=token_transport,
    )
    saved_path = save_token(token, config_dir=config_dir)
    return {
        "authenticated": True,
        "token_path": str(saved_path),
        "scope": token.get("scope", ""),
    }


def logout(*, config_dir: Path | None = None) -> dict[str, Any]:
    path = token_path(config_dir)
    if path.exists():
        path.unlink()
    return {"authenticated": False, "token_path": str(path)}


def get_access_token(
    *,
    config_dir: Path | None = None,
    token_transport=None,
    required_scope: str | tuple[str, ...] | None = None,
) -> str:
    path = token_path(config_dir)
    if not path.exists():
        raise OAuthFlowError("Not authenticated. Start the Sheets Bridge OAuth login tool first.")
    token = _read_json(path)
    _require_token_scope(token, required_scope)
    expires_at = _parse_datetime(str(token.get("expires_at", "")))
    if token.get("access_token") and expires_at and expires_at > datetime.now(UTC) + timedelta(seconds=60):
        return str(token["access_token"])

    refresh_token = str(token.get("refresh_token", "")).strip()
    if not refresh_token:
        raise OAuthFlowError("OAuth refresh token is missing. Start the Sheets Bridge OAuth login tool again.")
    config = load_oauth_client_config(config_dir)
    refreshed = refresh_access_token(
        refresh_token=refresh_token,
        config=config,
        token_transport=token_transport,
    )
    merged = {**token, **refreshed, "refresh_token": refreshed.get("refresh_token") or refresh_token}
    _require_token_scope(merged, required_scope)
    save_token(merged, config_dir=config_dir)
    return str(merged["access_token"])


def exchange_code_for_token(
    *,
    code: str,
    config: OAuthClientConfig,
    redirect_uri: str,
    token_transport=None,
) -> dict[str, Any]:
    body = {
        "client_id": config.client_id,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if config.client_secret:
        body["client_secret"] = config.client_secret
    return _normalize_token_response(_post_form(TOKEN_URL, body, token_transport=token_transport))


def refresh_access_token(
    *,
    refresh_token: str,
    config: OAuthClientConfig,
    token_transport=None,
) -> dict[str, Any]:
    body = {
        "client_id": config.client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    if config.client_secret:
        body["client_secret"] = config.client_secret
    return _normalize_token_response(_post_form(TOKEN_URL, body, token_transport=token_transport))


def save_oauth_client_config(
    *,
    client_id: str,
    client_secret: str = "",
    scopes: tuple[str, ...] = DEFAULT_SCOPES,
    config_dir: Path | None = None,
) -> Path:
    path = oauth_config_path(config_dir)
    _write_private_json(
        path,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "scopes": list(scopes),
        },
    )
    return path


def scopes_for_access(access: str) -> tuple[str, ...]:
    normalized = str(access).strip().lower()
    if normalized == "readwrite":
        return (READWRITE_SCOPE,)
    if normalized in {"copy", "drive_file", "readwrite_copy"}:
        return (READWRITE_SCOPE, DRIVE_FILE_SCOPE)
    if normalized in {"copy_full", "drive", "readwrite_drive"}:
        return (READWRITE_SCOPE, DRIVE_SCOPE)
    return DEFAULT_SCOPES


def save_token(token: dict[str, Any], *, config_dir: Path | None = None) -> Path:
    path = token_path(config_dir)
    _write_private_json(path, token)
    return path


def _authorization_url(*, config: OAuthClientConfig, redirect_uri: str, state: str) -> str:
    return (
        AUTHORIZATION_URL
        + "?"
        + urlencode(
            {
                "client_id": config.client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(config.scopes),
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
            }
        )
    )


def _post_form(url: str, body: dict[str, str], *, token_transport=None) -> dict[str, Any]:
    if token_transport:
        return token_transport(url, body)
    request = Request(
        url,
        data=urlencode(body).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _normalize_token_response(response: dict[str, Any]) -> dict[str, Any]:
    if "error" in response:
        raise OAuthFlowError(str(response.get("error_description") or response.get("error")))
    token = dict(response)
    expires_in = int(token.get("expires_in", 3600))
    token["expires_at"] = (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()
    return token


def _write_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
    finally:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise OAuthConfigError(f"{path} must contain a JSON object")
    return data


def _scopes_from_env() -> tuple[str, ...]:
    raw = os.environ.get("SHEETS_BRIDGE_OAUTH_SCOPES", "")
    return tuple(scope.strip() for scope in raw.split(",") if scope.strip())


def _require_token_scope(token: dict[str, Any], required_scope: str | tuple[str, ...] | None) -> None:
    if not required_scope:
        return
    token_scopes = {scope.strip() for scope in str(token.get("scope", "")).split() if scope.strip()}
    acceptable_scopes = (required_scope,) if isinstance(required_scope, str) else tuple(required_scope)
    if not any(scope in token_scopes for scope in acceptable_scopes):
        rendered = acceptable_scopes[0] if len(acceptable_scopes) == 1 else "one of " + ", ".join(acceptable_scopes)
        raise OAuthFlowError(
            f"OAuth token lacks the required write scope {rendered}. Configure OAuth with the needed access mode and start login again."
        )


def _oauth_client_configured(config_dir: Path | None) -> bool:
    return bool(os.environ.get("SHEETS_BRIDGE_OAUTH_CLIENT_ID")) or oauth_config_path(config_dir).exists()


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class _OneShotOAuthServer(HTTPServer):
    code = ""
    state = ""
    error = ""


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        params = parse_qs(urlparse(self.path).query)
        self.server.code = (params.get("code") or [""])[0]
        self.server.state = (params.get("state") or [""])[0]
        self.server.error = (params.get("error") or [""])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Sheets Bridge login complete. You can close this window.\n".encode("utf-8"))

    def log_message(self, _format: str, *_args: Any) -> None:
        return
