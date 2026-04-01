---
name: excel-workbook-editing
description: Design, edit, debug, reconcile, and validate Excel workbooks and workbook-generation scripts. Use when the task involves modifying, creating, debugging, or reconciling .xlsx files, Excel formulas, sheet layouts, named ranges, lookup logic, cross-sheet references, workbook templates, carryover flows, or Excel automation and validation. Avoid for CSV/TSV-only tasks without Excel-specific concerns.
license: MIT
---

# Excel Workbook Editing

Treat Excel as a calculation engine with its own behavior, not just as a file format.
When editing a workbook, preserve both the intended logic and the workbook's explainability inside Excel.

## Quick Start

1. Identify the authoritative logic for the workbook. This may be a spec, script, policy, approved workbook, or user-provided invariant.
2. Separate raw inputs, parameters, intermediate calculations, derived outputs, and any prior-period carryovers.
3. Read [references/excel-workbook-principles.md](references/excel-workbook-principles.md) for formula, structure, and validation defaults.
4. Read [references/efficient-excel-workflows.md](references/efficient-excel-workflows.md) when the task is messy, recurring, or involves reconciliation against an approved workbook, unexplained gaps between source data and workbook results, or source-versus-logic difference analysis.
5. Choose the lowest-risk edit surface: workbook formulas, named ranges, template layout, generator script, or validation automation.

## Editing Defaults

- Preserve a traceable path from inputs to outputs.
- Keep important parameters visible and centralized.
- Do not add a second workbook-only logic path that silently diverges from the authoritative logic.
- Do not hide known input limitations inside ad hoc override formulas.
- Prefer compatibility-safe formulas over newer functions when the target Excel environment is uncertain.
- For recurring period workbooks, separate prior-period carry-ins, current-period raw inputs, and next-period carry-outs explicitly instead of mixing them into one surface.
- If the workbook is meant for auditability, keep the workbook as an explanation surface for the logic rather than a thin shell around copied totals.

## Structural Patterns

For small workbooks, a simple `input -> calc -> output` layout is often enough.
For complex workbooks, separate these roles explicitly:

- input sheets
- config or parameter sheets
- intermediate calculation sheets
- bridge sheets for logic that would otherwise become opaque
- output or export sheets
- known limitation sheets when some cases are intentionally excluded or manually handled

Use visible intermediate sheets when a single formula chain becomes hard to audit or debug.
Keep prior-period detail visible when carryover or opening-balance logic affects current results.
When operational raw inputs are messy or inconsistent across sources, add a standard input sheet before the bridge layer instead of wiring formulas directly to the raw extract.
If a bridge sheet can legitimately have zero source rows in some periods, design it so that downstream formulas still evaluate to explicit zeroes rather than empty or missing objects.

## Formula Defaults

- Use defined names for lookup ranges, aggregation ranges, config cells, and single-value carryovers.
- Avoid hard-coded column letters and parameter cells such as `A:A`, `BG:BG`, or `Config!B4`.
- Normalize lookup IDs with explicit text key columns such as `transaction_id_key`.
- Prefer `INDEX/MATCH + IFERROR` over `XLOOKUP` for workbook compatibility.
- Prefer `SUMPRODUCT` over `SUMIFS` when aggregating named ranges.
- Keep config dates as real Excel date cells, not strings.
- Avoid heavy whole-column diagnostics unless you have confirmed the recalculation cost is acceptable.
- Normalize date comparisons when time fractions may exist in Excel datetime values; a displayed date is not always a date-only value for formula purposes.
- When matching duplicate keys, verify whether Excel is using first-hit behavior and keep any Python-side mirrors aligned to the same selection rule.
- For aggregates fed by bridge sheets that may be empty, prefer explicit coercion patterns such as `IFERROR`, `N()`, or `0+named_range` so outputs close to numeric zero instead of blank or missing values.

## Tool Selection

Choose tools by task type rather than by habit.

- Use `openpyxl` or a workbook-generation script for deterministic structural edits such as adding sheets, writing formulas, creating named ranges, filling tables, and producing repeatable workbook outputs.
- Use AppleScript only as a control layer for the real Excel application on macOS when you need Excel to open, recalculate, save, or expose a narrow set of computed cell values.
- Use the Excel application when you need authoritative recalculation, visual inspection, feature behavior that only Excel can express, or confirmation that a human reviewer can actually follow the workbook.
- Keep bulk data transformation and workbook construction out of AppleScript and Excel UI when code can do it more safely and repeatably.
- Use the bundled AppleScript sample at `scripts/excel_recalculate_and_sample.applescript` when you need a read-only recalc-and-sample loop in real Excel on macOS.

