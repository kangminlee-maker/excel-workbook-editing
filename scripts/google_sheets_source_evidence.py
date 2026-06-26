from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


def build_source_evidence_request(
    *,
    spreadsheet_id: str,
    principal: str = "",
    operation: str = "inspect.metadata",
    sheet_ids: list[int] | None = None,
    ranges: list[str] | None = None,
    field_mask: str | None = None,
    timeout_seconds: int | None = None,
    retry_count: int | None = None,
    total_cell_count: int | None = None,
    request_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    request = {
        "request_id": request_id or f"source-evidence-{uuid4()}",
        "operation": operation,
        "spreadsheet_id": spreadsheet_id,
        "sheet_ids": sheet_ids or [],
        "ranges": ranges or [],
        "risk_level": "low",
        "created_at": created_at or datetime.now(UTC).isoformat(),
    }
    if principal:
        request["source_actor_hint"] = {"principal": principal}
    if field_mask:
        request["field_mask"] = field_mask
    if timeout_seconds is not None:
        request["timeout_seconds"] = timeout_seconds
    if retry_count is not None:
        request["retry_count"] = retry_count
    if total_cell_count is not None:
        request["total_cell_count"] = total_cell_count
    return request


def load_source_evidence_results(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    value = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if isinstance(value, list):
        return [_require_object(item, "source evidence result") for item in value]
    if isinstance(value, dict):
        for key in ("source_evidence_results", "results"):
            items = value.get(key)
            if isinstance(items, list):
                return [_require_object(item, "source evidence result") for item in items]
        return [value]
    raise ValueError("source evidence results must be a JSON object or array")


def source_evidence_response_record(
    *,
    request: dict[str, Any],
    response: dict[str, Any],
    candidate_ids: list[str] | None = None,
    source_batch_id: str | None = None,
    read_candidate_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload = _payload_from_response(response, request)
    record = {
        "operation": str(response.get("operation") or request["operation"]),
        "requested_ranges": list(response.get("requested_ranges") or request.get("ranges", [])),
        "ok": _response_ok(response),
        "payload": payload,
    }
    if candidate_ids is not None:
        record["candidate_ids"] = candidate_ids
    if source_batch_id is not None:
        record["source_batch_id"] = source_batch_id
    if read_candidate_ids is not None:
        record["read_candidate_ids"] = read_candidate_ids
    return record


def _payload_from_response(response: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    if isinstance(response.get("payload"), dict):
        return response["payload"]
    if isinstance(response.get("windows"), list):
        return {"windows": response["windows"]}
    if "values" in response:
        return {
            "windows": [
                {
                    "range": response.get("range") or _first_range(request),
                    "values": response.get("values") or [],
                    "row_count": response.get("row_count", len(response.get("values") or [])),
                    "column_count": response.get("column_count", _max_columns(response.get("values") or [])),
                }
            ]
        }
    return response


def _response_ok(response: dict[str, Any]) -> bool:
    if "ok" in response:
        return bool(response["ok"])
    return bool(response.get("payload") or response.get("windows") or response.get("values"))


def _first_range(request: dict[str, Any]) -> str:
    ranges = request.get("ranges", [])
    return str(ranges[0]) if ranges else ""


def _max_columns(values: Any) -> int:
    if not isinstance(values, list):
        return 0
    return max((len(row) for row in values if isinstance(row, list)), default=0)


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value
