# Chrome Extension Managed Deployment Work Design

This document is the execution design for moving Chrome Sheets Bridge from a
tester-published Chrome Web Store item to a managed internal release. It covers
the work prepared before tester publication, the actions to take during the
tester pilot, and the completion criteria for the first internal pilot.

Use this document together with:

- `docs/codex-goal-chrome-extension-sheets-bridge.md`
- `docs/chrome-extension-sheets-bridge-design.md`
- `docs/chrome-extension-sheets-bridge-work-plan.md`

## 1. Goal

Prepare the internal deployment path so that approved Day1 testers can install
the extension, verify the Cloud Run broker path, inspect an allowed Google Sheet
through the impersonated user, and rollback safely if the pilot fails.

## 2. Current Known Inputs

These inputs are identifiers and deployment settings, not secrets.

| Item | Value |
| --- | --- |
| Extension name | `Chrome Sheets Bridge` |
| Chrome extension id | `jahlkdjaokmjbipfhlhnjggcgjmpeiij` |
| Chrome Web Store visibility target | Private internal distribution |
| Chrome Web Store tester status | Published to testers on 2026-06-03 by user report; pilot install and E2E evidence still pending |
| Chrome Web Store update URL | `https://clients2.google.com/service/update2/crx` |
| Repo next package candidate | `0.1.1`, aligning extension broker calls to `X-Broker-Authorization` |
| GCP project | `day1-dev` |
| Broker service | `run-mcp-day1-development-sheets-bridge-broker` |
| Broker region | `asia-northeast3` |
| Broker URL | `https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app` |
| Broker DWD service account | `day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com` |
| Broker DWD service account OAuth2 client id | `106391233015635066062` |
| Chrome OAuth client id | `862894425240-1r90upabo0gb42t41p7gj36dp1r37j24.apps.googleusercontent.com` |
| Local CLI OAuth audience | `32555940559.apps.googleusercontent.com` |
| Managed OAuth binding status | Ready for pilot confirmation; Chrome UI or broker evidence must still prove the active extension id and OAuth client binding |
| DWD scope for current inspect path | `https://www.googleapis.com/auth/spreadsheets.readonly` |
| First pilot user | `kangmin.lee@day1company.co.kr` |
| First pilot spreadsheet id | `16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg` |

Do not add service account keys, OAuth tokens, bearer tokens, cookies, refresh
tokens, or private keys to this document.

## 3. Deployment Authority Model

The tester-published internal release keeps the same authority split as the main
goal spec.

| Layer | Authority | Deployment implication |
| --- | --- | --- |
| Chrome Web Store | Hosts and updates the extension package for testers and later internal users | Internal users install a reviewed fixed extension id |
| Google Admin Console | Decides which users or browsers may install the extension | SRE/Admin applies allowlist or force-install policy |
| Chrome Extension | Detects the active Sheet and obtains user identity evidence | The extension never calls Sheets API directly |
| Cloud Run broker | Verifies identity, policy, and DWD subject before Google API calls | All Sheets API traffic goes through broker checks |
| Workspace DWD | Lets the broker impersonate the verified user | Google ACL and version history align to the actual user |
| Local CLI | Uses the current `gcloud` account identity token as evidence for pre-extension smoke tests | Calls only the broker through `X-Broker-Authorization`; it never calls Sheets API directly |
| Local agent/native host | Receives sanitized snapshots and persists artifacts | No credentials or raw authority material are written locally |

## 4. Workstream Overview

The work is split into five workstreams so tester-pilot execution does not
require path discovery.

| Workstream | Owner | Prepared before tester publication | Done when |
| --- | --- | --- | --- |
| A. Admin distribution | Workspace Admin/SRE | Prepare policy target, OU/group, and install mode | Extension appears in `chrome://policy` for pilot users |
| B. Broker readiness | Infra/SRE + Codex | Confirm health, env, DWD, and policy shape | `/v1/health` passes and unauthorized inspect returns structured JSON |
| C. Pilot policy | Codex + SRE | Prepare allowlist patch for pilot user and spreadsheet | Pilot user is allowed; unknown user/spreadsheet is denied |
| D. Smoke test | Codex + pilot user | Prepare test script and expected evidence | Extension inspect returns sanitized metadata for the pilot Sheet |
| E. Rollback/observability | SRE + Codex | Prepare rollback commands and log checks | Extension or broker can be disabled quickly with evidence retained |

## 5. Pilot Readiness Work

### A. Admin Distribution Preparation

Prepare or confirm the request for Workspace Admin before managed tester install.

Inputs:

- extension id: `jahlkdjaokmjbipfhlhnjggcgjmpeiij`
- update URL: `https://clients2.google.com/service/update2/crx`
- initial install mode: `normal_installed` or `force_installed`
- pilot target: a small Google Group or OU, not the whole company

