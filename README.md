# Excel Workbook and Connected Google Sheets Editing Skill

A model-agnostic agent skill for designing, editing, debugging, reconciling, previewing, and validating Excel workbooks and connected Google Sheets.

## What this skill does

When an LLM agent works with spreadsheet artifacts, this skill gives it a reusable workflow:

- Treat spreadsheets as calculation and review systems, not just tabular files
- Preserve traceable `input -> intermediate -> output` logic
- Prefer layered recurring-workbook structure such as `carry-in -> current raw -> bridge -> output -> carry-out`
- Standardize messy operational raw files into stable input sheets before wiring formulas
- Use compatibility-safe formulas (`INDEX/MATCH` over `XLOOKUP`, `SUMPRODUCT` over `SUMIFS`)
- Design empty-month and zero-row bridge cases explicitly instead of assuming every bridge has data
- Inspect workbook structure before flattening or editing complex `.xlsx` files
- Validate with the real Excel engine, not just openpyxl
- Use the temporary-copy Excel validation wrapper for unattended agent runs
- Use narrow recalc-and-sample validation loops instead of broad workbook scans
- Run workbook-wide formula error scans after recalculation
- Preserve existing Google Sheets identity, `sheetId` values, validations, protected ranges, formulas, Apps Script-connected behavior, and external dependencies
- Avoid `.xlsx` round-trips for existing connected Google Sheets unless replacement or cloning is explicitly requested
- Verify Google Sheets edits with live readback from the same spreadsheet
- Handle Google Sheets timeout, quota, `IMPORTRANGE`, external loading, Apps Script, and rollback risks explicitly
- Generate review packages with HTML/JSON/Markdown evidence when agent-visible inspection is needed
- Separate source gaps from logic bugs when debugging mismatches
- Keep known limitations explicit instead of hiding workbook-only patches in formulas

## Requirements

- macOS or Windows desktop with Microsoft Excel installed for real Excel-engine validation
- Approved external access for live Google Drive and Google Sheets operations
  when the task involves connected Sheets
- An agent runtime that can read a `SKILL.md`-style folder or otherwise load the skill files into context

The bundled Excel automation (`scripts/excel_engine_sample.py`) requires desktop Microsoft Excel. It uses AppleScript on macOS and PowerShell/COM Automation on Windows. Core skill guidance (formula design, workbook structure, debugging heuristics) works on any platform, but real Excel validation requires a supported desktop Excel environment.

Existing Google Sheets edits require live spreadsheet access through an
approved external access surface. This repository consumes bounded
values/formulas/structure/write results and keeps the processing, validation,
and review-package side of the workflow.

## Installation

Install this folder wherever your agent runtime discovers skills. Examples:

Claude Code:

```bash
git clone https://github.com/kangminlee-maker/excel-workbook-editing.git \
  ~/.claude/skills/excel-workbook-editing
```

Codex:

```bash
git clone https://github.com/kangminlee-maker/excel-workbook-editing.git \
  ~/.codex/skills/excel-workbook-editing
```

Other LLM agents, including Grok-style or custom runners:

- Point the agent at this folder.
- Load `SKILL.md` first.
- Load referenced files under `references/` only when needed.
- Run scripts under `scripts/` directly when the runtime supports local commands.

Codex-specific UI metadata is optional and lives in `agents/openai.yaml`.

Codex can also install from GitHub with its skill installer:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo kangminlee-maker/excel-workbook-editing \
  --path . \
  --name excel-workbook-editing
```

Restart or reload the agent runtime after installing so the new skill is picked up.

## Contents

```
excel-workbook-editing/
├── SKILL.md                          # Main skill (auto-trigger rules included)
├── IMPLEMENTATION_MAP.html           # Current architecture and roadmap view
├── agents/
│   └── openai.yaml                   # Optional Codex UI metadata
├── docs/
│   ├── data-processing-spreadsheet-package-design.md
│   ├── document-shaped-excel-understanding-design.md
│   ├── evidence-backed-spreadsheet-claim-ledger-design.md
│   └── sheets-formula-dataflow-discovery-design.md
├── projects/
│   ├── _registry.json                   # Project identity registry
│   ├── google-sheets/                   # spreadsheetId + gid workspaces
│   └── excel/                           # workbook-family workspaces
├── references/
│   ├── spreadsheet-principles.md # Shared CRUD, workflow, and validation rules
│   ├── excel-workbook-principles.md # Excel/.xlsx structure, formulas, validation, automation
│   ├── connected-google-sheets-principles.md # In-place Sheets editing and operational risks
│   └── spreadsheet-review-package.md # HTML/JSON/Markdown review bundle guidance
└── scripts/
    ├── excel_engine_sample.py                    # Temporary-copy Excel recalc wrapper
    ├── excel_recalculate_and_sample.applescript  # Read-only recalc helper
    ├── excel_recalculate_and_sample.ps1          # Windows COM recalc helper
    ├── formula_error_scan.py                     # Formula and literal error scanner
    └── inspect_workbook.py                       # Workbook structure summary
```

## Runtime docs

- [Data-Processing Spreadsheet Package](docs/data-processing-spreadsheet-package-design.md): processing package design for Excel workbooks and credential-free spreadsheet evidence/results
- [Implementation Map](IMPLEMENTATION_MAP.html)

## Key principles

- **Explainability first**: spreadsheet artifacts should explain the logic, not hide it behind copied totals
- **Code builds, Excel validates**: use `openpyxl` for deterministic edits, real Excel for recalculation
- **Live Sheets stay live**: edit existing Google Sheets in place and preserve `spreadsheetId`, `sheetId`, permissions, formulas, protections, validations, and connected dependencies
- **Prompt-safe validation**: for unattended agent runs, open a temporary workbook copy and sample only the cells needed
- **Live readback for Google Sheets**: consume approved external
  write/readback evidence for changed ranges and dependent outputs from the
  same spreadsheet
- **Bounded Google Sheets operations**: plan timeout budgets, retries, import-load checks, and rollback snapshots for large or externally linked Sheets
- **Review packages are evidence**: static HTML/JSON previews help agent review but do not replace Excel recalculation or Google Sheets live readback
- **Structure before dataframes**: inspect sheets, names, formulas, and template features before flattening a workbook into tables
- **Formula errors are blockers**: sweep formula and literal errors after recalculation, and document any intentional remaining errors
- **Source vs. logic**: classify mismatches before chasing formula bugs
- **Compatibility**: prefer `INDEX/MATCH + IFERROR` over `XLOOKUP` for cross-environment safety
- **Stable bindings**: prefer defined names, text key columns, and explicit source-binding checks over column letters and fragile file assumptions
- **Project continuity**: continue repeated analysis inside `projects/` using Google Sheets `spreadsheetId + gid` or Excel workbook-family identity, not only filenames

## Updating

Claude Code example:

```bash
cd ~/.claude/skills/excel-workbook-editing && git pull
```

Codex example:

```bash
cd ~/.codex/skills/excel-workbook-editing && git pull
```

## License

MIT
