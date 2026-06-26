# Spreadsheet Processing Scope Cleanup Plan

## Purpose

This plan fixes the active repository direction after Day1 MCP became the
installed Google Drive and Google Sheets access authority.

`excel-workbook-editing` should focus on Excel and spreadsheet processing:
analysis, evidence packaging, formula/dataflow discovery, validation,
review-package generation, and workbook-safe edits. It should not own Google
OAuth, Google Sheets API access, Cloud Run broker behavior, MCP server runtime,
Chrome extension behavior, native messaging, or MCP packaging.

## Authority Boundary

| Area | Owner |
| --- | --- |
| Google Drive and Google Sheets authentication | Day1 MCP |
| Google ACL/IAM, OAuth, scopes, target gates, write gates, and actual Google API calls | Day1 MCP |
| Connected Google Sheets read/write access from AI hosts | Day1 MCP tools |
| Excel workbook files, workbook-family identity, formulas, formatting, render evidence, and Excel-engine validation | `excel-workbook-editing` |
| Spreadsheet evidence interpretation, table/dataflow discovery, claim/gate projection, review packages, and processing plans | `excel-workbook-editing` |

Current installed Day1 MCP tool surface includes:

- `drive_list`
- `sheets_read`
- `sheets_analyze_structure`
- `sheets_preview_write`
- `sheets_update_values`
- `sheets_update_formulas`
- `sheets_create_table_sheet`
- `sheets_append_rows`
- `sheets_set_data_validation`
- `sheets_repeat_cell_format`
- `sheets_insert_dimension`
- `sheets_delete_dimension`

## Product Direction

The active product direction is:

```text
Day1 MCP
  -> spreadsheet access, auth, policy, write gates, Google API calls
  -> bounded values/formulas/structure/write results

excel-workbook-editing
  -> consume files or Day1 MCP evidence/results
  -> understand workbook/spreadsheet structure
  -> discover formulas, dataflow, tables, claims, and validation needs
  -> create review packages and processing artifacts
  -> validate Excel formula results with Microsoft Excel when values matter
```

This repository should expose reusable processing code and skill guidance, not
a second access runtime.

## Scope Decisions

### Keep

Keep active runtime and documentation that supports spreadsheet processing:

- Excel workbook processing scripts and schemas:
  - `scripts/workbook_*`
  - `schemas/workbook-*`
  - `tests/test_workbook_*`
  - `scripts/excel_engine_sample.py`
  - `scripts/formula_error_scan.py`
  - Excel render, copy, and recalculation helpers when they support workbook
    processing.
- Table-builder processing contracts and fixtures after they are split from
  host/runtime concepts:
  - `spreadsheet_processing/table_build_contracts.py`
  - `spreadsheet_processing/formula_table.py`
  - `schemas/table-build-intent.schema.json`
  - `schemas/table-build-plan.schema.json`
  - Excel workbook source preview.
  - Formula-table construction.
  - Excel engine validation.
  - Neutral `TableBuildIntent` and `TableBuildPlan` contracts when they support
    spreadsheet processing without MCP/App host authority.
- Spreadsheet evidence and understanding scripts:
  - `scripts/google_sheets_formula_dataflow_discovery.py`
  - `scripts/google_sheets_initial_understanding.py`
  - `scripts/google_sheets_table_io_pipelines.py`
  - `scripts/google_sheets_evidence_package.py`
  - `scripts/google_sheets_gate_execution.py`
  - Google Sheets ontology, claim, semantic proposal, and validated graph
    processing scripts that operate on existing evidence artifacts.
- Processing docs:
  - `docs/data-processing-spreadsheet-package-design.md`
  - `docs/document-shaped-excel-understanding-design.md`
  - `docs/evidence-backed-spreadsheet-claim-ledger-design.md`
  - `docs/sheets-formula-dataflow-discovery-design.md`
  - ADRs that describe current processing architecture.
- Active references:
  - `references/spreadsheet-principles.md`
  - `references/excel-workbook-principles.md`
  - `references/spreadsheet-review-package.md`
  - `references/connected-google-sheets-principles.md`, updated so connected
    Sheets access authority is Day1 MCP.
- Project and review artifacts that support current processing examples.

### Remove From Active Runtime

Remove these from active runtime ownership:

- `mcp/`
- `packaging/sheets-bridge-mcp/`
- `broker/cloud-run-sheets-broker/`
- `cli/sheets-bridge/`
- `extension/chrome-sheets-bridge/`
- `native-host/`
- Sheets Bridge MCP, Chrome extension, native-host, broker, OAuth, and
  workload-identity active docs.
- MCP/App table-builder schemas and tests when they only support host adapter,
  local MCP, ChatGPT web smoke, or `ui://sheets-bridge` runtime behavior.
- Review packages that only prove retired access runtime behavior:
  - `review-packages/sheets-bridge/mcp-*`
  - `review-packages/sheets-bridge/mcp-live-*`
  - `review-packages/sheets-bridge/workload-identity/`
  - `review-packages/sheets-bridge/keyless-extract/`
  - access-runtime-only portions of `review-packages/spreadsheet-table-builder/`

### Rework

Rework these instead of deleting immediately:

- Google Sheets processing scripts that currently mention broker reads.
  They should consume Day1 MCP evidence/result artifacts or generic
  `source_evidence` inputs.
- Processing logic currently located under `mcp/sheets_bridge/`, especially
  `excel_engine.py`, `table_builder.py`, `table_flow.py`, and processing parts
  of `contracts.py`. Extract or merge useful processing behavior before
  deleting the MCP runtime directory.
- Table-builder schemas, tests, and review packages that support Excel workbook
  or spreadsheet formula-table processing. Split host adapter/runtime fields
  from processing contracts before deciding what to remove.
- Schemas and tests that are still useful for spreadsheet understanding but use
  names such as `broker`, `mcp`, or `live`.
- Active docs and guidance that say MCP Sheets Bridge is the current runtime.
  Replace that with Day1 MCP as the access authority and this repository as the
  processing authority.

## Cleanup Phases

### Phase 0: Baseline, Classification, And Guardrails

Goal: capture the cleanup baseline, classify every ambiguous asset, and avoid
accidental loss of processing work.

Actions:

- Create `development-record/scope-cleanup-baseline/<YYYYMMDD>/`.
- Use this baseline directory setup:

```bash
BASELINE_DIR="development-record/scope-cleanup-baseline/$(date +%Y%m%d)"
mkdir -p "$BASELINE_DIR"
```

- Write `git-status.txt`:

```bash
git status --short > "$BASELINE_DIR/git-status.txt"
```

- Write `untracked-files.txt`:

```bash
git ls-files --others --exclude-standard > "$BASELINE_DIR/untracked-files.txt"
```

- Write `runtime-file-inventory.txt`:

```bash
(find mcp packaging broker cli extension native-host -type f 2>/dev/null || true) | sort > "$BASELINE_DIR/runtime-file-inventory.txt"
```

- Write `active-runtime-reference-grep.txt`:

```bash
rg -n "Sheets Bridge MCP|mcp-sheets-bridge|chrome-sheets-bridge|native-host|Cloud Run Sheets broker|local OAuth token cache|MCP-managed local OAuth|broker|Chrome|native messaging|remote MCP|Google Sheets API|connector/API|sheets_bridge|mcp/sheets_bridge|spreadsheet_table_builder|workload-identity|packaging/sheets-bridge|DEFAULT_BROKER_URL|gcloud auth print-identity-token|googleapiclient|google\\.auth" \
  --glob '!docs/spreadsheet-processing-scope-cleanup-plan.md' \
  --glob '!development-record/**' \
  AGENTS.md CLAUDE.md README.md SKILL.md IMPLEMENTATION_MAP.html docs references scripts schemas tests \
  > "$BASELINE_DIR/active-runtime-reference-grep.txt" || true
```

- Create `cleanup-classification.tsv` with these columns:
  - `path`
  - `current_status`
  - `action`
  - `reason`
  - `replacement_path`
  - `verification_command`
- Classify every path under runtime-removal directories and every top-level
  `review-packages/` folder as one of:
  - `keep`
  - `delete`
  - `move_to_development_record`
  - `rework`
  - `stop`
- Also classify every nested review-package path that will be moved, deleted,
  split, or reworked, including children under `review-packages/sheets-bridge/`
  and split targets under `review-packages/spreadsheet-table-builder/`.
