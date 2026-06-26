# Phase 1.5 Processing Extraction Summary

## Scope

Phase 1.5 extracted spreadsheet-processing behavior from the local Sheets
Bridge runtime boundary before any runtime-directory removal.

## Preserved In Active Processing

- `spreadsheet_processing/table_build_contracts.py`
  - `TableBuildIntent`
  - `TableBuildPlan`
  - artifact type and creation mode validation
- `spreadsheet_processing/formula_table.py`
  - formula-table spec normalization
  - source/output-canvas label extraction
  - formula-table grid construction
  - A1 range and sheet-title helpers
  - formula readback error scan helper

## Contract Split

Processing contracts kept active:

- `schemas/table-build-intent.schema.json`
- `schemas/table-build-plan.schema.json`
- `tests/test_table_builder_contracts.py`

Runtime-host contracts remain outside the active processing extraction:

- `schemas/table-builder-host-message.schema.json`
- `schemas/table-builder-session.schema.json`
- `tests/test_table_builder_host_adapter_js.py`
- host/session validators in `mcp/sheets_bridge/contracts.py`

## Formula Table Boundary

Extracted behavior is deterministic and does not require:

- local Google OAuth
- direct Google API calls
- a local MCP server
- browser extension state
- native messaging
- Cloud Run broker state

The extracted module builds formula grids from a normalized spec and existing
source evidence. Actual Google Sheets access and writes belong to Day1 MCP.
Excel workbook writes remain file-processing work in this repository.

## Excel Engine Boundary

`scripts/excel_engine_sample.py` remains the supported Excel recalculation and
cell-sampling path. `mcp/sheets_bridge/excel_engine.py` has no processing
behavior that is not already covered by the script; it only adapts the helper
for the local MCP runtime.

## Table Flow Boundary

`mcp/sheets_bridge/table_flow.py` contains useful table I/O ideas, but most of
the active code is mixed with Google API transport, MCP package output, or a
specific historical refactor pattern. The current active processing path for
formula/dataflow discovery is `scripts/google_sheets_formula_dataflow_discovery.py`.
Further `table_flow.py` extraction belongs with the Phase 2 evidence-input
boundary work.

## Verification

Run after this phase:

```bash
python3 -m unittest tests/test_table_builder_contracts.py tests/test_formula_table_processing.py
python3 -m py_compile spreadsheet_processing/*.py scripts/excel_engine_sample.py
python3 - <<'PY'
import json
from pathlib import Path
for path in [Path("schemas/table-build-intent.schema.json"), Path("schemas/table-build-plan.schema.json")]:
    json.loads(path.read_text())
print("table-builder processing schemas json ok")
PY
```
