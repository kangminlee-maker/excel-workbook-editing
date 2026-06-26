# MCP Sheets Bridge Design

## Purpose

MCP Sheets Bridge is the active connected Google Sheets access path for this
repository. Its user-facing surface is the MCP tool interface used by Claude
Desktop, ChatGPT web remote MCP apps, Codex, and other MCP-capable agents.

The bridge reads existing Google Sheets in place through local user OAuth,
preserves live spreadsheet identity, and writes sanitized local evidence
packages for repeatable agent review.

## Runtime Shape

```text
Desktop MCP client
  -> Sheets Bridge MCP stdio server
  -> local user OAuth token cache
  -> Google Sheets API
  -> sanitized local review package
  -> MCP structured result
```

Remote web MCP clients use the same semantic tool contract through an HTTPS MCP
endpoint:

```text
ChatGPT web or another remote MCP host
  -> HTTPS remote MCP endpoint
  -> user/session authorization boundary
  -> Sheets Bridge service layer
  -> Google Sheets API or approved spreadsheet runtime
  -> sanitized evidence/result package
  -> MCP structured result + optional app UI resource
```

Remote web hosts use remote spreadsheet authority. Local Excel file mutation,
desktop Excel recalculation, and local OAuth cache access are desktop-runtime
capabilities, with explicit local-runtime or uploaded-artifact workflows when a
web host needs them.

Optional current-tab convenience:

```text
MCP tool
  -> Chrome remote debugging endpoint
  -> current Google Sheets URL + gid + name-box range
  -> Google Sheets API through local OAuth
```

Chrome remote debugging reads visible browser context only: URL, `gid`, and
name-box range. Credential authority stays in MCP OAuth tools.

## Active Interfaces

| Interface | Role |
| --- | --- |
| MCP stdio server | Primary interface for desktop AI apps and agents. |
| MCP OAuth tools | Configure local OAuth client metadata, start login, report auth status, and logout with credential-free model-visible results. |
| MCP inspect tool | Read metadata, values, formulas, or grid windows and write sanitized packages. |
| MCP values apply tools | Apply or restore bounded USER_ENTERED values/formulas with before snapshots, readback, and rollback objects. |
| MCP table I/O visualization tool | Analyze a bounded table range and write a sanitized HTML/SVG package that shows source tabs, formula surfaces, output tables, and refactor candidates. |
| MCP minimal-formula refactor tool | For supported table patterns, create a new projection sheet with fewer formula anchors, validate it against the original output table, and return a deletion-based rollback path. |
| Generic spreadsheet table builder UI tool | Create a local spreadsheet-like HTML UI where the user sketches the desired output table and writes the LLM request prompt, using a Google Sheet or Excel workbook preview as source evidence. |
| Shared spreadsheet table-builder UI bundle | Canonical spreadsheet-like web UI for sketching desired output tables, entering the user's LLM prompt, previewing source evidence, and submitting a `TableBuildIntent`. |
| Table-builder host adapters | Thin host-specific bridges for Claude MCP Apps, ChatGPT web remote MCP/Apps SDK, and standalone local web tests. Host adapters translate messages and tool calls; spreadsheet semantics stay in MCP tools and canonical artifacts. |
| Remote session provider | HTTP runtime authority provider that maps a remote session handle to sanitized user/session metadata, granted scopes, expiry, and the internal access token used for Google API calls. |
| Generic spreadsheet formula table creation tool | Convert a table-builder spec into a new auditable sheet inside the target artifact or a workbook copy, depending on `output.creation_mode`. |
| Generic spreadsheet structure rollback tool | Execute table-builder rollback instructions for created Sheets tabs, copied Google spreadsheets, Excel workbook copies, or Excel worksheets. |
| Excel formula result validation tool | Run workbook-wide static formula-error checks and optionally sample formula results through the real Microsoft Excel engine. |
| Chrome remote resolver | Optional helper to read the current Sheets URL, `gid`, and selected A1 range from `#t-name-box`. |
| Local review package | Durable sanitized handoff artifact for repeatable analysis. |

## MCP Tool Contract

| Tool | Behavior |
| --- | --- |
| `sheets_bridge_auth_status` | Reports local OAuth configured/authenticated state with credential-free output. |
| `sheets_bridge_configure_oauth` | Stores local Google OAuth desktop client metadata outside the repo. `access=readonly` grants read-only Sheets access, `access=readwrite` grants Sheets writes, `access=copy` grants Sheets writes plus Drive `drive.file` per-file copy/delete access, and `access=copy_full` grants Sheets writes plus full Drive copy/delete authority for arbitrary user-accessible source files. |
| `sheets_bridge_start_oauth_login` | Opens the Google OAuth consent flow and waits for the local callback. |
| `sheets_bridge_logout` | Deletes the local OAuth token cache. |
| `sheets_bridge_current_chrome_sheet` | Reads current Sheets tab context through Chrome remote debugging. |
| `sheets_bridge_inspect` | Reads metadata, values, formulas, or grid windows through user OAuth and writes a sanitized package. |
| `sheets_bridge_apply_values_update` | Applies bounded values/formulas through `values:batchUpdate`, captures before state, reads back after state, and returns a rollback object. |
| `sheets_bridge_rollback_values_restore` | Restores values/formulas from a rollback object generated by Sheets Bridge and creates a new inverse rollback object. |
| `sheets_bridge_visualize_table_io` | Reads a bounded range, detects table/formula/source-reference structure, and emits `analysis.json`, `table-io-flow.svg`, `index.html`, `manifest.json`, and `mcp-handoff.json`. |
| `sheets_bridge_refactor_minimal_formula_sheet` | Creates a new minimal-formula projection sheet for `monthly_product_performance_v1`, copies source-output formatting, writes formula anchors, validates `A5:AQ129` by default, and returns the created-sheet deletion rollback instruction. |
| `spreadsheet_table_builder_ui` | Reads a bounded source range from Google Sheets or an Excel workbook and emits an interactive builder for sketching the output table, writing `llm_prompt`, optionally pointing to source evidence, and choosing output target metadata. Desktop Google Sheets source reads use the MCP-managed local OAuth token cache; remote hosts use their approved remote session authority. |
| `spreadsheet_table_builder_save_intent` | App-only write tool used by the MCP Apps UI to persist a submitted `TableBuildIntent` and send the saved intent path back into the host conversation for plan generation. |
| `spreadsheet_create_formula_table_from_spec` | Reads a validated formula-table apply spec generated from an approved `TableBuildPlan`, creates a new sheet inside the target Google spreadsheet, Excel workbook, or Excel workbook copy, writes labels and formula cells, validates the supported runtime surface, and returns a rollback instruction. |
| `spreadsheet_rollback_created_artifact` | Executes rollback instructions returned by table-builder and minimal-formula creation paths: delete a created Sheets tab, delete a copied Google spreadsheet, delete an Excel workbook copy, or remove a created Excel worksheet. |
| `spreadsheet_validate_excel_formula_results` | Runs static formula/error scanning for an Excel workbook and, when requested, calls `scripts/excel_engine_sample.py` to sample selected cells through the real Microsoft Excel engine. |

All tool outputs are credential-free and expose sanitized evidence only.

Example visualization call:

```json
{
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/<spreadsheet-id>/edit#gid=<gid>",
  "target_range": "A1:AQ129",
  "pattern": "auto"
}
```

Example minimal-formula refactor dry run:

```json
{
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/<spreadsheet-id>/edit#gid=<gid>",
  "validation_range": "A5:AQ129",
  "dry_run": true
}
```

Live refactor uses the same arguments with `dry_run=false` or omitted. It
creates a new sheet rather than changing the original output tab.

Example table-builder UI call:

```json
{
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/<spreadsheet-id>/edit#gid=<gid>",
  "source_range": "A1:Z200"
}
```

Excel workbook UI calls use the same tool with a local workbook path:

```json
{
  "workbook_path": "/path/to/workbook.xlsx",
  "sheet_name": "Raw",
  "source_range": "A1:Z200"
}
```

