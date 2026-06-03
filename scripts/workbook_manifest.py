from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from openpyxl.utils import get_column_letter, range_boundaries

SCHEMA_VERSION = "0.1"

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
DRAWING_NS = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
REL_ATTR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
REL_EMBED_ATTR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def build_workbook_manifest(
    workbook_path: Path,
    *,
    sample_limit: int = 20,
    max_sheet_xml_bytes: int = 50_000_000,
    max_shared_strings: int = 200_000,
) -> dict[str, Any]:
    workbook_path = workbook_path.expanduser().resolve()
    if not workbook_path.exists():
        raise FileNotFoundError(f"missing workbook: {workbook_path}")

    with ZipFile(workbook_path) as zf:
        shared_strings = _shared_strings(zf, max_shared_strings=max_shared_strings)
        workbook_rels = _relationships(zf, "xl/_rels/workbook.xml.rels")
        pivot_caches = _pivot_caches(zf, workbook_rels)
        external_links = _external_links(zf)
        sheets = _workbook_sheets(zf, workbook_rels)
        sheet_manifests = [
            _worksheet_manifest(
                zf,
                sheet,
                pivot_caches=pivot_caches,
                shared_strings=shared_strings["items"],
                sample_limit=sample_limit,
                max_sheet_xml_bytes=max_sheet_xml_bytes,
            )
            for sheet in sheets
        ]
        package_entries = _package_entries(zf)
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _utc_now(),
            "source": {
                "path": str(workbook_path),
                "file_name": workbook_path.name,
                "size_bytes": workbook_path.stat().st_size,
                "sha256": _sha256(workbook_path),
            },
            "limits": {
                "sample_limit": sample_limit,
                "max_sheet_xml_bytes": max_sheet_xml_bytes,
                "max_shared_strings": max_shared_strings,
            },
            "shared_strings": {
                "available": shared_strings["available"],
                "loaded_count": shared_strings["loaded_count"],
                "truncated": shared_strings["truncated"],
            },
            "package_entries": package_entries,
            "workbook": {
                "sheet_count": len(sheets),
                "pivot_caches": list(pivot_caches.values()),
                "external_links": external_links,
                "sheets": sheet_manifests,
            },
            "summary": _summary(sheet_manifests, package_entries),
            "parser_observations": _parser_observations(
                sheet_manifests,
                external_links,
            ),
        }


