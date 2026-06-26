from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from datetime import UTC, datetime
from uuid import uuid4


DEFAULT_BROKER_URL = "https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app"
AUTH_SCHEME = "".join(("Be", "arer"))


def build_inspect_request(
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
) -> dict:
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id is required")
    request = {
        "request_id": request_id or f"cli-{uuid4()}",
        "operation": operation,
        "spreadsheet_id": spreadsheet_id,
        "sheet_ids": sheet_ids or [],
        "ranges": ranges or [],
        "risk_level": "low",
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "identity_hint": {
            "principal": principal,
        },
    }
    if field_mask:
        request["field_mask"] = field_mask
    if timeout_seconds is not None:
        request["timeout_seconds"] = timeout_seconds
    if retry_count is not None:
        request["retry_count"] = retry_count
    if total_cell_count is not None:
        request["total_cell_count"] = total_cell_count
    return request


def fetch_gcloud_identity_token(token_command: list[str] | None = None) -> str:
    command = token_command or ["gcloud", "auth", "print-identity-token"]
    token = subprocess.check_output(command, text=True).strip()
    if not token:
        raise RuntimeError("gcloud did not return an identity token")
    return token


def invoke_broker_inspect(
    *,
    broker_url: str,
    request: dict[str, Any],
    identity_token_fetcher=fetch_gcloud_identity_token,
    transport=None,
) -> dict[str, Any]:
    identity_token = identity_token_fetcher()
    post = transport or post_json
    return post(_inspect_url(broker_url), request, identity_token)


def post_json(url: str, body: dict[str, Any], access_token: str) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "X-Broker-Authorization": f"{AUTH_SCHEME} {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            return _json_response(response.read().decode("utf-8"))
    except HTTPError as error:
        body_text = error.read().decode("utf-8", errors="replace")
        return _json_response(body_text)


def _inspect_url(broker_url: str) -> str:
    if not broker_url:
        raise ValueError("broker_url is required")
    return urljoin(f"{broker_url.rstrip('/')}/", "v1/inspect")


def _json_response(text: str) -> dict[str, Any]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("broker response must be a JSON object")
    return value


def main(
    argv: list[str] | None = None,
    *,
    identity_token_fetcher=fetch_gcloud_identity_token,
    transport=None,
) -> int:
    parser = argparse.ArgumentParser(description="Build Sheets Bridge broker requests.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--spreadsheet-id", required=True)
    inspect_parser.add_argument("--broker-url", default=DEFAULT_BROKER_URL)
    inspect_parser.add_argument(
        "--operation",
        default="inspect.metadata",
        choices=[
            "inspect.metadata",
            "inspect.grid_window",
            "inspect.values_window",
            "inspect.formula_window",
        ],
    )
    inspect_parser.add_argument("--principal", default="")
    inspect_parser.add_argument("--sheet-id", action="append", type=int, default=[])
    inspect_parser.add_argument("--range", dest="ranges", action="append", default=[])
    inspect_parser.add_argument("--field-mask")
    inspect_parser.add_argument("--timeout-seconds", type=int)
    inspect_parser.add_argument("--retry-count", type=int)
    inspect_parser.add_argument("--total-cell-count", type=int)
    inspect_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "inspect":
        request = build_inspect_request(
            spreadsheet_id=args.spreadsheet_id,
            principal=args.principal,
            operation=args.operation,
            sheet_ids=args.sheet_id,
            ranges=args.ranges,
            field_mask=args.field_mask,
            timeout_seconds=args.timeout_seconds,
            retry_count=args.retry_count,
            total_cell_count=args.total_cell_count,
        )
        if not args.dry_run:
            response = invoke_broker_inspect(
                broker_url=args.broker_url,
                request=request,
                identity_token_fetcher=identity_token_fetcher,
                transport=transport,
            )
            print(json.dumps(response, ensure_ascii=False, sort_keys=True))
            return 0 if response.get("ok") else 2
        print(json.dumps(request, ensure_ascii=False, sort_keys=True))
        return 0
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