The generated HTML uses `spreadsheet_table_builder_save_intent` as the accepted
submission path in MCP Apps mode. Standalone local HTML may expose a diagnostic
export for troubleshooting; write authority begins after the MCP server
validates and persists the submitted intent.

An initial submitted intent looks like:

```json
{
  "schema_version": "1.0",
  "intent_kind": "table_build_intent_v1",
  "source": {
    "artifact_type": "google_sheets",
    "spreadsheet_id": "<spreadsheet-id>",
    "sheet_title": "Raw",
    "qualified_range": "'Raw'!A1:Z200"
  },
  "source_package": {
    "manifest_path": "review-packages/spreadsheet-table-builder/mcp/2026-06-08/<request-id>/manifest.json",
    "source_path": "review-packages/spreadsheet-table-builder/mcp/2026-06-08/<request-id>/builder-source.json"
  },
  "artifact_type": "google_sheets",
  "output_canvas": [
    ["", "2026-01", "2026-02"],
    ["Team A", "", ""],
    ["Team B", "", ""]
  ],
  "llm_prompt": "원본 데이터 안에서 팀별 월별 매출 합계를 수식으로 계산하는 새 표를 만들어줘.",
  "source_hints": {
    "selected_ranges": ["'Raw'!A1:Z200"]
  },
  "output": {
    "creation_mode": "sheet",
    "preferred_title": "MCP_TABLE_RESULT"
  },
  "review_state": {
    "status": "submitted",
    "next_action": "Generate a TableBuildPlan from this intent and ask the user to confirm the interpreted table shape."
  }
}
```

The host LLM interprets the saved intent and source evidence into a
`TableBuildPlan`. The plan is shown to the user before any write:

```json
{
  "schema_version": "1.0",
  "plan_kind": "table_build_plan_v1",
  "intent_ref": "review-packages/spreadsheet-table-builder/intents/<request-id>/intent.json",
  "interpreted_output_shape": {
    "rows": ["Team A", "Team B"],
    "columns": ["2026-01", "2026-02"],
    "measure": "매출 합계"
  },
  "source_evidence_needed": [
    {"range": "'Raw'!A1:Z200", "purpose": "팀, 월, 매출 후보 열 확인"}
  ],
  "formula_strategy": {
    "summary": "팀과 월 조건으로 원본 매출 열을 집계하는 source-referencing formulas",
    "risk_annotations": []
  },
  "target": {
    "artifact_type": "google_sheets",
    "creation_mode": "sheet",
    "sheet_title": "MCP_TABLE_RESULT"
  },
  "validation_plan": {
    "readback": "created sheet formatted values and formulas",
    "compare_against": "source aggregate spot checks where deterministic"
  },
  "rollback_plan": {
    "kind": "delete_created_sheet"
  },
  "unresolved_questions": []
}
```

Only after explicit user confirmation does the MCP server create an approved
formula-table apply spec. A Google Sheets apply spec created from the plan may
look like:

```json
{
  "spec": {
    "schema_version": "1.0",
    "spec_kind": "formula_table_apply_v1",
    "plan_ref": "review-packages/spreadsheet-table-builder/plans/<request-id>/plan.json",
    "artifact_type": "google_sheets",
    "spreadsheet_id": "<spreadsheet-id>",
    "source": {
      "artifact_type": "google_sheets",
      "spreadsheet_id": "<spreadsheet-id>",
      "sheet_title": "Raw",
      "qualified_range": "'Raw'!A1:Z200",
      "header_row": 1
    },
    "fields": {
      "row_label": {"column": "A", "header": "Team"},
      "column_label": {"column": "B", "header": "Month"},
      "measure": {"column": "C", "header": "Revenue"}
    },
    "formula": {
      "template": "=IFERROR(SUMIFS({measure_range},{row_label_range},{row_label_cell},{column_label_range},{column_label_cell}),0)"
    },
    "output": {
      "sheet_title": "MCP_TABLE_RESULT",
      "title": "Team by Month",
      "creation_mode": "sheet",
      "format": {
        "header_bold": true,
        "freeze_header_rows": 2,
        "auto_resize_columns": true,
        "protect_created_sheet": false
      }
    }
  },
  "dry_run": true
}
```

The same apply spec supports `output.creation_mode=copy` for Google Sheets when
Drive authority is configured. It supports Excel workbook targets with
`artifact_type=excel_workbook`; Excel defaults to `creation_mode=copy`:

```json
{
  "spec": {
    "schema_version": "1.0",
    "spec_kind": "formula_table_apply_v1",
    "plan_ref": "review-packages/spreadsheet-table-builder/plans/<request-id>/plan.json",
    "artifact_type": "excel_workbook",
    "source": {
      "artifact_type": "excel_workbook",
      "workbook_path": "/path/to/source.xlsx",
      "sheet_title": "Raw",
      "qualified_range": "'Raw'!A1:Z200",
      "header_row": 1
    },
    "fields": {
      "row_label": {"column": "A", "header": "Team"},
      "column_label": {"column": "B", "header": "Month"},
      "measure": {"column": "C", "header": "Revenue"}
    },
    "formula": {
      "template": "=IFERROR(SUMIFS({measure_range},{row_label_range},{row_label_cell},{column_label_range},{column_label_cell}),0)"
    },
    "output": {
      "sheet_title": "MCP_TABLE_RESULT",
      "title": "Team by Month",
      "creation_mode": "copy",
      "workbook_path": "/path/to/source-formula-table.xlsx",
      "format": {
        "header_bold": true,
        "freeze_header_rows": 2,
        "auto_resize_columns": true,
        "protect_created_sheet": false
      }
    }
  },
  "dry_run": true
}
```

Live creation uses the approved apply spec with `dry_run=false` or omitted.
`output.creation_mode` accepts `copy` or `sheet`. Defaults are `sheet` for
Google Sheets and `copy` for Excel workbooks. Google Sheets `sheet` creates a
new tab in the source spreadsheet. Google Sheets `copy` first creates a Drive
copy of the spreadsheet, then writes the formula table into the copy. Excel
`copy` creates a workbook copy and adds the new worksheet there. Excel `sheet`
opens the target workbook file and adds a new worksheet inside that workbook.
In all modes, output cells use spreadsheet formulas and source references.
Spreadsheet engines calculate output values.

For Excel `copy`, the writer is selected by workbook size and local runtime.
Small workbooks use deterministic `openpyxl` sheet creation. Large workbooks
default to desktop Excel automation so the original workbook structures,
pivot caches, external-link parts, styles, and calculation metadata are
preserved by Excel itself rather than by a full Python workbook round-trip.
macOS uses AppleScript through `osascript`; Windows uses PowerShell with Excel
COM Automation. The engine can be overridden with
`SHEETS_BRIDGE_EXCEL_WRITE_ENGINE=auto|openpyxl|desktop`.

## OAuth Authority

The user authorizes a Google OAuth desktop client locally. Tokens are stored
outside the repo under the OS user config area with private file permissions.

Default read scope:

```text
https://www.googleapis.com/auth/spreadsheets.readonly
```

Values apply and rollback require explicit `readwrite` OAuth configuration and
login:

```text
https://www.googleapis.com/auth/spreadsheets
```

Google Sheets copy mode has two OAuth authority levels. Prefer
`access=copy` when the source file is app-created or explicitly selected/shared
with the app through a file-picker style flow:

```text
https://www.googleapis.com/auth/spreadsheets
https://www.googleapis.com/auth/drive.file
```

Use `access=copy_full` when the bridge copies arbitrary user-accessible
spreadsheets through full Drive authority:

```text
https://www.googleapis.com/auth/spreadsheets
https://www.googleapis.com/auth/drive
```

`drive.file` is the preferred least-privilege Drive scope, and it grants
per-file authority. Full `drive` is a restricted scope used when copying
arbitrary user-accessible source spreadsheets is a required product behavior.
Read-only OAuth tokens are rejected before write attempts, and read/write-only
OAuth tokens are rejected before Drive copy/delete attempts.

