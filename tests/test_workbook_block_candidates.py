from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_block_candidates import build_block_candidates  # noqa: E402


class WorkbookBlockCandidatesTest(unittest.TestCase):
    def test_builds_image_and_row_band_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            sample_path = Path(tmpdir) / "sample.json"
            manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
            sample_path.write_text(json.dumps(_sample()), encoding="utf-8")

            package = build_block_candidates(
                manifest_path,
                sample_path,
                sheets=["Sheet1"],
            )

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-block-candidates.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        self.assertEqual(package["schema_version"], "0.1")
        self.assertEqual(package["summary"]["image_block_count"], 1)
        self.assertGreaterEqual(package["summary"]["row_band_count"], 1)
        self.assertGreaterEqual(package["summary"]["relation_count"], 1)

        sheet = package["sheets"][0]
        image = next(block for block in sheet["blocks"] if block["type"] == "image")
        row_band = next(block for block in sheet["blocks"] if block["type"] == "row_band")
        self.assertEqual(image["bounds"]["start_cell"], "E1")
        self.assertEqual(row_band["subtype"], "table_candidate")
        self.assertEqual(sheet["relations"][0]["type"], "adjacent_left_of")

    def test_models_pivot_table_separately_from_sampled_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            sample_path = Path(tmpdir) / "sample.json"
            manifest = _manifest()
            manifest["workbook"]["sheets"][0]["pivot_tables"] = [_pivot_table()]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            sample_path.write_text(json.dumps(_sample()), encoding="utf-8")

            package = build_block_candidates(
                manifest_path,
                sample_path,
                sheets=["Sheet1"],
            )

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-block-candidates.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        sheet = package["sheets"][0]
        pivot = next(block for block in sheet["blocks"] if block["type"] == "pivot_table")
        row_band = next(block for block in sheet["blocks"] if block["type"] == "row_band")
        relation_types = {relation["type"] for relation in sheet["relations"]}

        self.assertEqual(pivot["source"]["cache_source_sheet"], "Raw")
        self.assertEqual(row_band["subtype"], "pivot_table_value_sample")
        self.assertIn("sample_of_pivot_table", relation_types)
        self.assertIn("derived_from_pivot_cache_source", relation_types)

    def test_classifies_external_workbook_and_pivot_formula_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            sample_path = Path(tmpdir) / "sample.json"
            manifest = _manifest()
            manifest["workbook"]["sheets"][0]["pivot_tables"] = [_pivot_table()]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            sample_path.write_text(
                json.dumps(_sample_with_formula_refs()),
                encoding="utf-8",
            )

            package = build_block_candidates(
                manifest_path,
                sample_path,
                sheets=["Sheet1"],
            )

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-block-candidates.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        sheet = package["sheets"][0]
        relation_types = {relation["type"] for relation in sheet["relations"]}
        formula_block = sheet["blocks"][-1]
        reference_kinds = {
            reference["kind"]
            for reference in formula_block["formula_references"]
        }
        target_sheets = {
            reference["target_sheet"]
            for reference in formula_block["formula_references"]
        }

        self.assertIn("pivot_function", reference_kinds)
        self.assertIn("external_workbook_range", reference_kinds)
        self.assertIn("누적", target_sheets)
        self.assertNotIn("B26-누적", target_sheets)
        self.assertIn("formula_references_pivot_table", relation_types)
        self.assertIn("formula_references_external_workbook", relation_types)

    def test_segments_2d_cell_regions_by_blank_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            sample_path = Path(tmpdir) / "sample.json"
            manifest = _manifest()
            manifest["workbook"]["sheets"][0]["drawing_objects"] = []
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            sample_path.write_text(
                json.dumps(_sample_with_side_by_side_gap()),
                encoding="utf-8",
            )

            package = build_block_candidates(
                manifest_path,
                sample_path,
                sheets=["Sheet1"],
            )

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-block-candidates.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        sheet = package["sheets"][0]
        bounds = [region["bounds"] for region in sheet["cell_regions"]]
        split_types = {
            candidate["type"]
            for candidate in sheet["cell_region_split_candidates"]
        }
        gate_statuses = {
            result["status"]
            for result in sheet["boundary_gate_results"]
        }

        self.assertEqual(package["summary"]["cell_region_count"], 2)
        self.assertEqual(package["summary"]["strong_boundary_candidate_count"], 1)
        self.assertEqual(bounds[0]["start_column"], 1)
        self.assertEqual(bounds[0]["end_column"], 2)
        self.assertEqual(bounds[1]["start_column"], 4)
        self.assertEqual(bounds[1]["end_column"], 5)
        self.assertIn("blank_column_boundary", split_types)
        self.assertIn("strong_candidate", gate_statuses)

    def test_flags_touching_repeated_headers_as_split_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            sample_path = Path(tmpdir) / "sample.json"
            manifest = _manifest()
            manifest["workbook"]["sheets"][0]["drawing_objects"] = []
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            sample_path.write_text(
                json.dumps(_sample_with_touching_repeated_headers()),
                encoding="utf-8",
            )

            package = build_block_candidates(
                manifest_path,
                sample_path,
                sheets=["Sheet1"],
            )

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-block-candidates.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(package)

        sheet = package["sheets"][0]
        split_types = {
            candidate["type"]
            for candidate in sheet["cell_region_split_candidates"]
        }

        self.assertEqual(package["summary"]["cell_region_count"], 2)
        self.assertEqual(package["summary"]["touching_header_split_candidate_count"], 1)
        self.assertIn("repeated_header_touching_boundary", split_types)


