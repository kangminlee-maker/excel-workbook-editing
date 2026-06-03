from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openpyxl.utils import range_boundaries

from google_sheets_live_manifest import classify_formula, render_live_manifest_html


SCHEMA_VERSION = "0.1"
CELL_RE = re.compile(r"^([A-Z]{1,3})([0-9]+)$")
CELL_REF_RE = re.compile(
    r"(?:(?P<sheet>'(?:[^']|'')+'|[A-Za-z_가-힣][A-Za-z0-9_가-힣 .&()-]*)!)?"
    r"(?P<start>\$?[A-Z]{1,3}\$?\d+)"
    r"(?::(?P<end>\$?[A-Z]{1,3}\$?\d+))?"
)
IMPORTRANGE_RE = re.compile(
    r"IMPORTRANGE\s*\(\s*(?P<source>\"[^\"]+\"|'[^']+'|[^,]+)\s*,\s*"
    r"(?P<range>\"[^\"]+\"|'[^']+')",
    re.IGNORECASE,
)


def build_live_view_formula_profile(
    *,
    live_manifest_path: Path,
    top_left_sample_path: Path,
    parser_window_smoke_path: Path | None = None,
    sample_limit: int = 80,
) -> dict[str, Any]:
    live_manifest_path = live_manifest_path.expanduser().resolve()
    top_left_sample_path = top_left_sample_path.expanduser().resolve()
    parser_window_smoke_path = (
        parser_window_smoke_path.expanduser().resolve()
        if parser_window_smoke_path
        else None
    )
    manifest = _read_json(live_manifest_path)
    top_left_sample = _read_json(top_left_sample_path)
    parser_window_smoke = (
        _read_json(parser_window_smoke_path)
        if parser_window_smoke_path and parser_window_smoke_path.exists()
        else None
    )
    sheet_index = {
        sheet["name"]: sheet
        for sheet in manifest["workbook"]["sheets"]
    }
    formula_observations = _formula_observations(top_left_sample, sheet_index)
    signature_groups = _signature_groups(formula_observations, sample_limit=sample_limit)
    dependency_edges = _dependency_edges(formula_observations, sheet_index, sample_limit=sample_limit)
    external_dependencies = _external_dependencies(formula_observations)
    view_state_surfaces = _view_state_surfaces(manifest)
    permission_requirements = _permission_requirements(formula_observations, parser_window_smoke)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source": {
            "spreadsheet_id": manifest["source"]["spreadsheet_id"],
            "spreadsheet_url": manifest["source"].get("spreadsheet_url"),
            "title": manifest["source"]["title"],
            "source_artifacts": {
                "live_manifest": str(live_manifest_path),
                "top_left_sample": str(top_left_sample_path),
                **(
                    {"parser_window_smoke": str(parser_window_smoke_path)}
                    if parser_window_smoke_path
                    else {}
                ),
            },
        },
        "authority": {
            "source_document": "live_google_sheet",
            "input_authority": "existing_live_manifest_and_top_left_sample_artifacts",
            "new_live_read_performed": False,
            "profile_window": manifest["limits"]["profile_range"],
            "formula_text_authority": "formula_text_only",
            "formula_result_authority": "not_established",
            "expanded_range_authority": _expanded_range_authority(parser_window_smoke),
        },
        "view_state_surfaces": view_state_surfaces,
        "formula_observations": formula_observations,
        "signature_groups": signature_groups,
        "dependency_edges": dependency_edges,
        "external_dependencies": external_dependencies,
        "permission_requirements": permission_requirements,
        "summary": _summary(
            manifest,
            view_state_surfaces,
            formula_observations,
            signature_groups,
            dependency_edges,
            external_dependencies,
            permission_requirements,
            parser_window_smoke,
        ),
        "parser_observations": _parser_observations(
            manifest,
            view_state_surfaces,
            formula_observations,
            dependency_edges,
            external_dependencies,
            permission_requirements,
            parser_window_smoke,
        ),
    }