## Package Contract

Each inspect/apply/values-rollback call writes:

```text
review-packages/sheets-bridge/mcp/<YYYY-MM-DD>/<request-id>/
  snapshot.json
  manifest.json
  mcp-handoff.json
```

`snapshot.json` is the sanitized point-in-time read/apply/rollback model.
`manifest.json` is the package entrypoint.
`mcp-handoff.json` contains a ready prompt and boundaries for agents that read
the package later.

The package source is recorded as `mcp_user_oauth` for connected Google Sheets
inspect/apply/rollback packages. Review packages are evidence. Live spreadsheet
authority stays with Google Sheets readback, Excel recalculation, and explicit
MCP apply/rollback results.

Table I/O visualization writes the same manifest/handoff shape under:

```text
review-packages/sheets-bridge/mcp-table-io-flow/<YYYY-MM-DD>/<request-id>/
  analysis.json
  table-io-flow.svg
  index.html
  manifest.json
  mcp-handoff.json
```

Minimal-formula refactor results write:

```text
review-packages/sheets-bridge/mcp-refactor/<YYYY-MM-DD>/<request-id>/
  result.json
  index.html
  manifest.json
  mcp-handoff.json
```

Table-builder UI and formula-table results write under:

```text
review-packages/spreadsheet-table-builder/mcp/<YYYY-MM-DD>/<request-id>/
  index.html
  builder-source.json or result.json
  manifest.json
  mcp-handoff.json
```

Those table-builder packages record `source: mcp_spreadsheet_table_builder`
because they may originate from user OAuth Google Sheets reads or local Excel
workbook reads.

`spreadsheet_rollback_created_artifact` returns a structured rollback result.
The creation result package remains the durable artifact that contains the
rollback instruction being executed.

For apply results, `snapshot.json` contains:

- requested write ranges and USER_ENTERED values/formulas;
- before values read with `valueRenderOption=FORMULA`;
- after readback values read with `valueRenderOption=FORMULA`;
- rollback instructions as `rollback.values_restore` write requests.

## Values Apply Boundaries

- Only `values:batchUpdate` with `USER_ENTERED` is in scope.
- `sheets_bridge_apply_values_update` requires `rollback_required=true`.
- Write ranges must be bounded A1 ranges and values must exactly match range
  dimensions.
- Rollback restores the captured formulas/values. Formatting, comments,
  protections, validation rules, charts, filters, Apps Script state, and
  external system side effects belong to explicit structure-aware workflows.
- Structural edits, tab deletion, row/column deletion, formatting writes, and
  Apps Script mutation are outside the values apply surface. Created-artifact
  deletion is available only through the separate explicit structure rollback
  tool.

## Table I/O Visualization Boundaries

- `sheets_bridge_visualize_table_io` is read-only.
- The tool reads a bounded range only. If no `target_range` is supplied, it
  caps the inspected window with `max_rows` and `max_columns` to reduce timeout
  risk.
- The output is an explanation package. Write plan authority comes from explicit
  MCP plan/apply artifacts.
- The first supported refactor pattern is
  `monthly_product_performance_v1`, which covers the observed product
  performance sheet shape with a product dimension area, daily revenue matrix,
  revenue/ad-spend/CAC KPI area, and SKU/ad-spend source tabs.

## Minimal-Formula Refactor Boundaries

- `sheets_bridge_refactor_minimal_formula_sheet` requires the read/write Sheets
  OAuth scope.
- The tool creates a new sheet and copies formatting from the original output
  range before writing formulas. The original output tab remains the comparison
  source.
- The active implementation supports only
  `monthly_product_performance_v1`. Unsupported sheets must be visualized and
  designed first.
- The default validation compares formatted values from the original output
  table and new projection table over `A5:AQ129`, retries while formulas settle,
  and reports mismatch/error samples.
- Rollback is deletion of the created projection sheet. The refactor tool
  returns this instruction, and `spreadsheet_rollback_created_artifact` can
  execute it when the user or agent explicitly calls the rollback tool.
- `dry_run=true` returns the planned structural/write request counts and writes
  a result package with Google write APIs idle.

## Shared Table-Builder UI Architecture

The table-builder UI is a single shared web surface with host-specific adapters.
The user-facing workflow is the same in every host:

1. Load a sanitized source preview from a Google Sheet or Excel workbook.
2. Let the user sketch the desired output table directly in a spreadsheet-like
   canvas.
3. Let the user write the prompt they want the LLM to follow.
4. Save the submitted sketch and prompt as a durable `TableBuildIntent`.
5. Ask the host LLM to interpret the intent into a `TableBuildPlan` and show
   the plan back to the user before any write/apply action.

The shared UI owns only interaction state. Spreadsheet authority remains in the
source artifact, sanitized evidence packages, live API readback, Excel
recalculation, and explicit apply/rollback tool results.

```text
Shared Table Builder UI
  -> reads host-provided sanitized source preview
  -> captures output_canvas + llm_prompt + optional source hints
  -> emits TableBuildIntentSubmitted

Host Adapter
  -> Claude MCP Apps adapter
  -> ChatGPT web remote MCP / Apps SDK adapter
  -> standalone local web test adapter

Sheets Bridge Tools
  -> save intent
  -> generate/confirm plan through host LLM
  -> create formula-only table
  -> validate readback/recalculation
  -> rollback only on explicit call
```

Host adapter responsibilities are deliberately narrow:

- provide the initial `app_source` payload from `spreadsheet_table_builder_ui`;
- translate UI submit events into `spreadsheet_table_builder_save_intent`;
- pass the saved intent path and normalized intent back into the host
  conversation;
- fetch UI resources through the host's MCP resource mechanism;
- surface errors, timeouts, and host capability gaps while preserving the saved
  intent contract.

Host adapter authority boundaries:

- formula generation belongs to `TableBuildPlan` and approved apply specs;
- output values belong to spreadsheet engines and readback/recalculation;
- credential authority belongs to MCP OAuth or approved remote session storage;
- Google Sheets and Excel mutations go through explicit MCP
  apply/create/rollback tools;
- spreadsheet truth stays in source artifacts, sanitized packages, validation
  packages, and rollback objects.

Claude Desktop currently uses the local stdio MCP server and the MCP Apps
resource `ui://sheets-bridge/table-builder`. ChatGPT web uses remote MCP/App
registration, so it requires an HTTPS MCP endpoint or approved secure tunnel.
Both hosts should render the same shared UI bundle and submit the same
`TableBuildIntent` shape.

UI runtime choices are evaluated by how well they support the accepted
`TableBuildIntent` flow:

| UI choice | Product fit |
| --- | --- |
| Host-neutral MCP Apps HTML resource | Default delivery surface. Works as a shared iframe-style UI for Claude MCP Apps, ChatGPT web remote MCP/App flows, and standalone local tests. |
| Purpose-built spreadsheet canvas | Default interaction model. Users sketch the desired result table directly, add plain-language instructions, and submit a bounded intent. |
| Third-party spreadsheet/grid engine | Candidate implementation detail for the canvas when it improves keyboard navigation, copy/paste, selection, resizing, accessibility, or performance without taking authority over formulas or writes. |

The canonical durable records remain `intent.json`, `manifest.json`, apply
result packages, validation packages, and explicit rollback objects.

## Table Builder Workbench UI Design

The shared table-builder UI is a workbench for describing a desired output
sheet. It is not the calculation authority and it is not a spreadsheet import
or export surface. The UI captures the user's sketch and request, then the MCP
runtime saves a validated `TableBuildIntent`. The host LLM uses that intent and
source evidence to produce a `TableBuildPlan` preview before any write tool can
run.

### UI Goal

The user should be able to open the table-builder, sketch the target table like
they would draw it in a blank spreadsheet, describe the desired calculation in
plain language, and ask the AI to confirm its understanding.

The UI is complete when a non-technical user can do these steps without knowing
schema names, JSON, formula placeholders, MCP tool names, or OAuth details:

1. See which workbook or spreadsheet is connected.
2. Draw the output table's visible shape in a spreadsheet-like canvas.
3. Add a plain-language request for how the empty cells should be filled.
4. Optionally point to useful source evidence.
5. Save the request as a `TableBuildIntent`.
6. See the host LLM produce a `TableBuildPlan` preview with formula strategy,
   source evidence, validation, rollback, and unresolved questions.
7. Confirm the plan before the create/apply tool writes a new sheet or copy.

### Layout

The default desktop/fullscreen layout uses three workbench regions. Narrow
inline host views collapse the source evidence and plan preview into tabs while
keeping the output sketch first.

```text
┌────────────────────────────────────────────────────────────────────┐
│ Header: connected file, sheet/range summary, auth/runtime status    │
├─────────────────┬──────────────────────────────────┬───────────────┤
│ Source Evidence │ Output Sketch Canvas             │ AI Plan       │
│                 │                                  │ Preview       │
│ - tabs/ranges   │ - editable blank grid            │               │
│ - values/formula│ - row/column resize              │ - understood  │
│ - search/filter │ - paste from Sheets/Excel        │   shape       │
│ - evidence pins │ - add row/column controls        │ - sources     │
│                 │                                  │ - formulas    │
│                 │ User Request Prompt              │ - validation  │
│                 │ Output Target                    │ - rollback    │
├─────────────────┴──────────────────────────────────┴───────────────┤
│ Action Bar: save intent, request plan, confirm apply, open package  │
└────────────────────────────────────────────────────────────────────┘
```

#### Header

The header shows the current source in user-facing language:

- `연결된 문서`: workbook or spreadsheet title.
- `현재 원본`: sheet/tab and preview range.
- `작업 방식`: Google Sheets defaults to `새 시트 만들기`; Excel defaults to
  `파일 복사본에 만들기`.
- `상태`: authenticated, source preview ready, local runtime required, or
  remote session required.

The header must not expose tokens, credential paths, raw session handles, or
local filesystem paths in remote-host mode.

#### Source Evidence Panel

The source panel is optional evidence help, not a required form. The user can
ignore it and still submit a valid sketch and prompt.

Required source-panel behavior:

- Shows source tabs, visible preview ranges, and formula/value toggles when the
  source package contains them.
- Lets the user pin a cell, row, column, table, or formula range as a
  `source_hints` entry.
- Uses simple labels such as `이 열 참고`, `이 행 참고`, `이 수식 참고`,
  and `이 표 참고`.
- Supports search by visible text and formula text for loaded preview data.
- Marks preview limits clearly when only a bounded window is loaded.
- Offers `문서 전체를 근거로 사용` when the source package or remote authority
  can inspect more than the preview range.

Pinned source evidence becomes a hint only. The plan generator can use or
ignore hints based on the full source evidence and must explain material
differences in the `TableBuildPlan`.

#### Output Sketch Canvas

The output sketch canvas is the primary UI. It behaves like a small blank
spreadsheet, not like a form wizard.

Required canvas behavior:

- Starts focused on an editable blank grid.
- Accepts direct typing and paste from Google Sheets or Excel.
- Lets the user add rows and columns with visible `+` controls.
- Lets the user resize columns and rows when the host viewport allows it.
- Stores only visible text entered by the user in `output_canvas`.
- Treats blank cells as intentional unknowns for the AI to fill with formulas
  or references.
- Shows row/column labels for navigation but does not require users to mark
  "row label", "column label", or "measure" roles before submitting.
- Keeps formulas typed by the user as visible text in `output_canvas`; formula
  execution belongs to spreadsheet engines after plan approval.

The canvas may use a purpose-built grid implementation. A third-party grid
engine can replace the internal canvas only if it preserves the
`output_canvas` contract and improves keyboard navigation, paste behavior,
selection, accessibility, or large-canvas performance.

#### User Request Prompt

The prompt box label is `AI에게 요청할 내용`.

The prompt asks for the user's instruction to the AI, not for a formal formula
description. Placeholder text should stay plain:

```text
예: 위 표의 빈 칸에 월별 브랜드별 결제액 합계를 넣어줘.
원본의 취소 금액은 음수로 반영하고, 기존 시트의 수식과 참조만 사용해줘.
```

The prompt is saved as `llm_prompt` and remains semantic input. Runtime code
does not parse it as a formula language.

#### Output Target Controls

Output controls are shown as simple choices:

| User label | Internal value |
| --- | --- |
| `새 시트 만들기` | `creation_mode=sheet` |
| `파일 복사본에 만들기` | `creation_mode=copy` |

Default target behavior:

- Google Sheets defaults to `새 시트 만들기`.
- Excel workbooks default to `파일 복사본에 만들기`.
- Source-workbook sheet creation for Excel stays available only as an explicit
  selected option in local desktop runtime.
- Google spreadsheet copy mode appears when Drive copy authority is available
  or when the host can guide the user to grant it.

#### AI Plan Preview

The preview panel shows what the AI understands after the intent is saved and
the host LLM produces a `TableBuildPlan`.

The preview uses user-facing sections:

- `만들 표 모양`: interpreted rows, columns, measures, and blank cells to fill.
- `참고할 원본`: source ranges, tables, formulas, or tabs the plan will use.
- `채우는 방법`: formula strategy in plain language.
- `확인 방법`: live readback or Excel recalculation plan.
- `되돌리는 방법`: created tab deletion, copied spreadsheet deletion,
  workbook-copy deletion, or created worksheet removal.
- `확인이 필요한 점`: unresolved questions.

The preview must distinguish draft understanding from write authority. The
create/apply action remains disabled until a validated `TableBuildPlan` exists
and the user explicitly confirms it.

### Workbench State Model

The UI keeps a draft state. The MCP runtime owns canonical artifacts.

| State | Owner | Description |
| --- | --- | --- |
| `draft_source_view` | UI | Sanitized source preview, loaded tabs, current search, and pinned hints. |
| `draft_output_canvas` | UI | Visible grid text the user entered. |
| `draft_llm_prompt` | UI | Plain-language request text. |
| `draft_output_target` | UI | User-selected creation mode and optional title. |
| `TableBuildIntent` | MCP runtime | Validated saved intent with runtime-owned ids, timestamps, paths, and review state. |
| `TableBuildPlan` | Host LLM plus MCP validation | Semantic plan preview validated against the schema and source evidence gates. |
| apply result package | MCP runtime | Write result, readback/recalculation evidence, validation outcome, and rollback object. |

Runtime-owned fields such as `schema_version`, `intent_id`, `created_at`,
artifact paths, package metadata, validation status, and rollback envelope are
not accepted from free-form UI or model text. The save-intent tool derives and
validates them.

### Interaction Flow

```text
User opens table builder
  -> MCP tool prepares sanitized source preview
  -> UI renders connected source and blank output canvas
  -> User sketches output table and writes plain-language request
  -> User optionally pins source evidence
  -> UI calls spreadsheet_table_builder_save_intent
  -> MCP runtime writes intent package
  -> Host LLM reads saved intent + source evidence and drafts TableBuildPlan
  -> User reviews plan preview
  -> User confirms create/apply
  -> MCP create/apply tool writes a new sheet or copy
  -> MCP runtime validates readback or recalculation evidence
  -> MCP runtime returns result package and rollback object
```

### Responsive Behavior

- Fullscreen desktop: three regions visible.
- Inline or narrow desktop: output sketch first, source evidence and plan
  preview behind tabs.
- Mobile-sized host viewport: output sketch, prompt, and primary action remain
  visible first; source evidence is a secondary expandable section.
- The UI uses stable row/column dimensions so typed text, formula markers,
  hover states, and status messages do not resize the grid unexpectedly.

### Candidate Grid Engines

The current default is a purpose-built canvas because the product contract is
small: capture a user sketch, not run a full spreadsheet. Candidate engines are
implementation details for the canvas only.

