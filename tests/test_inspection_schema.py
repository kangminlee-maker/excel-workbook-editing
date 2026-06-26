from __future__ import annotations

import json
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]


class InspectionSchemaTest(unittest.TestCase):
    def test_accepts_path_and_summary_artifact_refs(self) -> None:
        schema = json.loads(
            (REPO_ROOT / "schemas" / "inspection.schema.json").read_text(
                encoding="utf-8"
            )
        )
        payload = {
            "schema_version": "1.0",
            "snapshot_id": "snapshot-1",
            "captured_at": "2026-06-02T00:00:00+00:00",
            "spreadsheet_id": "spreadsheet-1",
            "title": "Sheet",
            "locale": "ko_KR",
            "time_zone": "Asia/Seoul",
            "tabs": [],
            "named_ranges": [],
            "protected_ranges": [],
            "data_validations": [],
            "formula_samples": [],
            "cell_states": [],
            "telemetry": {
                "request_count": 1,
                "retry_count": 0,
                "elapsed_ms": 10,
                "client_elapsed_ms": 12,
                "timeout_budget": {
                    "read_seconds": 60,
                    "write_seconds": 60,
                    "poll_seconds": 120,
                },
            },
            "artifacts": [
                {"kind": "source_access_policy_evidence", "summary": {"allowed": True}},
                {"kind": "local_artifact", "path": "access-preflight.json"},
            ],
        }

        jsonschema.Draft202012Validator(schema).validate(payload)

    def test_apply_result_schema_matches_values_update_snapshot(self) -> None:
        schema = json.loads(
            (REPO_ROOT / "schemas" / "apply-result.schema.json").read_text(
                encoding="utf-8"
            )
        )
        payload = {
            "schema_version": "1.0",
            "snapshot_id": "snapshot-apply",
            "captured_at": "2026-06-05T00:00:00+00:00",
            "operation": "apply.values_update",
            "spreadsheet_id": "spreadsheet-1",
            "requested_ranges": ["'Input'!A1:B1"],
            "value_input_option": "USER_ENTERED",
            "write_count": 1,
            "updated_cells": 2,
            "updated_rows": 1,
            "updated_columns": 2,
            "before": [
                {
                    "range": "'Input'!A1:B1",
                    "major_dimension": "ROWS",
                    "values": [["old", "=A2"]],
                    "row_count": 1,
                    "column_count": 2,
                }
            ],
            "after": [
                {
                    "range": "'Input'!A1:B1",
                    "major_dimension": "ROWS",
                    "values": [["new", "=A1"]],
                    "row_count": 1,
                    "column_count": 2,
                }
            ],
            "rollback": {
                "operation": "rollback.values_restore",
                "spreadsheet_id": "spreadsheet-1",
                "ranges": ["'Input'!A1:B1"],
                "write_requests": [
                    {"range": "'Input'!A1:B1", "values": [["old", "=A2"]]}
                ],
                "rollback_of_request_id": "snapshot-apply",
            },
            "artifacts": [
                {
                    "kind": "source_access_result",
                    "summary": {"provider": "approved_external_access"},
                }
            ],
        }

        jsonschema.Draft202012Validator(schema).validate(payload)


if __name__ == "__main__":
    unittest.main()