def _manifest() -> dict:
    return {
        "workbook": {
            "sheets": [
                {
                    "name": "Sheet1",
                    "dimension": "A1:J10",
                    "dimension_bounds": {
                        "min_row": 1,
                        "min_column": 1,
                        "max_row": 10,
                        "max_column": 10,
                    },
                    "drawing_objects": [
                        {
                            "id": "drawing1_object_1",
                            "name": "Picture 1",
                            "drawing_entry": "xl/drawings/drawing1.xml",
                            "media_entry": "xl/media/image1.png",
                            "from": {"row": 1, "column": 5, "cell": "E1"},
                            "to": {"row": 5, "column": 10, "cell": "J5"},
                        }
                    ],
                    "pivot_tables": [],
                }
            ]
        }
    }


def _pivot_table() -> dict:
    return {
        "id": "pivotTable1",
        "name": "PivotTable1",
        "entry": "xl/pivotTables/pivotTable1.xml",
        "cache_id": "1",
        "cache": {
            "cache_id": "1",
            "relationship_id": "rId1",
            "entry": "xl/pivotCache/pivotCacheDefinition1.xml",
            "source": {
                "type": "worksheet",
                "sheet": "Raw",
                "range": "A1:B100",
                "bounds": {
                    "min_row": 1,
                    "min_column": 1,
                    "max_row": 100,
                    "max_column": 2,
                },
            },
            "record_count": 99,
            "cache_field_count": 2,
            "cache_field_samples": ["Label", "Amount"],
        },
        "location": {
            "range": "A1:B2",
            "bounds": {
                "min_row": 1,
                "min_column": 1,
                "max_row": 2,
                "max_column": 2,
            },
            "first_header_row": 1,
            "first_data_row": 1,
            "first_data_column": 1,
        },
        "field_counts": {
            "pivot_fields": 2,
            "row_fields": 1,
            "column_fields": 0,
            "page_fields": 0,
            "data_fields": 1,
        },
        "relationship_id": "rId2",
    }


def _sample() -> dict:
    return {
        "sheets": [
            {
                "name": "Sheet1",
                "windows": [
                    {
                        "rows": [
                            {
                                "row": 1,
                                "non_empty_count": 2,
                                "formula_count": 0,
                                "cells": [
                                    {
                                        "cell": "A1",
                                        "row": 1,
                                        "column": 1,
                                        "value_type": "string",
                                        "value_preview": "Label",
                                        "formula": None,
                                    },
                                    {
                                        "cell": "B1",
                                        "row": 1,
                                        "column": 2,
                                        "value_type": "string",
                                        "value_preview": "Amount",
                                        "formula": None,
                                    },
                                ],
                            },
                            {
                                "row": 2,
                                "non_empty_count": 2,
                                "formula_count": 0,
                                "cells": [
                                    {
                                        "cell": "A2",
                                        "row": 2,
                                        "column": 1,
                                        "value_type": "string",
                                        "value_preview": "A",
                                        "formula": None,
                                    },
                                    {
                                        "cell": "B2",
                                        "row": 2,
                                        "column": 2,
                                        "value_type": "number",
                                        "value_preview": "10",
                                        "formula": None,
                                    },
                                ],
                            },
                        ]
                    }
                ],
            }
        ]
    }