- Confirm Day1 MCP tool availability when the tool surface is visible in the
  active host. If Day1 MCP is not visible in the current session, record the
  missing tool evidence in the baseline and continue only with docs/runtime
  cleanup that does not require live connected-Sheets verification.
- Avoid deleting processing scripts, schemas, tests, or review examples until
  their input boundary is classified.

Done when:

- The baseline folder exists and contains the files above.
- Every untracked file selected for cleanup is classified before deletion.
- Every runtime-removal path and top-level review package folder has exactly one
  classification action.
- Every nested review-package path selected for move, deletion, split, or rework
  has a classification action.
- Any `stop` or unclassified path blocks the destructive phase that would touch
  it.
- No file deletion has happened without a matching keep/remove/rework decision.

### Phase 1: Active Docs Realignment

Goal: make active docs describe the current product direction.

Files to update:

- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `SKILL.md`
- `IMPLEMENTATION_MAP.html`
- `docs/data-processing-spreadsheet-package-design.md`
- `docs/document-shaped-excel-understanding-design.md`
- `docs/evidence-backed-spreadsheet-claim-ledger-design.md`
- `docs/google-sheets-parser-permission-requirements.md`
- `docs/sheets-formula-dataflow-discovery-design.md`
- `docs/adr/0002-data-processing-spreadsheet-package.md`
- `references/connected-google-sheets-principles.md`
- `references/spreadsheet-principles.md` if needed.

Actions:

- Replace Sheets Bridge MCP runtime guidance with Day1 MCP access guidance.
- State that this repo consumes files and Day1 MCP evidence/results.
- Replace generic connector, direct Google API, and MCP Sheets Bridge wording
  with Day1 MCP tool-result wording where the document describes connected
  Google Sheets access.
- Remove active instructions for Chrome extension, native-host, local OAuth
  cache, Cloud Run Sheets broker, and Sheets Bridge MCP packaging.
- Keep Excel workbook and spreadsheet processing rules.

Done when:

- Active docs point to Day1 MCP for Google access.
- Active docs point to this repo for processing.
- A new session reading only active docs would not continue implementing local
  Sheets Bridge, broker, Chrome extension, or native host.
- Active docs do not describe this repository as the owner of Google OAuth,
  Google API calls, Cloud Run broker behavior, MCP server runtime, or write-gate
  policy.

### Phase 1.5: Processing Asset Extraction And Contract Split

Goal: extract useful Excel/spreadsheet processing behavior before removing
runtime directories.

Actions:

- Inspect `mcp/sheets_bridge/excel_engine.py`, `table_builder.py`,
  `table_flow.py`, and processing portions of `contracts.py`.
- Move or merge processing-owned behavior into neutral active locations before
  deleting `mcp/`.
- Confirm `scripts/excel_engine_sample.py` or another active processing helper
  remains the supported Excel-engine validation path.
- Split table-builder contracts:
  - keep neutral result-table intent/plan contracts when they support Excel or
    spreadsheet processing;
  - move MCP/App host messages, `ui://sheets-bridge`, ChatGPT web smoke, and
    local MCP host adapter contracts to `development-record/` or delete them;
  - keep Excel smoke fixtures and formula-table processing examples in an
    active fixture/review-package location.
- Move useful tests from `mcp/sheets_bridge/test/` into `tests/` only when they
  verify processing behavior without MCP server, OAuth, broker, Chrome, or
  remote-host authority.

Done when:

- Processing behavior formerly mixed into `mcp/sheets_bridge/` is either
  preserved in an active neutral location or classified as access/runtime-only.
- Table-builder schemas/tests are split into processing contracts and
  runtime-host records.
- Any remaining table-builder contract title, `$id`, test name, or fixture path
  matches the processing-only direction.
- `mcp/` can be deleted without losing Excel/table-builder processing behavior.

### Phase 2: Spreadsheet Evidence Input Boundary

Goal: change Google Sheets processing from broker/API ownership to evidence
processing before removing runtime directories.

Actions:

- Define the accepted connected-sheet processing inputs:
  - Day1 MCP `sheets_read` result;
  - Day1 MCP `sheets_analyze_structure` result;
  - Day1 MCP write/readback result;
  - existing review package JSON;
  - local exported evidence files;
  - Excel workbook files.
