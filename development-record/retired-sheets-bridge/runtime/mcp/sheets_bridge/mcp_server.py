from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Callable

from . import auth
from .chrome_resolver import DEFAULT_CHROME_DEBUG_URL, resolve_current_sheet
from .packages import write_bridge_package
from .sheets_api import apply_values_update, inspect_sheet, parse_spreadsheet_url
from .table_builder import (
    build_table_builder_mcp_app_html,
    build_table_builder_ui,
    create_formula_table_from_spec,
    rollback_created_artifact,
    save_table_build_intent,
    validate_excel_formula_results,
)
from .table_flow import refactor_minimal_formula_sheet, visualize_table_io
from .version import __version__


PROTOCOL_VERSION = "2025-06-18"
TABLE_BUILDER_APP_URI = "ui://sheets-bridge/table-builder"
MCP_APP_MIME_TYPE = "text/html;profile=mcp-app"


def tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "sheets_bridge_auth_status",
            "description": "Check whether Sheets Bridge has local Google OAuth credentials configured.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "idempotentHint": True},
        },
        {
            "name": "sheets_bridge_configure_oauth",
            "description": "Store the local Google OAuth desktop client id for Sheets Bridge.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "client_id": {"type": "string"},
                    "client_secret": {"type": "string"},
                    "access": {
                        "type": "string",
                        "enum": ["readonly", "readwrite", "copy", "copy_full"],
                        "default": "readonly",
                    },
                },
                "required": ["client_id"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": False, "idempotentHint": True},
        },
        {
            "name": "sheets_bridge_start_oauth_login",
            "description": "Open the Google OAuth consent flow and wait for the local callback.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": False, "idempotentHint": False},
        },
        {
            "name": "sheets_bridge_logout",
            "description": "Delete the local Sheets Bridge OAuth token cache.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": False, "idempotentHint": False},
        },
        {
            "name": "sheets_bridge_current_chrome_sheet",
            "description": "Read the current Google Sheets URL, gid, and selected range from Chrome remote debugging.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chrome_debug_url": {
                        "type": "string",
                        "default": DEFAULT_CHROME_DEBUG_URL,
                    }
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "idempotentHint": True},
        },
        {
            "name": "sheets_bridge_inspect",
            "description": "Inspect a Google Sheet through local user OAuth and write a sanitized review package.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spreadsheet_url": {"type": "string"},
                    "spreadsheet_id": {"type": "string"},
                    "gid": {"type": "string"},
                    "ranges": {"type": "array", "items": {"type": "string"}},
                    "operation": {
                        "type": "string",
                        "enum": [
                            "inspect.metadata",
                            "inspect.values_window",
                            "inspect.formula_window",
                            "inspect.grid_window",
                        ],
                        "default": "inspect.metadata",
                    },
                    "field_mask": {
                        "type": "string",
                        "enum": ["grid_basic_v1", "grid_formula_v1"],
                        "default": "grid_basic_v1",
                    },
                    "from_chrome": {"type": "boolean", "default": False},
                    "chrome_debug_url": {
                        "type": "string",
                        "default": DEFAULT_CHROME_DEBUG_URL,
                    },
                    "package_root": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "idempotentHint": False},
        },
        {
            "name": "sheets_bridge_apply_values_update",
            "description": "Apply a bounded USER_ENTERED values/formulas update with a before snapshot and rollback package.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spreadsheet_url": {"type": "string"},
                    "spreadsheet_id": {"type": "string"},
                    "gid": {"type": "string"},
                    "write_requests": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "range": {"type": "string"},
                                "values": {"type": "array", "items": {"type": "array"}},
                            },
                            "required": ["range", "values"],
                            "additionalProperties": False,
                        },
                    },
                    "rollback_required": {"type": "boolean"},
                    "package_root": {"type": "string"},
                },
                "required": ["write_requests", "rollback_required"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": False, "idempotentHint": False},
        },
        {
            "name": "sheets_bridge_rollback_values_restore",
            "description": "Restore values/formulas from a rollback object generated by Sheets Bridge.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rollback": {"type": "object"},
                    "spreadsheet_url": {"type": "string"},
                    "spreadsheet_id": {"type": "string"},
                    "gid": {"type": "string"},
                    "write_requests": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "range": {"type": "string"},
                                "values": {"type": "array", "items": {"type": "array"}},
                            },
                            "required": ["range", "values"],
                            "additionalProperties": False,
                        },
                    },
                    "package_root": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": False, "idempotentHint": False},
        },
        {
            "name": "sheets_bridge_visualize_table_io",
            "description": "Build a sanitized HTML/SVG package that visualizes table input/output flow for a bounded Google Sheets range.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spreadsheet_url": {"type": "string"},
                    "spreadsheet_id": {"type": "string"},
                    "gid": {"type": "string"},
                    "target_range": {"type": "string"},
                    "pattern": {
                        "type": "string",
                        "enum": ["auto", "monthly_product_performance_v1"],
                        "default": "auto",
                    },
                    "max_rows": {"type": "integer", "default": 300, "minimum": 1},
                    "max_columns": {"type": "integer", "default": 80, "minimum": 1},
                    "from_chrome": {"type": "boolean", "default": False},
                    "chrome_debug_url": {
                        "type": "string",
                        "default": DEFAULT_CHROME_DEBUG_URL,
                    },
                    "package_root": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "idempotentHint": False},
        },
        {
            "name": "sheets_bridge_refactor_minimal_formula_sheet",
            "description": "Create a new minimal-formula projection sheet for the supported monthly product performance pattern and validate it against the original output table.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spreadsheet_url": {"type": "string"},
                    "spreadsheet_id": {"type": "string"},
                    "gid": {"type": "string"},
                    "source_output_sheet_title": {"type": "string"},
                    "source_sku_sheet_title": {"type": "string"},
                    "source_ad_sheet_title": {"type": "string"},
                    "output_sheet_title": {"type": "string"},
                    "validation_range": {"type": "string", "default": "A5:AQ129"},
                    "dry_run": {"type": "boolean", "default": False},
                    "validation_attempts": {"type": "integer", "default": 6, "minimum": 1},
                    "validation_sleep_seconds": {"type": "number", "default": 2.0, "minimum": 0},
                    "from_chrome": {"type": "boolean", "default": False},
                    "chrome_debug_url": {
                        "type": "string",
                        "default": DEFAULT_CHROME_DEBUG_URL,
                    },
                    "package_root": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": False, "idempotentHint": False},
        },
        {
            "name": "spreadsheet_table_builder_ui",
            "description": "Create an interactive browser UI for sketching the desired output table and writing the LLM request prompt from a Google Sheet or Excel workbook preview. Desktop Google Sheets source reads use the MCP-managed local OAuth token cache.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spreadsheet_url": {"type": "string"},
                    "spreadsheet_id": {"type": "string"},
                    "gid": {"type": "string"},
                    "workbook_path": {"type": "string"},
                    "sheet_name": {"type": "string"},
                    "source_range": {"type": "string"},
                    "source_preview": {
                        "type": "object",
                        "description": "Sanitized source preview supplied by a remote host. When present, the server does not read local OAuth, Chrome, or workbook files.",
                    },
                    "max_rows": {"type": "integer", "default": 200, "minimum": 1},
                    "max_columns": {"type": "integer", "default": 30, "minimum": 1},
                    "from_chrome": {"type": "boolean", "default": False},
                    "chrome_debug_url": {
                        "type": "string",
                        "default": DEFAULT_CHROME_DEBUG_URL,
                    },
                    "package_root": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "idempotentHint": False},
            "_meta": {
                "ui": {"resourceUri": TABLE_BUILDER_APP_URI, "visibility": ["model", "app"]},
                "ui/resourceUri": TABLE_BUILDER_APP_URI,
            },
        },
        {
            "name": "spreadsheet_table_builder_save_intent",
            "description": "Save a TableBuildIntent submitted from the interactive table-builder UI.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "intent": {"type": "object"},
                    "package_root": {"type": "string"},
                },
                "required": ["intent"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": False, "idempotentHint": False},
            "_meta": {
                "ui": {"resourceUri": TABLE_BUILDER_APP_URI, "visibility": ["app"]},
                "ui/resourceUri": TABLE_BUILDER_APP_URI,
            },
        },
        {
            "name": "spreadsheet_create_formula_table_from_spec",
            "description": "Create a new auditable formula-only table from a table-builder spec JSON object or spec file path for Google Sheets or Excel workbooks.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spec": {"type": "object"},
                    "spec_path": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": False},
                    "package_root": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": False, "idempotentHint": False},
        },
        {
            "name": "spreadsheet_rollback_created_artifact",
            "description": "Execute a rollback instruction for a spreadsheet table-builder created sheet, spreadsheet copy, workbook copy, or Excel worksheet.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rollback": {"type": "object"},
                    "dry_run": {"type": "boolean", "default": False},
                },
                "required": ["rollback"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": False, "idempotentHint": False},
        },
        {
            "name": "spreadsheet_validate_excel_formula_results",
            "description": "Run static workbook formula-error checks and optionally sample cells through the real Microsoft Excel engine.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "workbook_path": {"type": "string"},
                    "worksheet": {"type": "string"},
                    "cells": {"type": "array", "items": {"type": "string"}},
                    "run_excel_engine": {"type": "boolean", "default": True},
                    "timeout_seconds": {"type": "integer", "default": 180, "minimum": 1},
                },
                "required": ["workbook_path", "worksheet", "cells"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "idempotentHint": False},
        },
    ]


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    if name == "sheets_bridge_auth_status":
        return auth.auth_status()
    if name == "sheets_bridge_configure_oauth":
        access = str(args.get("access") or "readonly")
        scopes = auth.scopes_for_access(access)
        path = auth.save_oauth_client_config(
            client_id=str(args.get("client_id", "")),
            client_secret=str(args.get("client_secret", "")),
            scopes=scopes,
        )
        return {"configured": True, "oauth_client_path": str(path), "access": access, "scopes": list(scopes)}
    if name == "sheets_bridge_start_oauth_login":
        return auth.login()
    if name == "sheets_bridge_logout":
        return auth.logout()
    if name == "sheets_bridge_current_chrome_sheet":
        return resolve_current_sheet(
            chrome_debug_url=str(args.get("chrome_debug_url") or DEFAULT_CHROME_DEBUG_URL)
        )
    if name == "sheets_bridge_inspect":
        return inspect_tool(args)
    if name == "sheets_bridge_apply_values_update":
        return apply_values_tool(args)
    if name == "sheets_bridge_rollback_values_restore":
        return rollback_values_tool(args)
    if name == "sheets_bridge_visualize_table_io":
        return visualize_table_io_tool(args)
    if name == "sheets_bridge_refactor_minimal_formula_sheet":
        return refactor_minimal_formula_sheet_tool(args)
    if name == "spreadsheet_table_builder_ui":
        return table_builder_ui_tool(args)
    if name == "spreadsheet_table_builder_save_intent":
        return save_table_build_intent_tool(args)
    if name == "spreadsheet_create_formula_table_from_spec":
        return create_formula_table_from_spec_tool(args)
    if name == "spreadsheet_rollback_created_artifact":
        return rollback_created_artifact_tool(args)
    if name == "spreadsheet_validate_excel_formula_results":
        return validate_excel_formula_results_tool(args)
    raise ValueError(f"unknown tool: {name}")