| Candidate | Fit | Use when |
| --- | --- | --- |
| Purpose-built canvas | Best control over MCP artifact contract, host iframe constraints, and simple Korean user-facing text. | Default path for Workbench v2. |
| ReactGrid | MIT licensed React spreadsheet-like grid with editing, paste, selection, resize, sticky rows/columns, and touch support. | Use if custom canvas keyboard/paste/accessibility becomes costly and a React bundle is acceptable. |
| Jspreadsheet CE | MIT licensed vanilla/JS spreadsheet grid with Excel-like controls, paste, column types, and lightweight integration. | Use if vanilla integration matters more than React and CE features cover the needed canvas behavior. |
| Univer | Apache-2.0 office SDK with full spreadsheet engine, plugin system, canvas rendering, formula engine, and browser/Node runtime. | Use when the product needs an embedded spreadsheet app, workbook processing surface, or richer source inspection UI. |
| Handsontable | Mature spreadsheet grid with HyperFormula support and strong UX. | Evaluate only with an approved commercial license. |

### UI Completion Criteria

- The shared UI can be served through `ui://sheets-bridge/table-builder`.
- Standalone browser tests and MCP Apps host-adapter tests use the same HTML
  bundle.
- The first visible task is an editable output sketch, not role selection.
- `AI에게 요청할 내용` is the prompt input and is saved as `llm_prompt`.
- Source evidence selection is optional and saved as hints.
- The UI submits through `spreadsheet_table_builder_save_intent`.
- Saved intents validate against `table-build-intent.schema.json`.
- The host can display or relay a `TableBuildPlan` preview before write tools
  are enabled.
- No credentials, raw tokens, or private session handles appear in UI state,
  model-visible context, or review packages.
- Playwright or equivalent browser smoke verifies desktop and narrow viewport
  layout, text overflow, direct typing, paste, save-intent submission, and
  host-adapter error states.

## Table-Builder Implementation Sequence

Implement the shared UI and remote-host path in the order below. Each phase has
an explicit output contract and verification gate. Progress phases in order so
the shared contract stays usable by local web tests, Claude MCP Apps, and
ChatGPT web remote MCP/App flows.

### Execution Protocol

Each implementation phase is a separate work package. A Codex session can take
one phase as its goal and advances after the completion gate for the current
phase has evidence.

Per-phase workflow:

1. Read this phase, `references/spreadsheet-principles.md`,
   `references/excel-workbook-principles.md`, and
   `references/connected-google-sheets-principles.md` when the phase touches
   spreadsheet read/write behavior.
2. Confirm the nearest existing concept and extend it instead of introducing a
   near-duplicate tool, schema, artifact, or failure kind.
3. Add or update the narrowest fixture/test/smoke that proves the phase output.
4. Implement only the files required by the phase output.
5. Run the phase completion gate and record any manual smoke evidence under
   `review-packages/spreadsheet-table-builder/`.
6. Update `IMPLEMENTATION_MAP.html` only when the runtime architecture, current
   work, or risk profile changes.

Default phase order:

| Phase | Depends on | Runtime outcome | Main evidence |
| --- | --- | --- | --- |
| 0. Baseline inventory | Current repo state | Existing behavior is frozen before extraction | MCP stdio smoke and fixture package |
| 1. Canonical contracts | Phase 0 | Intent, plan, and session are schema-backed artifacts | Schema validation tests |
| 2. Shared UI bundle | Phase 1 | One host-neutral table-builder UI is served everywhere | Render tests and JS syntax check |
| 3. Host adapters | Phase 2 | Host differences are isolated to thin adapters | Mocked message/tool-call tests |
| 4. Local desktop MCP path | Phase 3 | Claude/Desktop local path runs through stdio MCP | Claude/local MCP smoke |
| 5. Remote MCP HTTP wrapper | Phase 4 | Same tools are reachable through HTTPS MCP | HTTP JSON-RPC smoke |
| 6. Remote auth authority | Phase 5 | Remote Sheets access is user/session-authorized | Auth/permission smoke and redaction checks |
| 7. ChatGPT web connector smoke | Phase 6 | ChatGPT web can use the shared UI and tools | ChatGPT smoke package |
| 8. Table Builder Workbench UI | Phase 7 | Shared UI matches the workbench design and saves user-sketched intents | Browser/host-adapter smoke |
| 9. Apply/validate/rollback matrix | Phase 8 | Real edits run through approved apply paths | E2E packages and rollback results |

### Current Runtime Scope

Current runtime scope is MCP-first:

- Desktop operation uses the MCP stdio server.
- Desktop Google Sheets access uses the MCP-managed local OAuth token cache.
- Remote web operation uses an HTTPS MCP service with approved user/session
  authority.
- User-facing table creation uses `TableBuildIntent`,
  `TableBuildPlan`, and `formula_table_apply_v1`.
- Connected Sheets authority is described as MCP/approved authority path.
- Local Excel file mutation and real Excel recalculation are desktop-runtime
  capabilities unless an explicit local-runtime or uploaded-artifact workflow is
  added for a remote host.

### Phase 0: Baseline Inventory And Freeze

Goal: lock the current working behavior before extracting or adding host
adapters.

Implementation actions:

- Record the current `spreadsheet_table_builder_ui`,
  `spreadsheet_table_builder_save_intent`,
  `spreadsheet_create_formula_table_from_spec`, rollback, and Excel validation
  tool surfaces as the baseline.
- Add or update a small table-builder fixture package under
  `review-packages/spreadsheet-table-builder/fixtures/` or `tests/fixtures/`
  with one Google-Sheets-shaped source preview and one Excel-shaped source
  preview.
- Confirm the current local MCP Apps resource still serves
  `ui://sheets-bridge/table-builder`.

Expected outputs:

- Baseline fixture JSON with `app_source`, `output_canvas`, and `llm_prompt`.
- A smoke note or test fixture that identifies current tool/resource behavior
  with fixture-backed evidence.

Completion gate:

- `python3 -m unittest mcp.sheets_bridge.test.test_mcp_server` passes.
- MCP JSON-RPC smoke proves `initialize`, `tools/list`, `resources/list`,
  `resources/read`, and `spreadsheet_table_builder_save_intent` continue to
  work.

### Phase 1: Canonical Table-Builder Contracts

Goal: make the data contracts explicit before changing UI or transport.

Implementation actions:

- Add schemas for:
  - `TableBuildIntent`;
  - `TableBuildPlan`;
  - `TableBuilderSession`;
  - host adapter submit/result messages.
- Keep schema authority under `schemas/` and validation helpers under
  `mcp/sheets_bridge/`. Host-specific UI code consumes validated contracts.
- Ensure `TableBuildIntent` includes:
  - `schema_version`;
  - `intent_kind`;
  - `source`;
  - `source_package`;
  - `artifact_type`;
  - `output_canvas`;
  - `llm_prompt`;
  - optional source hints;
  - requested output mode;
  - review state.
- Ensure `TableBuildPlan` separates:
  - interpreted output shape;
  - source evidence needed;
  - proposed formula strategy;
  - target artifact and creation mode;
  - validation plan;
  - rollback plan;
  - unresolved questions.

Expected outputs:

- `schemas/table-build-intent.schema.json`
- `schemas/table-build-plan.schema.json`
- `schemas/table-builder-session.schema.json`
- `schemas/table-builder-host-message.schema.json`
- Narrow validation tests that load fixture payloads and reject malformed
  payloads.

Completion gate:

- Schema validation passes for existing saved intents.
- Intent validation requires both `output_canvas` and `llm_prompt` before any
  package write.
- Host adapters import transport and UI integration code only.

### Phase 2: Shared UI Bundle Extraction

Goal: move the table-builder UI out of a Python string into a host-neutral
bundle while preserving current behavior.

Implementation actions:

- Create a shared UI directory such as
  `mcp/sheets_bridge/ui/table_builder/`.
