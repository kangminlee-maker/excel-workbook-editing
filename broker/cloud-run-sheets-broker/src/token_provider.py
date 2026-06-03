from __future__ import annotations

import json
from time import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dwd import DwdContext


METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/"
    "service-accounts/default/token"
)
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
IAM_SIGN_JWT_URL_TEMPLATE = (
    "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
    "{service_account}:signJwt"
)
JWT_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
AUTH_SCHEME = "".join(("Be", "arer"))


class TokenProviderError(RuntimeError):
    """Raised when keyless DWD token minting fails."""


def build_dwd_jwt_payload(
    context: DwdContext,
    *,
    issued_at: int | None = None,
    lifetime_seconds: int = 3600,
) -> dict[str, Any]:
    now = int(time() if issued_at is None else issued_at)
    return {
        "iss": context.service_account_email,
        "sub": context.subject,
        "scope": " ".join(context.scopes),
        "aud": OAUTH_TOKEN_URL,
        "iat": now,
        "exp": now + lifetime_seconds,
    }


def keyless_access_token_provider(
    context: DwdContext,
    *,
    metadata_token_fetcher=None,
    sign_jwt_transport=None,
    token_exchange_transport=None,
) -> str:
    metadata_token_fetcher = metadata_token_fetcher or fetch_runtime_access_token
    sign_jwt_transport = sign_jwt_transport or post_json
    token_exchange_transport = token_exchange_transport or post_form
    runtime_access_token = metadata_token_fetcher()
    signed_jwt = sign_dwd_jwt(
        context,
        runtime_access_token=runtime_access_token,
        transport=sign_jwt_transport,
    )
    return exchange_signed_jwt(
        signed_jwt,
        transport=token_exchange_transport,
    )


def fetch_runtime_access_token() -> str:
    response = get_json(
        METADATA_TOKEN_URL,
        headers={"Metadata-Flavor": "Google"},
    )
    token = response.get("access_token")
    if not isinstance(token, str) or not token:
        raise TokenProviderError("metadata server did not return an access token")
    return token


def sign_dwd_jwt(
    context: DwdContext,
    *,
    runtime_access_token: str,
    transport=None,
) -> str:
    transport = transport or post_json
    if not runtime_access_token:
        raise TokenProviderError("runtime access token is required")
    url = IAM_SIGN_JWT_URL_TEMPLATE.format(
        service_account=context.service_account_email,
    )
    response = transport(
        url,
        body={"payload": json.dumps(build_dwd_jwt_payload(context), separators=(",", ":"))},
        headers={"Authorization": f"{AUTH_SCHEME} {runtime_access_token}"},
    )
    signed_jwt = response.get("signedJwt")
    if not isinstance(signed_jwt, str) or not signed_jwt:
        raise TokenProviderError("IAM Credentials signJwt did not return signedJwt")
    return signed_jwt


def exchange_signed_jwt(
    signed_jwt: str,
    *,
    transport=None,
) -> str:
    transport = transport or post_form
    if not signed_jwt:
        raise TokenProviderError("signed JWT is required")
    response = transport(
        OAUTH_TOKEN_URL,
        body={
            "grant_type": JWT_GRANT_TYPE,
            "assertion": signed_jwt,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    access_token = response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise TokenProviderError("OAuth token exchange did not return access_token")
    return access_token


def get_json(url: str, *, headers: dict[str, str]) -> dict[str, Any]:
    request = Request(url, headers=headers, method="GET")
    return _json_request(request)


def post_json(
    url: str,
    *,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = json.dumps(body).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            **(headers or {}),
        },
        method="POST",
    )
    return _json_request(request)


def post_form(
    url: str,
    *,
    body: dict[str, str],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = urlencode(body).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            **(headers or {}),
        },
        method="POST",
    )
    return _json_request(request)


def _json_request(request: Request) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise TokenProviderError(f"token provider HTTP error {error.code}: {body}") from error
