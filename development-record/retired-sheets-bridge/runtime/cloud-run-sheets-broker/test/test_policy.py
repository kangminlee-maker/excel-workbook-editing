from __future__ import annotations

import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from policy import evaluate


PILOT = "pilot.user@day1company.co.kr"
SECOND_USER = "second.user@day1company.co.kr"
SPREADSHEET_ID = "spreadsheet-1"


def policy() -> dict:
    return {
        "version": "phase1-test",
        "principals": {
            PILOT: {
                "spreadsheets": {
                    SPREADSHEET_ID: {
                        "operations": ["inspect.metadata"],
                        "sheet_ids": [10, 20],
                        "ranges": ["Input!A1:B10", "Summary!A1:D20"],
                        "max_risk": "low",
                    }
                }
            }
        },
    }


def window_policy() -> dict:
    value = policy()
    value["principals"][PILOT]["spreadsheets"] = {
        "*": {
            "operations": [
                "inspect.metadata",
                "inspect.grid_window",
                "inspect.values_window",
                "inspect.formula_window",
            ],
            "sheet_ids": ["*"],
            "ranges": ["*"],
            "max_risk": "low",
            "max_ranges_per_request": 2,
            "max_cells_per_request": 5000,
            "max_total_cells_per_run": 10000,
            "max_timeout_seconds": 60,
            "max_retries": 1,
            "allowed_field_masks": [
                "grid_basic_v1",
                "grid_formula_v1",
            ],
        }
    }
    return value


def enterprise_acl_policy() -> dict:
    return {
        "version": "enterprise-readonly-acl-v1",
        "principals": {
            "*@day1company.co.kr": {
                "spreadsheets": {
                    "*": {
                        "operations": [
                            "inspect.metadata",
                            "inspect.grid_window",
                            "inspect.values_window",
                            "inspect.formula_window",
                            "apply.values_update",
                            "rollback.values_restore",
                        ],
                        "sheet_ids": ["*"],
                        "ranges": ["*"],
                        "max_risk": "medium",
                        "max_ranges_per_request": 2,
                        "max_cells_per_request": 5000,
                        "max_total_cells_per_run": 10000,
                        "max_timeout_seconds": 60,
                        "max_retries": 1,
                        "allowed_field_masks": ["grid_basic_v1"],
                        "max_write_ranges_per_request": 1,
                        "max_write_cells_per_request": 100,
                        "max_write_cells_per_run": 200,
                    }
                }
            }
        },
    }


def request(**overrides) -> dict:
    base = {
        "verified_identity": {"principal": PILOT},
        "operation": "inspect.metadata",
        "spreadsheet_id": SPREADSHEET_ID,
        "sheet_ids": [10],
        "ranges": ["Input!A1:B10"],
        "risk_level": "low",
    }
    return {**base, **overrides}


