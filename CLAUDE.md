# CLAUDE.md

Claude agents working here follow `AGENTS.md`.

## Required Runtime References

For Excel workbook or spreadsheet CRUD work, consult:

- `references/spreadsheet-principles.md`
- `references/excel-workbook-principles.md`
- `references/spreadsheet-review-package.md`

For connected Google Sheets behavior, consult:

- `references/connected-google-sheets-principles.md`

For the current connected-Sheets processing boundary, consult:

- `docs/data-processing-spreadsheet-package-design.md`

## Credential Boundary

Claude agents consume local Excel files, review-package JSON, and
credential-free spreadsheet evidence/results.

Credential-bearing material stays inside approved external access surfaces:

- tokens
- bearer headers
- cookies
- raw credential material

## Current Product Surface

- Approved external spreadsheet access surfaces own Google Drive and Google
  Sheets access, authentication, policy, write gates, and Google API calls.
- This repository owns Excel/spreadsheet processing, evidence interpretation,
  formula/dataflow discovery, validation artifacts, and review packages.
- User-facing table creation follows neutral processing contracts after host
  runtime fields are split from table-builder artifacts.
- Spreadsheet value authority comes from Google Sheets live readback or real
  Microsoft Excel recalculation, according to artifact type.

## ADR Location

Store architecture decisions in `docs/adr/` and use `docs/adr/README.md` for
the local format.
