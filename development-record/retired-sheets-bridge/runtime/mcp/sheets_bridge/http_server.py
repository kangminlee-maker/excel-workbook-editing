from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any
from urllib.error import HTTPError

from . import auth, remote_auth
from .mcp_server import (
    PROTOCOL_VERSION,
    _spec_arg,
    _summary,
    _write_requests,
    call_tool,
    handle_message,
    sheet_context,
)
from .packages import write_bridge_package
from .sheets_api import (
    apply_values_update,
    google_delete_json,
    google_get_json,
    google_post_json,
    inspect_sheet,
)
from .table_builder import (
    build_table_builder_ui,
    create_formula_table_from_spec,
    rollback_created_artifact,
)
from .table_flow import refactor_minimal_formula_sheet, visualize_table_io
from .version import __version__


REMOTE_RUNTIME_NAME = "sheets-bridge-http"
LOCAL_OAUTH_TOOLS = {
    "sheets_bridge_auth_status",
    "sheets_bridge_configure_oauth",
    "sheets_bridge_start_oauth_login",
    "sheets_bridge_logout",
}
LOCAL_CHROME_TOOLS = {"sheets_bridge_current_chrome_sheet"}


class SheetsBridgeHttpHandler(BaseHTTPRequestHandler):
    server_version = "SheetsBridgeHTTP/1.0"

    def do_OPTIONS(self) -> None:
        self._send_json({}, status=204)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._send_json(
                {
                    "status": "ok",
                    "service": REMOTE_RUNTIME_NAME,
                    "protocolVersion": PROTOCOL_VERSION,
                    "serverInfo": {"name": "sheets-bridge", "version": __version__},
                }
            )
            return
        self._send_json({"error": "not_found", "path": self.path}, status=404)

    def do_POST(self) -> None:
        if self.path != "/mcp":
            self._send_json({"error": "not_found", "path": self.path}, status=404)
            return
        try:
            payload = self._read_json()
        except ValueError as error:
            self._send_json({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(error)}}, status=400)
            return

        if isinstance(payload, list):
            tool_caller = self._remote_tool_caller()
            responses = [
                response
                for message in payload
                if isinstance(message, dict)
                for response in [handle_message(message, tool_caller=tool_caller)]
                if response is not None
            ]
            if responses:
                self._send_json(responses)
                return
            self._send_json({}, status=204)
            return
        if not isinstance(payload, dict):
            self._send_json(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "JSON-RPC payload must be an object or array"}},
                status=400,
            )
            return

        response = handle_message(payload, tool_caller=self._remote_tool_caller())
        if response is None:
            self._send_json({}, status=204)
            return
        self._send_json(response)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _remote_tool_caller(self) -> "RemoteToolCaller":
        server = self.server
        return RemoteToolCaller(
            headers=self.headers,
            session_store=getattr(server, "remote_session_store", None),
            google_get_transport=getattr(server, "google_get_transport", None),
            google_post_transport=getattr(server, "google_post_transport", None),
            google_delete_transport=getattr(server, "google_delete_transport", None),
        )

    def _read_json(self) -> Any:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length)
        if not raw_body:
            raise ValueError("empty JSON body")
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON: {error.msg}") from error

    def _send_json(self, payload: Any, *, status: int = 200) -> None:
        body = b"" if status == 204 else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)


