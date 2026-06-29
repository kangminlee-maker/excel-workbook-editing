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

For MCP, MCPB, Claude-compatible tool authoring, or repository JSON schemas
intended for MCP/Claude tool projection, consult:

- `docs/mcp-mcpb-authoring-guide.md`

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

## MCP And Schema Authoring Rules

- Use MCP tool names in `namespace_verb` form matching
  `^[a-zA-Z0-9_-]{1,64}$`.
- Use underscore-separated names for tool names, `user_config` keys, and tool
  input property names.
- Keep tool `input_schema` top-level definitions as direct object schemas.
- Use an `operation` enum plus server-side validation for variant behavior
  instead of top-level `oneOf`, `anyOf`, or `allOf`.
- Keep MCP-projectable repository schemas free of `oneOf`, `anyOf`, and
  `allOf`; use explicit fields plus deterministic validation code for variant
  behavior.

## ADR Location

Store architecture decisions in `docs/adr/` and use `docs/adr/README.md` for
the local format.