def _workbook_sheets(
    zf: ZipFile,
    workbook_rels: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    root = ET.fromstring(zf.read("xl/workbook.xml"))
    sheets: list[dict[str, Any]] = []
    for index, sheet in enumerate(root.findall(f".//{MAIN_NS}sheet")):
        relationship_id = sheet.attrib.get(REL_ATTR)
        rel = workbook_rels.get(relationship_id or "", {})
        entry = _normalize_xl_target(rel.get("target", ""))
        sheets.append(
            {
                "name": sheet.attrib.get("name", ""),
                "index": index,
                "sheet_id": sheet.attrib.get("sheetId", ""),
                "state": sheet.attrib.get("state", "visible"),
                "relationship_id": relationship_id,
                "entry": entry,
            }
        )
    return sheets


def _worksheet_manifest(
    zf: ZipFile,
    sheet: dict[str, Any],
    *,
    pivot_caches: dict[str, dict[str, Any]],
    shared_strings: list[str],
    sample_limit: int,
    max_sheet_xml_bytes: int,
) -> dict[str, Any]:
    entry = sheet["entry"]
    base = {
        "name": sheet["name"],
        "index": sheet["index"],
        "sheet_id": sheet["sheet_id"],
        "state": sheet["state"],
        "relationship_id": sheet["relationship_id"],
        "entry": entry,
    }
    if not entry or entry not in zf.namelist():
        return {
            **base,
            "detail_status": "missing_entry",
            "entry_size_bytes": 0,
            "compressed_size_bytes": 0,
            "dimension": None,
            "dimension_bounds": None,
            "counts": _empty_counts(),
            "samples": _empty_samples(),
            "relationships": [],
            "pivot_tables": [],
            "drawing_objects": [],
        }

    info = zf.getinfo(entry)
    if info.file_size > max_sheet_xml_bytes:
        dimension = _dimension_from_head(zf, entry)
        relationships = _worksheet_relationships(zf, entry)
        return {
            **base,
            "detail_status": "skipped_large_xml",
            "entry_size_bytes": info.file_size,
            "compressed_size_bytes": info.compress_size,
            "dimension": dimension,
            "dimension_bounds": _dimension_bounds(dimension),
            "counts": _empty_counts(),
            "samples": _empty_samples(),
            "relationships": relationships,
            "pivot_tables": _pivot_tables_for_sheet(zf, relationships, pivot_caches),
            "drawing_objects": _drawing_objects_for_sheet(zf, entry, relationships),
        }

    details = _scan_worksheet_xml(
        zf,
        entry,
        sample_limit=sample_limit,
        shared_strings=shared_strings,
    )
    relationships = _worksheet_relationships(zf, entry)
    return {
        **base,
        "detail_status": "scanned",
        "entry_size_bytes": info.file_size,
        "compressed_size_bytes": info.compress_size,
        **details,
        "relationships": relationships,
        "pivot_tables": _pivot_tables_for_sheet(zf, relationships, pivot_caches),
        "drawing_objects": _drawing_objects_for_sheet(zf, entry, relationships),
    }


def _scan_worksheet_xml(
    zf: ZipFile,
    entry: str,
    *,
    sample_limit: int,
    shared_strings: list[str],
) -> dict[str, Any]:
    counts = _empty_counts()
    samples = _empty_samples()
    dimension: str | None = None
    current_cell: str | None = None
    current_cell_type: str | None = None
    current_cell_sample: dict[str, Any] | None = None
    inline_text_parts: list[str] = []
    inside_inline_string = False

    with zf.open(entry) as handle:
        for event, elem in ET.iterparse(handle, events=("start", "end")):
            tag = _local_name(elem.tag)

            if event == "start":
                if tag == "dimension":
                    dimension = elem.attrib.get("ref")
                elif tag == "row":
                    counts["row_elements"] += 1
                    row_sample = _row_sample(elem)
                    if row_sample and len(samples["row_dimensions"]) < sample_limit:
                        samples["row_dimensions"].append(row_sample)
                elif tag == "col":
                    counts["column_dimension_elements"] += 1
                    if len(samples["column_dimensions"]) < sample_limit:
                        samples["column_dimensions"].append(_col_sample(elem))
                elif tag == "c":
                    counts["cell_elements"] += 1
                    current_cell = elem.attrib.get("r")
                    current_cell_type = elem.attrib.get("t")
                    current_cell_sample = None
                    inline_text_parts = []
                    inside_inline_string = False
                    if "s" in elem.attrib:
                        counts["styled_cell_elements"] += 1
                    if len(samples["cells"]) < sample_limit:
                        current_cell_sample = _cell_sample(elem)
                        samples["cells"].append(current_cell_sample)
                elif tag == "is" and current_cell is not None:
                    inside_inline_string = True
                elif tag == "mergeCell":
                    counts["merged_ranges"] += 1
                    if len(samples["merged_ranges"]) < sample_limit:
                        samples["merged_ranges"].append(elem.attrib.get("ref", ""))
                elif tag == "drawing":
                    counts["drawing_refs"] += 1
                    if len(samples["drawing_refs"]) < sample_limit:
                        samples["drawing_refs"].append(elem.attrib.get(REL_ATTR, ""))
                elif tag == "tablePart":
                    counts["table_part_refs"] += 1
                    if len(samples["table_part_refs"]) < sample_limit:
                        samples["table_part_refs"].append(elem.attrib.get(REL_ATTR, ""))
                elif tag == "hyperlink":
                    counts["hyperlinks"] += 1

            elif event == "end":
                if tag == "f":
                    counts["formula_elements"] += 1
                    if len(samples["formulas"]) < sample_limit:
                        samples["formulas"].append(
                            {
                                "cell": current_cell,
                                "formula": elem.text or "",
                                "attributes": dict(elem.attrib),
                            }
                        )
                elif tag == "v":
                    counts["value_elements"] += 1
                    if current_cell_sample is not None:
                        raw_value = elem.text or ""
                        current_cell_sample["raw_value"] = raw_value
                        current_cell_sample["value_preview"] = _decode_cell_value(
                            raw_value,
                            current_cell_type,
                            shared_strings,
                        )
                elif tag == "is":
                    counts["inline_string_elements"] += 1
                    if current_cell_sample is not None:
                        value = "".join(inline_text_parts)
                        current_cell_sample["raw_value"] = value
                        current_cell_sample["value_preview"] = value
                    inside_inline_string = False
                elif tag == "t" and inside_inline_string:
                    inline_text_parts.append(elem.text or "")
                elif tag == "c":
                    current_cell = None
                    current_cell_type = None
                    current_cell_sample = None
                    inline_text_parts = []
                    inside_inline_string = False
                elem.clear()

    return {
        "dimension": dimension,
        "dimension_bounds": _dimension_bounds(dimension),
        "counts": counts,
        "samples": samples,
    }


def _worksheet_relationships(zf: ZipFile, sheet_entry: str) -> list[dict[str, str]]:
    rels_path = _sheet_rels_path(sheet_entry)
    relationships = _relationships(zf, rels_path)
    return [
        {
            "id": relationship_id,
            "type": rel["type"],
            "target": rel["target"],
            "entry": _normalize_related_target(sheet_entry, rel["target"]),
        }
        for relationship_id, rel in sorted(relationships.items())
    ]


def _drawing_objects_for_sheet(
    zf: ZipFile,
    sheet_entry: str,
    relationships: list[dict[str, str]],
) -> list[dict[str, Any]]:
    del sheet_entry
    objects: list[dict[str, Any]] = []
    for relationship in relationships:
        if not relationship["type"].endswith("/drawing"):
            continue
        drawing_entry = relationship["entry"]
        if drawing_entry not in zf.namelist():
            continue
        objects.extend(_drawing_objects(zf, drawing_entry))
    return objects


def _pivot_tables_for_sheet(
    zf: ZipFile,
    relationships: list[dict[str, str]],
    pivot_caches: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    pivot_tables: list[dict[str, Any]] = []
    for relationship in relationships:
        if not relationship["type"].endswith("/pivotTable"):
            continue
        entry = relationship["entry"]
        if entry not in zf.namelist():
            continue
        pivot_table = _pivot_table(zf, entry, pivot_caches)
        pivot_table["relationship_id"] = relationship["id"]
        pivot_tables.append(pivot_table)
    return pivot_tables


def _pivot_table(
    zf: ZipFile,
    pivot_table_entry: str,
    pivot_caches: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    root = ET.fromstring(zf.read(pivot_table_entry))
    cache_id = root.attrib.get("cacheId", "")
    location = root.find(f"{MAIN_NS}location")
    location_ref = location.attrib.get("ref") if location is not None else None
    return {
        "id": Path(pivot_table_entry).stem,
        "name": root.attrib.get("name"),
        "entry": pivot_table_entry,
        "cache_id": cache_id,
        "cache": pivot_caches.get(cache_id),
        "location": {
            "range": location_ref,
            "bounds": _dimension_bounds(location_ref),
            "first_header_row": _int_attr(location, "firstHeaderRow"),
            "first_data_row": _int_attr(location, "firstDataRow"),
            "first_data_column": _int_attr(location, "firstDataCol"),
        },
        "field_counts": {
            "pivot_fields": _count_child(root, "pivotFields"),
            "row_fields": _count_child(root, "rowFields"),
            "column_fields": _count_child(root, "colFields"),
            "page_fields": _count_child(root, "pageFields"),
            "data_fields": _count_child(root, "dataFields"),
        },
    }


def _pivot_caches(
    zf: ZipFile,
    workbook_rels: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    root = ET.fromstring(zf.read("xl/workbook.xml"))
    caches: dict[str, dict[str, Any]] = {}
    for cache in root.findall(f".//{MAIN_NS}pivotCache"):
        cache_id = cache.attrib.get("cacheId", "")
        relationship_id = cache.attrib.get(REL_ATTR, "")
        rel = workbook_rels.get(relationship_id, {})
        entry = _normalize_xl_target(rel.get("target", ""))
        caches[cache_id] = _pivot_cache(zf, cache_id, relationship_id, entry)
    return caches


def _pivot_cache(
    zf: ZipFile,
    cache_id: str,
    relationship_id: str,
    entry: str,
) -> dict[str, Any]:
    base = {
        "cache_id": cache_id,
        "relationship_id": relationship_id,
        "entry": entry,
        "source": None,
        "record_count": None,
        "cache_field_count": 0,
        "cache_field_samples": [],
    }
    if not entry or entry not in zf.namelist():
        return base

    root = ET.fromstring(zf.read(entry))
    source = root.find(f"{MAIN_NS}cacheSource/{MAIN_NS}worksheetSource")
    fields = root.findall(f"{MAIN_NS}cacheFields/{MAIN_NS}cacheField")
    return {
        **base,
        "source": {
            "type": root.find(f"{MAIN_NS}cacheSource").attrib.get("type")
            if root.find(f"{MAIN_NS}cacheSource") is not None
            else None,
            "sheet": source.attrib.get("sheet") if source is not None else None,
            "range": source.attrib.get("ref") if source is not None else None,
            "bounds": _dimension_bounds(source.attrib.get("ref")) if source is not None else None,
        },
        "record_count": _int_text(root.attrib.get("recordCount")),
        "cache_field_count": len(fields),
        "cache_field_samples": [
            field.attrib.get("name", "")
            for field in fields[:20]
        ],
    }


def _external_links(zf: ZipFile) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for entry in sorted(
        name
        for name in zf.namelist()
        if name.startswith("xl/externalLinks/externalLink")
        and name.endswith(".xml")
    ):
        root = ET.fromstring(zf.read(entry))
        external_book = root.find(f"{MAIN_NS}externalBook")
        relationship_id = (
            external_book.attrib.get(REL_ATTR)
            if external_book is not None
            else None
        )
        sheet_names = [
            node.attrib.get("val", "")
            for node in root.findall(f".//{MAIN_NS}sheetName")
        ]
        rels = _relationships(zf, _external_link_rels_path(entry))
        links.append(
            {
                "entry": entry,
                "relationship_id": relationship_id,
                "targets": [
                    {
                        "id": relationship_id,
                        "type": rel["type"],
                        "target": rel["target"],
                        "target_mode": rel.get("target_mode"),
                    }
                    for relationship_id, rel in sorted(rels.items())
                ],
                "sheet_name_count": len(sheet_names),
                "sheet_name_samples": sheet_names[:30],
            }
        )
    return links


def _drawing_objects(zf: ZipFile, drawing_entry: str) -> list[dict[str, Any]]:
    drawing_rels = _relationships(zf, _drawing_rels_path(drawing_entry))
    root = ET.fromstring(zf.read(drawing_entry))
    objects: list[dict[str, Any]] = []
    for index, anchor in enumerate(root):
        anchor_kind = _local_name(anchor.tag)
        if anchor_kind not in {"twoCellAnchor", "oneCellAnchor", "absoluteAnchor"}:
            continue
        picture = anchor.find(f".//{DRAWING_NS}pic")
        if picture is None:
            continue
        name_node = picture.find(f".//{DRAWING_NS}cNvPr")
        blip = picture.find(f".//{A_NS}blip")
        embed_id = blip.attrib.get(REL_EMBED_ATTR) if blip is not None else None
        rel = drawing_rels.get(embed_id or "", {})
        objects.append(
            {
                "id": f"{Path(drawing_entry).stem}_object_{index + 1}",
                "type": "picture",
                "name": name_node.attrib.get("name") if name_node is not None else None,
                "drawing_entry": drawing_entry,
                "anchor_kind": anchor_kind,
                "from": _drawing_marker(anchor.find(f"{DRAWING_NS}from")),
                "to": _drawing_marker(anchor.find(f"{DRAWING_NS}to")),
                "embed_relationship_id": embed_id,
                "media_entry": _normalize_related_target(drawing_entry, rel.get("target", "")),
            }
        )
    return objects


def _drawing_marker(marker: ET.Element | None) -> dict[str, Any] | None:
    if marker is None:
        return None
    col = _int_child(marker, "col")
    row = _int_child(marker, "row")
    col_off = _int_child(marker, "colOff") or 0
    row_off = _int_child(marker, "rowOff") or 0
    if col is None or row is None:
        return None
    one_based_col = col + 1
    one_based_row = row + 1
    return {
        "cell": f"{get_column_letter(one_based_col)}{one_based_row}",
        "row": one_based_row,
        "column": one_based_col,
        "row_offset": row_off,
        "column_offset": col_off,
    }


def _int_child(parent: ET.Element, local_name: str) -> int | None:
    child = parent.find(f"{DRAWING_NS}{local_name}")
    if child is None or child.text is None:
        return None
    return _int_text(child.text)


def _int_attr(elem: ET.Element | None, attr_name: str) -> int | None:
    if elem is None:
        return None
    return _int_text(elem.attrib.get(attr_name))


def _int_text(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _count_child(root: ET.Element, local_name: str) -> int:
    child = root.find(f"{MAIN_NS}{local_name}")
    if child is None:
        return 0
    count = _int_text(child.attrib.get("count"))
    if count is not None:
        return count
    return len(list(child))


def _relationships(zf: ZipFile, rels_path: str) -> dict[str, dict[str, str]]:
    if rels_path not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(rels_path))
    relationships: dict[str, dict[str, str]] = {}
    for rel in root.findall(f"{PACKAGE_REL_NS}Relationship"):
        relationship_id = rel.attrib.get("Id", "")
        relationships[relationship_id] = {
            "type": rel.attrib.get("Type", ""),
            "target": rel.attrib.get("Target", ""),
            "target_mode": rel.attrib.get("TargetMode"),
        }
    return relationships


def _shared_strings(
    zf: ZipFile,
    *,
    max_shared_strings: int,
) -> dict[str, Any]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return {
            "available": False,
            "loaded_count": 0,
            "truncated": False,
            "items": [],
        }

    items: list[str] = []
    truncated = False
    with zf.open("xl/sharedStrings.xml") as handle:
        for event, elem in ET.iterparse(handle, events=("end",)):
            if _local_name(elem.tag) != "si":
                continue
            if len(items) >= max_shared_strings:
                truncated = True
                elem.clear()
                continue
            items.append(
                "".join(
                    text_node.text or ""
                    for text_node in elem.iter()
                    if _local_name(text_node.tag) == "t"
                )
            )
            elem.clear()

    return {
        "available": True,
        "loaded_count": len(items),
        "truncated": truncated,
        "items": items,
    }


def _package_entries(zf: ZipFile) -> dict[str, Any]:
    infos = zf.infolist()
    names = [info.filename for info in infos]
    prefixes = {
        "worksheets": "xl/worksheets/",
        "drawings": "xl/drawings/",
        "charts": "xl/charts/",
        "media": "xl/media/",
        "tables": "xl/tables/",
        "pivot_cache_records": "xl/pivotCache/pivotCacheRecords",
        "external_links": "xl/externalLinks/",
    }
    return {
        "entry_count": len(infos),
        "worksheet_count": sum(1 for name in names if name.startswith(prefixes["worksheets"]) and name.endswith(".xml")),
        "drawing_count": sum(1 for name in names if name.startswith(prefixes["drawings"]) and name.endswith(".xml")),
        "chart_count": sum(1 for name in names if name.startswith(prefixes["charts"]) and name.endswith(".xml")),
        "media_count": sum(1 for name in names if name.startswith(prefixes["media"])),
        "table_count": sum(1 for name in names if name.startswith(prefixes["tables"]) and name.endswith(".xml")),
        "pivot_cache_record_count": sum(1 for name in names if name.startswith(prefixes["pivot_cache_records"])),
        "external_link_count": sum(1 for name in names if name.startswith(prefixes["external_links"]) and name.endswith(".xml")),
        "has_shared_strings": "xl/sharedStrings.xml" in names,
        "has_styles": "xl/styles.xml" in names,
        "has_calc_chain": "xl/calcChain.xml" in names,
        "largest_entries": [
            {
                "entry": info.filename,
                "size_bytes": info.file_size,
                "compressed_size_bytes": info.compress_size,
            }
            for info in sorted(infos, key=lambda item: item.file_size, reverse=True)[:20]
        ],
    }


def _summary(
    sheets: list[dict[str, Any]],
    package_entries: dict[str, Any],
) -> dict[str, Any]:
    scanned_sheets = [sheet for sheet in sheets if sheet["detail_status"] == "scanned"]
    skipped_sheets = [
        sheet for sheet in sheets if sheet["detail_status"] == "skipped_large_xml"
    ]
    return {
        "sheet_count": len(sheets),
        "scanned_sheet_count": len(scanned_sheets),
        "skipped_large_sheet_count": len(skipped_sheets),
        "visible_sheet_count": sum(1 for sheet in sheets if sheet["state"] == "visible"),
        "formula_elements_in_scanned_sheets": sum(
            sheet["counts"]["formula_elements"] for sheet in scanned_sheets
        ),
        "cell_elements_in_scanned_sheets": sum(
            sheet["counts"]["cell_elements"] for sheet in scanned_sheets
        ),
        "merged_ranges_in_scanned_sheets": sum(
            sheet["counts"]["merged_ranges"] for sheet in scanned_sheets
        ),
        "package_media_count": package_entries["media_count"],
        "package_external_link_count": package_entries["external_link_count"],
        "package_pivot_cache_record_count": package_entries["pivot_cache_record_count"],
        "pivot_table_count": sum(len(sheet["pivot_tables"]) for sheet in sheets),
        "pivot_cache_count": len(
            {
                table["cache_id"]
                for sheet in sheets
                for table in sheet["pivot_tables"]
                if table["cache_id"]
            }
        ),
    }


def _parser_observations(
    sheets: list[dict[str, Any]],
    external_links: list[dict[str, Any]],
) -> list[dict[str, str]]:
    observations: list[dict[str, str]] = []
    for sheet in sheets:
        if sheet["detail_status"] == "skipped_large_xml":
            observations.append(
                {
                    "level": "warning",
                    "message": f"Skipped detailed XML scan for sheet '{sheet['name']}' because its worksheet XML is {sheet['entry_size_bytes']} bytes.",
                }
            )
    if observations:
        observations.append(
            {
                "level": "info",
                "message": "Use a higher max_sheet_xml_bytes limit or targeted sheet extraction when detailed evidence is required.",
            }
        )
    if external_links:
        observations.append(
            {
                "level": "warning",
                "message": f"Workbook contains {len(external_links)} external link package entry; formula dependencies may require external workbook evidence.",
            }
        )
    return observations


def _empty_counts() -> dict[str, int]:
    return {
        "row_elements": 0,
        "column_dimension_elements": 0,
        "cell_elements": 0,
        "styled_cell_elements": 0,
        "value_elements": 0,
        "formula_elements": 0,
        "inline_string_elements": 0,
        "merged_ranges": 0,
        "drawing_refs": 0,
        "table_part_refs": 0,
        "hyperlinks": 0,
    }


def _empty_samples() -> dict[str, list[Any]]:
    return {
        "cells": [],
        "formulas": [],
        "merged_ranges": [],
        "column_dimensions": [],
        "row_dimensions": [],
        "drawing_refs": [],
        "table_part_refs": [],
    }


def _cell_sample(elem: ET.Element) -> dict[str, Any]:
    return {
        "cell": elem.attrib.get("r"),
        "type": elem.attrib.get("t"),
        "style_index": elem.attrib.get("s"),
        "raw_value": None,
        "value_preview": None,
    }


def _decode_cell_value(
    raw_value: str,
    cell_type: str | None,
    shared_strings: list[str],
) -> str:
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (IndexError, ValueError):
            return raw_value
    return raw_value


def _row_sample(elem: ET.Element) -> dict[str, Any] | None:
    if not any(key in elem.attrib for key in ("ht", "hidden", "customHeight")):
        return None
    return {
        "row": elem.attrib.get("r"),
        "height": elem.attrib.get("ht"),
        "hidden": elem.attrib.get("hidden"),
        "custom_height": elem.attrib.get("customHeight"),
    }


def _col_sample(elem: ET.Element) -> dict[str, Any]:
    return {
        "min": elem.attrib.get("min"),
        "max": elem.attrib.get("max"),
        "width": elem.attrib.get("width"),
        "hidden": elem.attrib.get("hidden"),
        "style": elem.attrib.get("style"),
    }


def _dimension_from_head(zf: ZipFile, entry: str) -> str | None:
    with zf.open(entry) as handle:
        head = handle.read(128 * 1024).decode("utf-8", errors="ignore")
    match = re.search(r"<dimension[^>]*\sref=\"([^\"]+)\"", head)
    return match.group(1) if match else None


def _dimension_bounds(dimension: str | None) -> dict[str, int] | None:
    if not dimension:
        return None
    try:
        min_col, min_row, max_col, max_row = range_boundaries(dimension)
    except ValueError:
        return None
    return {
        "min_row": min_row,
        "min_column": min_col,
        "max_row": max_row,
        "max_column": max_col,
    }


def _sheet_rels_path(sheet_entry: str) -> str:
    directory, name = sheet_entry.rsplit("/", 1)
    return f"{directory}/_rels/{name}.rels"


def _drawing_rels_path(drawing_entry: str) -> str:
    directory, name = drawing_entry.rsplit("/", 1)
    return f"{directory}/_rels/{name}.rels"


def _external_link_rels_path(external_link_entry: str) -> str:
    directory, name = external_link_entry.rsplit("/", 1)
    return f"{directory}/_rels/{name}.rels"


def _normalize_xl_target(target: str) -> str:
    if not target:
        return ""
    if target.startswith("/"):
        target = target.lstrip("/")
    elif not target.startswith("xl/"):
        target = f"xl/{target}"
    return target


def _normalize_related_target(sheet_entry: str, target: str) -> str:
    if not target:
        return ""
    if target.startswith("/"):
        return target.lstrip("/")
    sheet_dir = sheet_entry.rsplit("/", 1)[0]
    return posixpath.normpath(posixpath.join(sheet_dir, target))


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a fast ZIP/XML manifest for a workbook before expensive workbook loading."
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sample-limit", type=int, default=20)
    parser.add_argument("--max-sheet-xml-bytes", type=int, default=50_000_000)
    parser.add_argument("--max-shared-strings", type=int, default=200_000)
    args = parser.parse_args()

    manifest = build_workbook_manifest(
        args.workbook,
        sample_limit=args.sample_limit,
        max_sheet_xml_bytes=args.max_sheet_xml_bytes,
        max_shared_strings=args.max_shared_strings,
    )
    payload = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
