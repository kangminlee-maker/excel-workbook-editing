# Connected Google Sheets Principles

Read `references/spreadsheet-principles.md` first. This file covers existing Google Sheets, connected-document identity, live dependencies, operational risks, and verification.

## 1. Existing Sheets Are Connected Documents

An existing Google Sheet is not just a spreadsheet-shaped file. Preserve:

- `spreadsheetId`
- tab-level `sheetId` values
- sharing and permissions
- named ranges
- protected ranges
- data validations
- filters, filter views, charts, pivot tables, and slicers
- formulas that reference other documents or services
- Apps Script bindings, add-ons, triggers, dashboards, and webhooks

Do not download an existing Google Sheet to `.xlsx`, edit locally, and upload it back as the default workflow. That can create a different document and break links, permissions, script bindings, `IMPORTRANGE` approvals, dashboards, and external automation.

Use `.xlsx` import only for new standalone Sheets, explicit clones, or explicit replacement workflows.

## 2. Read

Before editing, confirm:

- exact spreadsheet URL or id
- target tabs and `sheetId` values
- ranges, headers, formulas, validations, protections, and named ranges
- filter views, pivot tables, charts, slicers, and hidden rows/columns
- connected-document risks such as `IMPORTRANGE`, import functions, `QUERY`, `ARRAYFORMULA`, `INDIRECT`, custom functions, Apps Script, and dashboards

Prefer narrow A1 ranges, field masks, and chunked reads for large Sheets.

## 3. Create

- Create new standalone Sheets only when the user asks for a new artifact.
- For clones or replacements, state that identity and connected dependencies may change.
- Rebuild validations, protected ranges, formulas, charts, filters, and Apps Script-connected behavior only when required and verifiable.

## 4. Update

- Prefer in-place connector/API updates against existing ranges.
- Write only needed cells, formulas, formats, or validations.
- Preserve formulas unless replacing them is the requested behavior.
- Check validation-backed cells before choosing replacement values.
- Avoid deleting/recreating tabs unless the user accepts the identity and dependency risk.

## 5. Delete

- Treat row, column, range, tab, named-range, and protected-range deletion as dependency-risky.
- Check formulas, dashboards, Apps Script, imports, filters, pivot tables, and external automations before deletion.
- Prefer clearing narrow values over deleting structure when dependencies are uncertain.

## 6. Operational Risks

Large or connected Sheets can fail because of:

- API timeouts or quota limits
- oversized reads/writes
- import functions still loading
- `IMPORTRANGE` permission blocks
- Apps Script or custom function delays
- external dashboards or automations
- rollback-sensitive edits

Set timeout, retry, polling, and rollback expectations before touching large or externally linked spreadsheets.

Classify external data states as:

- loaded
- loading
- permission_blocked
- source_blocked
- broken
- stale_unverified

## 7. Verification

- Re-read changed ranges from the same live spreadsheet.
- Re-read dependent outputs when formulas or dashboards matter.
- Verify formulas, validations, protections, and loading states when they are part of the change.
- Capture rollback snapshots for risky edits.
- Report quota, timeout, import loading, Apps Script, and connected-dashboard risks when they cannot be fully verified.

## 8. Done Criteria

- The intended spreadsheet identity was preserved or replacement was explicitly requested.
- Changed ranges were read back from the live spreadsheet.
- Important formulas and dependent outputs are correct or explicitly unverified.
- External loading, permission, quota, Apps Script, rollback, and dashboard risks are documented when relevant.
