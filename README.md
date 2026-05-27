# Excel Workbook Editing Skill

A model-agnostic agent skill for designing, editing, debugging, reconciling, and validating Excel workbooks.

## What this skill does

When an LLM agent works with `.xlsx` files, this skill gives it a reusable Excel workflow:

- Treat Excel as a calculation engine, not just a file format
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
- Separate source gaps from logic bugs when debugging mismatches
- Keep known limitations explicit instead of hiding workbook-only patches in formulas

## Requirements

- macOS or Windows desktop with Microsoft Excel installed for real Excel-engine validation
- An agent runtime that can read a `SKILL.md`-style folder or otherwise load the skill files into context

The bundled Excel automation (`scripts/excel_engine_sample.py`) requires desktop Microsoft Excel. It uses AppleScript on macOS and PowerShell/COM Automation on Windows. Core skill guidance (formula design, workbook structure, debugging heuristics) works on any platform, but real Excel validation requires a supported desktop Excel environment.

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
├── agents/
│   └── openai.yaml                   # Optional Codex UI metadata
├── references/
│   ├── excel-workbook-principles.md  # Formula, structure, and validation defaults
│   ├── efficient-excel-workflows.md  # Debugging heuristics and workflow patterns
│   ├── desktop-excel-automation.md   # macOS AppleScript and Windows COM examples
│   └── agent-excel-usage-guidelines.md # Model-agnostic agent checklist
└── scripts/
    ├── excel_engine_sample.py                    # Temporary-copy Excel recalc wrapper
    ├── excel_recalculate_and_sample.applescript  # Read-only recalc helper
    ├── excel_recalculate_and_sample.ps1          # Windows COM recalc helper
    ├── formula_error_scan.py                     # Formula and literal error scanner
    └── inspect_workbook.py                       # Workbook structure summary
```

## Key principles

- **Explainability first**: workbooks should explain the logic, not hide it behind copied totals
- **Code builds, Excel validates**: use `openpyxl` for deterministic edits, real Excel for recalculation
- **Prompt-safe validation**: for unattended agent runs, open a temporary workbook copy and sample only the cells needed
- **Structure before dataframes**: inspect sheets, names, formulas, and template features before flattening a workbook into tables
- **Formula errors are blockers**: sweep formula and literal errors after recalculation, and document any intentional remaining errors
- **Source vs. logic**: classify mismatches before chasing formula bugs
- **Compatibility**: prefer `INDEX/MATCH + IFERROR` over `XLOOKUP` for cross-environment safety
- **Stable bindings**: prefer defined names, text key columns, and explicit source-binding checks over column letters and fragile file assumptions

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
