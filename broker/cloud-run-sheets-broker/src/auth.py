from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any


class AuthError(ValueError):
    """Raised when user identity evidence cannot be trusted."""


@dataclass(frozen=True)
class AuthConfig:
    accepted_issuers: tuple[str, ...]
    audience: str
    hosted_domain: str | None = None
    leeway_seconds: int = 60
    accepted_audiences: tuple[str, ...] = ()


def verify_claims(
    claims: dict[str, Any],
    config: AuthConfig,
    *,
    now: int | None = None,
) -> dict[str, Any]:
    current_time = int(time() if now is None else now)
    issuer = _required_string(claims, "iss")
    audience = _required_string(claims, "aud")
    expires_at = _required_int(claims, "exp")
    principal = _principal_from_claims(claims)

    if issuer not in config.accepted_issuers:
        raise AuthError("identity issuer is not allowed")
    if audience not in _accepted_audiences(config):
        raise AuthError("identity audience does not match broker audience")
    if expires_at <= current_time - config.leeway_seconds:
        raise AuthError("identity token is expired")
    if claims.get("email_verified") is False:
        raise AuthError("identity email is not verified")
    if config.hosted_domain and not _matches_domain(claims, principal, config.hosted_domain):
        raise AuthError("identity hosted domain is not allowed")

    return {
        "principal": principal,
        "subject": principal,
        "issuer": issuer,
        "audience": audience,
        "expires_at": expires_at,
        "hosted_domain": claims.get("hd") or principal.rsplit("@", 1)[-1],
    }


def _accepted_audiences(config: AuthConfig) -> tuple[str, ...]:
    return config.accepted_audiences or (config.audience,)


def _principal_from_claims(claims: dict[str, Any]) -> str:
    email = claims.get("email")
    if isinstance(email, str) and "@" in email:
        return email.lower()
    _required_string(claims, "sub")
    raise AuthError("identity email principal is required")


def _matches_domain(
    claims: dict[str, Any],
    principal: str,
    hosted_domain: str,
) -> bool:
    claim_domain = claims.get("hd")
    if isinstance(claim_domain, str) and claim_domain.lower() == hosted_domain.lower():
        return True
    return principal.lower().endswith(f"@{hosted_domain.lower()}")


def _required_string(claims: dict[str, Any], key: str) -> str:
    value = claims.get(key)
    if not isinstance(value, str) or not value:
        raise AuthError(f"identity claim {key} is required")
    return value


def _required_int(claims: dict[str, Any], key: str) -> int:
    value = claims.get(key)
    if not isinstance(value, int):
        raise AuthError(f"identity claim {key} is required")
    return value
