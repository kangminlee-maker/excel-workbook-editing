# Pilot Broker Policy

## Observed Pilot Allowlist

| Field | Value |
| --- | --- |
| Policy version | `phase1-pilot-2026-06-01` |
| Principal | `kangmin.lee@day1company.co.kr` |
| Spreadsheet id | `16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg` |
| Allowed operation | `inspect.metadata` |
| Sheet ids | Not applicable for `inspect.metadata`; current env wildcard is metadata-only and must not be copied to range-read/write operations |
| Ranges | Not applicable for `inspect.metadata`; current env wildcard is metadata-only and must not be copied to range-read/write operations |
| Max risk | `low` |

## Required Pilot Behavior

- The pilot user can inspect only the allowed spreadsheet through the broker.
- The broker verifies the Chrome identity evidence on every inspect call.
- The broker DWD subject must equal the verified user principal.
- Policy authorization uses only broker-derived `verified_identity.principal`.
- Client-provided `identity_hint` is advisory and cannot authorize policy.
- Unknown users must be denied before Sheets API calls.
- Unknown spreadsheets must be denied before Sheets API calls.
- Operations other than `inspect.metadata` must be denied.

## Expansion Requirement

Do not expand this policy to a broader group until the approval-day smoke test
records both an allowed inspect result and an unauthorized deny result.
