from __future__ import annotations

import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import identity
from identity import (
    IdentityError,
    claims_from_authorization,
    extract_bearer_token,
    fetch_tokeninfo,
    normalize_tokeninfo,
)


class IdentityTests(unittest.TestCase):
    def test_extract_bearer_token_requires_authorization_header(self) -> None:
        with self.assertRaisesRegex(IdentityError, "required"):
            extract_bearer_token(None)
        with self.assertRaisesRegex(IdentityError, "bearer"):
            extract_bearer_token("Basic abc")

        self.assertEqual(extract_bearer_token("Bearer identity-evidence"), "identity-evidence")

    def test_normalize_id_tokeninfo_to_claims(self) -> None:
        claims = normalize_tokeninfo(
            {
                "iss": "https://accounts.google.com",
                "aud": "broker-client-id",
                "exp": "1900000000",
                "sub": "google-subject-1",
                "email": "pilot.user@day1company.co.kr",
                "email_verified": "true",
                "hd": "day1company.co.kr",
            },
            now=100,
        )

        self.assertEqual(claims["aud"], "broker-client-id")
        self.assertEqual(claims["exp"], 1_900_000_000)
        self.assertTrue(claims["email_verified"])

    def test_normalize_access_tokeninfo_to_claims(self) -> None:
        claims = normalize_tokeninfo(
            {
                "audience": "broker-client-id",
                "expires_in": "3600",
                "user_id": "google-subject-1",
                "email": "pilot.user@day1company.co.kr",
                "email_verified": True,
            },
            now=100,
        )

        self.assertEqual(claims["iss"], "https://accounts.google.com")
        self.assertEqual(claims["aud"], "broker-client-id")
        self.assertEqual(claims["exp"], 3700)
        self.assertEqual(claims["sub"], "google-subject-1")

    def test_normalize_chrome_access_tokeninfo_aliases_to_claims(self) -> None:
        claims = normalize_tokeninfo(
            {
                "issued_to": "broker-client-id",
                "expires_in": "3600",
                "user_id": "google-subject-1",
                "email": "pilot.user@day1company.co.kr",
                "verified_email": "true",
            },
            now=100,
        )

        self.assertEqual(claims["aud"], "broker-client-id")
        self.assertTrue(claims["email_verified"])

    def test_fetch_tokeninfo_tries_access_token_before_id_token(self) -> None:
        seen = []
        original_request_json = identity._request_json

        def fake_request_json(url: str) -> dict:
            seen.append(url)
            return {
                "aud": "broker-client-id",
                "expires_in": "3600",
                "user_id": "google-subject-1",
                "email": "pilot.user@day1company.co.kr",
            }

        try:
            identity._request_json = fake_request_json
            tokeninfo = fetch_tokeninfo("local access token/with slash")
        finally:
            identity._request_json = original_request_json

        self.assertEqual(tokeninfo["aud"], "broker-client-id")
        self.assertIn("?access_token=", seen[0])
        self.assertIn("%2F", seen[0])

    def test_claims_from_authorization_uses_tokeninfo_transport(self) -> None:
        seen = []

        def transport(token: str) -> dict:
            seen.append(token)
            return {
                "aud": "broker-client-id",
                "exp": 1_900_000_000,
                "sub": "google-subject-1",
                "email": "pilot.user@day1company.co.kr",
                "email_verified": True,
            }

        claims = claims_from_authorization("Bearer identity-evidence", transport=transport)

        self.assertEqual(seen, ["identity-evidence"])
        self.assertEqual(claims["email"], "pilot.user@day1company.co.kr")


if __name__ == "__main__":
    unittest.main()