def resource_definitions() -> list[dict[str, Any]]:
    return [
        {
            "uri": TABLE_BUILDER_APP_URI,
            "name": "Spreadsheet Table Builder",
            "description": "Interactive UI for sketching a desired spreadsheet output table inside MCP Apps hosts.",
            "mimeType": MCP_APP_MIME_TYPE,
            "_meta": {
                "ui": {
                    "prefersBorder": False,
                    "csp": {
                        "connectDomains": [],
                        "resourceDomains": [],
                        "frameDomains": [],
                    },
                }
            },
        }
    ]


def read_resource(uri: str) -> dict[str, Any]:
    if uri != TABLE_BUILDER_APP_URI:
        raise ValueError(f"unknown resource: {uri}")
    return {
        "contents": [
            {
                "uri": TABLE_BUILDER_APP_URI,
                "mimeType": MCP_APP_MIME_TYPE,
                "text": build_table_builder_mcp_app_html(),
                "_meta": {
                    "ui": {
                        "prefersBorder": False,
                        "csp": {
                            "connectDomains": [],
                            "resourceDomains": [],
                            "frameDomains": [],
                        },
                    }
                },
            }
        ]
    }


def inspect_tool(args: dict[str, Any]) -> dict[str, Any]:
    context = sheet_context(args)
    ranges = [str(item) for item in args.get("ranges") or [] if str(item).strip()]
    if not ranges and context.get("range"):
        ranges = [str(context["range"])]

    access_token = auth.get_access_token()
    snapshot = inspect_sheet(
        spreadsheet_id=str(context["spreadsheet_id"]),
        access_token=access_token,
        operation=str(args.get("operation") or "inspect.metadata"),
        ranges=ranges,
        gid=str(context.get("gid") or ""),
        field_mask=str(args.get("field_mask") or "grid_basic_v1"),
    )
    package = write_bridge_package(
        snapshot=snapshot,
        package_root=Path(str(args["package_root"])) if args.get("package_root") else "review-packages/sheets-bridge/mcp",
    )
    return {"snapshot": _summary(snapshot), "package": package}


