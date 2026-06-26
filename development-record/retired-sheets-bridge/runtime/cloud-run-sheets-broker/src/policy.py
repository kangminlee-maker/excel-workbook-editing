from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
WINDOW_OPERATIONS = {
    "inspect.grid_window",
    "inspect.values_window",
    "inspect.formula_window",
}
WRITE_OPERATIONS = {
    "apply.values_update",
    "rollback.values_restore",
}
A1_CELL_RE = re.compile(r"^\$?([A-Za-z]+)\$?([1-9][0-9]*)$")


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    decision_id: str
    policy_version: str
    principal: str
    spreadsheet_id: str

    def summary(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "decision_id": self.decision_id,
            "policy_version": self.policy_version,
            "principal": self.principal,
            "spreadsheet_id": self.spreadsheet_id,
        }


def evaluate(policy: dict[str, Any], request: dict[str, Any]) -> PolicyDecision:
    version = str(policy.get("version", "unknown"))
    principal = _principal(request)
    spreadsheet_id = str(request.get("spreadsheet_id", ""))
    operation = str(request.get("operation", ""))
    risk_level = str(request.get("risk_level", "low"))
    decision_id = f"{version}:{principal}:{spreadsheet_id}:{operation}"

    principal_policy = _principal_policy(policy, principal)
    if not principal_policy:
        return _deny("principal_not_allowed", decision_id, version, principal, spreadsheet_id)

    spreadsheet_policy = _spreadsheet_policy(principal_policy, spreadsheet_id)
    if not spreadsheet_policy:
        return _deny("spreadsheet_not_allowed", decision_id, version, principal, spreadsheet_id)

    allowed_operations = spreadsheet_policy.get("operations", [])
    if operation not in allowed_operations:
        return _deny("operation_not_allowed", decision_id, version, principal, spreadsheet_id)

    if _risk_value(risk_level) > _risk_value(spreadsheet_policy.get("max_risk", "low")):
        return _deny("risk_too_high", decision_id, version, principal, spreadsheet_id)

    if not _sheet_ids_allowed(request.get("sheet_ids", []), spreadsheet_policy.get("sheet_ids", [])):
        return _deny("sheet_not_allowed", decision_id, version, principal, spreadsheet_id)

    if not _ranges_allowed(request.get("ranges", []), spreadsheet_policy.get("ranges", [])):
        return _deny("range_not_allowed", decision_id, version, principal, spreadsheet_id)

    bounded_reason = _bounded_operation_reason(operation, request, spreadsheet_policy)
    if bounded_reason:
        return _deny(bounded_reason, decision_id, version, principal, spreadsheet_id)

    return PolicyDecision(True, "allowed", decision_id, version, principal, spreadsheet_id)


def _principal(request: dict[str, Any]) -> str:
    identity = request.get("verified_identity") or {}
    principal = identity.get("principal")
    return principal.lower() if isinstance(principal, str) else ""


def _principal_policy(policy: dict[str, Any], principal: str) -> dict[str, Any] | None:
    principals = policy.get("principals", {})
    if not isinstance(principals, dict):
        return None

    exact_policy = principals.get(principal)
    if isinstance(exact_policy, dict):
        return exact_policy

    if "@" not in principal:
        return None
    domain_policy = principals.get(f"*@{principal.rsplit('@', 1)[1]}")
    return domain_policy if isinstance(domain_policy, dict) else None


def _spreadsheet_policy(
    principal_policy: dict[str, Any],
    spreadsheet_id: str,
) -> dict[str, Any] | None:
    spreadsheets = principal_policy.get("spreadsheets", {})
    if not isinstance(spreadsheets, dict):
        return None
    exact_policy = spreadsheets.get(spreadsheet_id)
    if isinstance(exact_policy, dict):
        return exact_policy
    wildcard_policy = spreadsheets.get("*")
    return wildcard_policy if isinstance(wildcard_policy, dict) else None


