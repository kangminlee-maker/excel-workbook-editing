from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from auth import AuthConfig
from broker import handle_inspect_request
from identity import IdentityError, claims_from_authorization
from sheets_client import http_metadata_transport
from token_provider import keyless_access_token_provider


DEFAULT_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
AUDIT_EVENT_TYPE = "sheets_broker.inspect"
AUDIT_LOGGER = logging.getLogger("sheets_broker.audit")


def load_runtime_config(env: dict[str, str] | None = None) -> dict[str, Any]:
    values = env or os.environ
    audience = values.get("BROKER_AUDIENCE", "")
    accepted_audiences = _accepted_audiences(values, audience)
    service_account_email = values.get("BROKER_SERVICE_ACCOUNT_EMAIL", "")
    policy_json = values.get("BROKER_POLICY_JSON", "{}")
    if not audience:
        raise RuntimeError("BROKER_AUDIENCE is required")
    if not service_account_email:
        raise RuntimeError("BROKER_SERVICE_ACCOUNT_EMAIL is required")
    policy = json.loads(policy_json)
    if not isinstance(policy, dict):
        raise RuntimeError("BROKER_POLICY_JSON must be a JSON object")
    issuers = tuple(
        value.strip()
        for value in values.get("BROKER_ACCEPTED_ISSUERS", ",".join(DEFAULT_ISSUERS)).split(",")
        if value.strip()
    )
    return {
        "auth_config": AuthConfig(
            accepted_issuers=issuers,
            audience=audience,
            accepted_audiences=accepted_audiences,
            hosted_domain=values.get("BROKER_HOSTED_DOMAIN") or None,
        ),
        "policy": policy,
        "service_account_email": service_account_email,
    }


def _accepted_audiences(values: dict[str, str], primary_audience: str) -> tuple[str, ...]:
    audiences: list[str] = []
    for raw in (primary_audience, values.get("BROKER_ADDITIONAL_AUDIENCES", "")):
        audiences.extend(value.strip() for value in raw.split(",") if value.strip())
    return tuple(dict.fromkeys(audiences))


def dispatch_inspect(
    *,
    authorization: str | None,
    request: dict[str, Any],
    auth_config: AuthConfig,
    policy: dict[str, Any],
    service_account_email: str,
    identity_transport=None,
    access_token_provider=keyless_access_token_provider,
    metadata_transport=http_metadata_transport,
    audit_sink=None,
) -> tuple[int, dict[str, Any]]:
    try:
        if identity_transport is None:
            identity_claims = claims_from_authorization(authorization)
        else:
            identity_claims = claims_from_authorization(
                authorization,
                transport=identity_transport,
            )
    except IdentityError as error:
        status, result = 401, _error("identity_evidence_failed", str(error))
    else:
        result = handle_inspect_request(
            request=request,
            identity_claims=identity_claims,
            policy=policy,
            auth_config=auth_config,
            service_account_email=service_account_email,
            access_token_provider=access_token_provider,
            metadata_transport=metadata_transport,
        )
        status = _status_for_result(result)

    _emit_audit_event(
        status=status,
        request=request,
        result=result,
        audit_sink=audit_sink if audit_sink is not None else write_audit_event,
    )
    return status, result


def identity_authorization(headers) -> str | None:
    return headers.get("X-Broker-Authorization") or headers.get("Authorization")


def make_handler(runtime_config: dict[str, Any]):
    class SheetsBrokerHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/v1/health":
                self._write_json(404, _error("not_found", "unknown broker path"))
                return
            self._write_json(
                200,
                {
                    "ok": True,
                    "service": "cloud-run-sheets-broker",
                },
            )

        def do_POST(self) -> None:
            if self.path != "/v1/inspect":
                self._write_json(404, _error("not_found", "unknown broker path"))
                return
            request: dict[str, Any] = {}
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                parsed_request = json.loads(body)
                if not isinstance(parsed_request, dict):
                    raise ValueError("request body must be a JSON object")
                request = parsed_request
            except Exception as error:
                result = _error("bad_request", str(error))
                _emit_audit_event(
                    status=400,
                    request=request,
                    result=result,
                    audit_sink=runtime_config.get("audit_sink") or write_audit_event,
                )
                self._write_json(400, result)
                return

            status, result = dispatch_inspect(
                authorization=identity_authorization(self.headers),
                request=request,
                auth_config=runtime_config["auth_config"],
                policy=runtime_config["policy"],
                service_account_email=runtime_config["service_account_email"],
                audit_sink=runtime_config.get("audit_sink") or write_audit_event,
            )
            self._write_json(status, result)

        def log_message(self, _format: str, *_args) -> None:
            return

        def _write_json(self, status: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return SheetsBrokerHandler


def _status_for_result(result: dict[str, Any]) -> int:
    if result.get("ok"):
        return 200
    code = (result.get("error") or {}).get("code")
    if code == "auth_failed":
        return 401
    if code == "policy_denied":
        return 403
    if code in {
        "credential_failed",
        "dwd_subject_failed",
        "sheets_metadata_failed",
        "sheets_window_failed",
    }:
        return 502
    return 400


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _emit_audit_event(
    *,
    status: int,
    request: dict[str, Any],
    result: dict[str, Any],
    audit_sink,
) -> None:
    if audit_sink is None:
        return
    audit_sink(_build_audit_event(status=status, request=request, result=result))


def _build_audit_event(
    *,
    status: int,
    request: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    policy_summary = _policy_summary_from_result(result)
    auth_summary = _auth_summary_from_result(result)
    error = result.get("error") if isinstance(result.get("error"), dict) else {}
    return {
        "event": AUDIT_EVENT_TYPE,
        "logged_at": datetime.now(UTC).isoformat(),
        "request_id": _safe_string(request.get("request_id")),
        "operation": _safe_string(request.get("operation")),
        "spreadsheet_id": _safe_string(request.get("spreadsheet_id")),
        "http_status": status,
        "ok": bool(result.get("ok")),
        "error_code": _safe_string(error.get("code")),
        "principal": _safe_string(
            policy_summary.get("principal") or auth_summary.get("principal")
        ),
        "impersonated_subject": _safe_string(auth_summary.get("impersonated_subject")),
        "policy_decision_id": _safe_string(policy_summary.get("decision_id")),
        "policy_version": _safe_string(policy_summary.get("policy_version")),
        "policy_allowed": policy_summary.get("allowed"),
        "policy_reason": _safe_string(policy_summary.get("reason")),
    }


def _policy_summary_from_result(result: dict[str, Any]) -> dict[str, Any]:
    policy = result.get("policy")
    if isinstance(policy, dict):
        return policy
    return _artifact_summary(result, "broker_policy")


def _auth_summary_from_result(result: dict[str, Any]) -> dict[str, Any]:
    auth = result.get("auth")
    if isinstance(auth, dict):
        return auth
    return _artifact_summary(result, "broker_auth")


def _artifact_summary(result: dict[str, Any], kind: str) -> dict[str, Any]:
    payload = result.get("payload")
    if not isinstance(payload, dict):
        return {}
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        return {}
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("kind") != kind:
            continue
        summary = artifact.get("summary")
        return summary if isinstance(summary, dict) else {}
    return {}


def _safe_string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def write_audit_event(event: dict[str, Any]) -> None:
    AUDIT_LOGGER.info(json.dumps(event, ensure_ascii=False, sort_keys=True))


def configure_logging(env: dict[str, str] | None = None) -> None:
    values = env or os.environ
    level_name = values.get("BROKER_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")


def main() -> int:
    configure_logging()
    runtime_config = load_runtime_config()
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("", port), make_handler(runtime_config))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
