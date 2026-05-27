# Agent Excel Usage Guidelines

Use this checklist when an LLM agent edits, generates, reconciles, or validates
`.xlsx` workbooks. The guidance is model-agnostic: it applies to Claude, Codex,
Grok, and other agents that can read files, run scripts, and call local tools.

## 1. Default Position

- Treat Excel as a calculation engine, not just a file format.
- Use code for deterministic construction and edits.
- Use the real Microsoft Excel engine for formula-result validation.
- Do not present `openpyxl` formula writes or pure-Python formula evaluation as final workbook validation.
- Keep the workbook explainable to a human reviewer: inputs, config, bridges, outputs, and known limitations should be inspectable.

## 2. Tool Sequence

For most workbook tasks:

1. Inspect the authoritative logic, source files, and workbook purpose.
2. Inspect workbook structure before editing if the workbook is unfamiliar, template-like, or multi-sheet.
3. Classify the issue: logic bug, source gap, manual override, workbook wiring bug, Excel behavior gap, or accounting-policy question.
4. Patch the generator or workbook structure in code.
5. Recalculate with real Excel.
6. Sample a narrow set of representative cells.
7. Run a workbook-wide formula error scan.
8. Compare the Excel-calculated result against the authoritative logic.
9. Record unresolved row IDs, source gaps, and review questions.

## 3. Preflight Structure Inspection

Before editing a non-trivial workbook, summarize the workbook structure:

```bash
python3 /path/to/excel-workbook-editing/scripts/inspect_workbook.py \
  /path/to/workbook.xlsx \
  --format json
```

Use this to identify:

- sheet names, hidden sheets, dimensions, and freeze panes
- named ranges and their destinations
- formula cell counts and sample formulas
- merged ranges, tables, data validations, and conditional formatting

Do not flatten an unfamiliar workbook into a single pandas table before checking
whether workbook structure carries meaning.

## 4. Preferred Validation Command

Prefer the temporary-copy wrapper for unattended agent runs:

```bash
python3 /path/to/excel-workbook-editing/scripts/excel_engine_sample.py \
  /path/to/workbook.xlsx \
  1 \
  B8 \
  B17 \
  D17
```

This wrapper:

- copies the workbook into a temporary validation location
- opens the copy in Microsoft Excel
- disables alerts and update-link prompts
- runs `calculate full rebuild`
- reads only requested cells
- closes without saving
- deletes the temporary copy

Use `--direct` only when the source path itself must be opened by Excel.

## 5. Formula Error Sweep

After real Excel recalculation, scan for cached formula and literal error cells:

```bash
python3 /path/to/excel-workbook-editing/scripts/formula_error_scan.py \
  /path/to/workbook.xlsx \
  --format json
```

Treat `formula_error_count` and `literal_error_count` as failures unless each
remaining error is expected and documented. Treat `blank_cached_formula_count`
as a warning signal: it can mean stale or missing cached values, but it can also
be a legitimate blank-result formula.

## 6. Desktop Excel Automation Rules

Desktop automation is a control layer over Excel, not a transformation layer.
Use AppleScript on macOS and PowerShell/COM on Windows.

Use it for:

- real Excel recalculation
- narrow cell sampling
- repeatable validation loops after code-generated workbook changes

Avoid it for:

- bulk workbook edits
- data transformation
- broad workbook scans
- workflows where a user is actively editing the workbook
- server-side, headless, or non-interactive validation

If desktop Excel automation is flaky, try these cheap checks first:

- close modal Excel dialogs
- ensure no one is editing the target workbook
- open read-only
- reduce the sample cell list
- use the temporary-copy wrapper instead of opening the project path directly

## 7. Formula And Structure Defaults

- Use defined names for important ranges and config cells.
- Prefer `INDEX/MATCH + IFERROR` over `XLOOKUP`.
- Prefer `SUMPRODUCT` over named-range `SUMIFS` when compatibility is uncertain.
- Normalize text keys explicitly.
- Store config dates as real Excel date cells.
- Normalize date-only comparisons when source datetimes may contain time fractions.
- Preserve row grain for refunds, reversals, bundles, and mixed positive/negative rows.
- Design zero-row bridge cases explicitly and validate one empty-period case in Excel.
- Preserve existing workbook templates: established formatting, sheet structure,
  named-range conventions, and reviewer-facing layout override generic styling
  preferences unless the user asks for a redesign.

## 8. Reconciliation Defaults

Do not chase the final gap first.

Use this comparison shape:

- approved or golden workbook
- authoritative code or calculation script
- newly generated workbook

Break residuals down by:

- line item or category
- brand or business unit
- sign
- period bucket
- inclusion or exclusion reason
- row membership

Small net gaps can hide large offsetting gross errors. Inspect gross overstatements
and understatements separately before accepting a final reconciliation.

## 9. Known Limitations And Review Items

Keep limitations visible as data, not hidden formulas.

For each limitation or source gap, preserve:

- transaction ID or row key
- processor ID such as `imp_uid`
- source label or source file
- search terms for source-owner lookup
- amount impact
- classification: source gap, manual override, logic bug, Excel behavior gap, or accounting-policy question

When generated logic matches an approved workbook but may not align with an
accounting standard or policy, classify it as a norm-alignment review item.
Calculation lock and accounting-policy approval are separate states.

## 10. Final Response Expectations

When reporting Excel work back to the user:

- say whether real Excel-engine validation was run
- list sampled cells or workbook outputs that were checked
- report formula error scan status, or say why it could not be run
- mention any validation that could not be completed
- keep unresolved source gaps or accounting-policy review items explicit
- avoid claiming workbook correctness from `openpyxl` inspection alone

## 11. Minimal Done Criteria

An Excel workbook task is not done until:

- the intended code or workbook change is applied
- the workbook remains explainable from input to output
- important formulas are wired to the intended sheets and named ranges
- real Excel recalculation matches the expected outputs
- critical cells have no unexplained `#N/A`, blanks, or stale formula results
- workbook-wide formula errors are absent or explicitly documented
- source gaps, manual overrides, and accounting-policy questions are documented separately from logic bugs
