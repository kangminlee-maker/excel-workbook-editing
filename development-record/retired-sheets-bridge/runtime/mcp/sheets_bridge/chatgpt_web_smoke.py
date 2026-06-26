from __future__ import annotations

import argparse
from datetime import UTC, datetime
from html import escape
import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from .contracts import TABLE_BUILD_PLAN_KIND, validate_table_build_plan


DEFAULT_PACKAGE_ROOT = Path("review-packages/spreadsheet-table-builder/chatgpt-web-smoke")
DEFAULT_SOURCE_PREVIEW = {
    "artifact_type": "google_sheets",
    "spreadsheet_id": "chatgpt-web-smoke-spreadsheet",
    "workbook_title": "ChatGPT Web Smoke Source",
    "sheet_title": "Raw",
    "qualified_range": "'Raw'!A1:C4",
    "values": [
        ["Team", "Month", "Revenue"],
        ["Team A", "2026-01", "10"],
        ["Team A", "2026-02", "15"],
        ["Team B", "2026-01", "20"],
    ],
    "formulas": [
        ["Team", "Month", "Revenue"],
        ["Team A", "2026-01", ""],
        ["Team A", "2026-02", ""],
        ["Team B", "2026-01", ""],
    ],
}
DEFAULT_OUTPUT_CANVAS = [["", "2026-01", "2026-02"], ["Team A", "", ""], ["Team B", "", ""]]
DEFAULT_LLM_PROMPT = "원본 데이터 안에서 팀별 월별 매출 합계를 새 시트의 수식과 참조로 채워줘."


