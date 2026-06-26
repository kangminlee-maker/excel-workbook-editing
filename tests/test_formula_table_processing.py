from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from spreadsheet_processing.formula_table import (
    build_formula_table_grid,
    count_formula_cells,
    extract_layout_labels,
    formula_table_readback_validation,
    normalize_formula_table_spec,
    range_bounds,
)


class FormulaTableProcessingTest(unittest.TestCase):
    def test_builds_formula_grid_from_source_labels(self) -> None:
        spec = normalize_formula_table_spec(_formula_table_spec())
        labels = extract_layout_labels(spec, _source_values())

        grid = build_formula_table_grid(
            spec=spec,
            row_labels=labels["row_labels"],
            column_labels=labels["column_labels"],
            output_sheet_title=spec["output"]["sheet_title"],
        )

        self.assertEqual(labels["source"], "source_values")
        self.assertEqual(labels["row_labels"], ["A", "B"])
        self.assertEqual(labels["column_labels"], ["Jan", "Feb"])
        self.assertEqual(count_formula_cells(grid), 4)
        self.assertEqual(grid[1], ["Team", "Jan", "Feb"])
        self.assertIn("'Raw'!$C$2:$C$4", grid[2][1])
        self.assertIn("$A3", grid[2][1])
        self.assertIn("B$2", grid[2][1])

    def test_output_canvas_labels_take_precedence(self) -> None:
        spec = _formula_table_spec()
        spec["output_canvas"] = [
            ["", "Feb"],
            ["A", ""],
            ["C", ""],
        ]
        normalized = normalize_formula_table_spec(spec)

        labels = extract_layout_labels(normalized, _source_values())

        self.assertEqual(labels, {
            "row_labels": ["A", "C"],
            "column_labels": ["Feb"],
            "source": "output_canvas",
        })

    def test_rejects_out_of_range_field_column(self) -> None:
        spec = _formula_table_spec()
        spec["fields"]["measure"]["column"] = "Z"

        with self.assertRaisesRegex(ValueError, "outside the source range"):
            normalize_formula_table_spec(spec)

    def test_allows_arbitrary_sheet_formula_template(self) -> None:
        spec = _formula_table_spec()
        spec["formula"] = {
            "template": "=IFERROR(INDEX(FILTER({measure_range},{row_label_range}={row_label_cell},{column_label_range}={column_label_cell}),1),0)"
        }
        normalized = normalize_formula_table_spec(spec)
        labels = extract_layout_labels(normalized, _source_values())

        grid = build_formula_table_grid(
            spec=normalized,
            row_labels=labels["row_labels"],
            column_labels=labels["column_labels"],
            output_sheet_title=normalized["output"]["sheet_title"],
        )

        self.assertIn("INDEX(FILTER", grid[2][1])
        self.assertEqual(count_formula_cells(grid), 4)

    def test_defaults_to_sumproduct_formula_template(self) -> None:
        spec = _formula_table_spec()
        spec.pop("formula")
        normalized = normalize_formula_table_spec(spec)
        labels = extract_layout_labels(normalized, _source_values())

        grid = build_formula_table_grid(
            spec=normalized,
            row_labels=labels["row_labels"],
            column_labels=labels["column_labels"],
            output_sheet_title=normalized["output"]["sheet_title"],
        )

        self.assertIn("SUMPRODUCT", grid[2][1])
        self.assertNotIn("SUMIFS", grid[2][1])

    def test_rejects_non_formula_template(self) -> None:
        spec = _formula_table_spec()
        spec["formula"] = {"template": "SUM(A:A)"}

        with self.assertRaisesRegex(ValueError, "must start with '='"):
            normalize_formula_table_spec(spec)

    def test_excel_defaults_to_copy_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workbook_path = Path(tmpdir) / "source.xlsx"
            workbook_path.touch()
            spec = _formula_table_spec(
                artifact_type="excel_workbook",
                workbook_path=str(workbook_path),
            )

            normalized = normalize_formula_table_spec(spec)

        self.assertEqual(normalized["artifact_type"], "excel_workbook")
        self.assertEqual(normalized["output"]["creation_mode"], "copy")

    def test_excel_sheet_mode_rejects_output_workbook_path(self) -> None:
        spec = _formula_table_spec(
            artifact_type="excel_workbook",
            workbook_path="/tmp/source.xlsx",
            creation_mode="sheet",
        )
        spec["output"]["workbook_path"] = "/tmp/output.xlsx"

        with self.assertRaisesRegex(ValueError, "only valid when output.creation_mode='copy'"):
            normalize_formula_table_spec(spec)

    def test_range_and_readback_helpers_are_processing_only(self) -> None:
        self.assertEqual(range_bounds("'Raw'!A1:C4"), (1, 1, 3, 4))

        result = formula_table_readback_validation(
            [["Team", "Jan"], ["A", "#REF!"]],
            expected_rows=2,
            expected_columns=2,
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_count"], 1)


def _source_values() -> list[list[str]]:
    return [
        ["Team", "Month", "Revenue"],
        ["A", "Jan", "100"],
        ["A", "Feb", "120"],
        ["B", "Jan", "80"],
    ]


def _formula_table_spec(
    *,
    artifact_type: str = "google_sheets",
    workbook_path: str = "",
    creation_mode: str = "",
) -> dict:
    source = {
        "artifact_type": artifact_type,
        "spreadsheet_id": "spreadsheet-1" if artifact_type == "google_sheets" else "",
        "workbook_path": workbook_path,
        "sheet_title": "Raw",
        "qualified_range": "'Raw'!A1:C4",
        "header_row": 1,
    }
    output = {"sheet_title": "FORMULA_TABLE_TEST", "title": "Team by Month"}
    if creation_mode:
        output["creation_mode"] = creation_mode
    return {
        "schema_version": "1.0",
        "spec_kind": "formula_table_apply_v1",
        "artifact_type": artifact_type,
        "spreadsheet_id": "spreadsheet-1" if artifact_type == "google_sheets" else "",
        "source": source,
        "fields": {
            "row_label": {"column": "A", "header": "Team", "selected_cell": "A1"},
            "column_label": {"column": "B", "header": "Month", "selected_cell": "B1"},
            "measure": {"column": "C", "header": "Revenue", "selected_cell": "C1"},
        },
        "formula": {
            "template": "=IFERROR(SUMIFS({measure_range},{row_label_range},{row_label_cell},{column_label_range},{column_label_cell}),0)"
        },
        "output": output,
    }


if __name__ == "__main__":
    unittest.main()