def apply_values_tool(args: dict[str, Any]) -> dict[str, Any]:
    if args.get("rollback_required") is not True:
        raise ValueError("rollback_required=true is required for apply.values_update")
    context = sheet_context(args)
    access_token = auth.get_access_token(required_scope=auth.READWRITE_SCOPE)
    snapshot = apply_values_update(
        spreadsheet_id=str(context["spreadsheet_id"]),
        access_token=access_token,
        write_requests=_write_requests(args),
        gid=str(context.get("gid") or ""),
        operation="apply.values_update",
    )
    package = write_bridge_package(
        snapshot=snapshot,
        package_root=Path(str(args["package_root"])) if args.get("package_root") else "review-packages/sheets-bridge/mcp",
    )
    return {"snapshot": _summary(snapshot), "package": package, "rollback": snapshot["rollback"]}


def rollback_values_tool(args: dict[str, Any]) -> dict[str, Any]:
    rollback = args.get("rollback") if isinstance(args.get("rollback"), dict) else {}
    merged_args = {**args}
    if rollback:
        merged_args["spreadsheet_id"] = args.get("spreadsheet_id") or rollback.get("spreadsheet_id")
        merged_args["write_requests"] = args.get("write_requests") or rollback.get("write_requests")
    context = sheet_context(merged_args)
    access_token = auth.get_access_token(required_scope=auth.READWRITE_SCOPE)
    snapshot = apply_values_update(
        spreadsheet_id=str(context["spreadsheet_id"]),
        access_token=access_token,
        write_requests=_write_requests(merged_args),
        gid=str(context.get("gid") or ""),
        operation="rollback.values_restore",
    )
    package = write_bridge_package(
        snapshot=snapshot,
        package_root=Path(str(args["package_root"])) if args.get("package_root") else "review-packages/sheets-bridge/mcp",
    )
    return {"snapshot": _summary(snapshot), "package": package, "rollback": snapshot["rollback"]}