def run_chatgpt_web_smoke(
    *,
    endpoint_url: str,
    session_id: str = "",
    package_root: Path | str = DEFAULT_PACKAGE_ROOT,
    source_preview: dict[str, Any] | None = None,
    output_canvas: list[list[Any]] | None = None,
    llm_prompt: str = DEFAULT_LLM_PROMPT,
    timeout_seconds: int = 30,
    allow_insecure_localhost: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    endpoint = _normalize_endpoint(endpoint_url, allow_insecure_localhost=allow_insecure_localhost)
    created_at = (now or datetime.now(UTC)).isoformat()
    package_dir = _unique_package_dir(package_root, created_at, f"chatgpt-web-smoke-{uuid4().hex[:8]}")
    source_preview = source_preview or DEFAULT_SOURCE_PREVIEW
    output_canvas = output_canvas or DEFAULT_OUTPUT_CANVAS

    headers = {"Authorization": f"Bearer {session_id}"} if session_id else {}
    step_results: list[dict[str, Any]] = []
    health = _get_json(endpoint["healthz_url"], timeout_seconds=timeout_seconds)
    step_results.append(_step("healthz", health))
    initialized = _post_mcp(
        endpoint["mcp_url"],
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}}},
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    step_results.append(_step("initialize", initialized))
    tools = _post_mcp(endpoint["mcp_url"], {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, headers=headers, timeout_seconds=timeout_seconds)
    step_results.append(_step("tools_list", tools))
    resources = _post_mcp(endpoint["mcp_url"], {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}}, headers=headers, timeout_seconds=timeout_seconds)
    step_results.append(_step("resources_list", resources))
    resource = _post_mcp(
        endpoint["mcp_url"],
        {"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {"uri": "ui://sheets-bridge/table-builder"}},
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    step_results.append(_step("resource_read_table_builder", _resource_summary(resource)))
    auth_status = _post_mcp(
        endpoint["mcp_url"],
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "sheets_bridge_auth_status", "arguments": {}}},
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    step_results.append(_step("remote_auth_status", auth_status))
    ui_result = _post_mcp(
        endpoint["mcp_url"],
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "spreadsheet_table_builder_ui",
                "arguments": {
                    "source_preview": source_preview,
                    "package_root": str(package_dir / "table-builder-ui"),
                },
            },
        },
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    step_results.append(_step("table_builder_ui", _tool_summary(ui_result)))
    ui_structured = _structured(ui_result)
    intent_result = _post_mcp(
        endpoint["mcp_url"],
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "spreadsheet_table_builder_save_intent",
                "arguments": {
                    "package_root": str(package_dir / "intents"),
                    "intent": _intent_from_ui_result(ui_structured, output_canvas, llm_prompt),
                },
            },
        },
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    step_results.append(_step("save_intent", _tool_summary(intent_result)))
    local_boundary = _post_mcp(
        endpoint["mcp_url"],
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "spreadsheet_validate_excel_formula_results",
                "arguments": {"workbook_path": "/chatgpt-web/unavailable.xlsx", "worksheet": "Raw", "cells": ["A1"]},
            },
        },
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    step_results.append(_step("local_runtime_boundary", _tool_summary(local_boundary)))

    saved_intent = _structured(intent_result).get("intent", {})
    plan = _plan_from_intent(saved_intent)
    validate_table_build_plan(plan)
    write_gate = {
        "status": "awaiting_user_confirmation",
        "reason": "ChatGPT web smoke stops after TableBuildPlan preview. No spreadsheet write tool is called before explicit user confirmation.",
        "blocked_until_user_confirms": ["spreadsheet_create_formula_table_from_spec", "spreadsheet_rollback_created_artifact"],
    }
    package = _write_smoke_package(
        package_dir=package_dir,
        created_at=created_at,
        endpoint=endpoint,
        steps=step_results,
        tools_response=tools,
        resources_response=resources,
        resource_response=_resource_summary(resource),
        auth_status=auth_status,
        ui_result=ui_result,
        intent_result=intent_result,
        plan=plan,
        write_gate=write_gate,
        local_boundary=local_boundary,
    )
    return {
        "operation": "chatgpt_web_connector_smoke",
        "status": _smoke_status(step_results, plan, local_boundary),
        "endpoint": {"base_url": endpoint["base_url"], "mcp_url": endpoint["mcp_url"]},
        "package": package,
        "summary": {
            "tool_count": len(tools.get("result", {}).get("tools", []) or []),
            "resource_count": len(resources.get("result", {}).get("resources", []) or []),
            "intent_id": saved_intent.get("intent_id", ""),
            "write_gate_status": write_gate["status"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a ChatGPT web connector smoke against a Sheets Bridge remote MCP endpoint.")
    parser.add_argument("--endpoint-url", required=True, help="Remote MCP base URL or /mcp URL.")
    parser.add_argument("--session-id", default="", help="Optional remote session id sent as Authorization: Bearer <session-id>.")
    parser.add_argument("--package-root", default=str(DEFAULT_PACKAGE_ROOT))
    parser.add_argument("--source-preview", help="Optional JSON file containing a sanitized source_preview.")
    parser.add_argument("--output-canvas", help="Optional JSON file containing output_canvas rows.")
    parser.add_argument("--llm-prompt", default=DEFAULT_LLM_PROMPT)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--require-https", action="store_true", help="Require HTTPS even for localhost development.")
    args = parser.parse_args()
    result = run_chatgpt_web_smoke(
        endpoint_url=args.endpoint_url,
        session_id=args.session_id,
        package_root=args.package_root,
        source_preview=_read_optional_json_object(args.source_preview),
        output_canvas=_read_optional_json_array(args.output_canvas),
        llm_prompt=args.llm_prompt,
        timeout_seconds=args.timeout_seconds,
        allow_insecure_localhost=not args.require_https,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


def _normalize_endpoint(endpoint_url: str, *, allow_insecure_localhost: bool) -> dict[str, str]:
    parsed = urlparse(endpoint_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("endpoint_url must be an http(s) URL")
    is_local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (allow_insecure_localhost and is_local):
        raise ValueError("ChatGPT web connector endpoint must use HTTPS outside localhost development")
    base_url = endpoint_url[:-4] if endpoint_url.rstrip("/").endswith("/mcp") else endpoint_url.rstrip("/")
    return {
        "base_url": base_url,
        "mcp_url": urljoin(base_url + "/", "mcp"),
        "healthz_url": urljoin(base_url + "/", "healthz"),
        "https_ready": parsed.scheme == "https",
        "localhost_development": str(is_local).lower(),
    }


def _get_json(url: str, *, timeout_seconds: int) -> dict[str, Any]:
    with urlopen(url, timeout=timeout_seconds) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("HTTP response must be a JSON object")
    return data


def _post_mcp(url: str, payload: dict[str, Any], *, headers: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("MCP response must be a JSON object")
    return data


def _intent_from_ui_result(ui_result: dict[str, Any], output_canvas: list[list[Any]], llm_prompt: str) -> dict[str, Any]:
    app_source = ui_result.get("app_source") if isinstance(ui_result.get("app_source"), dict) else {}
    source = app_source.get("source") if isinstance(app_source.get("source"), dict) else {}
    package = app_source.get("package") if isinstance(app_source.get("package"), dict) else {}
    artifact_type = str(ui_result.get("artifact_type") or app_source.get("artifact_type") or source.get("artifact_type") or "google_sheets")
    return {
        "artifact_type": artifact_type,
        "source": source,
        "source_package": {
            "manifest_path": str(package.get("manifest_path") or ""),
            "source_path": str(package.get("source_path") or ""),
        },
        "output_canvas": output_canvas,
        "llm_prompt": llm_prompt,
        "source_hints": {"selected_ranges": [str(source.get("qualified_range") or ui_result.get("source_range") or "")]},
        "output": {
            "creation_mode": "copy" if artifact_type == "excel_workbook" else "sheet",
            "preferred_title": "CHATGPT_WEB_SMOKE_TABLE",
        },
    }


def _plan_from_intent(intent: dict[str, Any]) -> dict[str, Any]:
    output_canvas = intent.get("output_canvas") if isinstance(intent.get("output_canvas"), list) else []
    columns = [str(cell).strip() for cell in (output_canvas[0][1:] if output_canvas and isinstance(output_canvas[0], list) else []) if str(cell).strip()]
    rows = [
        str(row[0]).strip()
        for row in output_canvas[1:]
        if isinstance(row, list) and row and str(row[0]).strip()
    ]
    source = intent.get("source") if isinstance(intent.get("source"), dict) else {}
    output = intent.get("output") if isinstance(intent.get("output"), dict) else {}
    return {
        "schema_version": "1.0",
        "plan_kind": TABLE_BUILD_PLAN_KIND,
        "intent_ref": str((intent.get("source_package") if isinstance(intent.get("source_package"), dict) else {}).get("manifest_path") or intent.get("intent_id") or "submitted_intent"),
        "interpreted_output_shape": {
            "rows": rows,
            "columns": columns,
            "measure": "사용자 프롬프트에 설명된 집계값",
        },
        "source_evidence_needed": [
            {
                "range": str(source.get("qualified_range") or "source_preview"),
                "purpose": "사용자가 스케치한 결과표를 기존 데이터와 수식/참조만으로 구성할 수 있는지 확인",
            }
        ],
        "formula_strategy": {
            "summary": "원본 데이터를 AI가 직접 계산하지 않고, 새 시트의 수식과 원본 참조로 결과표를 채운다.",
            "risk_annotations": ["ChatGPT web smoke package does not execute write tools before user confirmation."],
        },
        "target": {
            "artifact_type": str(intent.get("artifact_type") or source.get("artifact_type") or "google_sheets"),
            "creation_mode": str(output.get("creation_mode") or "sheet"),
            "sheet_title": str(output.get("preferred_title") or "CHATGPT_WEB_SMOKE_TABLE"),
        },
        "validation_plan": {
            "readback": "After confirmation, read created sheet formulas and formatted values.",
            "credential_boundary": "Validation artifacts remain credential-free.",
        },
        "rollback_plan": {"kind": "delete_created_sheet"},
        "unresolved_questions": [],
    }


def _write_smoke_package(
    *,
    package_dir: Path,
    created_at: str,
    endpoint: dict[str, str],
    steps: list[dict[str, Any]],
    tools_response: dict[str, Any],
    resources_response: dict[str, Any],
    resource_response: dict[str, Any],
    auth_status: dict[str, Any],
    ui_result: dict[str, Any],
    intent_result: dict[str, Any],
    plan: dict[str, Any],
    write_gate: dict[str, Any],
    local_boundary: dict[str, Any],
) -> dict[str, str]:
    smoke_path = package_dir / "chatgpt-web-smoke.json"
    tools_path = package_dir / "tools.json"
    resources_path = package_dir / "resources.json"
    app_resource_path = package_dir / "table-builder-resource.json"
    auth_path = package_dir / "remote-auth-status.json"
    ui_path = package_dir / "table-builder-ui-result.json"
    intent_path = package_dir / "intent-save-result.json"
    plan_path = package_dir / "table-build-plan.json"
    gate_path = package_dir / "write-gate.json"
    boundary_path = package_dir / "local-runtime-boundary.json"
    html_path = package_dir / "index.html"
    manifest_path = package_dir / "manifest.json"
    handoff_path = package_dir / "mcp-handoff.json"

    smoke = {
        "schema_version": "1.0",
        "artifact_kind": "chatgpt_web_connector_smoke",
        "created_at": created_at,
        "endpoint": endpoint,
        "steps": steps,
        "summary": {
            "tool_count": len(tools_response.get("result", {}).get("tools", []) or []),
            "resource_count": len(resources_response.get("result", {}).get("resources", []) or []),
            "write_gate_status": write_gate["status"],
            "credential_boundary": {
                "access_token_returned": False,
                "refresh_token_returned": False,
                "raw_credentials_returned": False,
            },
        },
    }
    artifacts = [
        ("chatgpt_web_smoke", smoke_path, smoke),
        ("tools", tools_path, tools_response),
        ("resources", resources_path, resources_response),
        ("table_builder_resource", app_resource_path, resource_response),
        ("remote_auth_status", auth_path, auth_status),
        ("table_builder_ui_result", ui_path, ui_result),
        ("intent_save_result", intent_path, intent_result),
        ("table_build_plan", plan_path, plan),
        ("write_gate", gate_path, write_gate),
        ("local_runtime_boundary", boundary_path, local_boundary),
    ]
    for _kind, path, payload in artifacts:
        _write_json(path, payload)
    html_path.write_text(_smoke_html(smoke, plan, write_gate, local_boundary), encoding="utf-8")
    handoff = {
        "schema_version": "1.0",
        "artifact_kind": "chatgpt_web_smoke_handoff",
        "created_at": created_at,
        "manifest_path": str(manifest_path.resolve()),
        "mcp_prompt": f"이 ChatGPT web Sheets Bridge smoke 패키지를 검토해줘: {manifest_path.resolve()}",
        "analysis_boundary": [
            "Read manifest.json first.",
            "Use only sanitized artifacts referenced by the manifest.",
            "Use only credential-free MCP outputs and review artifacts.",
        ],
    }
    manifest = {
        "schema_version": "1.0",
        "artifact_kind": "chatgpt_web_connector_smoke_package",
        "created_at": created_at,
        "source": "remote_mcp_chatgpt_web_smoke",
        "artifacts": [
            {"kind": kind, "path": str(path.resolve())}
            for kind, path, _payload in artifacts
        ] + [
            {"kind": "html_review", "path": str(html_path.resolve())},
            {"kind": "mcp_handoff", "path": str(handoff_path.resolve())},
        ],
    }
    _write_json(handoff_path, handoff)
    _write_json(manifest_path, manifest)
    return {
        "package_dir": str(package_dir.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "html_path": str(html_path.resolve()),
        "smoke_path": str(smoke_path.resolve()),
        "plan_path": str(plan_path.resolve()),
        "mcp_handoff_path": str(handoff_path.resolve()),
    }


def _smoke_html(smoke: dict[str, Any], plan: dict[str, Any], write_gate: dict[str, Any], local_boundary: dict[str, Any]) -> str:
    steps = "".join(
        f"<tr><td>{escape(step['name'])}</td><td>{escape(step['status'])}</td></tr>"
        for step in smoke["steps"]
    )
    local_status = _structured(local_boundary).get("status", "")
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>ChatGPT Web Sheets Bridge Smoke</title>
  <style>
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:32px;background:#f7f8fb;color:#172033}}
    main{{max-width:960px;margin:auto;background:#fff;border:1px solid #d8e1ea;border-radius:8px;padding:24px}}
    h1{{margin-top:0;font-size:24px}} table{{width:100%;border-collapse:collapse;margin-top:12px}}
    th,td{{border-bottom:1px solid #e5ebf2;padding:9px;text-align:left}} th{{background:#eef3f8}}
    code{{background:#eef3f8;padding:2px 5px;border-radius:5px}}
  </style>
</head>
<body><main>
  <h1>ChatGPT Web Sheets Bridge Smoke</h1>
  <p>Status: <strong>{escape(smoke['summary']['write_gate_status'])}</strong></p>
  <table><thead><tr><th>Step</th><th>Status</th></tr></thead><tbody>{steps}</tbody></table>
  <h2>Plan Preview</h2>
  <p>Target: <code>{escape(plan['target']['artifact_type'])}</code> / <code>{escape(plan['target']['creation_mode'])}</code></p>
  <p>{escape(plan['formula_strategy']['summary'])}</p>
  <h2>Write Gate</h2>
  <p>{escape(write_gate['reason'])}</p>
  <h2>Local Runtime Boundary</h2>
  <p>Status: <code>{escape(str(local_status))}</code></p>
</main></body></html>
"""


def _step(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    status = "passed"
    if payload.get("error") or payload.get("result", {}).get("isError") is True:
        status = "failed"
    return {"name": name, "status": status, "response_keys": sorted(payload.keys())}


def _resource_summary(response: dict[str, Any]) -> dict[str, Any]:
    contents = response.get("result", {}).get("contents", []) if isinstance(response.get("result"), dict) else []
    summarized = []
    for item in contents:
        text = str(item.get("text") or "") if isinstance(item, dict) else ""
        summarized.append({
            "uri": item.get("uri", "") if isinstance(item, dict) else "",
            "mimeType": item.get("mimeType", "") if isinstance(item, dict) else "",
            "text_length": len(text),
            "contains_host_adapter": "SheetsBridgeHostAdapters" in text,
        })
    return {"jsonrpc": response.get("jsonrpc", "2.0"), "id": response.get("id"), "result": {"contents": summarized}}


def _tool_summary(response: dict[str, Any]) -> dict[str, Any]:
    structured = _structured(response)
    return {
        "jsonrpc": response.get("jsonrpc", "2.0"),
        "id": response.get("id"),
        "result": {
            "isError": response.get("result", {}).get("isError", False) if isinstance(response.get("result"), dict) else False,
            "structuredContent": structured,
        },
    }


def _structured(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    structured = result.get("structuredContent") if isinstance(result.get("structuredContent"), dict) else {}
    return structured


def _smoke_status(steps: list[dict[str, Any]], plan: dict[str, Any], local_boundary: dict[str, Any]) -> str:
    if any(step["status"] != "passed" for step in steps):
        return "failed"
    if plan.get("plan_kind") != TABLE_BUILD_PLAN_KIND:
        return "failed"
    if _structured(local_boundary).get("status") != "local_runtime_required":
        return "failed"
    return "passed"


def _unique_package_dir(package_root: Path | str, created_at: str, request_id: str) -> Path:
    root = Path(package_root)
    base = root / created_at[:10] / _safe_id(request_id)
    candidate = base
    index = 2
    while candidate.exists():
        candidate = Path(f"{base}-{index}")
        index += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def _safe_id(value: object) -> str:
    raw = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(value))
    return raw[:120] or "chatgpt-web-smoke"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_optional_json_object(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _read_optional_json_array(path: str | None) -> list[list[Any]] | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"{path} must contain a JSON array")
    return value


if __name__ == "__main__":
    main()
