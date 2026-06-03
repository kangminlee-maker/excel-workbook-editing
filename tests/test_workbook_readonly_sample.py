from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema
from openpyxl import Workbook

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from workbook_readonly_sample import build_readonly_sample  # noqa: E402


class WorkbookReadOnlySampleTest(unittest.TestCase):
    def test_samples_targeted_rows_in_read_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workbook_path = Path(tmpdir) / "readonly_sample.xlsx"
            self._write_sample_workbook(workbook_path)

            sample = build_readonly_sample(
                workbook_path,
                sheets=["Data"],
                row_windows=["Data:1-3", "Data:5-5"],
                max_columns=4,
            )

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-readonly-sample.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(sample)

        self.assertEqual(sample["schema_version"], "0.1")
        self.assertEqual(sample["engine"]["mode"], "read_only")
        self.assertEqual(sample["summary"]["sheet_count"], 1)
        self.assertEqual(sample["summary"]["window_count"], 2)

        sheet = sample["sheets"][0]
        self.assertEqual(sheet["name"], "Data")
        self.assertEqual(sheet["windows"][0]["rows"][0]["cells"][0]["value_preview"], "Name")
        formula_cell = sheet["windows"][0]["rows"][2]["cells"][2]
        self.assertEqual(formula_cell["cell"], "C3")
        self.assertEqual(formula_cell["value_type"], "formula")
        self.assertEqual(formula_cell["formula"], "=B3*2")

    def test_manifest_structural_windows_cover_pivot_locations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workbook_path = root / "readonly_sample.xlsx"
            manifest_path = root / "manifest.json"
            self._write_sample_workbook(workbook_path)
            manifest_path.write_text(
                json.dumps(_manifest_with_pivot_window()),
                encoding="utf-8",
            )

            sample = build_readonly_sample(
                workbook_path,
                manifest_path=manifest_path,
                include_structural_windows=True,
                default_max_rows=2,
                max_columns=4,
            )

        schema = json.loads(
            (REPO_ROOT / "schemas" / "workbook-readonly-sample.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(sample)

        sheet = sample["sheets"][0]
        windows = [(window["start_row"], window["end_row"]) for window in sheet["windows"]]
        self.assertEqual(sheet["name"], "Data")
        self.assertEqual(windows, [(1, 5)])
        self.assertEqual(sample["summary"]["window_count"], 1)

    @staticmethod
    def _write_sample_workbook(path: Path) -> None:
        wb = Workbook()
        ws = wb.active
        ws.title = "Data"
        ws.append(["Name", "Value", "Double"])
        ws.append(["A", 10, "=B2*2"])
        ws.append(["B", 20, "=B3*2"])
        ws.append([None, None, None])
        ws.append(["Total", None, "=SUM(C2:C3)"])
        wb.save(path)


def _manifest_with_pivot_window() -> dict:
    return {
        "workbook": {
            "sheets": [
                {
                    "name": "Data",
                    "dimension_bounds": {
                        "min_row": 1,
                        "min_column": 1,
                        "max_row": 5,
                        "max_column": 3,
                    },
                    "pivot_tables": [
                        {
                            "location": {
                                "bounds": {
                                    "min_row": 5,
                                    "min_column": 1,
                                    "max_row": 5,
                                    "max_column": 3,
                                }
                            }
                        }
                    ],
                    "drawing_objects": [],
                }
            ]
        }
    }


if __name__ == "__main__":
    unittest.main()