Recommended default:

- use a pilot Google Group first
- use allowed install or normal install for the first smoke test
- switch to force install only after the smoke test passes

Current decision state:

| Decision | Status |
| --- | --- |
| Pilot Google Group or OU | `TBD` |
| First install mode | `TBD`, default recommendation is allowed install or normal installed |
| Admin rollback owner | `TBD` |

Pilot start is blocked until the target group or OU and install mode are
explicitly named.

Admin policy string when a raw force-install entry is needed:

```text
jahlkdjaokmjbipfhlhnjggcgjmpeiij;https://clients2.google.com/service/update2/crx
```

Completion criteria:

- Target OU or group is named.
- Install mode is chosen.
- Admin knows not to deploy company-wide until pilot smoke tests pass.
- `chrome://policy` verification steps are ready.

### B. Broker Readiness Preparation

Confirm the broker is reachable before any user rollout.

Expected service:

```text
run-mcp-day1-development-sheets-bridge-broker
```

Expected checks:

```bash
curl -fsS https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app/v1/health
curl -sS -X POST https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app/v1/inspect
```

Expected results:

- health returns `ok: true`
- unauthenticated inspect returns a structured `identity_evidence_failed` error
- no HTML error page is returned from the broker endpoint

Completion criteria:

- Current Cloud Run revision is known.
- Runtime environment includes the expected broker audience, hosted domain, DWD
  service account email, broker policy JSON, and local CLI additional audience.
- Logs are queryable for request id, principal, spreadsheet id, policy decision,
  and error code.
- Structured broker audit events exclude bearer tokens, OAuth tokens, service
  account keys, private keys, cookies, refresh tokens, and raw credentials.
- Managed OAuth binding evidence proves that the active `BROKER_AUDIENCE`
  matches the Chrome App OAuth client id bound to extension id
  `jahlkdjaokmjbipfhlhnjggcgjmpeiij`.
- Local Codex/gcloud readiness evidence proves that
  `BROKER_ADDITIONAL_AUDIENCES` accepts the Cloud SDK OAuth client id for
  extension-free smoke tests.
- Client identity evidence uses `X-Broker-Authorization` so Cloud Run/IAM
  request authentication stays separate from broker user verification.
- Authenticated DWD readiness evidence proves IAM `signJwt`, Workspace DWD
  scope, token minting, and read-only metadata inspect for the pilot user.

Required SRE IAM binding for the current keyless DWD shape:

```bash
gcloud iam service-accounts add-iam-policy-binding \
  day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com \
  --project=day1-dev \
  --member=serviceAccount:day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com \
  --role=roles/iam.serviceAccountTokenCreator
```

Required Workspace Admin DWD entry:

```text
Client ID: 106391233015635066062
Scope: https://www.googleapis.com/auth/spreadsheets.readonly
```

### C. Pilot Broker Policy Preparation

Prepare a narrow first policy. Do not start with broad domain access.

Initial pilot policy behavior:

- allow only `kangmin.lee@day1company.co.kr`
- allow `inspect.metadata` for spreadsheets that the impersonated pilot user
  can access through Google ACL
- allow only `inspect.metadata`
- allow only read-only metadata path
- authorize only from broker-verified `verified_identity.principal`
- deny unknown users before Sheets API calls
- deny spreadsheet access when the impersonated user lacks Google access
- treat sheet ids and ranges as not applicable for `inspect.metadata` unless a
  future operation explicitly reads cell ranges

Completion criteria:

- Policy hash/version can be identified in broker response or logs.
- Pilot user allow path is documented.
- At least one deny-path test is planned.
- A request with only `identity_hint` is denied by policy.

### D. Smoke Test Design

The first successful pilot should prove the complete authority path, not only
that the popup opens.

Smoke test steps:

1. Pilot user signs in to Chrome with the Day1 Workspace account.
2. Pilot user opens the allowed Google Sheet.
3. Pilot user opens the extension popup.
4. Extension extracts the active `spreadsheetId`.
5. Extension obtains user identity evidence.
6. Extension calls the Cloud Run broker.
7. Broker verifies identity and policy.
8. Broker impersonates the same user through DWD.
9. Broker reads sanitized metadata through Sheets API.
10. Popup displays the workbook title, locale, time zone, tab count, grid sizes,
    and request id.

Completion criteria:

- The displayed spreadsheet id matches the active Sheet.
- The verified principal and impersonated subject are the pilot user.
- Sanitized response contains metadata only.
- Broker audit logs include request id, principal, impersonated subject,
  spreadsheet id, policy decision id/version, status, and error code.
- The local agent does not receive OAuth tokens, ID tokens, access tokens,
  bearer headers, service account keys, or raw credentials.
