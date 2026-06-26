# Google Sheets Parser Permission Requirements

This document lists current permission requirements for connected Google Sheets
parser work through approved external access surfaces.

## Required Authority

- The user or approved principal must have Google Sheets access to the target
  spreadsheet and any source spreadsheets used by formulas such as
  `IMPORTRANGE`.
- Approved external access surfaces own Google authentication, scopes, policy
  gates, write gates, and Google API calls. This repository consumes sanitized
  credential-free evidence/results only.
- The authority path must allow only the required spreadsheet ids, sheet ids,
  ranges, scopes, and operations for the requested task.
- Local agents must consume sanitized credential-free results or review-package
  artifacts, not Google credentials.

## Parser Operations

| Operation | Requirement |
| --- | --- |
| Metadata inspect | Spreadsheet id, title, locale, timezone, sheet ids, sizes, hidden states, and named ranges are allowed. |
| Values window | Bounded ranges only; large ranges require chunking. |
| Formula window | Formula text is evidence only; formula-result authority requires effective values or a recalculation authority. |
| Grid window | Formatting, merges, validations, notes, hidden rows/columns, and effective values may be captured when authority allows. |
| Source lineage | External source spreadsheets require their own ACL and approved access scope. |
| Apps Script or automation metadata | Requires separate authority; absence of evidence is not evidence of absence. |

## Required Defaults

- Use an approved external access surface for live spreadsheet access.
- Keep local artifacts credential-free.
- Treat formula text as evidence and use effective values, recalculation, or
  another approved result source for formula-result authority.
- Promote semantic or causal claims only when source lineage, freshness, and
  result authority are supported by evidence.