- Store the UI as a self-contained HTML bundle or as source files that are
  deterministically bundled into one HTML resource:
  - `index.html`;
  - `table_builder.css`;
  - `table_builder.js`;
  - optional `host_adapter.js`.
- Use bundled CSS/JS or inline output so Claude and ChatGPT can render the same
  iframe resource.
- Replace `build_table_builder_mcp_app_html()` with a renderer that reads the
  shared bundle and injects only safe static metadata if needed.
- Preserve the current user-facing workflow:
  - direct spreadsheet-like output canvas;
  - user-entered `llm_prompt`;
  - optional source hint selection;
  - "AI에게 이해한 내용 확인하기";
  - canvas/prompt/hint inputs for the user.

Expected outputs:

- Shared UI files under `mcp/sheets_bridge/ui/table_builder/`.
- Python renderer/helper that serves the shared UI for MCP Apps and local
  packages.
- Tests proving the rendered HTML is credential-free and includes only
  explicitly sanitized package paths.

Completion gate:

- Existing MCP Apps resource test still passes.
- Extracted JavaScript passes `node --check`.
- Standalone local HTML/package mode and MCP Apps resource mode render the same
  core UI labels and submit the same normalized intent fixture.

### Phase 3: Host Adapter Interface

Goal: make host differences explicit and small.

Implementation actions:

- Define one JavaScript host adapter interface:
  - `initialize()`;
  - `onToolInput(callback)`;
  - `onToolResult(callback)`;
  - `callTool(name, arguments)`;
  - `updateModelContext(payload)`;
  - `sendMessage(text)`;
  - `reportError(error)`.
- Implement:
  - `mcpAppsHostAdapter` for Claude MCP Apps and ChatGPT web MCP Apps bridge;
  - `standaloneHostAdapter` for browser-only local tests.
- Keep adapter code transport-only. It translates JSON-RPC messages while
  formula validation, output calculation, and spreadsheet write authority stay
  in MCP tools and canonical artifacts.

Expected outputs:

- Host adapter source and tests using mocked `postMessage`.
- Fixture tests for:
  - host sends `ui/notifications/tool-result`;
  - UI calls `tools/call` with `spreadsheet_table_builder_save_intent`;
  - UI sends `ui/update-model-context` and `ui/message` after successful save;
  - missing host support produces a visible non-fatal error.

Completion gate:

- Claude MCP Apps smoke still works through the new adapter.
- Standalone adapter can run from a local browser package for development
  tests.
- Intent package writes occur only after the submit tool succeeds.

### Phase 4: Local Stdio Compatibility

Goal: keep desktop clients stable while the shared UI changes.

Implementation actions:

- Preserve `mcp/sheets_bridge_server.py` as the local stdio entrypoint.
- Keep Claude Desktop configuration compatible with the current
  `mcpServers.sheets-bridge.command + args` shape.
- Ensure `spreadsheet_table_builder_ui` still supports:
  - Google Sheets source preview through local user OAuth;
  - Excel workbook source preview through bounded local `.xlsx` reads;
  - current Chrome tab resolution when explicitly requested.

Expected outputs:

- Updated stdio tests and a manual smoke command in packaging docs if the
  command changes.

Completion gate:

- Claude Desktop can list tools after restart.
- `resources/read` returns the shared UI HTML.
- Local Google Sheets read and local Excel preview fixtures still generate
  sanitized packages.

### Phase 5: Remote MCP HTTP Wrapper

Goal: expose the same semantic tools through an HTTPS-compatible remote MCP
endpoint for ChatGPT web.

Implementation actions:

- Add a remote transport entrypoint, for example
  `mcp/sheets_bridge_http_server.py` or
  `mcp/sheets_bridge/http_server.py`.
- Provide:
  - `GET /healthz` for deployment readiness;
  - `POST /mcp` for MCP requests over HTTP;
  - any additional streamable HTTP/SSE behavior required by the selected MCP
    server framework.
- Reuse existing tool handlers where runtime authority is compatible.
- Accept host-supplied sanitized `source_preview` payloads for
  `spreadsheet_table_builder_ui` so remote hosts can render the shared UI before
  live remote Google authorization is available.
- Return structured capability-boundary results for desktop-runtime
  capabilities:
  - local Excel file path reads;
  - desktop Excel recalculation;
  - local OAuth token cache access;
  - local Chrome current-tab resolution.
- Keep tool names, schemas, structured outputs, and resource URIs aligned with
  the stdio server.

Expected outputs:

- Remote MCP server entrypoint and tests.
- Deployment-ready health endpoint.
- A local HTTP smoke that lists tools/resources and calls
  `spreadsheet_table_builder_save_intent`.
- A local HTTP smoke that builds the shared table-builder UI from a sanitized
  `source_preview`.

Completion gate:

- MCP Inspector or equivalent JSON-RPC smoke passes against `/mcp`.
- `spreadsheet_table_builder_ui` over HTTP returns a shared UI resource and
  sanitized source preview for a supported remote source. In Phase 5, the
  supported remote source is a host-provided sanitized `source_preview`; live
  Google Sheets reads belong to Phase 6 remote authorization.
- Desktop-runtime source requests return structured
  `local_runtime_required` or `remote_capability_boundary` results.

### Phase 6: Remote Auth And Google Sheets Authority

Goal: make ChatGPT web access real spreadsheets through remote user/session
authority with credential-free model-visible results.

Implementation actions:

- Implement the default remote authorization path as a user-delegated remote
  MCP session: the remote service verifies the user/session, stores session
  credentials only in approved infrastructure, and calls Google APIs with the
  scopes granted for that user.
- Treat Cloud Run broker/DWD as an enterprise deployment variant when it is
  explicitly approved for the remote service. Runtime uses keyless service
  identity for that variant. The active runtime contract is
  `docs/workload-identity-runtime-contract.md`.
- Keep runtime files and model-visible outputs credential-free.
- Persist remote tokens/session state in approved infrastructure storage.
  Review packages contain sanitized session/evidence summaries.
- The development HTTP runtime can use
  `SHEETS_BRIDGE_REMOTE_AUTH_SESSIONS_PATH` as a local session-store adapter;
  hosted deployments replace that adapter with approved infrastructure storage.
- Scope remote Google Sheets access to the user/session authority required by
  the requested operation.
- Keep existing connected-Sheets constraints:
  - preserve `spreadsheetId`;
  - preserve tab `sheetId`;
  - identity-preserving in-place Sheets operation;
  - live readback after writes;
  - import/loading/permission state reporting.

Expected outputs:

- Remote auth configuration/runbook.
- Tool behavior for unauthenticated, unauthorized, read-only, and read/write
  sessions.
- Tests or smoke fixtures proving credential-free model-visible results.

Completion gate:

- ChatGPT web can call a read-only Sheets preview on a user-authorized
  spreadsheet.
- Write authority gates run before mutation.
- Authorized writes create a new sheet or approved copy, read back the result,
  and return rollback instructions.

### Phase 7: ChatGPT Web Connector Smoke

Goal: prove the remote UI and tools work from ChatGPT web.

Implementation actions:

- Expose the remote MCP server over HTTPS. For development, use an approved
  secure tunnel; for production, use hosted infrastructure such as Cloud Run.
- Register the `/mcp` endpoint in ChatGPT web developer/app connector settings.
- Refresh metadata after tool/resource changes.
- Run the connector smoke helper against the registered endpoint:
  `PYTHONPATH=mcp python3 mcp/sheets_bridge_chatgpt_web_smoke.py --endpoint-url <https-url>`.
- Exercise the table-builder flow:
  - ask ChatGPT to inspect a source preview;
  - render the shared UI;
  - submit a `TableBuildIntent`;
  - generate a `TableBuildPlan`;
  - confirm writes wait for explicit user confirmation.

Expected outputs:

- ChatGPT web smoke package under
  `review-packages/spreadsheet-table-builder/chatgpt-web-smoke/`.
- Captured sanitized tool/resource metadata, submitted intent, generated plan,
  and capability-boundary messages.
