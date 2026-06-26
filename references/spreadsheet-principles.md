# Spreadsheet Principles

Use this file first for spreadsheet work. It covers rules shared by Excel workbooks, workbook generators, connected Google Sheets, and review packages.

Artifact-specific details live in:

- `references/excel-workbook-principles.md`
- `references/connected-google-sheets-principles.md`
- `references/spreadsheet-review-package.md`

## 1. Source Of Authority

- Identify the authoritative logic before editing: spec, approved workbook, source data, script, policy, or user-provided invariant.
- Identify the artifact identity before editing: local `.xlsx` path, workbook template, generator output, Google `spreadsheetId`, tab `sheetId`, or review package output.
- Do not let a convenience export become the new authority unless the user explicitly asks for a clone, replacement, or derived report.
- Treat spreadsheets as calculation and review systems, not just tables.

## 2. Agent Workflow

For every spreadsheet task:

1. Identify the artifact type and identity that must be preserved.
2. Inspect source files, workbook structure, connected sources, and review purpose.
3. Separate inputs, parameters, intermediate calculations, outputs, carryovers, and limitations.
4. Choose the lowest-risk edit surface.
5. Apply the smallest coherent edit.
6. Validate with the artifact's real engine or live readback.
7. Record unresolved row IDs, source gaps, dependency risks, and review questions.

## 3. Read

- Inspect before flattening unfamiliar spreadsheet artifacts.
- Read sheet names, dimensions, hidden sheets, formulas, named ranges, validations, protected ranges, merged ranges, tables, filters, external links, charts, images, and object anchors when they may carry meaning.
- Prefer narrow reads around the target range when the artifact is large.
- Do not flatten a workbook or live spreadsheet into a dataframe before checking whether structure carries meaning.

## 4. Create

- Build new artifacts from explicit inputs, parameters, intermediate calculations, and outputs.
- Keep generated workbooks explainable to a human reviewer.
- Use stable identities and deterministic generation paths when artifacts will be regenerated.
- Keep review package artifacts separate from source workbooks or live Sheets.

## 5. Update

- Patch the smallest range, structure, or script surface that solves the task.
- Cluster related edits into a coherent operation when the platform supports it.
- Preserve formulas, lookup keys, named ranges, array formulas, validations, protections, formatting, and reviewer-facing layout unless explicitly changing them.
- Do not overwrite formulas with displayed values unless that is the requested behavior.
- Normalize join keys explicitly when source data may mix numeric and text IDs.
- Treat blank, error, and zero outputs as different states until proven equivalent.

## 6. Delete

- Avoid whole-sheet replacement, tab recreation, workbook regeneration, or live Sheet deletion when a range-scoped edit preserves more context.
- Do not delete hidden sheets, helper ranges, named ranges, validations, or protected ranges until their role is understood.
- For existing Google Sheets, deletion can break dashboards, scripts, `IMPORTRANGE`, and tab-level `sheetId` dependencies.

## 7. Validation

- Excel formulas require Microsoft Excel validation when calculated results matter.
- Existing Google Sheets require live readback from the same spreadsheet.
- Static inspection can prove structure and formulas were written; it cannot prove all computed results.
- Use schema validation for generated JSON artifacts.
- Run formula error scans when Excel formula correctness matters.
- Report unverified risks explicitly instead of implying validation happened.

## 8. Evidence And Done Criteria

When agent-visible evidence is needed, create a review package that separates:

- artifact identity
- structure and dependency inventory
- key values and formulas
- validation or readback status
- formula and connected-document risks
- before/after summaries
- static HTML or Markdown previews

Done means:

- The intended artifact was edited or generated.
- The artifact identity that matters was preserved.
- Important formulas still point to intended inputs and named ranges.
- Critical outputs were validated through Excel recalculation or Google Sheets live readback when those outputs matter.
- Remaining formula errors, source gaps, manual overrides, and connected risks are documented.