class PolicyTests(unittest.TestCase):
    def test_allowed_pilot_can_inspect_configured_spreadsheet_and_range(self) -> None:
        decision = evaluate(policy(), request())

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "allowed")
        self.assertEqual(decision.principal, PILOT)
        self.assertEqual(decision.spreadsheet_id, SPREADSHEET_ID)

    def test_unknown_principal_is_denied(self) -> None:
        decision = evaluate(
            policy(),
            request(verified_identity={"principal": "unknown@day1company.co.kr"}),
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "principal_not_allowed")

    def test_identity_hint_without_verified_identity_is_denied(self) -> None:
        hint_only_request = request(identity_hint={"principal": PILOT})
        del hint_only_request["verified_identity"]

        decision = evaluate(policy(), hint_only_request)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "principal_not_allowed")

    def test_identity_hint_does_not_override_verified_identity(self) -> None:
        decision = evaluate(
            policy(),
            request(identity_hint={"principal": "unknown@day1company.co.kr"}),
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.principal, PILOT)

    def test_unknown_spreadsheet_is_denied(self) -> None:
        decision = evaluate(policy(), request(spreadsheet_id="spreadsheet-2"))

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "spreadsheet_not_allowed")

    def test_wildcard_spreadsheet_policy_allows_google_acl_to_decide_access(self) -> None:
        wildcard_policy = policy()
        wildcard_policy["principals"][PILOT]["spreadsheets"] = {
            "*": {
                "operations": ["inspect.metadata"],
                "sheet_ids": ["*"],
                "ranges": ["*"],
                "max_risk": "low",
            }
        }

        decision = evaluate(wildcard_policy, request(spreadsheet_id="spreadsheet-2"))

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.spreadsheet_id, "spreadsheet-2")

    def test_domain_principal_policy_allows_company_user_without_per_user_listing(self) -> None:
        decision = evaluate(
            enterprise_acl_policy(),
            request(
                verified_identity={"principal": SECOND_USER},
                spreadsheet_id="external-owned-spreadsheet",
                operation="inspect.values_window",
                ranges=["'External Sheet'!A1:D20"],
            ),
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.principal, SECOND_USER)
        self.assertEqual(decision.spreadsheet_id, "external-owned-spreadsheet")

    def test_domain_principal_policy_still_rejects_other_domains(self) -> None:
        decision = evaluate(
            enterprise_acl_policy(),
            request(verified_identity={"principal": "user@example.com"}),
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "principal_not_allowed")

    def test_exact_principal_policy_overrides_domain_policy(self) -> None:
        value = enterprise_acl_policy()
        value["principals"][PILOT] = {
            "spreadsheets": {
                "approved-only": {
                    "operations": ["inspect.metadata"],
                    "sheet_ids": ["*"],
                    "ranges": ["*"],
                    "max_risk": "low",
                }
            }
        }

        denied = evaluate(value, request(spreadsheet_id="external-owned-spreadsheet"))
        allowed = evaluate(value, request(spreadsheet_id="approved-only"))

        self.assertFalse(denied.allowed)
        self.assertEqual(denied.reason, "spreadsheet_not_allowed")
        self.assertTrue(allowed.allowed)

    def test_wildcard_spreadsheet_policy_still_denies_unknown_operation(self) -> None:
        wildcard_policy = policy()
        wildcard_policy["principals"][PILOT]["spreadsheets"] = {
            "*": {
                "operations": ["inspect.metadata"],
                "sheet_ids": ["*"],
                "ranges": ["*"],
                "max_risk": "low",
            }
        }

        decision = evaluate(
            wildcard_policy,
            request(spreadsheet_id="spreadsheet-2", operation="apply.batchUpdate"),
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "operation_not_allowed")

    def test_unknown_operation_is_denied(self) -> None:
        decision = evaluate(policy(), request(operation="apply.batchUpdate"))

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "operation_not_allowed")

    def test_unknown_sheet_id_is_denied(self) -> None:
        decision = evaluate(policy(), request(sheet_ids=[999]))

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "sheet_not_allowed")

    def test_unknown_range_is_denied(self) -> None:
        decision = evaluate(policy(), request(ranges=["Input!A1:Z999"]))

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "range_not_allowed")

    def test_risk_above_policy_is_denied(self) -> None:
        decision = evaluate(policy(), request(risk_level="medium"))

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "risk_too_high")

    def test_bounded_grid_window_is_allowed_inside_policy_limits(self) -> None:
        decision = evaluate(
            window_policy(),
            request(
                operation="inspect.grid_window",
                spreadsheet_id="spreadsheet-2",
                ranges=["'26_0601'!A1:Z80"],
                field_mask="grid_basic_v1",
                timeout_seconds=30,
                retry_count=1,
            ),
        )

        self.assertTrue(decision.allowed)

    def test_bounded_window_requires_ranges(self) -> None:
        decision = evaluate(
            window_policy(),
            request(operation="inspect.values_window", spreadsheet_id="spreadsheet-2", ranges=[]),
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "range_required")

    def test_bounded_window_denies_unbounded_or_large_ranges(self) -> None:
        unbounded = evaluate(
            window_policy(),
            request(
                operation="inspect.values_window",
                spreadsheet_id="spreadsheet-2",
                ranges=["'26_0601'!A:Z"],
            ),
        )
        too_large = evaluate(
            window_policy(),
            request(
                operation="inspect.formula_window",
                spreadsheet_id="spreadsheet-2",
                ranges=["'26_0601'!A1:ZZ100"],
            ),
        )

        self.assertFalse(unbounded.allowed)
        self.assertEqual(unbounded.reason, "range_unbounded")
        self.assertFalse(too_large.allowed)
        self.assertEqual(too_large.reason, "range_too_large")

    def test_bounded_window_denies_field_mask_timeout_retry_and_run_budget(self) -> None:
        bad_mask = evaluate(
            window_policy(),
            request(
                operation="inspect.grid_window",
                spreadsheet_id="spreadsheet-2",
                ranges=["'26_0601'!A1:B2"],
                field_mask="unapproved",
            ),
        )
        bad_timeout = evaluate(
            window_policy(),
            request(
                operation="inspect.values_window",
                spreadsheet_id="spreadsheet-2",
                ranges=["'26_0601'!A1:B2"],
                timeout_seconds=61,
            ),
        )
        bad_retry = evaluate(
            window_policy(),
            request(
                operation="inspect.values_window",
                spreadsheet_id="spreadsheet-2",
                ranges=["'26_0601'!A1:B2"],
                retry_count=2,
            ),
        )
        bad_budget = evaluate(
            window_policy(),
            request(
                operation="inspect.values_window",
                spreadsheet_id="spreadsheet-2",
                ranges=["'26_0601'!A1:B2"],
                total_cell_count=10001,
            ),
        )

        self.assertFalse(bad_mask.allowed)
        self.assertEqual(bad_mask.reason, "field_mask_not_allowed")
        self.assertFalse(bad_timeout.allowed)
        self.assertEqual(bad_timeout.reason, "timeout_too_high")
        self.assertFalse(bad_retry.allowed)
        self.assertEqual(bad_retry.reason, "retry_too_high")
        self.assertFalse(bad_budget.allowed)
        self.assertEqual(bad_budget.reason, "total_cell_budget_exceeded")

    def test_apply_values_update_requires_rollback_snapshot_and_matching_shape(self) -> None:
        allowed = evaluate(
            enterprise_acl_policy(),
            request(
                verified_identity={"principal": SECOND_USER},
                operation="apply.values_update",
                spreadsheet_id="spreadsheet-2",
                ranges=["Input!A1:B1"],
                risk_level="medium",
                rollback_required=True,
                write_requests=[{"range": "Input!A1:B1", "values": [["new", "=A1"]]}],
                total_cell_count=2,
            ),
        )
        missing_rollback = evaluate(
            enterprise_acl_policy(),
            request(
                verified_identity={"principal": SECOND_USER},
                operation="apply.values_update",
                spreadsheet_id="spreadsheet-2",
                ranges=["Input!A1:B1"],
                risk_level="medium",
                write_requests=[{"range": "Input!A1:B1", "values": [["new", "=A1"]]}],
                total_cell_count=2,
            ),
        )
        shape_mismatch = evaluate(
            enterprise_acl_policy(),
            request(
                verified_identity={"principal": SECOND_USER},
                operation="apply.values_update",
                spreadsheet_id="spreadsheet-2",
                ranges=["Input!A1:B1"],
                risk_level="medium",
                rollback_required=True,
                write_requests=[{"range": "Input!A1:B1", "values": [["new"]]}],
                total_cell_count=2,
            ),
        )

        self.assertTrue(allowed.allowed)
        self.assertFalse(missing_rollback.allowed)
        self.assertEqual(missing_rollback.reason, "rollback_snapshot_required")
        self.assertFalse(shape_mismatch.allowed)
        self.assertEqual(shape_mismatch.reason, "write_shape_mismatch")

    def test_rollback_values_restore_uses_same_bounded_write_limits(self) -> None:
        allowed = evaluate(
            enterprise_acl_policy(),
            request(
                verified_identity={"principal": SECOND_USER},
                operation="rollback.values_restore",
                spreadsheet_id="spreadsheet-2",
                ranges=["Input!A1:A1"],
                risk_level="medium",
                write_requests=[{"range": "Input!A1:A1", "values": [["old"]]}],
                total_cell_count=1,
            ),
        )
        unbounded = evaluate(
            enterprise_acl_policy(),
            request(
                verified_identity={"principal": SECOND_USER},
                operation="rollback.values_restore",
                spreadsheet_id="spreadsheet-2",
                ranges=["Input!A:A"],
                risk_level="medium",
                write_requests=[{"range": "Input!A:A", "values": [["old"]]}],
                total_cell_count=1,
            ),
        )

        self.assertTrue(allowed.allowed)
        self.assertFalse(unbounded.allowed)
        self.assertEqual(unbounded.reason, "range_unbounded")


if __name__ == "__main__":
    unittest.main()
