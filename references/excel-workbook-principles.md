# Excel Workbook Principles

This reference distills reusable rules for editing Excel workbooks safely.

## 1. Workbook Purpose

- A workbook is not just a final-number report.
- For complex logic, it should let users follow `input -> intermediate calculation -> output`.
- The workbook should explain the authoritative logic with formulas, not quietly replace it.

## 2. Structural Rules

- Build the workbook around raw inputs.
- Keep parameters visible and centralized.
- Use intermediate sheets when transformations are too opaque to audit in a single formula chain.
- Keep prior-period artifacts visible when carryover logic depends on them.
- Do not add workbook-only rules to patch known input coverage gaps without making that limitation explicit.
- When operational raw files are inconsistent or semi-manual, standardize them into a stable input sheet before connecting formulas to them.
- Separate current-period raw inputs from prior-period carry-ins and next-period carry-outs so reviewers can see what belongs to each period.

Known input limitations should stay explicit rather than hidden inside formulas. Typical examples:

- transactions that only exist in a prior derived workbook
- manual override rows that are not reconstructable from current raw inputs

Treat those as coverage limitations, not as Excel logic bugs.

## 3. Recommended Layering

For complex workbooks, use a layered structure such as:

- input
- config
- intermediate calculation
- bridge
- output
- known limitations

Key implications:

- Keep a bridge sheet when important outputs are not just a direct sum of an upstream schedule.
- Keep prior-period detail separate so carryover behavior stays inspectable.
- Preserve readable breakdowns for any output that depends on multiple drivers.

## 4. Formula Design Defaults

- Use defined names for all important ranges and parameter cells.
- Use defined names for single values too, including config dates and opening balances.
- Avoid hard references that drift after row or column insertions.

Examples of the right kind of named anchors:

- `transaction_id`
- `transaction_id_key`
- `calc_amount`
- `prior_detail_key`
- `cfg_target_end_date`
- `adjustment_set`

Practical defaults:

- Prefer `INDEX/MATCH + IFERROR` over `XLOOKUP`.
- Prefer `SUMPRODUCT` over `SUMIFS` when named ranges are involved.
- Create text key columns such as `transaction_id_key` for joins and lookups.
- Keep human-readable ID columns separate from formula-safe key columns.
- Store comparison dates as real Excel date cells, not strings.
- Treat whole-column formulas and diagnostics as performance-sensitive.
- If a bridge or derived range may be empty, design the aggregate path so Excel still evaluates to explicit zero rather than blank or missing.
- Normalize date-only comparisons explicitly when workbook inputs may contain datetime fractions.
- When using lookups against non-unique keys, confirm whether first-hit behavior is the intended Excel meaning and keep any mirrored implementation consistent with it.

## 5. Validation Method

- `openpyxl` is useful for writing formulas but not for proving Excel results.
- Validate with the actual Excel engine.

Recommended loop:

1. Generate or edit the workbook.
2. Open it in Excel.
3. Recalculate the workbook.
4. Read only a small set of representative rows and key aggregate cells.
5. Fix formulas, names, or sheet wiring.
6. Repeat.

Operational cautions:

- Do not let the user open, save, or actively manipulate the workbook during Excel automation.
- Do not use whole-column diagnostics such as `COUNTIF(T:T)` unless there is no lighter option.

## 6. Tool Choice Rules

### Use `openpyxl` when

- you need repeatable workbook generation
- you need bulk structural edits across sheets or columns
- you need to write formulas, named ranges, formatting, validations, or static seed data
- you need deterministic edits that belong in version-controlled code
- you need to patch the workbook generator rather than manually repair a single file

### Do not rely on `openpyxl` when

- you need the authoritative calculated value of formulas
- you need to confirm that Excel recalculates the workbook correctly
- you need visual review of how a human will experience the workbook
- the workbook depends on Excel-native behavior that is safer to verify in the real app

Use extra caution with complex templates containing macros, pivot tables, external connections, or other Excel-native objects. Edit a copy first and verify preservation in Excel.

### Use AppleScript when

