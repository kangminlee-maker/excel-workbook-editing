# Spreadsheet Review Packages

Use this file when spreadsheet work needs agent-visible evidence without requiring a human to open Excel or Google Sheets during review.

The package is evidence, not the source of truth. The source of truth remains the `.xlsx` workbook, generator code, or live Google Sheet.

## 1. Suggested Structure

```text
review-package/
├── index.html
├── summary.md
├── artifact-identity.json
├── structure.json
├── key-values.json
├── formulas.json
├── validation-status.json
├── risks.json
├── previews/
└── diffs/
```

Add PNG or PDF previews only when visual layout materially helps review.

## 2. Include

- requested change summary
- artifact identity and preserved IDs
- sheet/range inventory
- key input, calculation, and output cells
- important formulas, named ranges, validations, and protections
- formula errors or connected-document risks
- Excel recalculation status or Google Sheets live readback status
- before/after tables for changed ranges
- known limitations, source gaps, manual overrides, and unresolved review items

## 3. Visualization

- Prefer static HTML tables for range previews.
- Use Markdown for short summaries and status logs.
- Use JSON for reproducible structure, formulas, risks, and key values.
- Keep previews narrow and reviewer-facing.
- Distinguish blank, zero, error, and missing values visibly.

## 4. Validation Language

Use precise wording:

- "Validated with Microsoft Excel recalculation" only after real Excel ran.
- "Verified by Google Sheets live readback" only after reading the live document.
- "Structure inspected only" when formulas or outputs were not recalculated.
- "External data still loading" when imports or custom functions have not resolved.
- "Connected-document risk unverified" when scripts, triggers, webhooks, or dashboards could not be checked.

## 5. Done Criteria

- The package opens locally through `index.html` when HTML is included.
- The summary names the artifact, changed ranges, and validation method.
- Key formulas, values, risks, and before/after evidence are present.
- Missing engine validation or connected-document verification is explicit.
- Timeout/quota retry history and rollback status are explicit when the artifact
  is a connected Google Sheet.