- Logs contain enough information to debug a failure without exposing
  credentials.

### E. Rollback And Disable Preparation

Prepare rollback before enabling the pilot.

Rollback levers:

| Layer | Disable method | Expected effect |
| --- | --- | --- |
| Admin Console | Remove extension install policy for pilot group | Extension stops being installed by policy |
| Broker policy | Remove pilot allowlist or set policy deny-all | Extension stays installed but broker denies work |
| Cloud Run | Shift traffic to a known prior revision or deploy deny-only config | Broker behavior reverts or blocks safely |
| Web Store | Upload fixed tester version if client code is wrong | Client update follows Web Store lifecycle |

Completion criteria:

- At least one fast server-side disable path is ready.
- Admin rollback owner is named.
- Broker rollback owner is named.
- Server-side disable path has been tested and recorded before rollout expands.
- Rollback does not require deleting user data or editing live spreadsheets.

## 6. Tester Pilot Runbook

Run this sequence now that the Chrome Web Store item is published to testers.

1. Confirm the item is published to testers and remains private/internal.
2. Confirm the approved extension id is still
   `jahlkdjaokmjbipfhlhnjggcgjmpeiij`.
3. Confirm the installed tester package version. If it is older than the repo
   candidate, record the gap before deciding whether a new Web Store upload is
   needed.
4. Ask Workspace Admin to apply the prepared pilot install policy when managed
   install is used.
5. On the pilot user's Chrome profile, open `chrome://policy` and reload
   policies.
6. Confirm the extension is installed or installable.
7. Confirm the extension details show the expected id and version.
8. Run broker health check.
9. Run unauthenticated deny check.
10. Open the pilot spreadsheet and run extension inspect.
11. Record request id, principal, spreadsheet id, policy decision, and result
    summary in the pilot evidence package.
12. Run one deny-path check with an unauthorized spreadsheet or user.
13. Decide whether to keep pilot enabled, disable, upload a fixed package, or
    expand to the next group.

Done when:

- Pilot user can inspect the allowed spreadsheet through the extension.
- Unauthorized access is denied.
- Evidence is recorded without credentials.
- There is no need to edit, export, or re-upload the Google Sheet.

## 6A. Extension-Free Broker Smoke

This smoke test can run without the extension. It proves the broker, policy,
DWD, Sheets API, and current Codex account path independently from Chrome Web
Store installation.

Expected command:

```bash
python3 cli/sheets-bridge/sheets_bridge_cli.py inspect \
  --spreadsheet-id 16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg \
  --principal kangmin.lee@day1company.co.kr
```

Completion criteria:

- CLI obtains identity evidence from the active `gcloud` account with
  `gcloud auth print-identity-token`.
- Broker accepts the Cloud SDK OAuth audience through
  `BROKER_ADDITIONAL_AUDIENCES`.
- Broker policy allows only the pilot principal, read-only metadata operation,
  low risk, and wildcard spreadsheet delegation to Google ACL.
- DWD subject equals `kangmin.lee@day1company.co.kr`.
- Sheets metadata read succeeds and the response contains only sanitized
  workbook metadata.
- No OAuth token, access token, service account credential, private key, cookie,
  or bearer value is written to disk or logs.

Current evidence:

- 2026-06-03: Chrome Extension tester pilot passed. `Inspect` returned
  sanitized metadata for `[DB_raw] 가벼운학습지 엔진`, and `Record Package`
  persisted a native-host review package with request id
  `f5fb141c-4439-4968-b663-12b2161459ee`.
- 2026-06-03: Pilot decision recorded in
  `review-packages/sheets-bridge/managed-deployment/20260603-tester-pilot/pilot-decision.md`:
  keep pilot enabled, do not expand company-wide yet, run a second-tester or
  managed-policy pilot next.
- 2026-06-03: Native package credential scan found no private key, service
  account key, OAuth token, access token, refresh token, API key, bearer header,
  or cookie pattern.
- 2026-06-03: Tester pilot evidence directory initialized at
  `review-packages/sheets-bridge/managed-deployment/20260603-tester-pilot/`.
- 2026-06-03: Chrome profile `day1company` opened the pilot Sheet and loaded
  title `[DB_raw] 가벼운학습지 엔진 - Google Sheets`.
- 2026-06-03: Direct automation of the extension internal popup URL was blocked
  by Chrome control security policy. Continue the pilot through the normal
  human-visible Chrome extension popup and record the result in
  `pilot-inspect-result.md`.
- 2026-06-03: Cloud Run broker health returned `ok: true`.
- 2026-06-03: unauthenticated `/v1/inspect` returned structured
  `identity_evidence_failed`.