- Remove live broker execution from active scripts.
- Delete or isolate `scripts/google_sheets_broker_client.py`.
- Rework scripts such as `scripts/google_sheets_bounded_window_sample.py` and
  `scripts/google_sheets_validation_batch_execution.py` so they accept local
  Day1 MCP result/evidence artifacts, or move them to `development-record/` if
  they only prove broker runtime behavior.
- Apply this canonical vocabulary map unless a file-specific review requires a
  different mapping:

| Current term | Processing-only term |
| --- | --- |
| `broker_read_plan` | `source_evidence_read_plan` |
| `broker_responses` | `source_evidence_results` |
| `broker_backed_read` | `evidence_backed_read` |
| `broker_bounded_sample` | `bounded_source_evidence` |
| `blocked_until_source_acl_and_broker_allowlist` | `blocked_until_source_access_evidence` |
| `required_broker_operations` | `required_source_evidence_operations` |
| `broker_policy` | `source_access_policy_evidence` |
| `broker_batch` | `source_evidence_batch` |

Done when:

- Spreadsheet processing scripts can run from local evidence artifacts.
- Scripts do not require local Google OAuth, Cloud Run broker, or direct Google
  API credentials.
- Day1 MCP remains the only live connected-Sheets access path.
- Active scripts do not expose `--broker-url`, `--execute` live broker modes,
  `DEFAULT_BROKER_URL`, or `gcloud auth print-identity-token`.
- Any vocabulary term that still contains `broker` is either historical content
  under `development-record/` or a blocking finding.

Current Phase 2 implementation note:

- `scripts/google_sheets_source_evidence.py` is the active source-evidence
  request/result normalization helper.
- `scripts/google_sheets_bounded_window_sample.py` and
  `scripts/google_sheets_validation_batch_execution.py` consume
  `source_evidence_results` directly or from `--source-evidence-results`.
- `scripts/google_sheets_broker_client.py` is absent from active scripts.

### Phase 3: Runtime Directory Removal

Goal: remove access/runtime code from this repository after useful processing
assets have been extracted.

Actions:

- Before deletion, run:

```bash
rg -n "mcp-sheets-bridge-design|mcp-sheets-bridge-remote-auth-runbook|table-builder-host-message|table-builder-session|test_table_builder_host_adapter_js|ui://sheets-bridge|mcp/sheets_bridge|packaging/sheets-bridge-mcp|PYTHONPATH=mcp" \
  --glob '!docs/spreadsheet-processing-scope-cleanup-plan.md' \
  --glob '!development-record/**' \
  scripts tests schemas docs references README.md SKILL.md AGENTS.md CLAUDE.md IMPLEMENTATION_MAP.html
```

- Rehome or resolve any processing-owned match before deleting runtime
  directories.
- Remove `mcp/`.
- Remove `packaging/sheets-bridge-mcp/`.
- Remove `broker/cloud-run-sheets-broker/`.
- Keep already-deleted `cli/sheets-bridge/`, `extension/chrome-sheets-bridge/`,
  and `native-host/` deleted.
- Phase 3 execution recorded on 2026-06-25:
  - `mcp/` moved to
    `development-record/retired-sheets-bridge/runtime/mcp/`.
  - `broker/cloud-run-sheets-broker/` moved to
    `development-record/retired-sheets-bridge/runtime/cloud-run-sheets-broker/`.
  - `packaging/sheets-bridge-mcp/` removed from the active tree.
  - empty `broker/` and `packaging/` containers were removed.

Done when:

- The pre-deletion active reference grep returns no matches.
- No active code path exposes a local Sheets Bridge MCP server.
- No active code path owns Google OAuth or Cloud Run broker behavior.
- No active package builds an MCP runtime from this repo.
- These paths are absent from the active tree:
  - `mcp/`
  - `packaging/sheets-bridge-mcp/`
  - `broker/cloud-run-sheets-broker/`
  - `cli/sheets-bridge/`
  - `extension/chrome-sheets-bridge/`
  - `native-host/`

### Phase 4: Historical Records Isolation

Goal: preserve useful history without active-runtime authority.

Actions:

- Move useful historical docs and evidence into
  `development-record/retired-sheets-bridge/`.