def _sheet_ids_allowed(requested: list[Any], allowed: list[Any]) -> bool:
    if "*" in allowed:
        return True
    if not requested:
        return True
    allowed_set = {int(value) for value in allowed if isinstance(value, int)}
    return all(isinstance(value, int) and value in allowed_set for value in requested)


def _ranges_allowed(requested: list[Any], allowed: list[Any]) -> bool:
    if "*" in allowed:
        return True
    if not requested:
        return True
    allowed_set = {str(value) for value in allowed}
    return all(str(value) in allowed_set for value in requested)


def _bounded_operation_reason(
    operation: str,
    request: dict[str, Any],
    spreadsheet_policy: dict[str, Any],
) -> str:
    if operation in WRITE_OPERATIONS:
        return _bounded_write_reason(operation, request, spreadsheet_policy)

    if operation not in WINDOW_OPERATIONS:
        return ""
    ranges = request.get("ranges", [])
    if not ranges:
        return "range_required"
    max_ranges = spreadsheet_policy.get("max_ranges_per_request")
    if isinstance(max_ranges, int) and max_ranges >= 0 and len(ranges) > max_ranges:
        return "too_many_ranges"

    cell_count = 0
    for range_value in ranges:
        range_cells = _range_cell_count(str(range_value))
        if range_cells is None:
            return "range_unbounded"
        cell_count += range_cells

    max_cells = spreadsheet_policy.get("max_cells_per_request")
    if isinstance(max_cells, int) and max_cells >= 0 and cell_count > max_cells:
        return "range_too_large"

    max_total_cells = spreadsheet_policy.get("max_total_cells_per_run")
    request_total_cells = request.get("total_cell_count", cell_count)
    if (
        isinstance(max_total_cells, int)
        and max_total_cells >= 0
        and isinstance(request_total_cells, int)
        and request_total_cells > max_total_cells
    ):
        return "total_cell_budget_exceeded"

    allowed_field_masks = spreadsheet_policy.get("allowed_field_masks", [])
    if operation == "inspect.grid_window" and allowed_field_masks and "*" not in allowed_field_masks:
        field_mask = request.get("field_mask")
        if field_mask not in allowed_field_masks:
            return "field_mask_not_allowed"

    timeout_seconds = request.get("timeout_seconds", 60)
    max_timeout_seconds = spreadsheet_policy.get("max_timeout_seconds")
    if (
        isinstance(timeout_seconds, int)
        and isinstance(max_timeout_seconds, int)
        and timeout_seconds > max_timeout_seconds
    ):
        return "timeout_too_high"

    retry_count = request.get("retry_count", 0)
    max_retries = spreadsheet_policy.get("max_retries")
    if isinstance(retry_count, int) and isinstance(max_retries, int) and retry_count > max_retries:
        return "retry_too_high"

    return ""


