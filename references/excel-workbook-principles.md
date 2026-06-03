# Excel Workbook Principles

Read `references/spreadsheet-principles.md` first. This file covers `.xlsx` files, workbook generators, Excel formula behavior, reconciliation, and Microsoft Excel validation.

## 1. Workbook Purpose

- A workbook is both a calculation surface and a review surface.
- Complex logic should remain inspectable as `input -> config -> bridge/calc -> output`.
- Known source limitations should stay visible rather than hidden in formula patches.
- Do not replace an explainable workbook with copied totals unless the user explicitly requests a static report.

## 2. Read

Use the cheapest read path that preserves the evidence needed.

- Fast ZIP/XML manifest: use before expensive full workbook loading on large files.
- `openpyxl` `read_only=True`: use for large row/value/formula-text sampling.
- Targeted XML parsing: use for styles, shared formulas, drawing anchors, media, table parts, and oversized sheets.
- `openpyxl` normal mode: use for template-sized structural inspection or deterministic edits.
- Excel render capture: use when visual layout is an authority.

Before editing unfamiliar workbooks, inspect sheets, dimensions, hidden sheets, formulas, named ranges, merged ranges, tables, validations, conditional formatting, charts, images, external links, and pivot/cache objects.

## 3. Create

- Build around raw inputs, visible parameters, intermediate calculations, and outputs.
- Use explicit input/config/bridge/output/limitations layers for complex workbooks.
- Keep prior-period carry-ins, current-period raw inputs, and carry-outs separated when rollforward behavior matters.
- Use deterministic generator code for repeatable workbook construction.

## 4. Update

- Prefer generator or workbook-structure patches over manual one-off repairs when the artifact will recur.
- Preserve sheet names, named ranges, formulas, validations, formatting, hidden structure, print/review layout, and Excel-native objects unless explicitly changing them.
- Use `openpyxl` for deterministic structural writes such as formulas, names, formats, validations, tables, and seed data.
- Use a safe copy first for complex templates with macros, pivot tables, external connections, or native objects.

## 5. Delete

- Do not delete sheets, helper columns, named ranges, validations, pivot caches, media, or hidden structures before confirming they are not wired into formulas or review workflows.
- Prefer marking limitations or deprecating unused surfaces over removing ambiguous workbook structures.
- Treat source-file selection and source-binding as part of workbook correctness.

## 6. Formula Defaults

- Use defined names for important ranges, lookup domains, config cells, and single values.
- Prefer compatibility-safe formulas such as `INDEX/MATCH + IFERROR` when the target Excel version is uncertain.
- Normalize join IDs with explicit text key columns such as `transaction_id_key`.
- Store comparison dates as real Excel dates, not strings.
- Avoid performance-heavy whole-column diagnostics unless necessary.
- If a bridge may be empty, design downstream aggregates to return explicit zero rather than blank or missing values.
- Confirm first-hit versus last-hit lookup behavior when keys are not unique.
- Treat formula text as logic, not as calculated truth.

## 7. Reconciliation And Debugging

Classify mismatches before changing formulas:

- source gap
- workbook wiring bug
- formula logic bug
- Excel behavior difference
- manual override
- accounting or policy question

Debug totals by decomposing them into source rows, bridge rows, exclusions, adjustments, and output formulas. Keep raw values and limitation-adjusted values visibly separate.

For recurring workbooks, make repeated manual fixes into code or explicit input surfaces.

## 8. Excel Engine Validation

`openpyxl` can write formulas but does not prove calculated results. Use the real Microsoft Excel engine when formula outputs matter.

Preferred local wrapper:

```bash
python3 scripts/excel_engine_sample.py /path/to/workbook.xlsx 1 A1 B2 C10
```

Validation loop:

1. Generate or edit the workbook.
2. Open a temporary copy in Excel when possible.
3. Run full recalculation.
4. Read only representative cells and key aggregates.
5. Run a formula error scan.
6. Compare against the authoritative logic.

Automation cautions:

- Do not rely on desktop automation in headless/server contexts.
- Avoid broad workbook scans through Excel automation.
- Ask the user not to edit the workbook while automation is running.
- If Excel is unavailable, report formula-result validation as incomplete.

## 9. Failure Patterns

Watch for:

- hard-coded references drifting after row or column insertions
- formulas pointing to the wrong sheet or period
- numeric-versus-text key mismatches
- dates stored as text or containing time fractions
- empty bridges causing blanks instead of zeroes
- stale formulas or cached values
- external links or source resolver drift
- hidden sheets or names still wired into outputs

## 10. Done Criteria

- Workbook structure and formulas are inspectable.
- Critical formulas recalculate correctly in Excel when formula results matter.
- Formula errors are absent or intentionally documented.
- Important sheets are actually wired into the active calculation path.
- Known limitations, manual steps, and unverified risks are explicit.
