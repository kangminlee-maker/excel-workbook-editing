from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from auth import AuthConfig, AuthError, verify_claims
from dwd import DwdError, build_dwd_context
from policy import evaluate
from sheets_client import (
    apply_values_update,
    fetch_grid_window,
    fetch_metadata,
    fetch_values_window,
    normalize_grid_window,
    normalize_metadata,
    normalize_values_apply_result,
    normalize_values_window,
    rollback_write_requests_from_values_snapshot,
)
from token_provider import TokenProviderError


READONLY_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
WRITE_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
WRITE_OPERATIONS = {"apply.values_update", "rollback.values_restore"}


def handle_inspect_request(
    *,
    request: dict,
    identity_claims: dict,
    policy: dict,
    auth_config: AuthConfig,
    service_account_email: str,
    access_token_provider,
    metadata_transport,
    write_transport=None,
) -> dict:
    try:
        verified_identity = verify_claims(identity_claims, auth_config)
    except AuthError as error:
        return _error("auth_failed", str(error))

    request_with_identity = {
        **request,
        "verified_identity": verified_identity,
    }
    policy_decision = evaluate(policy, request_with_identity)
    if not policy_decision.allowed:
        return {
            "ok": False,
            "error": {
                "code": "policy_denied",
                "message": policy_decision.reason,
            },
            "policy": policy_decision.summary(),
        }
    policy_summary = policy_decision.summary()

    try:
        dwd_context = build_dwd_context(
            service_account_email=service_account_email,
            verified_identity=verified_identity,
            scopes=_scopes_for_operation(str(request.get("operation", ""))),
        )
    except DwdError as error:
        return _error("dwd_subject_failed", str(error))
    auth_summary = {
        "principal": verified_identity["principal"],
        "impersonated_subject": dwd_context.subject,
    }

    try:
        access_token = access_token_provider(dwd_context)
    except TokenProviderError as error:
        return _error(
            "credential_failed",
            _credential_error_message(error),
            policy=policy_summary,
            auth=auth_summary,
        )
    except Exception:
        return _error(
            "credential_failed",
            "broker could not mint a DWD access token",
            policy=policy_summary,
            auth=auth_summary,
        )

    operation = str(request.get("operation", ""))
    captured_at = datetime.now(UTC).isoformat()
    snapshot_id = f"snapshot-{uuid4()}"

    if operation == "inspect.metadata":
        try:
            metadata, elapsed_ms = fetch_metadata(
                spreadsheet_id=request["spreadsheet_id"],
                access_token=access_token,
                transport=metadata_transport,
            )
        except Exception:
            return _error(
                "sheets_metadata_failed",
                "broker could not read spreadsheet metadata",
                policy=policy_summary,
                auth=auth_summary,
            )

        snapshot = normalize_metadata(
            metadata,
            snapshot_id=snapshot_id,
            captured_at=captured_at,
            elapsed_ms=elapsed_ms,
            policy_summary=policy_summary,
            auth_summary=auth_summary,
        )
        return {"ok": True, "payload": snapshot}

    if operation == "inspect.grid_window":
        try:
            metadata, elapsed_ms = fetch_grid_window(
                spreadsheet_id=request["spreadsheet_id"],
                ranges=list(request.get("ranges", [])),
                field_mask=str(request.get("field_mask", "grid_basic_v1")),
                access_token=access_token,
                transport=metadata_transport,
            )
        except Exception:
            return _error(
                "sheets_window_failed",
                "broker could not read spreadsheet grid window",
                policy=policy_summary,
                auth=auth_summary,
            )
        return {
            "ok": True,
            "payload": normalize_grid_window(
                metadata,
                snapshot_id=snapshot_id,
                captured_at=captured_at,
                operation=operation,
                ranges=list(request.get("ranges", [])),
                field_mask=str(request.get("field_mask", "grid_basic_v1")),
                elapsed_ms=elapsed_ms,
                policy_summary=policy_summary,
                auth_summary=auth_summary,
            ),
        }

    if operation in {"inspect.values_window", "inspect.formula_window"}:
        value_render_option = (
            "FORMULA" if operation == "inspect.formula_window" else "FORMATTED_VALUE"
        )
        try:
            values, elapsed_ms = fetch_values_window(
                spreadsheet_id=request["spreadsheet_id"],
                ranges=list(request.get("ranges", [])),
                value_render_option=value_render_option,
                access_token=access_token,
                transport=metadata_transport,
            )
        except Exception:
            return _error(
                "sheets_window_failed",
                "broker could not read spreadsheet value window",
                policy=policy_summary,
                auth=auth_summary,
            )
        return {
            "ok": True,
            "payload": normalize_values_window(
                values,
                snapshot_id=snapshot_id,
                captured_at=captured_at,
                operation=operation,
                ranges=list(request.get("ranges", [])),
                value_render_option=value_render_option,
                elapsed_ms=elapsed_ms,
                policy_summary=policy_summary,
                auth_summary=auth_summary,
            ),
        }

    if operation in WRITE_OPERATIONS:
        try:
            return _handle_values_write_request(
                request=request,
                operation=operation,
                access_token=access_token,
                metadata_transport=metadata_transport,
                write_transport=write_transport,
                snapshot_id=snapshot_id,
                captured_at=captured_at,
                policy_summary=policy_summary,
                auth_summary=auth_summary,
            )
        except Exception:
            return _error(
                "sheets_apply_failed",
                "broker could not apply spreadsheet values update",
                policy=policy_summary,
                auth=auth_summary,
            )

    return _error("unsupported_operation", "broker operation is not implemented")