- you are on macOS and need to drive the real Excel app
- you need a repeatable loop of open workbook, recalculate, save, and read a narrow set of cells
- you need to validate computed results after a code-generated workbook change
- you need automation around Excel, but the actual calculation must still happen inside Excel

### Do not use AppleScript when

- you need large-scale workbook construction or transformation
- you need a cross-platform solution
- the task can be handled deterministically in Python without opening Excel
- the user is likely to interact with the workbook during the run

Treat AppleScript as glue for Excel, not as the primary transformation layer.
Prefer read-only recalc-and-sample loops unless you have confirmed no other Excel session is touching the workbook.

### Use Excel directly when

- you need authoritative recalculation
- you need to inspect charts, filters, conditional formatting, layout, or audit readability
- you need to verify that manual reviewers can follow the workbook
- you are diagnosing formula results that differ from what Python-side tooling suggests

### Avoid using Excel as the primary editing surface when

- the task is repetitive and should be encoded in a generator script
- the workbook must be regenerated reliably over time
- you need bulk edits across many sheets or periods
- the task is primarily data transformation rather than Excel-native review

Default rule:

- build and patch in code
- validate in Excel
- automate Excel with AppleScript only when manual recalculation is too slow or too repetitive

If the real Excel application is unavailable, do not present Python-side formula writes as validated Excel results.

## 7. Known Excel-Specific Failure Patterns

- `XLOOKUP` instability or unexpected `#N/A`
- hard-coded config cell references drifting after sheet edits
- `SUMIFS` on named ranges returning zero unexpectedly
- numeric-versus-text ID mismatches breaking joins
- dates stored as text
- copied formulas pointing to the wrong sheet or period
- empty bridge sheets yielding blanks, `<missing>`, or non-numeric aggregate behavior
- hidden time fractions in datetime cells breaking apparent date comparisons
- generator-side last-write-wins joins disagreeing with Excel first-match lookups
- sheets or helper tables that exist in the workbook but are disconnected from the live output path

Typical fixes:

- Replace `XLOOKUP` with `INDEX/MATCH + IFERROR`
- Replace fixed config references with named parameters
- Replace named-range `SUMIFS` with `SUMPRODUCT`
- Normalize IDs through explicit text key columns
- Convert comparison fields into real Excel date cells
- Re-audit copied formulas after structural edits
- Add explicit zero-row bridge handling with sentinel rows or coercion formulas
- Strip or normalize datetime fractions before cutoff comparisons
- Align Python-side join semantics with Excel lookup semantics when duplicate keys are possible
- Verify not only that a sheet exists, but that downstream outputs actually read from it

## 8. Execution Playbooks

### Case: Add or rename sheets, columns, formulas, or named ranges

- Start in code or `openpyxl`.
- Keep the sheet structure explicit.
- Recalculate in Excel after the change.

### Case: Investigate a wrong total

- Start from the authoritative source and the final output cell.
- Walk backward through bridge and intermediate sheets.
- Use Excel results as the judge of computed values.
- Use AppleScript if you need a repeatable recalc-and-sample loop.
- Prefer the bundled read-only AppleScript sample before attempting save or write-back automation.

### Case: Build a recurring monthly or periodic workbook

- Put workbook construction in code.
- Keep Excel usage focused on validation and human review.
- Avoid manual-only fixes that will have to be repeated next period.

### Case: Repair a workbook that a reviewer cannot follow

- Open it in Excel first.
- Identify where the logic becomes opaque.
- Introduce visible config, intermediate, or bridge sheets in code.

## 9. Cross-Check Sources

When a workbook change affects business meaning, compare against:

- the project source-of-truth specification
- the upstream generator or calculation scripts
- approved prior-period workbooks or workpapers
- any documented accounting, reporting, or reconciliation policy

The workbook is done only when Excel recalculation still agrees with those sources.

## 10. Done Criteria

- Excel recalculation matches source-of-truth outputs.
- Critical cells do not contain unexplained `#N/A` or blanks.
- The workbook still explains the calculation from input to output.
