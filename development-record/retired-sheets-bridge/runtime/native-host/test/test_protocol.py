import io
import json
import struct
import sys
import unittest
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

from protocol import (  # noqa: E402
    ALLOWED_MESSAGE_TYPES,
    InvalidMessageError,
    MessageTooLargeError,
    PLANNED_REQUEST_MESSAGE_TYPES,
    PLANNED_RESULT_MESSAGE_TYPES,
    UnknownMessageTypeError,
    read_message,
    validate_message,
    write_message,
)


def framed(payload):
    data = json.dumps(payload).encode("utf-8")
    return struct.pack("<I", len(data)) + data


class ProtocolTest(unittest.TestCase):
    def test_valid_frame_roundtrip(self):
        message = {
            "protocol_version": "1.0",
            "request_id": "request-1",
            "type": "inspect.snapshot",
            "payload": {"spreadsheet_id": "sheet-123"},
        }
        stream = io.BytesIO()

        write_message(stream, message)
        stream.seek(0)

        self.assertEqual(read_message(stream), message)

    def test_invalid_json_raises(self):
        stream = io.BytesIO(struct.pack("<I", 1) + b"{")

        with self.assertRaises(InvalidMessageError):
            read_message(stream)

    def test_oversized_message_guard(self):
        stream = io.BytesIO(struct.pack("<I", 10) + b"{}")

        with self.assertRaises(MessageTooLargeError):
            read_message(stream, max_message_bytes=3)

    def test_unknown_message_type_raises(self):
        message = {
            "protocol_version": "1.0",
            "request_id": "request-1",
            "type": "sheet.magic",
            "payload": {},
        }

        with self.assertRaises(UnknownMessageTypeError):
            validate_message(message)

        with self.assertRaises(UnknownMessageTypeError):
            read_message(io.BytesIO(framed(message)))

    def test_phase1_allowed_messages_exclude_planned_plan_and_apply_types(self):
        self.assertEqual(
            ALLOWED_MESSAGE_TYPES,
            {"inspect.snapshot", "review.generate", "review.result", "error"},
        )
        self.assertEqual(PLANNED_REQUEST_MESSAGE_TYPES, {"plan.generate", "apply.record"})
        self.assertEqual(PLANNED_RESULT_MESSAGE_TYPES, {"plan.result", "apply.result"})


if __name__ == "__main__":
    unittest.main()
