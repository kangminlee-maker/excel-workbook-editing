# Google Sheets Parser Permission Requirements

Last updated: 2026-06-02

This document lists the permissions and broker contracts needed to continue the
connected Google Sheets document-understanding pipeline for the current target:

```text
Spreadsheet: [Day 1] 1.0 (from 20250707)
Spreadsheet ID: 1gp3jl_DyB8kvxHO7m4YjsCPbFTPGi-XKyqPhGAlTZ60
Principal / DWD subject: kangmin.lee@day1company.co.kr
Service account: day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com
Current broker policy version: parser-readonly-windows-2026-06-02
```

Do not store service account keys, OAuth tokens, access tokens, ID tokens,
Bearer headers, or raw credentials in this repository, review packages, logs, or
native messages.

## Current Verified Baseline

| Gate | Status | Evidence |
| --- | --- | --- |
| Cloud Run broker health | Verified | `broker-keyless-readiness.json` |
| `roles/iam.serviceAccountTokenCreator` for keyless DWD | Verified | Broker succeeds on the current policy-allowed target |
| DWD impersonation as `kangmin.lee@day1company.co.kr` | Verified | Broker auth summary and prior read-only DWD samples |
| Google Sheets read-only metadata access | Verified | `spreadsheets.readonly` path works |
| Broker operation for current target metadata | Verified | `inspect.metadata` is allowed |
| Broker operation for bounded grid/formula/value windows | Verified | `inspect.grid_window`, `inspect.values_window`, and `inspect.formula_window` succeeded for `26_0601!A1:Z80` |
| Drive metadata authority | Not yet secured | Needed only for owner/sharing/revision/dependency metadata |
| Apps Script project authority | Not yet secured | Needed only for bound script or trigger analysis |
| Write/apply authority | Not yet secured | Not needed for read-only parsing; required for approved in-place edits |

## Authority Model

| Layer | Requirement | Why it matters |
| --- | --- | --- |
| User identity | Every broker request must identify and verify the end-user principal. | The broker must know who is asking. |
| Google resource access | Broker uses Cloud Run runtime identity plus DWD with `subject` equal to the verified user. | Google ACLs and version history align with the real user. |
| Broker policy | Default-deny allowlist for principal, operation, sheet id, range, field mask, timeout, retry, risk level, and cell budgets. Spreadsheet reachability is delegated to the impersonated user's Google ACL for read-only parser operations. | Sheets API scopes cannot be limited to one tab or range, so parser-window control must live here. |
| Local artifacts | Store sanitized summaries, schemas, request ids, policy decisions, and evidence refs only. | Review packages remain auditable without leaking credentials. |

## Requirement Matrix

| Area | Needed for | Google / IAM requirement | Broker contract requirement | Current state |
| --- | --- | --- | --- | --- |
| Metadata inspect | Spreadsheet title, locale, time zone, tab list, sheet ids, dimensions, hidden tab state, named ranges, protected ranges. | Cloud Run runtime service can sign DWD tokens; DWD scope `https://www.googleapis.com/auth/spreadsheets.readonly`. | Allow `inspect.metadata` for the principal and spreadsheet id. Return request id, auth summary, policy summary, and normalized metadata schema. | Ready. |
| Grid/value/formula windows | View-state profiling, formula/dataflow profiling, table boundary candidates, cross-validation inputs. | Same read-only Sheets scope as metadata. | `inspect.grid_window`, `inspect.values_window`, and `inspect.formula_window` are allowed for the pilot principal through bounded policy limits. Policy limits sheet ids/ranges, max ranges per request, max cells per request, max total cells per run, timeout, retry, and grid field masks. | Ready for bounded parser samples. |
| Pivot, filter, slicer, chart, banded range, validation, protection metadata | Document-shaped object evidence and dependency risk scan. | Usually covered by `spreadsheets.readonly` when fetched through Sheets API metadata/gridData. Confirm any missing object fields during implementation. | Expose object fields through a broker operation such as `inspect.objects` or a versioned extension of `inspect.metadata`. | Partially available through direct read-only DWD sample; broker contract still needed. |
| `IMPORTRANGE` and external Sheet sources | Source/output pipeline tracing across connected spreadsheets. | `spreadsheets.readonly`; the impersonated user must have Google ACL access to each source spreadsheet. | After source IDs are enumerated, allow each source spreadsheet id and classify states as `loaded`, `loading`, `permission_blocked`, `source_blocked`, `broken`, or `stale_unverified`. | Source allowlist not yet secured. |
| Drive metadata | Owner, sharing, parent folder, file metadata, revision metadata, rollback context, and dependency inventory. | Add the narrowest viable Drive metadata scope, usually `https://www.googleapis.com/auth/drive.metadata.readonly`. Broader Drive scopes require separate justification. | Add `inspect.drive_metadata` with file-id allowlist, fields allowlist, no file content export by default, and sanitized permission metadata. | Optional gap. |
| Apps Script project metadata/content | Bound script inventory, manifest scopes, custom function detection, trigger/dependency analysis. | Enable Apps Script API and add `https://www.googleapis.com/auth/script.projects.readonly` if project metadata or content is required. Trigger inspection may need a separate method and scope decision; confirm before requesting. | Add `inspect.apps_script` with script-id allowlist, returned-file limits, manifest/code redaction policy, and no script execution. | Optional gap. |
| Apply Plan write mode | Approved in-place edits, formula fixes, range updates, formatting/protection changes. | Add `https://www.googleapis.com/auth/spreadsheets` only for write/apply phases. | Add plan/apply operations with human approval evidence, precondition re-read, range-scoped write batches, protected-range checks, readback, before-state artifact, rollback instructions, and audit log. | Not needed for current read-only parsing. |
| Drive copy/export/import or rollback clone | Explicit clone, copy, export, or replacement workflows. | Scope depends on chosen operation; do not request broad Drive write by default. | Separate operation and approval path. Must not be used as a workaround for live read gaps. | Out of scope unless explicitly requested. |
| External data sources such as BigQuery-connected Sheets | Data-source object analysis and refresh/dependency checks if discovered. | Source-specific API permissions may be required. Do not infer until the Sheet exposes the dependency. | Separate operation and policy gate for each external system. | Unknown until discovered. |