@dataclass
class RemoteToolCaller:
    headers: Any
    session_store: remote_auth.RemoteSessionStore | None = None
    google_get_transport: Any = None
    google_post_transport: Any = None
    google_delete_transport: Any = None

    def __call__(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        try:
            return self._call(name, args)
        except remote_auth.RemoteAuthError as error:
            return error.to_result(tool=name)
        except HTTPError as error:
            return _remote_google_error_result(name, error)

    def _call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "sheets_bridge_auth_status":
            return remote_auth.remote_auth_status(self.headers, store=self.session_store)
        if name in {"sheets_bridge_configure_oauth", "sheets_bridge_start_oauth_login", "sheets_bridge_logout"}:
            return _boundary_result(
                tool=name,
                status="remote_auth_managed_by_host",
                reason="Remote MCP authorization is managed by the remote host/session store, not by the desktop OAuth tools.",
                required_runtime="remote_authorized_google_sheets_session",
                next_action="Configure remote session storage or authorize through the remote MCP host.",
                request_summary=_request_summary(args),
            )
        if name == "spreadsheet_table_builder_save_intent":
            return call_tool(name, args)
        if name == "spreadsheet_table_builder_ui" and isinstance(args.get("source_preview"), dict):
            return call_tool(name, args)
        boundary = remote_capability_boundary(name, args)
        if boundary is not None:
            return boundary
        if name == "sheets_bridge_inspect":
            return self._inspect(args)
        if name == "sheets_bridge_apply_values_update":
            return self._apply_values(args)
        if name == "sheets_bridge_rollback_values_restore":
            return self._rollback_values(args)
        if name == "sheets_bridge_visualize_table_io":
            return self._visualize_table_io(args)
        if name == "sheets_bridge_refactor_minimal_formula_sheet":
            return self._refactor_minimal_formula_sheet(args)
        if name == "spreadsheet_table_builder_ui":
            return self._table_builder_ui(args)
        if name == "spreadsheet_create_formula_table_from_spec":
            return self._create_formula_table(args)
        if name == "spreadsheet_rollback_created_artifact":
            return self._rollback_created_artifact(args)
        return call_tool(name, args)

    def _read_session(self) -> remote_auth.RemoteSession:
        return remote_auth.require_remote_session(
            self.headers,
            store=self.session_store,
            required_any=remote_auth.READ_SCOPES,
        )

    def _write_session(self) -> remote_auth.RemoteSession:
        return remote_auth.require_remote_session(
            self.headers,
            store=self.session_store,
            required_all=(auth.READWRITE_SCOPE,),
        )

    def _copy_session(self) -> remote_auth.RemoteSession:
        return remote_auth.require_remote_session(
            self.headers,
            store=self.session_store,
            required_all=(auth.READWRITE_SCOPE,),
            required_any=auth.DRIVE_COPY_SCOPES,
        )

    def _inspect(self, args: dict[str, Any]) -> dict[str, Any]:
        session = self._read_session()
        context = sheet_context(args)
        ranges = [str(item) for item in args.get("ranges") or [] if str(item).strip()]
        if not ranges and context.get("range"):
            ranges = [str(context["range"])]
        snapshot = inspect_sheet(
            spreadsheet_id=str(context["spreadsheet_id"]),
            access_token=session.access_token,
            operation=str(args.get("operation") or "inspect.metadata"),
            ranges=ranges,
            gid=str(context.get("gid") or ""),
            field_mask=str(args.get("field_mask") or "grid_basic_v1"),
            auth_summary=session.sanitized_summary(),
            transport=self.google_get_transport or google_get_json,
        )
        package = write_bridge_package(
            snapshot=snapshot,
            package_root=args.get("package_root") or "review-packages/sheets-bridge/mcp",
        )
        return {"snapshot": _summary(snapshot), "package": package}

    def _apply_values(self, args: dict[str, Any]) -> dict[str, Any]:
        if args.get("rollback_required") is not True:
            raise ValueError("rollback_required=true is required for apply.values_update")
        session = self._write_session()
        context = sheet_context(args)
        snapshot = apply_values_update(
            spreadsheet_id=str(context["spreadsheet_id"]),
            access_token=session.access_token,
            write_requests=_write_requests(args),
            gid=str(context.get("gid") or ""),
            operation="apply.values_update",
            auth_summary=session.sanitized_summary(),
            transport=self.google_get_transport or google_get_json,
            write_transport=self.google_post_transport or google_post_json,
        )
        package = write_bridge_package(
            snapshot=snapshot,
            package_root=args.get("package_root") or "review-packages/sheets-bridge/mcp",
        )
        return {"snapshot": _summary(snapshot), "package": package, "rollback": snapshot["rollback"]}

    def _rollback_values(self, args: dict[str, Any]) -> dict[str, Any]:
        session = self._write_session()
        rollback = args.get("rollback") if isinstance(args.get("rollback"), dict) else {}
        merged_args = {**args}
        if rollback:
            merged_args["spreadsheet_id"] = args.get("spreadsheet_id") or rollback.get("spreadsheet_id")
            merged_args["write_requests"] = args.get("write_requests") or rollback.get("write_requests")
        context = sheet_context(merged_args)
        snapshot = apply_values_update(
            spreadsheet_id=str(context["spreadsheet_id"]),
            access_token=session.access_token,
            write_requests=_write_requests(merged_args),
            gid=str(context.get("gid") or ""),
            operation="rollback.values_restore",
            auth_summary=session.sanitized_summary(),
            transport=self.google_get_transport or google_get_json,
            write_transport=self.google_post_transport or google_post_json,
        )
        package = write_bridge_package(
            snapshot=snapshot,
            package_root=args.get("package_root") or "review-packages/sheets-bridge/mcp",
        )
        return {"snapshot": _summary(snapshot), "package": package, "rollback": snapshot["rollback"]}

    def _visualize_table_io(self, args: dict[str, Any]) -> dict[str, Any]:
        session = self._read_session()
        context = sheet_context(args)
        return visualize_table_io(
            spreadsheet_id=str(context["spreadsheet_id"]),
            access_token=session.access_token,
            gid=str(context.get("gid") or ""),
            target_range=str(args.get("target_range") or context.get("range") or ""),
            pattern=str(args.get("pattern") or "auto"),
            max_rows=int(args.get("max_rows") or 300),
            max_columns=int(args.get("max_columns") or 80),
            package_root=args.get("package_root") or "review-packages/sheets-bridge/mcp-table-io-flow",
            transport=self.google_get_transport or google_get_json,
        )

    def _refactor_minimal_formula_sheet(self, args: dict[str, Any]) -> dict[str, Any]:
        session = self._write_session()
        context = sheet_context(args)
        return refactor_minimal_formula_sheet(
            spreadsheet_id=str(context["spreadsheet_id"]),
            access_token=session.access_token,
            gid=str(context.get("gid") or ""),
            source_output_sheet_title=str(args.get("source_output_sheet_title") or ""),
            source_sku_sheet_title=str(args.get("source_sku_sheet_title") or ""),
            source_ad_sheet_title=str(args.get("source_ad_sheet_title") or ""),
            output_sheet_title=str(args.get("output_sheet_title") or ""),
            validation_range=str(args.get("validation_range") or "A5:AQ129"),
            dry_run=bool(args.get("dry_run")),
            validation_attempts=int(args.get("validation_attempts") or 6),
            validation_sleep_seconds=float(
                args["validation_sleep_seconds"] if args.get("validation_sleep_seconds") is not None else 2.0
            ),
            package_root=args.get("package_root") or "review-packages/sheets-bridge/mcp-refactor",
            transport=self.google_get_transport or google_get_json,
            write_transport=self.google_post_transport or google_post_json,
        )

    def _table_builder_ui(self, args: dict[str, Any]) -> dict[str, Any]:
        session = self._read_session()
        context = sheet_context(args)
        return build_table_builder_ui(
            spreadsheet_id=str(context.get("spreadsheet_id") or ""),
            access_token=session.access_token,
            gid=str(context.get("gid") or ""),
            source_range=str(args.get("source_range") or context.get("range") or ""),
            max_rows=int(args.get("max_rows") or 200),
            max_columns=int(args.get("max_columns") or 30),
            package_root=args.get("package_root") or "review-packages/spreadsheet-table-builder/mcp",
            transport=self.google_get_transport or google_get_json,
        )

    def _create_formula_table(self, args: dict[str, Any]) -> dict[str, Any]:
        spec = _spec_arg(args)
        source = spec.get("source") if isinstance(spec.get("source"), dict) else {}
        if source.get("workbook_path") or spec.get("workbook_path") or source.get("artifact_type") == "excel_workbook":
            return _create_formula_table_boundary("spreadsheet_create_formula_table_from_spec", args)
        output = spec.get("output") if isinstance(spec.get("output"), dict) else {}
        session = self._copy_session() if str(output.get("creation_mode") or "").strip().lower() == "copy" else self._write_session()
        return create_formula_table_from_spec(
            spec=spec,
            access_token=session.access_token,
            dry_run=bool(args.get("dry_run")),
            package_root=args.get("package_root") or "review-packages/spreadsheet-table-builder/mcp",
            transport=self.google_get_transport or google_get_json,
            write_transport=self.google_post_transport or google_post_json,
        )

    def _rollback_created_artifact(self, args: dict[str, Any]) -> dict[str, Any]:
        rollback = args.get("rollback") if isinstance(args.get("rollback"), dict) else {}
        rollback_type = str(rollback.get("type") or rollback.get("operation") or "")
        if rollback_type in {"delete_output_workbook_copy", "delete_created_worksheet"}:
            return _rollback_boundary("spreadsheet_rollback_created_artifact", args)
        session = self._copy_session() if rollback_type == "delete_copied_spreadsheet" else self._write_session()
        return rollback_created_artifact(
            rollback=rollback,
            access_token=session.access_token,
            dry_run=bool(args.get("dry_run")),
            write_transport=self.google_post_transport or google_post_json,
            delete_transport=self.google_delete_transport or google_delete_json,
        )


def remote_tool_caller(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return RemoteToolCaller(headers={})(name, arguments)


def remote_capability_boundary(name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    if name in LOCAL_CHROME_TOOLS or args.get("from_chrome") is True:
        return _boundary_result(
            tool=name,
            status="local_runtime_required",
            reason="Chrome current-tab resolution requires a desktop browser debugging context.",
            required_runtime="desktop_runtime",
            next_action="Call this tool through the local stdio MCP server, or pass spreadsheet_id/spreadsheet_url and range explicitly.",
            request_summary=_request_summary(args),
        )
    if name == "spreadsheet_table_builder_ui":
        if args.get("workbook_path"):
            return _boundary_result(
                tool=name,
                status="local_runtime_required",
                reason="Local workbook paths are available only to the desktop runtime.",
                required_runtime="uploaded_artifact_workflow",
                next_action="Provide a sanitized source_preview for remote UI creation, or use the local stdio MCP server for workbook files.",
                request_summary=_request_summary(args),
            )
        return None
    if name == "spreadsheet_validate_excel_formula_results":
        return _boundary_result(
            tool=name,
            status="local_runtime_required",
            reason="Excel formula-result validation needs a local workbook file and desktop Excel runtime.",
            required_runtime="desktop_runtime",
            next_action="Use the local stdio MCP server for Excel validation.",
            request_summary=_request_summary(args),
        )
    if name == "spreadsheet_create_formula_table_from_spec":
        spec = args.get("spec") if isinstance(args.get("spec"), dict) else {}
        source = spec.get("source") if isinstance(spec.get("source"), dict) else {}
        if source.get("workbook_path") or spec.get("workbook_path") or source.get("artifact_type") == "excel_workbook":
            return _create_formula_table_boundary(name, args)
        return None
    if name == "spreadsheet_rollback_created_artifact":
        rollback = args.get("rollback") if isinstance(args.get("rollback"), dict) else {}
        rollback_type = str(rollback.get("type") or rollback.get("operation") or "")
        if rollback_type in {"delete_output_workbook_copy", "delete_created_worksheet"}:
            return _rollback_boundary(name, args)
        return None
    return None


def make_http_server(
    host: str = "127.0.0.1",
    port: int = 8766,
    *,
    remote_session_store: remote_auth.RemoteSessionStore | None = None,
    google_get_transport: Any = None,
    google_post_transport: Any = None,
    google_delete_transport: Any = None,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), SheetsBridgeHttpHandler)
    server.remote_session_store = remote_session_store or remote_auth.default_remote_session_store()  # type: ignore[attr-defined]
    server.google_get_transport = google_get_transport  # type: ignore[attr-defined]
    server.google_post_transport = google_post_transport  # type: ignore[attr-defined]
    server.google_delete_transport = google_delete_transport  # type: ignore[attr-defined]
    return server


def serve_http(host: str = "127.0.0.1", port: int = 8766) -> None:
    server = make_http_server(host=host, port=port)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Sheets Bridge remote MCP HTTP server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    serve_http(host=args.host, port=args.port)


def _create_formula_table_boundary(name: str, args: dict[str, Any]) -> dict[str, Any]:
    spec = args.get("spec") if isinstance(args.get("spec"), dict) else {}
    source = spec.get("source") if isinstance(spec.get("source"), dict) else {}
    artifact_type = str(spec.get("artifact_type") or source.get("artifact_type") or "")
    if artifact_type == "excel_workbook" or source.get("workbook_path") or spec.get("workbook_path"):
        return _boundary_result(
            tool=name,
            status="local_runtime_required",
            reason="Excel formula-table creation requires local workbook access.",
            required_runtime="desktop_runtime",
            next_action="Use the local stdio MCP server or an approved uploaded-artifact runtime for Excel workbooks.",
            request_summary=_request_summary(args),
        )
    return _boundary_result(
        tool=name,
        status="remote_capability_boundary",
        reason="Google Sheets formula-table creation over HTTP requires remote user/session authorization.",
        required_runtime="remote_authorized_google_sheets_session",
        next_action="Complete remote authorization before creating live Google Sheets tabs or copies.",
        request_summary=_request_summary(args),
    )


def _rollback_boundary(name: str, args: dict[str, Any]) -> dict[str, Any]:
    rollback = args.get("rollback") if isinstance(args.get("rollback"), dict) else {}
    rollback_type = str(rollback.get("type") or rollback.get("operation") or "")
    if rollback_type in {"delete_output_workbook_copy", "delete_created_worksheet"}:
        return _boundary_result(
            tool=name,
            status="local_runtime_required",
            reason="Excel rollback requires local workbook file access.",
            required_runtime="desktop_runtime",
            next_action="Use the local stdio MCP server for Excel rollback.",
            request_summary=_request_summary(args),
        )
    return _boundary_result(
        tool=name,
        status="remote_capability_boundary",
        reason="Google Sheets rollback over HTTP requires remote user/session authorization.",
        required_runtime="remote_authorized_google_sheets_session",
        next_action="Complete remote authorization before deleting created Sheets tabs or copied spreadsheets.",
        request_summary=_request_summary(args),
    )


def _boundary_result(
    *,
    tool: str,
    status: str,
    reason: str,
    required_runtime: str,
    next_action: str,
    request_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "operation": "remote.capability_boundary",
        "status": status,
        "tool": tool,
        "reason": reason,
        "required_runtime": required_runtime,
        "next_action": next_action,
        "credential_boundary": {
            "local_oauth_cache_visible": False,
            "raw_credentials_returned": False,
            "local_workbook_paths_available": False,
            "desktop_excel_available": False,
            "chrome_debug_context_available": False,
        },
        "request_summary": request_summary,
    }


def _remote_google_error_result(tool: str, error: HTTPError) -> dict[str, Any]:
    return {
        "operation": "remote.google_api_error",
        "status": "remote_google_api_error",
        "tool": tool,
        "http_status": error.code,
        "reason": error.reason,
        "next_action": "Check the remote session permission, spreadsheet access, and requested range, then retry.",
        "credential_boundary": {
            "access_token_returned": False,
            "refresh_token_returned": False,
            "raw_credentials_returned": False,
        },
    }


def _request_summary(args: dict[str, Any]) -> dict[str, Any]:
    spec = args.get("spec") if isinstance(args.get("spec"), dict) else {}
    source = spec.get("source") if isinstance(spec.get("source"), dict) else {}
    rollback = args.get("rollback") if isinstance(args.get("rollback"), dict) else {}
    return {
        "has_spreadsheet_id": bool(args.get("spreadsheet_id") or spec.get("spreadsheet_id") or source.get("spreadsheet_id")),
        "has_spreadsheet_url": bool(args.get("spreadsheet_url")),
        "has_workbook_path": bool(args.get("workbook_path") or spec.get("workbook_path") or source.get("workbook_path")),
        "has_source_preview": isinstance(args.get("source_preview"), dict),
        "from_chrome": bool(args.get("from_chrome")),
        "artifact_type": str(args.get("artifact_type") or spec.get("artifact_type") or source.get("artifact_type") or ""),
        "creation_mode": str((spec.get("output") if isinstance(spec.get("output"), dict) else {}).get("creation_mode") or ""),
        "rollback_type": str(rollback.get("type") or rollback.get("operation") or ""),
    }


if __name__ == "__main__":
    main()