def _handle_values_write_request(
    *,
    request: dict,
    operation: str,
    access_token: str,
    metadata_transport,
    write_transport,
    snapshot_id: str,
    captured_at: str,
    policy_summary: dict,
    auth_summary: dict,
) -> dict:
    if write_transport is None:
        raise ValueError("write_transport is required")
    spreadsheet_id = str(request.get("spreadsheet_id", ""))
    ranges = [str(value) for value in request.get("ranges", [])]
    write_requests = [
        {
            "range": str(write_request.get("range", "")),
            "values": write_request.get("values", []),
        }
        for write_request in request.get("write_requests", [])
        if isinstance(write_request, dict)
    ]
    before_values, before_elapsed_ms = fetch_values_window(
        spreadsheet_id=spreadsheet_id,
        ranges=ranges,
        value_render_option="FORMULA",
        access_token=access_token,
        transport=metadata_transport,
    )
    rollback_write_requests = rollback_write_requests_from_values_snapshot(
        ranges=ranges,
        values_snapshot=before_values,
    )
    update_response, write_elapsed_ms = apply_values_update(
        spreadsheet_id=spreadsheet_id,
        write_requests=write_requests,
        access_token=access_token,
        transport=write_transport,
    )
    readback_values, readback_elapsed_ms = fetch_values_window(
        spreadsheet_id=spreadsheet_id,
        ranges=ranges,
        value_render_option="FORMULA",
        access_token=access_token,
        transport=metadata_transport,
    )
    normalized = normalize_values_apply_result(
        spreadsheet_id=spreadsheet_id,
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        operation=operation,
        write_requests=write_requests,
        before_values=before_values,
        update_response=update_response,
        readback_values=readback_values,
        rollback_write_requests=rollback_write_requests,
        elapsed_ms=before_elapsed_ms + write_elapsed_ms + readback_elapsed_ms,
        policy_summary=policy_summary,
        auth_summary=auth_summary,
    )
    normalized["rollback"]["rollback_of_request_id"] = str(request.get("request_id", ""))
    return {"ok": True, "payload": normalized}


def _error(code: str, message: str, **extra) -> dict:
    result = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    result.update(extra)
    return result


def _scopes_for_operation(operation: str) -> tuple[str, ...]:
    if operation in WRITE_OPERATIONS:
        return (WRITE_SHEETS_SCOPE,)
    return (READONLY_SHEETS_SCOPE,)


def _credential_error_message(error: TokenProviderError) -> str:
    detail = str(error).strip()
    if not detail:
        return "broker could not mint a DWD access token"
    return f"broker could not mint a DWD access token: {detail[:800]}"