def _sample_with_formula_refs() -> dict:
    return {
        "sheets": [
            {
                "name": "Sheet1",
                "windows": [
                    {
                        "rows": [
                            {
                                "row": 1,
                                "non_empty_count": 2,
                                "formula_count": 0,
                                "cells": [
                                    {
                                        "cell": "A1",
                                        "row": 1,
                                        "column": 1,
                                        "value_type": "string",
                                        "value_preview": "Label",
                                        "formula": None,
                                    },
                                    {
                                        "cell": "B1",
                                        "row": 1,
                                        "column": 2,
                                        "value_type": "string",
                                        "value_preview": "Amount",
                                        "formula": None,
                                    },
                                ],
                            },
                            {
                                "row": 2,
                                "non_empty_count": 2,
                                "formula_count": 0,
                                "cells": [
                                    {
                                        "cell": "A2",
                                        "row": 2,
                                        "column": 1,
                                        "value_type": "string",
                                        "value_preview": "A",
                                        "formula": None,
                                    },
                                    {
                                        "cell": "B2",
                                        "row": 2,
                                        "column": 2,
                                        "value_type": "number",
                                        "value_preview": "10",
                                        "formula": None,
                                    },
                                ],
                            },
                            {
                                "row": 3,
                                "non_empty_count": 0,
                                "formula_count": 0,
                                "cells": [],
                            },
                            {
                                "row": 4,
                                "non_empty_count": 0,
                                "formula_count": 0,
                                "cells": [],
                            },
                            {
                                "row": 5,
                                "non_empty_count": 3,
                                "formula_count": 3,
                                "cells": [
                                    {
                                        "cell": "D5",
                                        "row": 5,
                                        "column": 4,
                                        "value_type": "formula",
                                        "value_preview": '=GETPIVOTDATA("Amount",$A$1)',
                                        "formula": '=GETPIVOTDATA("Amount",$A$1)',
                                    },
                                    {
                                        "cell": "E5",
                                        "row": 5,
                                        "column": 5,
                                        "value_type": "formula",
                                        "value_preview": "='[Budget.xlsx]Raw'!$B$2",
                                        "formula": "='[Budget.xlsx]Raw'!$B$2",
                                    },
                                    {
                                        "cell": "F5",
                                        "row": 5,
                                        "column": 6,
                                        "value_type": "formula",
                                        "value_preview": "=B26-누적!DA1",
                                        "formula": "=B26-누적!DA1",
                                    },
                                ],
                            },
                        ]
                    }
                ],
            }
        ]
    }


def _sample_with_side_by_side_gap() -> dict:
    return {
        "sheets": [
            {
                "name": "Sheet1",
                "windows": [
                    {
                        "rows": [
                            _sample_row(
                                1,
                                [
                                    (1, "A1", "string", "Label"),
                                    (2, "B1", "string", "Amount"),
                                    (4, "D1", "string", "Label"),
                                    (5, "E1", "string", "Amount"),
                                ],
                            ),
                            _sample_row(
                                2,
                                [
                                    (1, "A2", "string", "A"),
                                    (2, "B2", "number", "10"),
                                    (4, "D2", "string", "B"),
                                    (5, "E2", "number", "20"),
                                ],
                            ),
                        ]
                    }
                ],
            }
        ]
    }


def _sample_with_touching_repeated_headers() -> dict:
    return {
        "sheets": [
            {
                "name": "Sheet1",
                "windows": [
                    {
                        "rows": [
                            _sample_row(
                                1,
                                [
                                    (1, "A1", "string", "Label"),
                                    (2, "B1", "string", "Amount"),
                                    (3, "C1", "string", "Label"),
                                    (4, "D1", "string", "Amount"),
                                ],
                            ),
                            _sample_row(
                                2,
                                [
                                    (1, "A2", "string", "A"),
                                    (2, "B2", "number", "10"),
                                    (3, "C2", "string", "B"),
                                    (4, "D2", "number", "20"),
                                ],
                            ),
                        ]
                    }
                ],
            }
        ]
    }


def _sample_row(row_number: int, cells: list[tuple[int, str, str, str]]) -> dict:
    return {
        "row": row_number,
        "non_empty_count": len(cells),
        "formula_count": sum(1 for _, _, value_type, _ in cells if value_type == "formula"),
        "cells": [
            {
                "cell": cell_ref,
                "row": row_number,
                "column": column,
                "value_type": value_type,
                "value_preview": value_preview,
                "formula": value_preview if value_type == "formula" else None,
            }
            for column, cell_ref, value_type, value_preview in cells
        ],
    }


if __name__ == "__main__":
    unittest.main()
