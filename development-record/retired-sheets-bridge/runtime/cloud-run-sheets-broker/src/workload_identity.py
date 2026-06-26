from __future__ import annotations

from typing import Any


AUTHORITY_MODE = "workload_identity"
DELEGATION_MODE = "domain_wide_delegation"
TOKEN_FLOW = (
    "runtime_identity_metadata",
    "iam_credentials_sign_jwt",
    "oauth_jwt_bearer_exchange",
)


def build_readiness_summary(runtime_config: dict[str, Any]) -> dict[str, Any]:
    auth_config = runtime_config.get("auth_config")
    audience = getattr(auth_config, "audience", "")
    accepted_audiences = getattr(auth_config, "accepted_audiences", ()) or (
        (audience,) if audience else ()
    )
    checks = {
        "broker_audience": bool(audience),
        "accepted_audiences": bool(accepted_audiences),
        "delegated_identity": bool(runtime_config.get("service_account_email")),
        "broker_policy": isinstance(runtime_config.get("policy"), dict),
    }
    return {
        "authority_mode": AUTHORITY_MODE,
        "delegation_mode": DELEGATION_MODE,
        "ready": all(checks.values()),
        "configured": checks,
        "accepted_audience_count": len(accepted_audiences),
        "hosted_domain_required": bool(getattr(auth_config, "hosted_domain", None)),
        "token_flow": list(TOKEN_FLOW),
        "live_probe": "deferred_to_authorized_inspect_or_sre_smoke",
    }