- Already-isolated records:
  - `development-record/retired-sheets-bridge/docs/mcp-sheets-bridge-design.md`
  - `development-record/retired-sheets-bridge/docs/mcp-sheets-bridge-remote-auth-runbook.md`
  - `development-record/retired-sheets-bridge/docs/workload-identity-runtime-contract.md`
  - `development-record/retired-sheets-bridge/schemas/table-builder-host-message.schema.json`
  - `development-record/retired-sheets-bridge/schemas/table-builder-session.schema.json`
  - `development-record/retired-sheets-bridge/tests/test_table_builder_host_adapter_js.py`
  - `development-record/retired-sheets-bridge/runtime/mcp/`
  - `development-record/retired-sheets-bridge/runtime/cloud-run-sheets-broker/`
- Move or remove retired runtime review packages.
- Move these docs out of active `docs/` unless rewritten as current Day1 MCP
  boundary notes:
  - `docs/mcp-sheets-bridge-design.md`
  - `docs/mcp-sheets-bridge-remote-auth-runbook.md`
  - `docs/workload-identity-runtime-contract.md`
  - access-runtime portions of `docs/google-sheets-parser-permission-requirements.md`
- Keep active docs free of default references to historical runtime designs.

Done when:

- `docs/` contains current processing designs and ADRs only.
- `development-record/retired-sheets-bridge/` contains useful historical
  context.
- Active runtime code and docs do not depend on `development-record/`.

### Phase 5: Schema And Test Cleanup

Goal: keep only processing contracts and tests.

Actions:

- Remove or relocate MCP/App host adapter schemas/tests that no longer support
  current processing.
- Keep neutral table-builder schemas/tests only when they support Excel workbook
  or spreadsheet result-table processing without defining access authority.
- Keep workbook schemas/tests.
- Keep spreadsheet evidence, claim, ontology, dataflow, and validation
  schemas/tests after renaming access-runtime terms.
- Re-evaluate `apply-result.schema.json`, `edit-plan.schema.json`, and
  `inspection.schema.json` under the processing-only model. Their default action
  is `delete` or `move_to_development_record`; keep them only if they become
  Day1 MCP result evidence snapshot validators rather than canonical write-gate
  contracts.

Done when:

- `python3 -m unittest discover -s tests` runs against the remaining processing
  surface.
- Test names and schema titles match current product direction.
- JSON schema `$id` and `title` fields do not name Sheets Bridge or local MCP
  runtime for active contracts.

### Phase 6: Review Package Cleanup

Goal: keep review packages that support current processing examples.

Actions:

- Keep workbook-understanding packages and current spreadsheet-processing
  examples.
- Move or remove packages that only prove retired access runtime behavior.
- Split `review-packages/spreadsheet-table-builder/` by content:
  - keep Excel formula-table smoke outputs and processing fixtures;
  - move host adapter, MCP/App, ChatGPT web, and access-runtime smoke evidence to
    `development-record/retired-sheets-bridge/` or remove it.
- Classify each top-level folder under `review-packages/sheets-bridge/` before
  moving or deleting it.
- Keep generated artifacts out of active docs unless they are current fixtures
  or examples.
- Phase 6 execution recorded on 2026-06-26:
  - Google Sheets test fixtures moved from
    `review-packages/sheets-bridge/live-inspections/test-*` to
    `review-packages/spreadsheet-processing/live-inspections/test-*`.
  - Runtime-coupled review packages moved to
    `development-record/retired-sheets-bridge/review-packages/`.
  - Tracked managed-deployment evidence from
    `review-packages/sheets-bridge/managed-deployment/` restored from git into
    `development-record/retired-sheets-bridge/review-packages/sheets-bridge/managed-deployment/`.
  - `review-packages/spreadsheet-table-builder/` moved to records because its
    package manifests and handoff files describe the retired host runtime.
  - `review-packages/workbook-understanding/process-ledger.jsonl` moved to
    `development-record/workbook-understanding/process-ledger.jsonl`.
  - Active `review-packages/` now contains current fixture/evidence surfaces
    only: `spreadsheet-processing/live-inspections/test-*` and
    `workbook-understanding/`.

Done when:

- `review-packages/` contains current evidence/review examples.
- Retired runtime evidence is in `development-record/` or removed.
- The baseline classification manifest explains every moved or deleted review
  package folder.

