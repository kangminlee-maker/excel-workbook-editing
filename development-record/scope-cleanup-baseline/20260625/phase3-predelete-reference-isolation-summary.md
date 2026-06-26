# Phase 3 Pre-Delete Reference Isolation Summary

Date: 2026-06-25

## Goal

Prepare runtime directory cleanup by removing active references to retired
Sheets Bridge MCP, host adapter, packaging, and hosted broker authority files.

## Moved To Development Record

- `docs/mcp-sheets-bridge-design.md` ->
  `development-record/retired-sheets-bridge/docs/mcp-sheets-bridge-design.md`
- `docs/mcp-sheets-bridge-remote-auth-runbook.md` ->
  `development-record/retired-sheets-bridge/docs/mcp-sheets-bridge-remote-auth-runbook.md`
- `docs/workload-identity-runtime-contract.md` ->
  `development-record/retired-sheets-bridge/docs/workload-identity-runtime-contract.md`
- `schemas/table-builder-host-message.schema.json` ->
  `development-record/retired-sheets-bridge/schemas/table-builder-host-message.schema.json`
- `schemas/table-builder-session.schema.json` ->
  `development-record/retired-sheets-bridge/schemas/table-builder-session.schema.json`
- `tests/test_table_builder_host_adapter_js.py` ->
  `development-record/retired-sheets-bridge/tests/test_table_builder_host_adapter_js.py`

## Classification Update

`cleanup-classification.tsv` now includes the retired active docs that were
found by the pre-delete active-reference grep. Host schema and host adapter test
rows were already classified as `move_to_development_record`.

## Next Gate

Before removing `mcp/`, `packaging/sheets-bridge-mcp/`, and
`broker/cloud-run-sheets-broker/`, active reference grep must return no matches
outside `development-record/` and the cleanup plan itself.