## Immediate Requirements To Secure

1. Keep the verified broker-backed keyless DWD path:
   - Cloud Run broker health remains OK.
   - Runtime service account keeps `roles/iam.serviceAccountTokenCreator`.
   - DWD subject remains the verified principal.

2. Keep broker read contracts for bounded grid/formula/value windows on the
   current spreadsheet:
   - Principal: `kangmin.lee@day1company.co.kr`
   - Spreadsheet ID: delegated to Google ACL through wildcard policy for
     read-only parser operations
   - Operations: `inspect.grid_window`, `inspect.values_window`,
     `inspect.formula_window`
   - Current policy limits:
     - max ranges per request: `8`
     - max cells per request: `20000`
     - max total cells per run: `120000`
     - max timeout seconds: `60`
     - max retries: `1`
     - allowed grid field masks: `grid_basic_v1`, `grid_formula_v1`
     - allowed ranges: `*`, bounded by cell budgets
     - allowed sheet ids: `*`, bounded by Google ACL and cell budgets

3. Add Drive metadata only if the next parser pass must inspect sharing,
   ownership, parent folders, or revision/rollback context.

4. Add Apps Script readonly only if the next parser pass must inspect bound
   script projects, script manifests, or custom-function implementations.

5. Add source spreadsheet allowlist entries only after formulas enumerate actual
   `IMPORTRANGE` or external spreadsheet IDs.

## Stop Conditions

Stop and ask for permission or a broker policy update before continuing if any
of these occur:

- A required operation is missing from broker policy.
- A required spreadsheet id, sheet id, or range is outside policy.
- A source spreadsheet referenced by `IMPORTRANGE` is not accessible to the DWD
  subject or not allowed by broker policy.
- Drive metadata, Apps Script, write/apply, copy, export, or external data-source
  evidence is needed but the relevant scope/operation has not been approved.
- The only available path would be DOM scraping, `.xlsx` export/import, document
  replacement, service-account direct sharing, or local credential handling.

## Verification Checklist

Before treating a permission as ready, produce sanitized evidence for:

- Broker health check.
- Broker metadata inspect for the current spreadsheet.
- Broker bounded grid/value/formula sample with schema validation.
- Source spreadsheet smoke read for each allowed `IMPORTRANGE` source.
- Drive metadata smoke read, if Drive metadata was approved.
- Apps Script metadata/content smoke read, if Apps Script was approved.
- For write/apply phases only: dry-run plan, explicit human approval,
  precondition re-read, write execution, live readback, before-state artifact,
  and rollback instructions.

## Official Scope References

- Google Sheets API scopes:
  https://developers.google.com/workspace/sheets/api/scopes
- Google Drive API scopes:
  https://developers.google.com/workspace/drive/api/guides/api-specific-auth
- Drive `files.get` metadata scopes:
  https://developers.google.com/workspace/drive/api/reference/rest/v3/files/get
- Apps Script `projects.getContent` scopes:
  https://developers.google.com/apps-script/api/reference/rest/v1/projects/getContent
- Apps Script scope guidance:
  https://developers.google.com/apps-script/concepts/scopes

## Current Parser Window Evidence

Verified on 2026-06-02 through Cloud Run revision
`run-mcp-day1-development-sheets-bridge-broker-00014-v84`:

Evidence file:

```text
review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/parser-window-permission-smoke.json
```

| Operation | Range | Result | Evidence summary |
| --- | --- | --- | --- |
| `inspect.metadata` | spreadsheet metadata | Passed | Title `[Day 1] 1.0 (from 20250707)`, 52 tabs, policy `parser-readonly-windows-2026-06-02` |
| `inspect.grid_window` | `'26_0601'!A1:Z80` | Passed | `includeGridData=true`, field mask `grid_basic_v1`, one sheet window returned |
| `inspect.values_window` | `'26_0601'!A1:Z80` | Passed | `valueRenderOption=FORMATTED_VALUE`, 80 rows returned |
| `inspect.formula_window` | `'26_0601'!A1:Z80` | Passed | `valueRenderOption=FORMULA`, 80 rows returned |
| `inspect.values_window` | `'26_0601'!A1:ZZ100` | Denied | Broker policy returned `range_too_large` before Sheets API read |

Parser window snapshots use:

```text
schemas/google-sheets-parser-window.schema.json
```