- `write-gate.json` showing that
  `spreadsheet_create_formula_table_from_spec` waits for explicit user
  confirmation after the `TableBuildPlan` preview.

Completion gate:

- ChatGPT web lists the expected tool set.
- Shared UI renders and saves intent.
- ChatGPT-visible structured outputs are credential-free.
- Local Excel-only capabilities produce visible local-runtime-required results.

### Phase 8: Table Builder Workbench UI

Goal: make the shared table-builder UI match the workbench design before
running write-path E2E tests.

Implementation actions:

- Rework `mcp/sheets_bridge/ui/table_builder/mcp_app.html` around the
  three-region workbench layout:
  - source evidence panel;
  - output sketch canvas as the primary first task;
  - AI plan preview panel;
  - bottom action/status bar.
- Keep `host_adapter.js` as transport glue. UI state changes must not move
  spreadsheet formula planning, source authority, validation, or write authority
  into the adapter.
- Preserve the accepted submit path:
  `spreadsheet_table_builder_save_intent`.
- Add canvas controls for:
  - direct typing;
  - paste from spreadsheet sources;
  - adding rows and columns;
  - optional source evidence pins;
  - output target choice with Google Sheets and Excel defaults.
- Update user-facing language:
  - output canvas first;
  - prompt label `AI에게 요청할 내용`;
  - action label `AI에게 이해한 내용 확인하기`;
  - source evidence as optional help.
- Keep `TableBuildIntent` unchanged unless a required field cannot represent
  the workbench design. If a schema change is required, update the schema,
  contracts, fixtures, and tests in the same phase.
- Add or update browser/static tests for:
  - desktop layout;
  - narrow layout;
  - no text overflow in primary buttons and labels;
  - direct canvas typing;
  - paste into canvas;
  - save-intent submission;
  - host-adapter timeout/error messaging;
  - credential redaction.

Expected outputs:

- Updated shared UI bundle under `mcp/sheets_bridge/ui/table_builder/`.
- Fixture-backed standalone package or browser smoke showing the workbench
  layout and a saved intent.
- Updated tests for host-adapter and UI-resource rendering.

Completion gate:

- MCP Apps resource test still passes.
- Shared UI labels match the user-facing language in this design.
- Standalone local browser smoke and MCP Apps host-adapter smoke submit the same
  normalized `TableBuildIntent`.
- Saved intent validates against `table-build-intent.schema.json`.
- Browser screenshot checks show the output sketch as the primary task on
  desktop and narrow viewports.

### Phase 9: End-To-End Apply, Validate, Rollback Matrix

Goal: prove the shared UI leads to real spreadsheet edits through approved
apply paths with live readback and rollback evidence.

Implementation actions:

- Run the table-builder flow for:
  - local Google Sheets new-tab creation;
  - local Google Sheets copy mode when Drive authority is configured;
  - local Excel workbook copy mode;
  - local Excel source-workbook sheet mode when explicitly selected;
  - ChatGPT web remote Google Sheets new-tab creation when remote auth is
    available.
- Validate:
  - generated formula text;
  - Google Sheets live readback;
  - Excel formula text statically;
  - Excel calculated values through Microsoft Excel where required.
- Execute rollback through `spreadsheet_rollback_created_artifact` from an
  explicit user/tool call.

Expected outputs:

- E2E review packages for each supported path.
- Rollback objects and rollback execution results.
- A support matrix documenting runtime capability boundaries.

Completion gate:

- Every supported path has a passing create/readback/rollback smoke.
- Every capability boundary has a clear structured result.
- Every test/package uses spreadsheet-engine or live-readback authority for
  output values.

## Design Review Triggers

Revisit the design when any of these material changes occur:

- ChatGPT web requires a UI metadata or MCP transport shape outside the shared
  UI bundle contract used by Claude MCP Apps.
- Remote auth requires a different user/session spreadsheet authority proof
  while keeping model-visible outputs credential-free.
- A remote web path expands into local Excel file access or desktop Excel
  recalculation through a local runtime or uploaded-artifact workflow.
- Host adapter logic starts duplicating spreadsheet formula planning,
  validation, or write authority.
- A connected Sheets flow proposes export/edit/reupload as the main product
  path.

## Generic Spreadsheet Table Builder Boundaries

- `spreadsheet_table_builder_ui` serves the shared table-builder UI and creates
  sanitized source preview packages.
- The table-builder also exposes an MCP Apps resource at
  `ui://sheets-bridge/table-builder` with MIME type
  `text/html;profile=mcp-app`. Hosts that support MCP Apps, starting with
  Claude Desktop in the current target path, can render this UI inline instead
  of opening the local `index.html` package. ChatGPT web support uses the same
  shared UI through a remote MCP/App host adapter.
- For Google Sheets, the UI source preview reads through local user OAuth and
  keeps the original spreadsheet identity. For Excel workbooks, it reads a
  bounded local `.xlsx` range with deterministic workbook tooling.
- The UI captures intent as a `TableBuildIntent`: source artifact type, source
  package reference, source range, user-entered `output_canvas`, user-entered
  `llm_prompt`, optional source hints, output creation mode, and output target
  metadata.
  `llm_prompt` is the user's instruction to the MCP client/LLM about how to
  complete the requested table; spreadsheet calculation results come from
  formulas and readback/recalculation.
- The user sketches the desired output shape, adds a natural-language prompt,
  and submits it. After submission, the UI shows an "is this shape correct?"
  AI work-plan preview for confirmation.
- In MCP Apps mode, the UI submits the sketch and prompt through
  `spreadsheet_table_builder_save_intent`. The saved intent is a durable
  artifact under `review-packages/spreadsheet-table-builder/intents/`, and the
  host conversation continues by generating a `TableBuildPlan` from that intent.
- If `output_canvas` contains both row labels and column labels, formula-table
  planning treats those labels as the requested output shape instead of
  expanding every distinct label found in the source preview.
- Formula templates, source-field bindings, and target write requests are stored
  in `TableBuildPlan` and the approved apply spec.
- `spreadsheet_create_formula_table_from_spec` chooses the write path from the
  approved apply spec artifact type.
- For Google Sheets, both the UI source read and any subsequent write/apply path
  are executed by the MCP server through the MCP-managed local OAuth token cache
  in desktop mode, or through the approved remote session authority in remote
  web mode. Credential access remains inside MCP OAuth tools or approved remote
  session storage.
- For Google Sheets, formula-table creation defaults to `creation_mode=sheet`,
  requires read/write Sheets OAuth, creates a new tab in the existing
  spreadsheet, reads back formatted values, and returns created-tab deletion as
  rollback.
- Google Sheets `creation_mode=copy` requires Drive copy authority. `access=copy`
  is sufficient for app-created or explicitly app-selected files; `access=copy_full`
  is required for arbitrary user-accessible source spreadsheets. The tool
  creates a Drive copy of the source spreadsheet, writes the formula table into
  that copy, reads back formatted values from the copy, and returns copied-file
  deletion as rollback.
- For Excel workbooks, formula-table creation defaults to `creation_mode=copy`:
  it creates a workbook copy, adds the formula-table worksheet inside that copy,
  verifies the written formula text statically, and returns copy-file deletion
  as rollback.
- Excel workbook copy mode uses desktop Excel automation by default for files
  at or above `SHEETS_BRIDGE_EXCEL_DESKTOP_WRITE_THRESHOLD_BYTES` bytes
  (default: 20 MiB). On macOS the bridge calls
  `scripts/excel_copy_sheet_into_workbook.applescript` through `osascript`; on
  Windows it calls `scripts/excel_copy_sheet_into_workbook.ps1` through
  PowerShell and Excel COM Automation. The desktop writer copies a small
  generated template sheet into the workbook copy, then rewrites formula cells
  on the copied sheet so the copied workbook keeps local formula references.
- Excel `creation_mode=sheet` adds a new worksheet inside the source workbook
  file, verifies the written formula text statically, and returns
  created-worksheet deletion as rollback.