## Validation Workflow

1. Confirm the intended logic from the authoritative source.
2. Make the workbook or script change.
3. Recalculate with the real Excel engine before trusting results.
4. Inspect representative rows, key aggregate cells, and likely edge cases.
5. Compare results against the authoritative source.
6. Fix formulas, names, sheet wiring, or automation and repeat.

For recurring reconciliations, prefer a three-surface comparison when possible:

- approved or golden workbook
- authoritative code or calculation script
- newly generated workbook

This separates logic bugs, source gaps, workbook wiring bugs, and Excel behavior differences faster than comparing only one pair of outputs.

## Automation Cautions

- `openpyxl` and similar libraries can write formulas but do not prove calculated results.
- Assume Excel automation is fragile while the target workbook is being edited by a user.
- Avoid validation loops that depend on active sheet focus or manual save timing.
- Read only the cells you need during automated checks; broad workbook scans are slow and noisy.
- If the real Excel application is unavailable, treat formula-result validation as incomplete and say so explicitly.

## Execution Examples

### Example 1: Add a new input column and wire it into formulas

1. Update the generator script or use `openpyxl` to add the column, related formulas, and named ranges.
2. Normalize any lookup key needed for joins.
3. Open the workbook in Excel and recalculate.
4. Check a few representative rows plus one aggregate cell.

Primary tools:

- `openpyxl` or generator script for the edit
- Excel for recalculation and review

### Example 2: Debug a workbook that shows unexpected `#N/A`

1. Identify which lookup or aggregation path produces the error.
2. Inspect whether the key type, named range, or date type is inconsistent.
3. Recalculate in Excel.
4. Read only the affected cells and a few upstream cells.
5. Replace fragile formulas such as `XLOOKUP` or hard-coded references if needed.

Primary tools:

- Excel for authoritative results
- AppleScript for repeatable recalc-and-read loops on macOS
- `openpyxl` only for applying the eventual structural fix

Example command:

```bash
cd /path/to/excel-workbook-editing
osascript scripts/excel_recalculate_and_sample.applescript \
  "/path/to/workbook.xlsx" \
  1 \
  A1 \
  B2 \
  C10
```

### Example 3: Generate a monthly workbook from source data

1. Build the workbook in code.
2. Write formulas, names, and sheet structure with `openpyxl` or another generator layer.
3. Open the output in Excel.
4. Recalculate and compare key outputs against the source of truth.

Primary tools:

- generator script plus `openpyxl` for creation
- Excel for final validation

### Example 4: Check whether a workbook is visually and logically reviewable

1. Open the workbook in Excel.
2. Inspect whether inputs, parameters, intermediate logic, and outputs are visually separated.
3. Confirm that major totals can be traced back through visible intermediate steps.
4. Only after that, decide whether a structural refactor is needed in code.

Primary tools:

- Excel first
- code second if the workbook needs repeatable repair

## Common Failure Modes

- hard-coded references drifting after row or column insertions
- `XLOOKUP` or newer functions behaving inconsistently across environments
- named-range aggregations returning unexpected zeroes
- numeric-versus-text key mismatches breaking joins
- dates stored as text causing comparison errors
- copied formulas silently pointing at the wrong sheet or period
- empty bridge ranges causing downstream aggregates to collapse into blanks or missing values
- first-hit versus last-hit mismatches between Excel formulas and Python-side joins
- datetime fractions causing period cutoff comparisons to behave differently from displayed dates
- sheets that exist structurally but are not actually wired into the active calculation path

## Done Criteria

- Excel recalculation matches the authoritative logic.
- Critical cells do not contain unexplained `#N/A`, blank values, or stale formulas.
- The workbook remains understandable to a human reviewer.
- Any intentional limitations or manual steps are explicitly visible.
- Important sheets are not just present; they are actually wired into the active calculation path and produce inspectable outputs.

## Reference

Load [references/excel-workbook-principles.md](references/excel-workbook-principles.md) when you need more detail on structure choices, formula safety, tool selection, validation discipline, or typical Excel-specific bugs.
Load [references/efficient-excel-workflows.md](references/efficient-excel-workflows.md) when you need reusable debugging heuristics, source-gap triage rules, or recurring-workbook operating patterns.
Load [references/applescript-examples.md](references/applescript-examples.md) when you need macOS Excel automation examples and concurrency cautions.