def write_live_view_formula_profile_package(
    *,
    out_dir: Path,
    access_preflight_path: Path,
    live_manifest_path: Path,
    top_left_sample_path: Path,
    profile: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    profile_path = out_dir / "live-view-formula-profile.json"
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    access_preflight = _read_json(access_preflight_path)
    manifest = _read_json(live_manifest_path)
    (out_dir / "index.html").write_text(
        render_live_manifest_html(
            access_preflight=access_preflight,
            manifest=manifest,
            live_view_formula_profile=profile,
        ),
        encoding="utf-8",
    )


def _view_state_surfaces(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    for sheet in manifest["workbook"]["sheets"]:
        counts = sheet["view_state_counts"]
        hidden_or_filtered = (
            sheet["state"] == "hidden"
            or counts.get("hidden_rows_in_profile_window", 0) > 0
            or counts.get("filtered_rows_in_profile_window", 0) > 0
            or counts.get("hidden_columns_in_profile_window", 0) > 0
        )
        surfaces.append(
            {
                "id": f"view_state_{sheet['sheet_id']}",
                "sheet": sheet["name"],
                "sheet_id": sheet["sheet_id"],
                "index": sheet["index"],
                "state": sheet["state"],
                "dimensions": sheet["dimensions"],
                "profile_window": sheet["profile_window"],
                "view_state_counts": counts,
                "object_counts": sheet["object_counts"],
                "style_counts": sheet["style_counts"],
                "risk_flags": sheet["risk_flags"],
                "semantic_effect": (
                    "structural_data_may_be_hidden_from_human_view"
                    if hidden_or_filtered
                    else "visible_profile_window"
                ),
                "diagnostic_status": (
                    "requires_view_state_aware_parsing"
                    if hidden_or_filtered
                    else "no_profile_window_view_state_risk"
                ),
            }
        )
    return surfaces


def _formula_observations(
    top_left_sample: dict[str, Any],
    sheet_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    observations = []
    for item in top_left_sample.get("formula_samples", []):
        sheet = item.get("sheet_title", "")
        cell = item.get("cell", "")
        formula = item.get("formula", "")
        row, column = _cell_position(cell)
        classifications = item.get("classifications") or classify_formula(formula)
        refs = _formula_references(
            formula=formula,
            current_sheet=sheet,
            known_sheet_names=set(sheet_index),
        )
        observations.append(
            {
                "id": f"formula_{_slug(sheet)}_{cell}",
                "sheet": sheet,
                "sheet_id": item.get("sheet_id"),
                "cell": cell,
                "row": row,
                "column": column,
                "formula": formula,
                "signature": _formula_signature(formula, row, column),
                "classifications": classifications,
                "references": refs,
                "authority": "formula_text_only",
                "result_status": "not_recalculated",
            }
        )
    return observations


def _formula_references(
    *,
    formula: str,
    current_sheet: str,
    known_sheet_names: set[str],
) -> list[dict[str, Any]]:
    references = []
    seen = set()
    stripped_formula = _strip_string_literals(formula)
    for match in CELL_REF_RE.finditer(stripped_formula):
        sheet = _clean_sheet_name(match.group("sheet")) or current_sheet
        start = _clean_cell_ref(match.group("start"))
        end = _clean_cell_ref(match.group("end") or match.group("start"))
        key = (sheet, start, end)
        if key in seen:
            continue
        seen.add(key)
        references.append(
            {
                "kind": (
                    "cross_sheet_range"
                    if sheet != current_sheet
                    else "same_sheet_range"
                ),
                "target_sheet": sheet,
                "target_range": f"{start}:{end}" if start != end else start,
                "target_sheet_status": (
                    "known_sheet" if sheet in known_sheet_names else "unresolved_sheet"
                ),
            }
        )

    for match in IMPORTRANGE_RE.finditer(formula):
        source_arg = _unquote(match.group("source").strip())
        range_arg = _unquote(match.group("range").strip())
        references.append(
            {
                "kind": "external_importrange",
                "source_argument": source_arg,
                "range_argument": range_arg,
                "source_resolution_status": (
                    "literal_source_available"
                    if source_arg.startswith("http") or len(source_arg) > 20
                    else "source_argument_requires_value_lookup"
                ),
            }
        )
    return references


def _signature_groups(
    formulas: list[dict[str, Any]],
    *,
    sample_limit: int,
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for item in formulas:
        group_id = hashlib.sha1(item["signature"].encode("utf-8")).hexdigest()[:12]
        group = groups.setdefault(
            item["signature"],
            {
                "id": f"signature_{group_id}",
                "signature": item["signature"],
                "formula_count": 0,
                "source_sheets": [],
                "sample_cells": [],
                "formula_examples": [],
                "reference_sheets": [],
                "classifications": [],
                "structure_hint": "single_formula_sample",
            },
        )
        group["formula_count"] += 1
        _append_unique(group["source_sheets"], item["sheet"], sample_limit)
        _append_unique(group["sample_cells"], f"{item['sheet']}!{item['cell']}", sample_limit)
        _append_unique(group["formula_examples"], item["formula"], 3)
        for classification in item["classifications"]:
            _append_unique(group["classifications"], classification, sample_limit)
        for ref in item["references"]:
            target_sheet = ref.get("target_sheet")
            if target_sheet:
                _append_unique(group["reference_sheets"], target_sheet, sample_limit)

    for group in groups.values():
        if group["formula_count"] >= 3 and len(group["source_sheets"]) >= 2:
            group["structure_hint"] = "repeated_cross_sheet_formula_family"
        elif group["formula_count"] >= 3:
            group["structure_hint"] = "repeated_formula_family"
        elif group["reference_sheets"]:
            group["structure_hint"] = "dependency_formula_sample"
    return sorted(groups.values(), key=lambda item: (-item["formula_count"], item["id"]))


def _dependency_edges(
    formulas: list[dict[str, Any]],
    sheet_index: dict[str, dict[str, Any]],
    *,
    sample_limit: int,
) -> list[dict[str, Any]]:
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in formulas:
        for ref in item["references"]:
            if ref["kind"] == "external_importrange":
                target_key = "external_importrange"
                target_sheet = None
            else:
                target_sheet = ref.get("target_sheet")
                target_key = target_sheet or "unresolved_sheet"
            key = (item["sheet"], ref["kind"], target_key)
            edge = edges.setdefault(
                key,
                {
                    "id": f"edge_{_slug(item['sheet'])}_{_slug(ref['kind'])}_{_slug(target_key)}",
                    "source_sheet": item["sheet"],
                    "source_sheet_id": item.get("sheet_id"),
                    "target_kind": ref["kind"],
                    "target_sheet": target_sheet,
                    "target_sheet_id": (
                        sheet_index.get(target_sheet, {}).get("sheet_id")
                        if target_sheet
                        else None
                    ),
                    "target_status": _target_status(ref, sheet_index),
                    "formula_count": 0,
                    "sample_formula_cells": [],
                    "sample_target_ranges": [],
                    "classifications": [],
                    "authority": "formula_text_dependency_candidate",
                },
            )
            edge["formula_count"] += 1
            _append_unique(edge["sample_formula_cells"], item["cell"], sample_limit)
            target_range = ref.get("target_range") or ref.get("range_argument")
            if target_range:
                _append_unique(edge["sample_target_ranges"], target_range, sample_limit)
            for classification in item["classifications"]:
                _append_unique(edge["classifications"], classification, sample_limit)
    return sorted(edges.values(), key=lambda item: (-item["formula_count"], item["id"]))


def _external_dependencies(formulas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dependencies = []
    for item in formulas:
        for ref in item["references"]:
            if ref["kind"] != "external_importrange":
                continue
            dependencies.append(
                {
                    "id": f"external_dep_{_slug(item['sheet'])}_{item['cell']}",
                    "formula_sheet": item["sheet"],
                    "formula_cell": item["cell"],
                    "source_argument": ref["source_argument"],
                    "range_argument": ref["range_argument"],
                    "source_resolution_status": ref["source_resolution_status"],
                    "state": "stale_unverified",
                    "required_evidence": [
                        "source argument value lookup",
                        "source spreadsheet Google ACL check",
                        "broker source spreadsheet allowlist",
                    ],
                }
            )
    return dependencies


def _permission_requirements(
    formulas: list[dict[str, Any]],
    parser_window_smoke: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    window_status = (
        "verified_for_current_policy_limits"
        if _parser_window_ops_verified(parser_window_smoke)
        else "required_for_next_live_read"
    )
    window_reason = (
        "Broker smoke passed for bounded grid/value/formula parser windows; later reads must stay within policy limits."
        if _parser_window_ops_verified(parser_window_smoke)
        else "Current profile is limited to existing A1:Z80 artifacts; deeper block and pipeline parsing needs range-scoped broker reads."
    )
    requirements = [
        {
            "capability": "bounded_grid_formula_value_windows",
            "status": window_status,
            "required_broker_operations": [
                "inspect.grid_window",
                "inspect.values_window",
                "inspect.formula_window",
            ],
            "reason": window_reason,
        }
    ]
    if any(
        ref["kind"] == "external_importrange"
        for item in formulas
        for ref in item["references"]
    ):
        requirements.append(
            {
                "capability": "source_spreadsheet_allowlist",
                "status": "required_after_source_ids_are_resolved",
                "required_broker_operations": ["inspect.metadata", "inspect.grid_window"],
                "reason": "IMPORTRANGE source spreadsheets must be authorized separately by Google ACL and broker policy.",
            }
        )
    return requirements


def _summary(
    manifest: dict[str, Any],
    view_state_surfaces: list[dict[str, Any]],
    formulas: list[dict[str, Any]],
    signature_groups: list[dict[str, Any]],
    dependency_edges: list[dict[str, Any]],
    external_dependencies: list[dict[str, Any]],
    permission_requirements: list[dict[str, Any]],
    parser_window_smoke: dict[str, Any] | None,
) -> dict[str, int | str]:
    return {
        "sheet_count": manifest["workbook"]["sheet_count"],
        "view_state_surface_count": len(view_state_surfaces),
        "hidden_sheet_count": sum(1 for item in view_state_surfaces if item["state"] == "hidden"),
        "view_state_risk_surface_count": sum(
            1 for item in view_state_surfaces
            if item["diagnostic_status"] == "requires_view_state_aware_parsing"
        ),
        "formula_observation_count": len(formulas),
        "signature_group_count": len(signature_groups),
        "repeated_signature_group_count": sum(
            1 for item in signature_groups if item["formula_count"] >= 3
        ),
        "dependency_edge_count": len(dependency_edges),
        "cross_sheet_dependency_edge_count": sum(
            1 for item in dependency_edges if item["target_kind"] == "cross_sheet_range"
        ),
        "external_dependency_count": len(external_dependencies),
        "permission_requirement_count": len(permission_requirements),
        "broker_window_contract_status": (
            "verified_for_current_policy_limits"
            if _parser_window_ops_verified(parser_window_smoke)
            else "not_verified"
        ),
        "profile_status": "profiled_from_existing_artifacts_no_new_live_read",
    }


def _parser_observations(
    manifest: dict[str, Any],
    view_state_surfaces: list[dict[str, Any]],
    formulas: list[dict[str, Any]],
    dependency_edges: list[dict[str, Any]],
    external_dependencies: list[dict[str, Any]],
    permission_requirements: list[dict[str, Any]],
    parser_window_smoke: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    observations = [
        {
            "level": "info",
            "message": (
                "Live view/formula profile was built from existing live-manifest and "
                "top-left sample artifacts; no new Google Sheets read was performed."
            ),
            "evidence_refs": ["live-manifest.json", "top-left-sample.json"],
        },
    ]
    if _parser_window_ops_verified(parser_window_smoke):
        observations.append(
            {
                "level": "info",
                "message": (
                    "Broker-backed bounded grid/value/formula window operations are verified "
                    "for the current policy limits; expanded reads must remain within those limits."
                ),
                "evidence_refs": ["parser-window-permission-smoke.json"],
            }
        )
    else:
        observations.append(
            {
                "level": "warning",
                "message": (
                    f"Profile authority is limited to {manifest['limits']['profile_range']} windows; "
                    "expanded block parsing needs broker-backed bounded grid/formula/value reads."
                ),
                "evidence_refs": ["docs/google-sheets-parser-permission-requirements.md"],
            }
        )
    view_risks = [
        item for item in view_state_surfaces
        if item["diagnostic_status"] == "requires_view_state_aware_parsing"
    ]
    if view_risks:
        observations.append(
            {
                "level": "warning",
                "message": (
                    f"{len(view_risks)} sheet surfaces have hidden or filtered view-state "
                    "evidence and must preserve visible-state vs structural-data distinction."
                ),
                "evidence_refs": [item["id"] for item in view_risks[:8]],
            }
        )
    if dependency_edges:
        observations.append(
            {
                "level": "info",
                "message": (
                    f"{len(dependency_edges)} formula dependency edge candidates were derived "
                    "from formula text. They are not formula-result authority."
                ),
                "evidence_refs": [item["id"] for item in dependency_edges[:8]],
            }
        )
    if external_dependencies:
        observations.append(
            {
                "level": "warning",
                "message": (
                    f"{len(external_dependencies)} IMPORTRANGE dependency requires source "
                    "argument resolution, Google ACL confirmation, and broker allowlist review."
                ),
                "evidence_refs": [item["id"] for item in external_dependencies[:8]],
            }
        )
    if permission_requirements:
        observations.append(
            {
                "level": "warning",
                "message": "Missing broker contract items remain explicit stop conditions for deeper live reads.",
                "evidence_refs": [item["capability"] for item in permission_requirements],
            }
        )
    if not formulas:
        observations.append(
            {
                "level": "info",
                "message": "No formula samples were present in the current profile windows.",
                "evidence_refs": ["top-left-sample.json"],
            }
        )
    return observations


def _formula_signature(formula: str, row: int | None, column: int | None) -> str:
    if row is None or column is None:
        return _strip_string_literals(formula.upper())
    expression = formula[1:] if formula.startswith("=") else formula
    expression = _strip_string_literals(expression.upper())
    return CELL_REF_RE.sub(
        lambda match: _relative_reference(match, row, column),
        expression,
    )


def _expanded_range_authority(parser_window_smoke: dict[str, Any] | None) -> str:
    if _parser_window_ops_verified(parser_window_smoke):
        return "broker_bounded_window_contract_verified"
    return "requires_broker_grid_window_contract"


def _parser_window_ops_verified(parser_window_smoke: dict[str, Any] | None) -> bool:
    if not parser_window_smoke:
        return False
    required = {
        "inspect.grid_window",
        "inspect.values_window",
        "inspect.formula_window",
    }
    passed = {
        item.get("operation")
        for item in parser_window_smoke.get("smoke_results", [])
        if item.get("result") == "passed"
    }
    return required <= passed


def _relative_reference(match: re.Match[str], row: int, column: int) -> str:
    sheet_prefix = f"{match.group('sheet')}!" if match.group("sheet") else ""
    start = _clean_cell_ref(match.group("start"))
    end = _clean_cell_ref(match.group("end") or match.group("start"))
    start_token = _relative_cell_token(start, row, column)
    if start == end:
        return f"{sheet_prefix}{start_token}"
    return f"{sheet_prefix}{start_token}:{_relative_cell_token(end, row, column)}"


def _relative_cell_token(cell: str, anchor_row: int, anchor_column: int) -> str:
    match = CELL_RE.match(cell)
    if not match:
        return cell
    column_letters, row_text = match.groups()
    target_column = range_boundaries(f"{cell}:{cell}")[0]
    target_row = int(row_text)
    return f"R[{target_row - anchor_row}]C[{target_column - anchor_column}]"


def _cell_position(cell: str) -> tuple[int | None, int | None]:
    match = CELL_RE.match(cell)
    if not match:
        return None, None
    column_letters, row_text = match.groups()
    column = range_boundaries(f"{column_letters}{row_text}:{column_letters}{row_text}")[0]
    return int(row_text), column


def _target_status(ref: dict[str, Any], sheet_index: dict[str, dict[str, Any]]) -> str:
    if ref["kind"] == "external_importrange":
        return "external_source_unresolved"
    target_sheet = ref.get("target_sheet")
    if target_sheet in sheet_index:
        return "known_sheet"
    return "unresolved_sheet"


def _strip_string_literals(value: str) -> str:
    return re.sub(r'("[^"]*"|\'[^\']*\')', "STR", value)


def _clean_sheet_name(value: str | None) -> str | None:
    if not value:
        return None
    value = value.rstrip("!")
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def _clean_cell_ref(value: str) -> str:
    return value.replace("$", "")


def _unquote(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _append_unique(values: list[Any], value: Any, limit: int) -> None:
    if value is None or value in values or len(values) >= limit:
        return
    values.append(value)


def _slug(value: Any) -> str:
    text = str(value or "none")
    text = re.sub(r"[^A-Za-z0-9가-힣]+", "_", text).strip("_").lower()
    return text or "none"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def render_live_view_formula_profile_section(profile: dict[str, Any]) -> str:
    metrics = "".join(
        f'<div class="metric"><div class="label">{_esc(key)}</div>'
        f'<div class="value">{_esc(value)}</div></div>'
        for key, value in profile["summary"].items()
    )
    risk_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['sheet'])}</td>"
        f"<td>{_esc(item['state'])}</td>"
        f"<td>{_esc(item['diagnostic_status'])}</td>"
        f"<td>{_esc(item['view_state_counts'])}</td>"
        f"<td>{_esc(item['object_counts'])}</td>"
        "</tr>"
        for item in profile["view_state_surfaces"]
        if item["diagnostic_status"] == "requires_view_state_aware_parsing"
    )
    if not risk_rows:
        risk_rows = '<tr><td colspan="5">No view-state risks in current profile windows.</td></tr>'
    signature_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['id'])}</td>"
        f"<td>{_esc(item['formula_count'])}</td>"
        f"<td>{_esc(item['structure_hint'])}</td>"
        f"<td>{_esc(', '.join(item['source_sheets'][:8]))}</td>"
        f"<td><code>{_esc(item['signature'])}</code></td>"
        "</tr>"
        for item in profile["signature_groups"][:30]
    )
    if not signature_rows:
        signature_rows = '<tr><td colspan="5">No formula signature groups.</td></tr>'
    edge_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['source_sheet'])}</td>"
        f"<td>{_esc(item['target_kind'])}</td>"
        f"<td>{_esc(item.get('target_sheet') or 'external')}</td>"
        f"<td>{_esc(item['target_status'])}</td>"
        f"<td>{_esc(item['formula_count'])}</td>"
        f"<td>{_esc(', '.join(item['sample_formula_cells'][:8]))}</td>"
        "</tr>"
        for item in profile["dependency_edges"][:40]
    )
    if not edge_rows:
        edge_rows = '<tr><td colspan="6">No dependency edge candidates.</td></tr>'
    external_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['formula_sheet'])}!{_esc(item['formula_cell'])}</td>"
        f"<td><code>{_esc(item['source_argument'])}</code></td>"
        f"<td><code>{_esc(item['range_argument'])}</code></td>"
        f"<td>{_esc(item['source_resolution_status'])}</td>"
        f"<td>{_esc(item['state'])}</td>"
        "</tr>"
        for item in profile["external_dependencies"]
    )
    if not external_rows:
        external_rows = '<tr><td colspan="5">No IMPORTRANGE dependencies in current profile windows.</td></tr>'
    requirement_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['capability'])}</td>"
        f"<td>{_esc(item['status'])}</td>"
        f"<td>{_esc(', '.join(item['required_broker_operations']))}</td>"
        f"<td>{_esc(item['reason'])}</td>"
        "</tr>"
        for item in profile["permission_requirements"]
    )
    observation_rows = "".join(
        "<tr>"
        f"<td>{_esc(item['level'])}</td>"
        f"<td>{_esc(item['message'])}</td>"
        f"<td>{_esc(', '.join(item.get('evidence_refs', [])))}</td>"
        "</tr>"
        for item in profile["parser_observations"]
    )
    return f"""
  <h2>Live View-State / Formula Dependency Profile</h2>
  <section class="grid">{metrics}</section>
  <h2>View-State Risk Surfaces</h2>
  <section class="panel"><table><thead><tr><th>Sheet</th><th>State</th><th>Status</th><th>View Counts</th><th>Objects</th></tr></thead><tbody>{risk_rows}</tbody></table></section>
  <h2>Formula Signature Groups</h2>
  <section class="panel"><table><thead><tr><th>ID</th><th>Formulas</th><th>Hint</th><th>Sheets</th><th>Signature</th></tr></thead><tbody>{signature_rows}</tbody></table></section>
  <h2>Formula Dependency Edges</h2>
  <section class="panel"><table><thead><tr><th>Source</th><th>Target Kind</th><th>Target</th><th>Status</th><th>Formulas</th><th>Cells</th></tr></thead><tbody>{edge_rows}</tbody></table></section>
  <h2>External Dependencies</h2>
  <section class="panel"><table><thead><tr><th>Formula Cell</th><th>Source Arg</th><th>Range Arg</th><th>Resolution</th><th>State</th></tr></thead><tbody>{external_rows}</tbody></table></section>
  <h2>Next Permission Requirements</h2>
  <section class="panel"><table><thead><tr><th>Capability</th><th>Status</th><th>Broker Ops</th><th>Reason</th></tr></thead><tbody>{requirement_rows}</tbody></table></section>
  <h2>Stage Observations</h2>
  <section class="panel"><table><thead><tr><th>Level</th><th>Message</th><th>Evidence</th></tr></thead><tbody>{observation_rows}</tbody></table></section>
"""


def _esc(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a Google Sheets live view-state/formula dependency profile from existing artifacts."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--access-preflight", type=Path, required=True)
    parser.add_argument("--live-manifest", type=Path, required=True)
    parser.add_argument("--top-left-sample", type=Path, required=True)
    parser.add_argument("--parser-window-smoke", type=Path)
    parser.add_argument("--sample-limit", type=int, default=80)
    args = parser.parse_args()

    profile = build_live_view_formula_profile(
        live_manifest_path=args.live_manifest,
        top_left_sample_path=args.top_left_sample,
        parser_window_smoke_path=args.parser_window_smoke,
        sample_limit=args.sample_limit,
    )
    write_live_view_formula_profile_package(
        out_dir=args.out_dir,
        access_preflight_path=args.access_preflight,
        live_manifest_path=args.live_manifest,
        top_left_sample_path=args.top_left_sample,
        profile=profile,
    )


if __name__ == "__main__":
    main()