- Output formatting options cover review-safe structural presentation:
  bold header rows, frozen header rows, column auto-resize, and optional
  warning/protection on the created output sheet. Source ranges remain
  unchanged.
- The spec may provide any formula template that starts with `=`.
- External, volatile, or permission-sensitive functions such as `IMPORTRANGE`,
  `IMPORTDATA`, `GOOGLEFINANCE`, custom functions, and cross-workbook references
  are allowed as spreadsheet formulas. The plan and validation result annotate
  their loading, timeout, freshness, and permission risks and use live readback
  or real Excel recalculation before treating resulting values as authority.
- Formula templates may use placeholders such as `{measure_range}`,
  `{row_label_range}`, `{column_label_range}`, `{row_label_cell}`,
  `{column_label_cell}`, `{row_label_value}`, `{column_label_value}`,
  `{source_sheet}`, `{source_range}`, and `{output_sheet}`.
- Output values come from spreadsheet formulas referencing the source range.
  Deterministic code may extract visible row/column labels to size the table.
  Spreadsheet engines calculate output values.
- Excel formula results require Microsoft Excel recalculation before they are
  treated as value authority. `openpyxl` can verify written formula text, but it
  is a formula text reader/writer. `spreadsheet_validate_excel_formula_results`
  provides the active static scan plus optional real-Excel sampling path.
- The table-builder follows the shared spreadsheet and workbook edit rules in
  `references/spreadsheet-principles.md`,
  `references/excel-workbook-principles.md`, and
  `references/connected-google-sheets-principles.md`.
- Rollback is a separate explicit call to
  `spreadsheet_rollback_created_artifact`.

## MCP Client Configuration

Desktop MCP clients launch the server command directly. For developer runs, use
the repository Python entrypoint:

```json
{
  "mcpServers": {
    "sheets-bridge": {
      "command": "python3",
      "args": [
        "/Users/kangmin/Documents/excel-workbook-editing/mcp/sheets_bridge_server.py"
      ]
    }
  }
}
```

For non-developer deployment, use the Python-included bundled executable built
from `packaging/sheets-bridge-mcp/`:

```json
{
  "mcpServers": {
    "sheets-bridge": {
      "command": "/Users/<user>/Applications/Sheets Bridge MCP/sheets-bridge-mcp"
    }
  }
}
```

Windows bundled runtime configuration uses the installed `.exe` path:

```json
{
  "mcpServers": {
    "sheets-bridge": {
      "command": "C:\\Users\\<user>\\AppData\\Local\\Programs\\Sheets Bridge MCP\\sheets-bridge-mcp.exe"
    }
  }
}
```

The bundled executable includes its own Python runtime and the required helper
scripts for Excel automation. Build artifacts must be produced on each target
OS: macOS builds macOS executables, and Windows builds Windows executables.
Versioned releases are produced through
`packaging/sheets-bridge-mcp/release.py`, which can update the single version
source, run tests, build the local OS executable, smoke-test MCP
initialization, tool/resource listing, table-builder resource reads, and write release checksums plus
`release-manifest.json`.

Chrome current-tab fallback requires Chrome to be started with a remote
debugging endpoint such as `http://127.0.0.1:9222`.

### Remote MCP And ChatGPT Web

ChatGPT web uses a reachable HTTPS MCP endpoint registered through the ChatGPT
web developer/app surface. Development can use an approved secure tunnel, while
production should use a hosted remote MCP service such as Cloud Run.

The remote MCP service must preserve the same tool names, JSON schemas, and
artifact contracts as the local stdio server. It may implement transport and
authentication differently, but the model-visible spreadsheet contract remains:

- remote requests carry a session handle in `Authorization: Bearer <session-id>`
  or `X-Sheets-Bridge-Session`;
- the session provider resolves the handle to internal Google access authority,
  granted scope names, expiry, and sanitized user/session metadata;
- `sheets_bridge_auth_status` over HTTP reports remote session status and never
  reports desktop OAuth token paths;
- `spreadsheet_table_builder_ui` returns sanitized source preview metadata and
  a shared UI resource reference;
- before remote Google authorization is active, `spreadsheet_table_builder_ui`
  can render from a host-provided sanitized `source_preview`;
- `spreadsheet_table_builder_save_intent` persists the submitted
  `TableBuildIntent`;
- `spreadsheet_create_formula_table_from_spec` and rollback tools remain the
  only write paths;
- missing, expired, or under-scoped remote sessions return
  `remote_auth_required`, `remote_session_expired`, or
  `remote_permission_denied` structured results;
- live Google Sheets writes require user/session authority and live readback;
- Excel local-file mutation and desktop Excel recalculation are represented as
  local-runtime-required or uploaded-artifact workflows.

Remote auth setup and smoke behavior are described in
`docs/mcp-sheets-bridge-remote-auth-runbook.md`.

Remote web hosts receive credential-free capability results. Local OAuth token
files, local Excel paths, and desktop rollback actions stay inside desktop
runtime workflows or are represented through `local_runtime_required`,
`upload_required`, or equivalent structured capability results.

## Security Boundaries

- MCP tools are model-callable, and credentials remain inside the local OAuth
  cache or approved remote session storage.
- Browser context reads are limited to URL, title, `gid`, and selected A1 range.
- Review packages are sanitized evidence; live spreadsheet authority comes from
  MCP readback, apply, validation, and rollback tools.
- Shared UI host adapters are transport glue. Spreadsheet formulas, validation,
  credential access, and rollback execution remain MCP tool responsibilities.
- Google Sheets identity, formulas, protections, validations, Apps Script
  behavior, and external dependencies must be preserved.
- Connected Sheets work uses in-place API reads/writes by default. User-directed
  export/edit/reupload flows are handled as explicit one-off workflows.

## Done Criteria

- MCP `initialize`, `tools/list`, and `tools/call` work over stdio JSON-RPC.
- Auth status, OAuth setup/login, logout, current-tab, and inspect tools return
  credential-free structured content.
- Inspect/apply/rollback writes `snapshot.json`, `manifest.json`, and
  `mcp-handoff.json` under `review-packages/sheets-bridge/mcp/`.
- Apply returns a rollback object and rollback creates a new inverse rollback
  object.
- Table I/O visualization writes credential-free HTML/SVG/JSON packages.
- Minimal-formula refactor supports dry-run and live new-sheet creation for the
  declared pattern, validates baseline/generated output values, and returns the
  created sheet as the rollback target.
- Generic spreadsheet table-builder UI creates an interactive local HTML spec
  builder for Google Sheets and Excel workbooks. The user sketches the target
  table and writes `llm_prompt`; formula-table creation converts the resulting
  spec into source-referencing formulas on a new sheet inside the selected
  target artifact according to `output.creation_mode`. Spreadsheet engines own
  output-value calculation.
- The shared table-builder UI is host-neutral: Claude MCP Apps, ChatGPT web
  remote MCP/App, and standalone local web tests submit the same
  `TableBuildIntent` shape through host adapters.
- ChatGPT web support is considered complete only when an HTTPS remote MCP
  endpoint exposes the same tools/resources, the shared UI can save a
  `TableBuildIntent`, and web-runtime capability gaps such as local Excel files
  are surfaced explicitly.
- Google Sheets table-builder supports both existing-spreadsheet tab creation
  and Drive copy mode with explicit `access=copy` or `access=copy_full` OAuth
  authority.
- Table-builder rollback instructions can be explicitly executed for created
  Sheets tabs, copied Google spreadsheets, Excel workbook copies, and Excel
  worksheets.
- Excel formula-table results clearly mark formula-result validation as pending
  real Microsoft Excel recalculation until
  `spreadsheet_validate_excel_formula_results` samples the selected cells
  through the Excel engine.
- Active runtime code exposes the Sheets Bridge through MCP tools and the
  optional browser remote resolver only.
- Active docs and schemas point to MCP Sheets Bridge as the current connected
  Google Sheets inspection contract.
- Bundled runtime smoke passes `initialize` and `tools/list` through the
  Python-included installed executable.
