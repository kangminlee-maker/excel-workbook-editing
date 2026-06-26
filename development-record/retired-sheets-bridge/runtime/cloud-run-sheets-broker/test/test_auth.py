from __future__ import annotations

import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth import AuthConfig, AuthError, verify_claims


class AuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AuthConfig(
            accepted_issuers=("https://accounts.google.com", "accounts.google.com"),
            audience="broker-client-id",
            hosted_domain="day1company.co.kr",
        )
        self.claims = {
            "iss": "https://accounts.google.com",
            "aud": "broker-client-id",
            "exp": 1_000,
            "sub": "google-subject-1",
            "email": "Pilot.User@day1company.co.kr",
            "email_verified": True,
            "hd": "day1company.co.kr",
        }

    def test_verify_claims_returns_lowercase_principal_for_allowed_identity(self) -> None:
        verified = verify_claims(self.claims, self.config, now=900)

        self.assertEqual(verified["principal"], "pilot.user@day1company.co.kr")
        self.assertEqual(verified["subject"], "pilot.user@day1company.co.kr")
        self.assertEqual(verified["issuer"], "https://accounts.google.com")
        self.assertEqual(verified["audience"], "broker-client-id")

    def test_verify_claims_denies_invalid_issuer(self) -> None:
        with self.assertRaisesRegex(AuthError, "issuer"):
            verify_claims({**self.claims, "iss": "https://evil.example"}, self.config, now=900)

    def test_verify_claims_denies_invalid_audience(self) -> None:
        with self.assertRaisesRegex(AuthError, "audience"):
            verify_claims({**self.claims, "aud": "other-client"}, self.config, now=900)

    def test_verify_claims_accepts_additional_mcp_audience(self) -> None:
        config = AuthConfig(
            accepted_issuers=("https://accounts.google.com",),
            audience="mcp-client-id",
            accepted_audiences=("mcp-client-id", "32555940559.apps.googleusercontent.com"),
            hosted_domain="day1company.co.kr",
        )

        verified = verify_claims(
            {**self.claims, "aud": "32555940559.apps.googleusercontent.com"},
            config,
            now=900,
        )

        self.assertEqual(verified["audience"], "32555940559.apps.googleusercontent.com")

    def test_verify_claims_denies_expired_token(self) -> None:
        with self.assertRaisesRegex(AuthError, "expired"):
            verify_claims({**self.claims, "exp": 839}, self.config, now=900)

    def test_verify_claims_denies_unverified_email(self) -> None:
        with self.assertRaisesRegex(AuthError, "email"):
            verify_claims({**self.claims, "email_verified": False}, self.config, now=900)

    def test_verify_claims_denies_wrong_hosted_domain(self) -> None:
        with self.assertRaisesRegex(AuthError, "domain"):
            verify_claims(
                {
                    **self.claims,
                    "email": "pilot.user@example.com",
                    "hd": "example.com",
                },
                self.config,
                now=900,
            )

    def test_verify_claims_denies_missing_email_principal(self) -> None:
        claims = {**self.claims}
        claims.pop("email")

        with self.assertRaisesRegex(AuthError, "email principal"):
            verify_claims(claims, self.config, now=900)


if __name__ == "__main__":
    unittest.main()
