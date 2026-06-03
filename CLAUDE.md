# CLAUDE.md

Claude agents working here must follow `AGENTS.md`.

## Required References

For Excel workbook or spreadsheet CRUD work, consult the relevant files in `references/`:

- `references/spreadsheet-principles.md`
- `references/excel-workbook-principles.md`
- `references/spreadsheet-review-package.md`

For connected Google Sheets behavior, also consult:

- `references/connected-google-sheets-principles.md`

For Chrome Sheets Bridge or native-host review packages, also consult:

- `docs/claude-code-sheets-bridge.md`
- `docs/chrome-extension-sheets-bridge-design.md`
- `native-host/README.md`

Claude agents must consume only sanitized bridge artifacts such as
`manifest.json` and `snapshot.json`. Do not request, store, echo, or derive
OAuth tokens, ID tokens, access tokens, bearer headers, service account keys,
private keys, cookies, or raw DWD credentials.

## ADR Location

Store architecture decisions in `docs/adr/` and use `docs/adr/README.md` for the local format.
