"""Chrome Native Messaging protocol utilities for the Sheets bridge."""

from __future__ import annotations

import json
import struct
from typing import Any, BinaryIO

PROTOCOL_VERSION = "1.0"
NATIVE_HOST_NAME = "com.day1company.sheets_bridge"
MAX_MESSAGE_BYTES = 1024 * 1024

ACTIVE_REQUEST_MESSAGE_TYPES = frozenset(
    {
        "inspect.snapshot",
        "review.generate",
    }
)
PLANNED_REQUEST_MESSAGE_TYPES = frozenset({"plan.generate", "apply.record"})
ACTIVE_RESULT_MESSAGE_TYPES = frozenset({"review.result"})
PLANNED_RESULT_MESSAGE_TYPES = frozenset({"plan.result", "apply.result"})
REQUEST_MESSAGE_TYPES = ACTIVE_REQUEST_MESSAGE_TYPES
RESULT_MESSAGE_TYPES = ACTIVE_RESULT_MESSAGE_TYPES
TERMINAL_MESSAGE_TYPES = frozenset({"error"})
ALLOWED_MESSAGE_TYPES = (
    ACTIVE_REQUEST_MESSAGE_TYPES | ACTIVE_RESULT_MESSAGE_TYPES | TERMINAL_MESSAGE_TYPES
)

DEFAULT_TIMEOUT_BUDGET = {
    "read_seconds": 60,
    "write_seconds": 60,
    "poll_seconds": 120,
}


class ProtocolError(ValueError):
    """Base class for protocol validation and framing failures."""


class InvalidMessageError(ProtocolError):
    """Raised when a framed payload is not a valid protocol message."""


class MessageTooLargeError(ProtocolError):
    """Raised when a Native Messaging payload exceeds the configured limit."""


class UnknownMessageTypeError(InvalidMessageError):
    """Raised when a message type is outside the active Phase 1 protocol."""


def _read_exact(stream: BinaryIO, byte_count: int) -> bytes:
    data = stream.read(byte_count)
    if len(data) != byte_count:
        raise InvalidMessageError("unexpected end of stream")
    return data


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidMessageError(f"{label} must be an object")
    return value


def validate_message(message: Any) -> dict[str, Any]:
    envelope = _require_object(message, "message")

    protocol_version = envelope.get("protocol_version")
    if protocol_version != PROTOCOL_VERSION:
        raise InvalidMessageError("unsupported protocol_version")

    request_id = envelope.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise InvalidMessageError("request_id must be a non-empty string")

    message_type = envelope.get("type")
    if not isinstance(message_type, str) or not message_type:
        raise InvalidMessageError("type must be a non-empty string")
    if message_type not in ALLOWED_MESSAGE_TYPES:
        raise UnknownMessageTypeError(f"unknown message type: {message_type}")

    if message_type in REQUEST_MESSAGE_TYPES:
        _require_object(envelope.get("payload"), "payload")
        return envelope

    if message_type in RESULT_MESSAGE_TYPES:
        if envelope.get("ok") is not True:
            raise InvalidMessageError("result messages must set ok=true")
        _require_object(envelope.get("payload"), "payload")
        return envelope

    if message_type == "error":
        if envelope.get("ok") is not False:
            raise InvalidMessageError("error messages must set ok=false")
        error = _require_object(envelope.get("error"), "error")
        code = error.get("code")
        message_text = error.get("message")
        if not isinstance(code, str) or not code:
            raise InvalidMessageError("error.code must be a non-empty string")
        if not isinstance(message_text, str) or not message_text:
            raise InvalidMessageError("error.message must be a non-empty string")
        return envelope

    raise UnknownMessageTypeError(f"unknown message type: {message_type}")


def read_message(
    stream: BinaryIO,
    *,
    max_message_bytes: int = MAX_MESSAGE_BYTES,
) -> dict[str, Any] | None:
    header = stream.read(4)
    if header == b"":
        return None
    if len(header) != 4:
        raise InvalidMessageError("incomplete length prefix")

    (payload_length,) = struct.unpack("<I", header)
    if payload_length > max_message_bytes:
        raise MessageTooLargeError(
            f"message length {payload_length} exceeds limit {max_message_bytes}"
        )

    payload = _read_exact(stream, payload_length)
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidMessageError("payload is not valid UTF-8 JSON") from exc

    return validate_message(decoded)


def write_message(
    stream: BinaryIO,
    message: dict[str, Any],
    *,
    max_message_bytes: int = MAX_MESSAGE_BYTES,
) -> None:
    envelope = validate_message(message)
    payload = json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    if len(payload) > max_message_bytes:
        raise MessageTooLargeError(
            f"message length {len(payload)} exceeds limit {max_message_bytes}"
        )
    stream.write(struct.pack("<I", len(payload)))
    stream.write(payload)
    flush = getattr(stream, "flush", None)
    if callable(flush):
        flush()