def visualize_table_io_tool(args: dict[str, Any]) -> dict[str, Any]:
    context = sheet_context(args)
    access_token = auth.get_access_token()
    return visualize_table_io(
        spreadsheet_id=str(context["spreadsheet_id"]),
        access_token=access_token,
        gid=str(context.get("gid") or ""),
        target_range=str(args.get("target_range") or context.get("range") or ""),
        pattern=str(args.get("pattern") or "auto"),
        max_rows=int(args.get("max_rows") or 300),
        max_columns=int(args.get("max_columns") or 80),
        package_root=Path(str(args["package_root"])) if args.get("package_root") else "review-packages/sheets-bridge/mcp-table-io-flow",
    )


def refactor_minimal_formula_sheet_tool(args: dict[str, Any]) -> dict[str, Any]:
    context = sheet_context(args)
    access_token = auth.get_access_token(required_scope=auth.READWRITE_SCOPE)
    return refactor_minimal_formula_sheet(
        spreadsheet_id=str(context["spreadsheet_id"]),
        access_token=access_token,
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
        package_root=Path(str(args["package_root"])) if args.get("package_root") else "review-packages/sheets-bridge/mcp-refactor",
    )


def table_builder_ui_tool(args: dict[str, Any]) -> dict[str, Any]:
    workbook_path = str(args.get("workbook_path") or "")
    source_preview = args.get("source_preview") if isinstance(args.get("source_preview"), dict) else None
    context = {} if workbook_path or source_preview else sheet_context(args)
    access_token = "" if workbook_path or source_preview else auth.get_access_token()
    return build_table_builder_ui(
        spreadsheet_id=str(context.get("spreadsheet_id") or ""),
        access_token=access_token,
        workbook_path=workbook_path,
        sheet_name=str(args.get("sheet_name") or ""),
        gid=str(context.get("gid") or ""),
        source_range=str(args.get("source_range") or context.get("range") or ""),
        source_preview=source_preview,
        max_rows=int(args.get("max_rows") or 200),
        max_columns=int(args.get("max_columns") or 30),
        package_root=Path(str(args["package_root"])) if args.get("package_root") else "review-packages/spreadsheet-table-builder/mcp",
    )


