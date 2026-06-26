from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "mcp"))

from sheets_bridge import auth, remote_auth  # noqa: E402


class RemoteAuthTest(unittest.TestCase):
    def test_file_session_store_loads_session_without_exposing_token_in_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sessions.json"
            path.write_text(
                json.dumps(
                    {
                        "sessions": {
                            "session-1": {
                                "access_token": "access-token-secret",
                                "scopes": [auth.READONLY_SCOPE],
                                "user_email": "user@example.com",
                                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            store = remote_auth.FileRemoteSessionStore(path)
            session = remote_auth.require_remote_session(
                {"Authorization": "Bearer session-1"},
                store=store,
                required_any=remote_auth.READ_SCOPES,
            )

        summary = session.sanitized_summary()
        rendered = json.dumps(summary)
        self.assertEqual(session.access_token, "access-token-secret")
        self.assertEqual(summary["mode"], "remote_user_session")
        self.assertEqual(summary["user_email"], "user@example.com")
        self.assertNotIn("access-token-secret", rendered)

    def test_readwrite_scope_satisfies_readonly_requirement(self) -> None:
        self.assertTrue(remote_auth.scope_satisfied((auth.READWRITE_SCOPE,), auth.READONLY_SCOPE))
        self.assertFalse(remote_auth.scope_satisfied((auth.READONLY_SCOPE,), auth.READWRITE_SCOPE))

    def test_missing_session_and_missing_scope_raise_structured_errors(self) -> None:
        store = _MemoryStore(
            {
                "readonly": remote_auth.RemoteSession(
                    session_id="readonly",
                    access_token="access-token-secret",
                    scopes=(auth.READONLY_SCOPE,),
                )
            }
        )

        with self.assertRaises(remote_auth.RemoteAuthError) as missing:
            remote_auth.require_remote_session({}, store=store, required_any=remote_auth.READ_SCOPES)
        with self.assertRaises(remote_auth.RemoteAuthError) as denied:
            remote_auth.require_remote_session(
                {"Authorization": "Bearer readonly"},
                store=store,
                required_all=(auth.READWRITE_SCOPE,),
            )

        self.assertEqual(missing.exception.status, "remote_auth_required")
        self.assertEqual(denied.exception.status, "remote_permission_denied")
        self.assertIn(auth.READWRITE_SCOPE, denied.exception.required_scopes)
        rendered = json.dumps(denied.exception.to_result(tool="write"))
        self.assertNotIn("access-token-secret", rendered)

    def test_remote_auth_status_reports_expired_session_without_credentials(self) -> None:
        store = _MemoryStore(
            {
                "expired": remote_auth.RemoteSession(
                    session_id="expired",
                    access_token="expired-token",
                    scopes=(auth.READONLY_SCOPE,),
                    expires_at=datetime.now(UTC) - timedelta(minutes=1),
                )
            }
        )

        status = remote_auth.remote_auth_status({"X-Sheets-Bridge-Session": "expired"}, store=store)

        rendered = json.dumps(status)
        self.assertEqual(status["status"], "remote_session_expired")
        self.assertFalse(status["authenticated"])
        self.assertNotIn("expired-token", rendered)


class _MemoryStore(remote_auth.RemoteSessionStore):
    def __init__(self, sessions: dict[str, remote_auth.RemoteSession]) -> None:
        self.sessions = sessions

    def configured(self) -> bool:
        return True

    def get(self, session_id: str) -> remote_auth.RemoteSession | None:
        return self.sessions.get(session_id)


if __name__ == "__main__":
    unittest.main()
