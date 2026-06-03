from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dwd import DwdContext
from token_provider import (
    AUTH_SCHEME,
    IAM_SIGN_JWT_URL_TEMPLATE,
    JWT_GRANT_TYPE,
    OAUTH_TOKEN_URL,
    TokenProviderError,
    build_dwd_jwt_payload,
    exchange_signed_jwt,
    keyless_access_token_provider,
    sign_dwd_jwt,
)


class TokenProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = DwdContext(
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            subject="pilot.user@day1company.co.kr",
            scopes=("https://www.googleapis.com/auth/spreadsheets.readonly",),
        )

    def test_build_dwd_jwt_payload_uses_impersonated_subject(self) -> None:
        payload = build_dwd_jwt_payload(self.context, issued_at=100)

        self.assertEqual(payload["iss"], self.context.service_account_email)
        self.assertEqual(payload["sub"], "pilot.user@day1company.co.kr")
        self.assertEqual(payload["scope"], "https://www.googleapis.com/auth/spreadsheets.readonly")
        self.assertEqual(payload["aud"], OAUTH_TOKEN_URL)
        self.assertEqual(payload["iat"], 100)
        self.assertEqual(payload["exp"], 3700)

    def test_sign_dwd_jwt_uses_iam_credentials_without_private_key(self) -> None:
        calls = []

        def transport(url: str, *, body: dict, headers: dict) -> dict:
            calls.append((url, body, headers))
            return {"signedJwt": "signed-jwt-1"}

        signed_jwt = sign_dwd_jwt(
            self.context,
            runtime_access_token="runtime-token-1",
            transport=transport,
        )

        self.assertEqual(signed_jwt, "signed-jwt-1")
        self.assertEqual(
            calls[0][0],
            IAM_SIGN_JWT_URL_TEMPLATE.format(
                service_account=self.context.service_account_email,
            ),
        )
        self.assertEqual(calls[0][2]["Authorization"], f"{AUTH_SCHEME} runtime-token-1")
        payload = json.loads(calls[0][1]["payload"])
        self.assertEqual(payload["sub"], "pilot.user@day1company.co.kr")

    def test_exchange_signed_jwt_returns_access_token(self) -> None:
        calls = []

        def transport(url: str, *, body: dict, headers: dict) -> dict:
            calls.append((url, body, headers))
            return {"access_token": "dwd-access-token-1"}

        access_token = exchange_signed_jwt("signed-jwt-1", transport=transport)

        self.assertEqual(access_token, "dwd-access-token-1")
        self.assertEqual(calls[0][0], OAUTH_TOKEN_URL)
        self.assertEqual(calls[0][1]["grant_type"], JWT_GRANT_TYPE)
        self.assertEqual(calls[0][1]["assertion"], "signed-jwt-1")

    def test_keyless_access_token_provider_composes_metadata_sign_and_exchange(self) -> None:
        def metadata_token_fetcher() -> str:
            return "runtime-token-1"

        def sign_transport(url: str, *, body: dict, headers: dict) -> dict:
            self.assertIn(":signJwt", url)
            self.assertEqual(headers["Authorization"], f"{AUTH_SCHEME} runtime-token-1")
            return {"signedJwt": "signed-jwt-1"}

        def exchange_transport(url: str, *, body: dict, headers: dict) -> dict:
            self.assertEqual(url, OAUTH_TOKEN_URL)
            self.assertEqual(body["assertion"], "signed-jwt-1")
            return {"access_token": "dwd-access-token-1"}

        access_token = keyless_access_token_provider(
            self.context,
            metadata_token_fetcher=metadata_token_fetcher,
            sign_jwt_transport=sign_transport,
            token_exchange_transport=exchange_transport,
        )

        self.assertEqual(access_token, "dwd-access-token-1")

    def test_keyless_provider_rejects_missing_signed_jwt_or_access_token(self) -> None:
        with self.assertRaisesRegex(TokenProviderError, "signedJwt"):
            sign_dwd_jwt(
                self.context,
                runtime_access_token="runtime-token-1",
                transport=lambda _url, *, body, headers: {},
            )
        with self.assertRaisesRegex(TokenProviderError, "access_token"):
            exchange_signed_jwt(
                "signed-jwt-1",
                transport=lambda _url, *, body, headers: {},
            )


if __name__ == "__main__":
    unittest.main()