def save_table_build_intent_tool(args: dict[str, Any]) -> dict[str, Any]:
    return save_table_build_intent(
        intent=args.get("intent") if isinstance(args.get("intent"), dict) else {},
        package_root=Path(str(args["package_root"])) if args.get("package_root") else "review-packages/spreadsheet-table-builder/intents",
    )


def create_formula_table_from_spec_tool(args: dict[str, Any]) -> dict[str, Any]:
    spec = _spec_arg(args)
    source = spec.get("source") if isinstance(spec.get("source"), dict) else {}
    is_excel = bool(source.get("workbook_path") or spec.get("workbook_path") or source.get("artifact_type") == "excel_workbook")
    output = spec.get("output") if isinstance(spec.get("output"), dict) else {}
    is_google_copy = not is_excel and str(output.get("creation_mode") or "").strip().lower() == "copy"
    access_token = ""
    if not is_excel:
        access_token = auth.get_access_token(required_scope=auth.READWRITE_SCOPE)
        if is_google_copy:
            access_token = auth.get_access_token(required_scope=auth.DRIVE_COPY_SCOPES)
    return create_formula_table_from_spec(
        spec=spec,
        access_token=access_token,
        dry_run=bool(args.get("dry_run")),
        package_root=Path(str(args["package_root"])) if args.get("package_root") else "review-packages/spreadsheet-table-builder/mcp",
    )


def rollback_created_artifact_tool(args: dict[str, Any]) -> dict[str, Any]:
    rollback = args.get("rollback") if isinstance(args.get("rollback"), dict) else {}
    rollback_type = str(rollback.get("type") or rollback.get("operation") or "")
    access_token = ""
    if rollback_type == "delete_created_sheet":
        access_token = auth.get_access_token(required_scope=auth.READWRITE_SCOPE)
    elif rollback_type == "delete_copied_spreadsheet":
        access_token = auth.get_access_token(required_scope=auth.DRIVE_COPY_SCOPES)
    return rollback_created_artifact(
        rollback=rollback,
        access_token=access_token,
        dry_run=bool(args.get("dry_run")),
    )