- 2026-06-03: extension-free CLI metadata smoke was blocked before broker call
  because `gcloud auth print-identity-token` could not refresh credentials under
  Context-Aware Access. Continue the tester pilot through the Chrome Extension
  path or re-run CLI only after the local `gcloud` account is refreshed from an
  allowed managed-device session.
- 2026-06-02: CLI smoke passed for
  `16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg`.
- 2026-06-02: wildcard spreadsheet policy smoke passed for
  `1gp3jl_DyB8kvxHO7m4YjsCPbFTPGi-XKyqPhGAlTZ60`, proving Google ACL can decide
  read reachability without adding each spreadsheet id to broker policy.
- Verified principal and impersonated DWD subject were both
  `kangmin.lee@day1company.co.kr`.
- Broker policy decision was `allowed`.
- Sanitized metadata read returned title
  `[DB_raw] 가벼운학습지 엔진`, locale `ko_KR`, time zone `Asia/Tokyo`,
  8 tabs, and 3 named ranges.

## 7. Evidence Package

Create one local evidence directory for the managed deployment pilot.

Recommended path:

```text
review-packages/sheets-bridge/managed-deployment/<YYYYMMDD>-pilot/
```

Recommended files:

```text
tester-publication.md
admin-policy.md
extension-version-check.md
broker-health.json
unauthenticated-deny.json
broker-audit-contract.md
dwd-readiness-check.md
oauth-client-binding-check.md
pilot-inspect-result.json
broker-log-summary.md
chrome-policy-check.md
rollback-checklist.md
pilot-decision.md
```

Evidence rules:

- Store request ids and sanitized metadata.
- Store policy version/hash summaries.
- Store user-visible error codes and broker error codes.
- Do not store bearer tokens, ID tokens, access tokens, refresh tokens,
  service account keys, private keys, cookies, or raw credentials.

## 8. Expansion Gates

Do not expand beyond the pilot group until all gates pass.

| Gate | Pass condition | Failure action |
| --- | --- | --- |
| Web Store gate | Approved private item with fixed id | Do not deploy |
| Version gate | Installed tester package behavior matches the documented broker header and metadata-only scope, or the version gap is explicitly accepted for pilot only | Upload fixed package before expansion |
| Admin gate | Pilot policy visible in `chrome://policy` | Fix Admin Console target |
| Identity gate | Broker verifies expected principal | Stop and inspect OAuth/audience/domain config |
| DWD gate | Broker subject equals verified user | Stop and fix DWD subject handling |
| Policy gate | Allowed pilot passes and unauthorized path denies | Fix broker policy |
| Data boundary gate | Sanitized metadata only, no credentials in artifacts/logs | Stop and remove leakage |
| Reliability gate | Health and inspect complete within pilot timeout | Fix broker timeout/retry/logging |
| Audit gate | Structured audit event is queryable and credential-free | Stop and fix broker audit logging |
| Rollback gate | Server-side disable path tested | Do not expand |

## 9. Open Decisions

These can remain open during the tester pilot but must be decided before
company-wide rollout.

- Whether first pilot uses `normal_installed` or `force_installed`.
- Whether rollout target is a Google Group or Workspace OU.
- Whether Admin Console should pin the extension.
- Whether broker policy is managed through environment JSON for pilot only or
  moved to a managed config source before broader rollout.
- Whether Web Store API automation should use the same service account or a
  separate release automation service account.
- Whether write scopes remain absent until Apply Plan Phase 5, or whether a
  separate staging environment prepares write-mode DWD in advance.

## 10. Handoff Prompt For A New Codex Session

Use this prompt when resuming from a clean session after tester publication:

```text
Work in /Users/kangmin/Documents/excel-workbook-editing.

Goal: execute the tester-published private Chrome Web Store managed deployment pilot for
Chrome Sheets Bridge using docs/chrome-extension-managed-deployment.md as the
runbook.

Do not redesign the architecture. Do not distribute service account keys or pass
OAuth/access/ID tokens into local artifacts, native messages, logs, or prompts.
The fixed extension id is jahlkdjaokmjbipfhlhnjggcgjmpeiij. The broker service
is run-mcp-day1-development-sheets-bridge-broker in day1-dev,
asia-northeast3. First pilot user is kangmin.lee@day1company.co.kr and first
pilot spreadsheet id is 16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg.

First inspect current git status and do not revert unrelated changes. Then:
1. confirm Web Store tester publication/private status with the user or Chrome UI;
2. prepare/confirm Admin Console pilot policy;
3. verify broker health and unauthenticated deny behavior;
4. run the extension pilot inspect on the allowed Sheet;
5. record sanitized evidence under review-packages/sheets-bridge/managed-deployment/;
6. verify unauthorized access is denied;
7. report pass/fail, files changed, commands run, and whether rollout can expand.
```
