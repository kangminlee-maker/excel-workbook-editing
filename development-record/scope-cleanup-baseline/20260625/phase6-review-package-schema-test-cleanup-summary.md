# Phase 6 Review Package, Schema, And Test Cleanup Summary

Date: 2026-06-26

## Goal

Keep active review packages, schemas, and tests focused on spreadsheet
processing while preserving runtime-coupled Sheets Bridge evidence as
development records.

## Active Review Packages Kept

- `review-packages/spreadsheet-processing/live-inspections/test-*`
- `review-packages/workbook-understanding/`

## Moved To Development Record

- `review-packages/sheets-bridge/*`
- `review-packages/spreadsheet-processing/live-inspections/20260602-day1-1-0`
- `review-packages/spreadsheet-processing/formula-dataflow`
- `review-packages/spreadsheet-processing/initial-understanding`
- `review-packages/spreadsheet-processing/table-io-flow-real-sheet`
- `review-packages/spreadsheet-table-builder`
- `review-packages/workbook-understanding/process-ledger.jsonl`

## Active Contract Cleanup

- `schemas/apply-result.schema.json`
- `schemas/edit-plan.schema.json`
- `schemas/inspection.schema.json`
- `schemas/google-sheets-parser-window.schema.json`
- `tests/test_inspection_schema.py`
- `tests/test_table_builder_contracts.py`

## Verification Gate

Active grep for Sheets Bridge review-package paths, MCP handoff terms, broker
terms, and host smoke package names must return no matches outside
`development-record/` and the cleanup plan. Remaining tests and schema/script
checks must pass.
