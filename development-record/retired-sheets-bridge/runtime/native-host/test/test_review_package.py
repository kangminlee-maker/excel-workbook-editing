from __future__ import annotations

from datetime import datetime, timezone
import io
import json
import struct
import sys
from pathlib import Path
import tempfile
import unittest


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

from host import handle_message, run  # noqa: E402
from protocol import read_message  # noqa: E402
from review_package import ReviewPackageError, write_inspection_package  # noqa: E402


SNAPSHOT = {
    "schema_version": "1.0",
    "spreadsheet_id": "spreadsheet-1",
    "title": "Ops Sheet",
    "captured_at": "2026-06-02T00:00:00+00:00",
    "tabs": [{"sheet_id": 10, "title": "Input"}],
}


class ReviewPackageTests(unittest.TestCase):
    def test_write_inspection_package_persists_snapshot_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_inspection_package(
                message=_message(SNAPSHOT),
                package_root=tmpdir,
                now=datetime(2026, 6, 2, tzinfo=timezone.utc),
            )

            manifest = json.loads(Path(result["artifact_path"]).read_text())
            snapshot = json.loads(Path(result["snapshot_path"]).read_text())

        self.assertEqual(snapshot, SNAPSHOT)
        self.assertEqual(manifest["request_id"], "request-1")
        self.assertEqual(manifest["artifacts"][0]["kind"], "inspection_snapshot")
        self.assertEqual(manifest["artifacts"][0]["summary"]["spreadsheet_id"], "spreadsheet-1")
        self.assertEqual(result["summary"]["tab_count"], 1)

    def test_credential_like_snapshot_is_rejected_without_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ReviewPackageError, "credential-like"):
                write_inspection_package(
                    message=_message({"spreadsheet_id": "spreadsheet-1", "access_token": "secret"}),
                    package_root=tmpdir,
                )
            self.assertEqual(list(Path(tmpdir).rglob("*")), [])

    def test_handle_message_returns_review_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            response = handle_message(_message(SNAPSHOT), package_root=tmpdir)

        self.assertEqual(response["type"], "review.result")
        self.assertTrue(response["ok"])
        self.assertEqual(response["payload"]["summary"]["spreadsheet_id"], "spreadsheet-1")

    def test_handle_message_rejects_denied_response_without_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            response = handle_message(
                _message({"ok": False, "error": {"code": "policy_denied"}}),
                package_root=tmpdir,
            )
            self.assertEqual(list(Path(tmpdir).rglob("*")), [])

        self.assertEqual(response["type"], "error")
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "review_package_failed")

    def test_run_reads_framed_message_and_writes_framed_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_stream = io.BytesIO(_framed(_message(SNAPSHOT)))
            output_stream = io.BytesIO()

            status = run(
                input_stream=input_stream,
                output_stream=output_stream,
                package_root=tmpdir,
            )
            output_stream.seek(0)
            response = read_message(output_stream)

        self.assertEqual(status, 0)
        self.assertEqual(response["type"], "review.result")
        self.assertTrue(response["ok"])


def _message(snapshot: dict) -> dict:
    return {
        "protocol_version": "1.0",
        "request_id": "request-1",
        "type": "inspect.snapshot",
        "payload": {
            "snapshot": snapshot,
        },
    }


def _framed(message: dict) -> bytes:
    payload = json.dumps(message).encode("utf-8")
    return struct.pack("<I", len(payload)) + payload


if __name__ == "__main__":
    unittest.main()
