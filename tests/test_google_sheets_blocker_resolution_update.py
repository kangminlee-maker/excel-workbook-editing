from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_blocker_resolution_update import (  # noqa: E402
    build_google_sheets_blocker_resolution_update,
)


class GoogleSheetsBlockerResolutionUpdateTest(unittest.TestCase):
    def test_records_resolved_source_boundary_and_cash_basis_without_parser_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_json(root / "source-fc-data-broker-metadata.json", _metadata())
            _write_json(root / "source-fc-data-values-window.json", _values_window())
            _write_json(root / "source-fc-data-formula-window.json", _formula_window())

            update = build_google_sheets_blocker_resolution_update(
                out_dir=root,
                fc_data_source_url="https://docs.google.com/spreadsheets/d/source/edit",
                formula_result_authority="requires_targeted_validation",
                local_boundary="전사레벨 현황 보고 문서",
                repeated_workbook_family="all tabs repeat with version breakpoints",
                reporting_basis="cash basis payment amount",
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-blocker-resolution-update.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(update)

        statuses = {item["id"]: item["status"] for item in update["blocker_status"]}
        self.assertEqual(statuses["direct_fc_data_source_authority"], "resolved")
        self.assertEqual(statuses["local_boundary"], "resolved_by_user")
        self.assertEqual(statuses["reporting_basis"], "resolved_by_user")
        self.assertEqual(statuses["formula_result_authority"], "open")
        self.assertEqual(
            update["authority"]["parser_truth"],
            "no_new_parser_claims_until_rerun",
        )
        self.assertEqual(update["summary"]["shared_ontology_update_count"], 0)
        self.assertEqual(update["summary"]["nested_importrange_count"], 1)
        self.assertEqual(update["summary"]["version_breakpoint_candidate_count"], 2)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _metadata() -> dict:
    return {
        "ok": True,
        "payload": {
            "spreadsheet_id": "source",
            "title": "Source Sheet",
            "artifacts": [_policy("inspect.metadata")],
            "tabs": [
                {"title": "25_0915", "sheet_id": 1, "row_count": 10, "column_count": 96, "hidden": False},
                {"title": "25_0908", "sheet_id": 2, "row_count": 10, "column_count": 95, "hidden": False},
                {"title": "25_0901", "sheet_id": 3, "row_count": 10, "column_count": 95, "hidden": False},
                {"title": "24_1230", "sheet_id": 4, "row_count": 10, "column_count": 66, "hidden": True},
                {"title": "FC_DATA", "sheet_id": 5, "row_count": 676, "column_count": 32, "hidden": False},
            ],
        },
    }


def _values_window() -> dict:
    return {
        "ok": True,
        "payload": {
            "operation": "inspect.values_window",
            "requested_ranges": ["FC_DATA!A1:Z80"],
            "artifacts": [_policy("inspect.values_window")],
            "windows": [
                {
                    "range": "FC_DATA!A1:Z80",
                    "row_count": 2,
                    "column_count": 2,
                    "values": [["label", "#N/A"], ["cash", "100"]],
                }
            ],
        },
    }


def _formula_window() -> dict:
    return {
        "ok": True,
        "payload": {
            "operation": "inspect.formula_window",
            "requested_ranges": ["FC_DATA!A1:Z80"],
            "artifacts": [_policy("inspect.formula_window")],
            "windows": [
                {
                    "range": "FC_DATA!A1:Z80",
                    "row_count": 5,
                    "column_count": 2,
                    "values": [
                        ["", ""],
                        ["", ""],
                        ["", ""],
                        ["", ""],
                        ['=IMPORTRANGE(B1,"지표!T4:AH175")', ""],
                    ],
                }
            ],
        },
    }


def _policy(operation: str) -> dict:
    return {
        "kind": "broker_policy",
        "summary": {
            "allowed": True,
            "decision_id": f"policy:source:{operation}",
            "policy_version": "parser-readonly-windows-2026-06-02",
            "principal": "kangmin.lee@day1company.co.kr",
            "reason": "allowed",
            "spreadsheet_id": "source",
        },
    }


if __name__ == "__main__":
    unittest.main()
