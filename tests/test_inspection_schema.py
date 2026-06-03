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
                "timeout_budget": {
                    "read_seconds": 60,
                    "write_seconds": 60,
                    "poll_seconds": 120,
                },
            },
            "artifacts": [
                {"kind": "broker_policy", "summary": {"allowed": True}},
                {"kind": "local_artifact", "path": "access-preflight.json"},
            ],
        }

        jsonschema.Draft202012Validator(schema).validate(payload)


if __name__ == "__main__":
    unittest.main()