### Phase 7: Verification

Goal: prove the repository still works as a processing skill.

Run:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile scripts/*.py
```

Confirm removed runtime directories are absent:

```bash
test ! -e mcp
test ! -e packaging/sheets-bridge-mcp
test ! -e broker/cloud-run-sheets-broker
test ! -e cli/sheets-bridge
test ! -e extension/chrome-sheets-bridge
test ! -e native-host
```

Confirm active scripts and contracts do not contain direct access-runtime hooks:

```bash
rg -n "DEFAULT_BROKER_URL|X-Broker-Authorization|gcloud auth print-identity-token|urlopen\\(|googleapiclient|google\\.auth|sheets_bridge|mcp/sheets_bridge|spreadsheet_table_builder" \
  --glob '!docs/spreadsheet-processing-scope-cleanup-plan.md' \
  --glob '!development-record/**' \
  scripts schemas tests docs references README.md SKILL.md AGENTS.md CLAUDE.md IMPLEMENTATION_MAP.html
```

Also run:

```bash
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
HTMLParser().feed(Path("IMPLEMENTATION_MAP.html").read_text())
print("implementation map html ok")
PY
```

When schemas change, parse every JSON schema:

```bash
python3 - <<'PY'
import json
from pathlib import Path
for path in sorted(Path("schemas").glob("*.json")):
    json.loads(path.read_text())
print("schemas json ok")
PY
```

Done when:

- Remaining tests pass.
- Changed scripts compile.
- Active docs and implementation map parse.
- No active docs describe this repository as a Google access runtime.
- No active script, schema, test, or doc exposes local OAuth, direct Google API,
  Cloud Run broker, Chrome extension, native host, local Sheets Bridge MCP, or
  MCP packaging behavior as this repository's responsibility.

## Stop Conditions

Stop and ask before continuing if:

- `cleanup-classification.tsv` has an unclassified path that would be touched by
  the current phase.
- A file or test appears to mix processing logic with access-runtime behavior in
  a way that cannot be safely split.
- Removing a runtime directory breaks a processing script that cannot be
  converted to artifact input in the same phase.
- A schema appears to be used by both retired runtime behavior and current
  processing behavior.
- Review packages are the only example fixtures for a current processing path.
- The cleanup would delete user-provided evidence or project continuity files
  under `projects/`.
- Day1 MCP availability is required for the current phase but the active host
  does not expose Day1 MCP tools.

## Goal Setup Additions

A cleanup goal should include these fields so a new Codex session can execute
without rediscovering the whole history.

### Objective

Clean up `excel-workbook-editing` so it no longer owns Google Sheets access,
MCP server runtime, Cloud Run broker runtime, Chrome extension runtime, native
host runtime, or MCP packaging. Keep and verify only Excel/spreadsheet
processing code, docs, schemas, tests, references, and review-package examples.

### Required Context

- Day1 MCP is installed in the active environment and owns Google Drive/Sheets
  access.
- Current useful Day1 MCP tools include `drive_list`, `sheets_read`,
  `sheets_analyze_structure`, `sheets_preview_write`,
  `sheets_update_values`, `sheets_update_formulas`,
  `sheets_create_table_sheet`, `sheets_append_rows`,
  `sheets_set_data_validation`, `sheets_repeat_cell_format`,
  `sheets_insert_dimension`, and `sheets_delete_dimension`.
- This repo should process files and Day1 MCP evidence/results, not call Google
  APIs directly.
- Historical runtime records belong in `development-record/`; active docs and
  code should not depend on them.
- The current working tree contains tracked, deleted, modified, and untracked
  assets. Classify untracked assets before destructive cleanup.
- Some useful Excel/table-builder processing logic may currently live under
  `mcp/sheets_bridge/`; extract or merge that logic before deleting `mcp/`.

### In-Scope Work

- Update active docs and references.
- Create the Phase 0 baseline and classification manifest.
- Split useful processing logic from local MCP/App host runtime code.
- Remove retired access/runtime directories and tests.
- Rework processing scripts and schemas to accept evidence artifacts instead of
  broker/runtime inputs.
- Keep Excel workbook processing fully functional.
- Keep connected-sheet processing as artifact/evidence processing.
- Update `IMPLEMENTATION_MAP.html`.
- Run the verification gates in this plan.

### Out-Of-Scope Work

- Do not implement or modify Day1 MCP.
- Do not add a new MCP server to this repository.
- Do not add Google OAuth, service-account, Cloud Run broker, Chrome extension,
  native-host, or local CLI access runtime here.
- Do not delete processing examples or project continuity files without
  classifying them.
- Do not attempt live spreadsheet writes as part of cleanup verification.

### Completion Criteria

- Active docs present Day1 MCP as the Google access authority.
- Active docs present this repository as the Excel/spreadsheet processing
  authority.
- Phase 0 baseline files exist under
  `development-record/scope-cleanup-baseline/<YYYYMMDD>/`.
- `cleanup-classification.tsv` classifies every removed, moved, or reworked
  runtime/review-package path.
- Useful Excel/table-builder processing behavior from `mcp/sheets_bridge/` is
  preserved in active neutral locations or explicitly classified as
  access/runtime-only.
- Runtime directories for Sheets Bridge MCP, broker, Chrome extension,
  native-host, and local CLI access are absent from active code.
- Remaining scripts/tests/schemas are processing-focused.
- Remaining tests and compile checks pass.
- `rg` over active docs/code shows no active instruction to continue the
  retired runtime.

Suggested final grep:

```bash
rg -n "Sheets Bridge MCP|mcp-sheets-bridge|chrome-sheets-bridge|native-host|Cloud Run Sheets broker|local OAuth token cache|MCP-managed local OAuth|broker|Chrome|native messaging|remote MCP|Google Sheets API|connector/API|sheets_bridge|mcp/sheets_bridge|spreadsheet_table_builder|workload-identity|packaging/sheets-bridge|DEFAULT_BROKER_URL|gcloud auth print-identity-token|googleapiclient|google\\.auth" \
  --glob '!docs/spreadsheet-processing-scope-cleanup-plan.md' \
  --glob '!development-record/**' \
  AGENTS.md CLAUDE.md README.md SKILL.md IMPLEMENTATION_MAP.html docs references scripts schemas tests
```

Any remaining match must be either:

- historical content under `development-record/`; or
- a deliberately renamed processing concept; or
- a finding to resolve before completion.

### Suggested Goal Prompt

```text
Use /Users/kangmin/Documents/excel-workbook-editing/docs/spreadsheet-processing-scope-cleanup-plan.md as the cleanup authority.

Goal: clean up excel-workbook-editing so the active repository is an Excel/spreadsheet processing skill only. Day1 MCP owns Google Drive/Sheets access, auth, policy, write gates, and Google API calls. Remove retired local Sheets Bridge MCP, Cloud Run broker, Chrome extension, native-host, local CLI access, and MCP packaging from active runtime. Preserve and verify workbook/spreadsheet processing code, schemas, docs, references, review-package examples, and tests.

Proceed phase by phase from the cleanup plan. Start with Phase 0 baseline and cleanup-classification.tsv. Before deleting mcp/, split useful Excel/table-builder processing logic from MCP/App host runtime behavior. For each phase, make the smallest safe edits, keep historical records only under development-record/, update IMPLEMENTATION_MAP.html when architecture changes, and run the verification gates. Stop on any condition listed in the Stop Conditions section above, especially if a processing artifact would be lost, an untracked asset is unclassified, Day1 MCP is required but unavailable, or a runtime/processing boundary cannot be classified safely.
```

### Recommended First Goal Slice

For a safer first session, start with Phase 0 and Phase 1 only:

```text
Work in /Users/kangmin/Documents/excel-workbook-editing. Use /Users/kangmin/Documents/excel-workbook-editing/docs/spreadsheet-processing-scope-cleanup-plan.md. Execute Phase 0 and Phase 1 only. Create development-record/scope-cleanup-baseline/<YYYYMMDD>/ with git status, untracked file inventory, runtime file inventory, active runtime reference grep, and cleanup-classification.tsv. Then realign AGENTS.md, CLAUDE.md, README.md, SKILL.md, IMPLEMENTATION_MAP.html, active processing docs, ADR 0002, and connected spreadsheet references so Day1 MCP is the Google access authority and this repo is the processing authority. Do not delete runtime directories in this slice. Verify docs and report remaining runtime references.
```
