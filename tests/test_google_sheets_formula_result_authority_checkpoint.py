from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from google_sheets_formula_result_authority_checkpoint import (  # noqa: E402
    build_google_sheets_formula_result_authority_checkpoint,
)


class GoogleSheetsFormulaResultAuthorityCheckpointTest(unittest.TestCase):
    def test_accepts_clean_effective_formula_range_and_blocks_error_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_json(root / "live-manifest.json", _manifest())
            _write_json(root / "live-table-io-pipelines.json", _pipelines())
            _write_json(root / "live-data-view-projection.json", _projection())
            _write_json(root / "live-blocker-resolution-update.json", _blocker_update())
            _write_json(root / "formula-result-grid-current-probes.json", _current_grid())
            _write_json(root / "source-fc-data-grid-formula-window.json", _source_grid())

            checkpoint = build_google_sheets_formula_result_authority_checkpoint(
                out_dir=root
            )

        schema = json.loads(
            (
                REPO_ROOT
                / "schemas"
                / "google-sheets-formula-result-authority-checkpoint.schema.json"
            ).read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(schema).validate(checkpoint)

        self.assertEqual(checkpoint["summary"]["accepted_range_result_count"], 1)
        self.assertEqual(checkpoint["summary"]["blocked_range_result_count"], 1)
        self.assertEqual(checkpoint["summary"]["accepted_pipeline_result_count"], 1)
        self.assertEqual(checkpoint["summary"]["blocked_pipeline_result_count"], 1)
        self.assertEqual(checkpoint["summary"]["shared_ontology_update_count"], 0)
        self.assertEqual(
            checkpoint["authority"]["parser_truth"],
            "range_level_authority_only_no_semantic_promotion",
        )


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _manifest() -> dict:
    return {
        "source": {
            "spreadsheet_id": "sheet-1",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/sheet-1/edit",
            "title": "Live Sheet",
        }
    }


def _pipelines() -> dict:
    return {
        "pipelines": [
            {
                "id": "pipeline_clean",
                "role": "calculation",
                "output_refs": [{"sheet": "24_0102", "range": "B8:C8"}],
                "transform_refs": [{"formula_count": 1}],
                "review_flags": ["formula_result_not_established"],
                "evidence_refs": ["edge_clean"],
            },
            {
                "id": "pipeline_error",
                "role": "input_staging",
                "output_refs": [{"sheet": "FC_DATA", "range": "A1:B1"}],
                "transform_refs": [{"formula_count": 1}],
                "review_flags": ["formula_error_observed", "external_source_dependency"],
                "evidence_refs": ["edge_error"],
            },
        ]
    }


def _projection() -> dict:
    return {
        "data_view_projections": [
            {
                "pipeline_id": "pipeline_clean",
                "preview": {"status": "sampled_from_top_left_window"},
            }
        ]
    }


def _blocker_update() -> dict:
    return {
        "user_inputs": {
            "reporting_basis": "cash basis payment amount",
            "local_boundary": "전사레벨 현황 보고 문서",
        }
    }


def _current_grid() -> dict:
    return {
        "ok": True,
        "payload": {
            "requested_ranges": ["'24_0102'!B8:C8"],
            "artifacts": [_policy()],
            "windows": [
                {
                    "title": "24_0102",
                    "windows": [
                        {
                            "rows": [
                                [
                                    {
                                        "formatted_value": "7",
                                        "effective_value": {"numberValue": 7},
                                        "user_entered_value": {"formulaValue": "=A1+B1"},
                                    }
                                ]
                            ]
                        }
                    ],
                }
            ],
        },
    }


def _source_grid() -> dict:
    return {
        "ok": True,
        "payload": {
            "requested_ranges": ["FC_DATA!A1:B1"],
            "artifacts": [_policy()],
            "windows": [
                {
                    "title": "FC_DATA",
                    "windows": [
                        {
                            "rows": [
                                [
                                    {
                                        "formatted_value": "#N/A",
                                        "effective_value": {"errorValue": {"type": "N_A"}},
                                        "user_entered_value": {"formulaValue": "=IMPORTRANGE(B1,\"지표!A1\")"},
                                    }
                                ]
                            ]
                        }
                    ],
                }
            ],
        },
    }


def _policy() -> dict:
    return {
        "kind": "source_access_policy_evidence",
        "summary": {
            "decision_id": "policy:grid_formula_v1",
            "allowed": True,
        },
    }


if __name__ == "__main__":
    unittest.main()
