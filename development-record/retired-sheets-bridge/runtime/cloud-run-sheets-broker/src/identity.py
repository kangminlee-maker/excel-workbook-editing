from __future__ import annotations

import json
from time import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
DEFAULT_TOKENINFO_ISSUER = "https://accounts.google.com"


class IdentityError(ValueError):
    """Raised when broker user identity evidence is missing or invalid."""


def claims_from_authorization(
    authorization: str | None,
    *,
    transport=None,
    now: int | None = None,
) -> dict[str, Any]:
    transport = transport or fetch_tokeninfo
    token = extract_bearer_token(authorization)
    tokeninfo = transport(token)
    return normalize_tokeninfo(tokeninfo, now=now)


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise IdentityError("Authorization header is required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise IdentityError("Authorization header must use bearer identity evidence")
    return token


def fetch_tokeninfo(token: str) -> dict[str, Any]:
    if not token:
        raise IdentityError("identity token is required")
    errors = []
    for token_param in ("access_token", "id_token"):
        try:
            return _request_json(f"{TOKENINFO_URL}?{token_param}={quote(token, safe='')}")
        except IdentityError as error:
            errors.append(str(error))
    raise IdentityError(
        "tokeninfo request failed for access_token and id_token: " + " | ".join(errors)
    )


def normalize_tokeninfo(
    tokeninfo: dict[str, Any],
    *,
    now: int | None = None,
) -> dict[str, Any]:
    current_time = int(time() if now is None else now)
    audience = tokeninfo.get("aud") or tokeninfo.get("audience") or tokeninfo.get("issued_to")
    expires_at = tokeninfo.get("exp")
    expires_in = tokeninfo.get("expires_in")
    if not isinstance(expires_at, int):
        if isinstance(expires_at, str) and expires_at.isdigit():
            expires_at = int(expires_at)
        elif isinstance(expires_in, int):
            expires_at = current_time + expires_in
        elif isinstance(expires_in, str) and expires_in.isdigit():
            expires_at = current_time + int(expires_in)
    email_verified = tokeninfo.get("email_verified")
    if email_verified is None:
        email_verified = tokeninfo.get("verified_email")
    if isinstance(email_verified, str):
        email_verified = email_verified.lower() == "true"

    return {
        "iss": tokeninfo.get("iss") or DEFAULT_TOKENINFO_ISSUER,
        "aud": audience,
        "exp": expires_at,
        "sub": tokeninfo.get("sub") or tokeninfo.get("user_id") or "",
        "email": tokeninfo.get("email") or "",
        "email_verified": email_verified,
        "hd": tokeninfo.get("hd"),
    }


def _request_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=30) as response:
            value = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise IdentityError(f"tokeninfo request failed with HTTP {error.code}: {body}") from error
    if not isinstance(value, dict):
        raise IdentityError("tokeninfo response must be a JSON object")
    return value
