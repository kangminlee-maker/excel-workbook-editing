# Excel Workbook Editing Skill

A [Claude Code](https://claude.ai/claude-code) and Codex skill for designing, editing, debugging, reconciling, and validating Excel workbooks.

## What this skill does

When you work with `.xlsx` files in Claude Code or Codex, this skill automatically loads and guides the agent to:

- Treat Excel as a calculation engine, not just a file format
- Preserve traceable `input -> intermediate -> output` logic
- Prefer layered recurring-workbook structure such as `carry-in -> current raw -> bridge -> output -> carry-out`
- Standardize messy operational raw files into stable input sheets before wiring formulas
- Use compatibility-safe formulas (`INDEX/MATCH` over `XLOOKUP`, `SUMPRODUCT` over `SUMIFS`)
- Design empty-month and zero-row bridge cases explicitly instead of assuming every bridge has data
- Validate with the real Excel engine, not just openpyxl
- Use narrow recalc-and-sample validation loops instead of broad workbook scans
- Separate source gaps from logic bugs when debugging mismatches
- Keep known limitations explicit instead of hiding workbook-only patches in formulas

## Requirements

- **macOS** with Microsoft Excel installed
- [Claude Code](https://claude.ai/claude-code) CLI, desktop app, or IDE extension

The bundled AppleScript automation (`scripts/excel_recalculate_and_sample.applescript`) requires macOS and Microsoft Excel. Core skill guidance (formula design, workbook structure, debugging heuristics) works on any platform, but real Excel validation features are macOS-only.

## Installation

Clone this repository into your Claude Code skills directory:

```bash
git clone https://github.com/kangminlee-maker/excel-workbook-editing.git \
  ~/.claude/skills/excel-workbook-editing
```

Restart Claude Code. The skill appears in the skill list and triggers automatically on Excel-related tasks.

For Codex, clone the same repository into your Codex skills directory:

```bash
git clone https://github.com/kangminlee-maker/excel-workbook-editing.git \
  ~/.codex/skills/excel-workbook-editing
```

Codex uses `SKILL.md` plus `agents/openai.yaml` for discovery and UI metadata.

## Contents

```
excel-workbook-editing/
├── SKILL.md                          # Main skill (auto-trigger rules included)
├── agents/
│   └── openai.yaml                   # Codex UI metadata
├── references/
│   ├── excel-workbook-principles.md  # Formula, structure, and validation defaults
│   ├── efficient-excel-workflows.md  # Debugging heuristics and workflow patterns
│   └── applescript-examples.md       # macOS Excel automation examples
└── scripts/
    └── excel_recalculate_and_sample.applescript  # Read-only recalc helper
```

## Key principles

- **Explainability first**: workbooks should explain the logic, not hide it behind copied totals
- **Code builds, Excel validates**: use `openpyxl` for deterministic edits, real Excel for recalculation
- **Source vs. logic**: classify mismatches before chasing formula bugs
- **Compatibility**: prefer `INDEX/MATCH + IFERROR` over `XLOOKUP` for cross-environment safety
- **Stable bindings**: prefer defined names, text key columns, and explicit source-binding checks over column letters and fragile file assumptions

## Updating

Claude Code:

```bash
cd ~/.claude/skills/excel-workbook-editing && git pull
```

Codex:

```bash
cd ~/.codex/skills/excel-workbook-editing && git pull
```

## License

MIT
