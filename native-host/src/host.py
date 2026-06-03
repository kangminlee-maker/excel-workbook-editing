from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any, BinaryIO

from protocol import (
    PROTOCOL_VERSION,
    InvalidMessageError,
    ProtocolError,
    read_message,
    write_message,
)
from review_package import ReviewPackageError, write_inspection_package


def handle_message(
    message: dict[str, Any],
    *,
    package_root: Path | str | None = None,
) -> dict[str, Any]:
    request_id = message.get("request_id") if isinstance(message.get("request_id"), str) else ""
    try:
        message_type = message.get("type")
        if message_type != "inspect.snapshot":
            raise InvalidMessageError(f"unsupported native host request: {message_type}")
        result = write_inspection_package(
            message=message,
            package_root=package_root or _default_package_root(),
        )
        return {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id,
            "type": "review.result",
            "ok": True,
            "payload": result,
        }
    except (ProtocolError, ReviewPackageError, OSError) as error:
        return _error_response(
            request_id=request_id,
            code="review_package_failed",
            message=str(error),
        )


def run(
    *,
    input_stream: BinaryIO,
    output_stream: BinaryIO,
    package_root: Path | str | None = None,
) -> int:
    while True:
        try:
            message = read_message(input_stream)
        except ProtocolError as error:
            write_message(
                output_stream,
                _error_response(
                    request_id="",
                    code="invalid_message",
                    message=str(error),
                ),
            )
            continue
        if message is None:
            return 0
        write_message(
            output_stream,
            handle_message(message, package_root=package_root),
        )


def _error_response(*, request_id: str, code: str, message: str) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id or "native-error",
        "type": "error",
        "ok": False,
        "error": {
            "code": code,
            "message": message or code,
        },
    }


def _default_package_root() -> Path:
    configured = os.environ.get("SHEETS_BRIDGE_REVIEW_ROOT")
    if configured:
        return Path(configured)
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "review-packages" / "sheets-bridge" / "native-host"


def main() -> int:
    return run(input_stream=sys.stdin.buffer, output_stream=sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