def validate_excel_formula_results_tool(args: dict[str, Any]) -> dict[str, Any]:
    return validate_excel_formula_results(
        workbook_path=str(args.get("workbook_path") or ""),
        worksheet=str(args.get("worksheet") or ""),
        cells=[str(item) for item in args.get("cells") or []],
        run_excel_engine=bool(args.get("run_excel_engine", True)),
        timeout_seconds=int(args.get("timeout_seconds") or 180),
    )


def sheet_context(args: dict[str, Any]) -> dict[str, str]:
    context = {}
    if args.get("from_chrome"):
        context = resolve_current_sheet(
            chrome_debug_url=str(args.get("chrome_debug_url") or DEFAULT_CHROME_DEBUG_URL)
        )
    parsed_url = parse_spreadsheet_url(str(args.get("spreadsheet_url") or context.get("url") or ""))
    spreadsheet_id = str(args.get("spreadsheet_id") or parsed_url["spreadsheet_id"] or context.get("spreadsheet_id") or "")
    gid = str(args.get("gid") or parsed_url["gid"] or context.get("gid") or "")
    if not spreadsheet_id:
        raise ValueError("spreadsheet_id or spreadsheet_url is required")
    return {
        "spreadsheet_id": spreadsheet_id,
        "gid": gid,
        "range": str(parsed_url.get("range") or context.get("range") or ""),
    }


def _write_requests(args: dict[str, Any]) -> list[dict[str, Any]]:
    write_requests = args.get("write_requests")
    if not isinstance(write_requests, list) or not write_requests:
        raise ValueError("write_requests are required")
    return [
        {
            "range": str(item.get("range", "")),
            "values": item.get("values", []),
        }
        for item in write_requests
        if isinstance(item, dict)
    ]


def _spec_arg(args: dict[str, Any]) -> dict[str, Any]:
    if isinstance(args.get("spec"), dict):
        return args["spec"]
    spec_path = str(args.get("spec_path") or "")
    if spec_path:
        value = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("spec_path must point to a JSON object")
        return value
    raise ValueError("spec or spec_path is required")


def serve(
    *,
    stdin=None,
    stdout=None,
    tool_caller: Callable[[str, dict[str, Any] | None], dict[str, Any]] = call_tool,
) -> None:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for raw_line in stdin:
        line = raw_line.strip()
        if not line:
            continue
        request = json.loads(line)
        response = handle_message(request, tool_caller=tool_caller)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            stdout.flush()


def handle_message(
    message: dict[str, Any],
    *,
    tool_caller: Callable[[str, dict[str, Any] | None], dict[str, Any]] = call_tool,
) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    try:
        if method == "initialize":
            return _response(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                    "serverInfo": {"name": "sheets-bridge", "version": __version__},
                },
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _response(request_id, {"tools": tool_definitions()})
        if method == "resources/list":
            return _response(request_id, {"resources": resource_definitions()})
        if method == "resources/read":
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            return _response(request_id, read_resource(str(params.get("uri") or "")))
        if method == "tools/call":
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            result = tool_caller(str(params.get("name", "")), params.get("arguments") or {})
            return _response(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
                        }
                    ],
                    "structuredContent": result,
                },
            )
        return _error(request_id, -32601, f"Method not found: {method}")
    except Exception as error:  # MCP tool errors should be surfaced as tool results.
        if method == "tools/call":
            return _response(
                request_id,
                {
                    "isError": True,
                    "content": [{"type": "text", "text": str(error)}],
                },
            )
        return _error(request_id, -32000, str(error))


def _response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": snapshot.get("operation", ""),
        "spreadsheet_id": snapshot.get("spreadsheet_id", ""),
        "title": snapshot.get("title", ""),
        "requested_ranges": snapshot.get("requested_ranges", []),
        "window_count": len(snapshot.get("windows", []) if isinstance(snapshot.get("windows"), list) else []),
        "tab_count": len(snapshot.get("tabs", []) if isinstance(snapshot.get("tabs"), list) else []),
        "write_count": snapshot.get("write_count", 0),
        "updated_cells": snapshot.get("updated_cells", 0),
    }


if __name__ == "__main__":
    serve()