def _bounded_write_reason(
    operation: str,
    request: dict[str, Any],
    spreadsheet_policy: dict[str, Any],
) -> str:
    write_requests = request.get("write_requests")
    if not isinstance(write_requests, list) or not write_requests:
        return "write_requests_required"

    if operation == "apply.values_update" and request.get("rollback_required") is not True:
        return "rollback_snapshot_required"

    max_ranges = spreadsheet_policy.get(
        "max_write_ranges_per_request",
        spreadsheet_policy.get("max_ranges_per_request"),
    )
    if isinstance(max_ranges, int) and max_ranges >= 0 and len(write_requests) > max_ranges:
        return "too_many_write_ranges"

    request_ranges = request.get("ranges")
    if not isinstance(request_ranges, list) or not request_ranges:
        return "range_required"

    write_ranges = []
    total_cells = 0
    for write_request in write_requests:
        if not isinstance(write_request, dict):
            return "invalid_write_request"
        range_value = str(write_request.get("range", ""))
        if not range_value:
            return "range_required"
        write_ranges.append(range_value)
        range_cells = _range_cell_count(range_value)
        if range_cells is None:
            return "range_unbounded"
        values = write_request.get("values")
        if not _values_match_range(values, range_cells, range_value):
            return "write_shape_mismatch"
        total_cells += range_cells

    if [str(value) for value in request_ranges] != write_ranges:
        return "write_ranges_mismatch"

    max_cells = spreadsheet_policy.get(
        "max_write_cells_per_request",
        spreadsheet_policy.get("max_cells_per_request"),
    )
    if isinstance(max_cells, int) and max_cells >= 0 and total_cells > max_cells:
        return "write_range_too_large"

    max_total_cells = spreadsheet_policy.get(
        "max_write_cells_per_run",
        spreadsheet_policy.get("max_total_cells_per_run"),
    )
    request_total_cells = request.get("total_cell_count", total_cells)
    if (
        isinstance(max_total_cells, int)
        and max_total_cells >= 0
        and isinstance(request_total_cells, int)
        and request_total_cells > max_total_cells
    ):
        return "total_cell_budget_exceeded"

    timeout_seconds = request.get("timeout_seconds", 60)
    max_timeout_seconds = spreadsheet_policy.get("max_timeout_seconds")
    if (
        isinstance(timeout_seconds, int)
        and isinstance(max_timeout_seconds, int)
        and timeout_seconds > max_timeout_seconds
    ):
        return "timeout_too_high"

    retry_count = request.get("retry_count", 0)
    max_retries = spreadsheet_policy.get("max_retries")
    if isinstance(retry_count, int) and isinstance(max_retries, int) and retry_count > max_retries:
        return "retry_too_high"

    return ""


def _range_cell_count(a1_range: str) -> int | None:
    coordinate = a1_range.rsplit("!", 1)[-1].replace("$", "")
    start, separator, end = coordinate.partition(":")
    end = end if separator else start
    start_cell = _cell_coordinate(start)
    end_cell = _cell_coordinate(end)
    if start_cell is None or end_cell is None:
        return None
    start_column, start_row = start_cell
    end_column, end_row = end_cell
    if end_column < start_column or end_row < start_row:
        return None
    return (end_column - start_column + 1) * (end_row - start_row + 1)


def _values_match_range(values: Any, range_cells: int, range_value: str) -> bool:
    if not isinstance(values, list):
        return False
    dimensions = _range_dimensions(range_value)
    if dimensions is None:
        return False
    expected_rows, expected_columns = dimensions
    if len(values) != expected_rows:
        return False
    for row in values:
        if not isinstance(row, list) or len(row) != expected_columns:
            return False
    return sum(len(row) for row in values) == range_cells


def _range_dimensions(a1_range: str) -> tuple[int, int] | None:
    coordinate = a1_range.rsplit("!", 1)[-1].replace("$", "")
    start, separator, end = coordinate.partition(":")
    end = end if separator else start
    start_cell = _cell_coordinate(start)
    end_cell = _cell_coordinate(end)
    if start_cell is None or end_cell is None:
        return None
    start_column, start_row = start_cell
    end_column, end_row = end_cell
    if end_column < start_column or end_row < start_row:
        return None
    return end_row - start_row + 1, end_column - start_column + 1


def _cell_coordinate(cell: str) -> tuple[int, int] | None:
    match = A1_CELL_RE.match(cell)
    if not match:
        return None
    column = 0
    for char in match.group(1).upper():
        column = column * 26 + ord(char) - 64
    return column, int(match.group(2))


def _risk_value(risk: Any) -> int:
    return RISK_ORDER.get(str(risk), RISK_ORDER["high"])


def _deny(
    reason: str,
    decision_id: str,
    version: str,
    principal: str,
    spreadsheet_id: str,
) -> PolicyDecision:
    return PolicyDecision(False, reason, decision_id, version, principal, spreadsheet_id)
