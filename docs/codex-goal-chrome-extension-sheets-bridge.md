# Codex Goal: Chrome Extension Sheets Bridge

Use this document as the execution goal for implementing the Chrome Extension
Sheets bridge. It intentionally closes implementation choices so Codex does not
spend cycles exploring paths, replacing earlier work, or reimplementing working
surfaces.

## 1. Goal Statement

Build a Chrome Extension, optional local CLI, Cloud Run broker, and local Native
Messaging bridge that can inspect an existing Google Sheet by verifying the
end-user identity on every broker call, using Cloud Run keyless service identity
and Workspace Domain-Wide Delegation to impersonate that same user, generating
a sanitized local review package, producing a schema-validated edit plan, and
later applying approved range-scoped edits with broker policy checks,
precondition checks, before-state capture, live readback, audit evidence, and
rollback evidence.

Existing Google Sheets must remain live, in place, and identified by their
original `spreadsheetId` and tab `sheetId` values.

## 2. Fixed Implementation Choices

These choices are fixed for the first implementation. Do not replace them unless
the user explicitly asks for a redesign.

| Area | Decision |
| --- | --- |
| Extension platform | Chrome Extension Manifest V3 |
| Extension language | Plain JavaScript ES modules, HTML, and CSS |
| Extension build step | None for MVP; files load directly from the extension folder |
| Extension root | `extension/chrome-sheets-bridge/` |
| Primary user client | Chrome Extension |
| Secondary user client | Local CLI for power users, smoke tests, and batch/ops workflows |
| Native host language | Python 3 standard library |
| Native host root | `native-host/` |
| Native host name | `com.day1company.sheets_bridge` |
| Broker platform | Cloud Run |
| Broker root | `broker/cloud-run-sheets-broker/` |
| Broker credential model | Cloud Run runtime service account; no distributed service account key |
| Broker Google API authority | Domain-Wide Delegation with `subject` set to the verified end-user principal |
| Schema format | JSON Schema 2020-12 |
| Schema root | `schemas/` |
| Review output root | `review-packages/sheets-bridge/` |
| Credential boundary | OAuth tokens, DWD credentials, service account tokens, and raw credentials never reach the local agent, review packages, native messages, or repository |
| Google API caller | Cloud Run broker only |
| User authorization | Broker verifies user identity and default-deny policy before every Sheets API call |
| Local agent input | Sanitized snapshots, plans, and apply results only |
| Primary data source | Google Sheets API, not Google Sheets DOM |
| Reference-only tools | `googleworkspace/cli` may be used to study API shapes, JSON output, and smoke-test ergonomics, but not as a runtime dependency or credential path |
| Apply default | Disabled until Phase 5 is complete |

This is a user-requested redesign from the earlier Chrome OAuth and local
service-account-key models. Phase 0 protocol/schema envelope contracts remain
frozen. Phase 1 was not frozen, so Chrome OAuth and local service-account
implementation candidates may be replaced by the Cloud Run broker model without
a protocol bump.

## 3. Execution Authority And Phase Lock

This document is an implementation contract, not a prompt for broad path
exploration.

When a user does not name a phase, implement **Phase 0 only**. When a user names
a phase, implement only that phase and the smallest direct prerequisites from
earlier incomplete phases. Do not infer the current phase from the target file
tree or from partially existing files.

The target file tree is an allowed path inventory. It does not authorize early
creation of future-phase files. Each phase section is the authority for which
files may be created or changed during that phase.

At phase completion, the handoff must list:

- phase number and whether it is complete
- files created or changed
- verification commands run
- manual checks still required
- frozen public contracts for the phase
- compatible follow-up changes allowed in the next phase

Frozen public contracts include message types, schema top-level fields,
operation type names, artifact file names, and user-visible apply states. After
a phase is complete, change a frozen contract only by bumping
`protocol_version` or `schema_version` and updating compatibility tests.

## 4. Actor And Artifact Ownership

Use these ownership rules to avoid reimplementation and ambiguous placement.

| Surface | Owns | Must not own |
| --- | --- | --- |
| Chrome Extension service worker | Active Sheet detection, Google user login/identity token retrieval, user intent input, plan preview, approval UI, status display, HTTPS calls to the broker, and compact Native Messaging calls for local artifacts | Service account keys, DWD credentials, direct Google Sheets API calls, local file artifact rendering, hidden approval decisions |
| Extension popup/content scripts | Active tab detection, user intent input, plan preview, approval UI, status display | Google API writes, service account keys, local file writes, hidden approval decisions |
| Local CLI | Power-user inspect/plan/apply smoke workflows, batch checks, broker login/session acquisition without Sheets API scopes, broker calls, and deterministic artifact commands | Service account keys, DWD credentials, bypassing broker policy, bypassing apply gates |
| Cloud Run broker | User identity token verification on every call, default-deny bridge policy, DWD impersonation with subject equal to the verified user, Sheets API reads/writes, timeout/retry policy, Apply Plan Gate enforcement, precondition re-read, before-state capture, readback, broker audit log | Returning OAuth/access tokens or raw credentials, accepting unbounded user claims, letting local clients call Sheets API directly |
| Native Messaging host | Chrome local bridge, message framing, protocol validation, local artifact writes, review package manifests, plan/apply artifact persistence, and local agent invocation | Google API calls, service account keys, OAuth tokens, DWD impersonation, deciding whether a live write is authorized |
| Local spreadsheet agent | Analyze sanitized snapshots, generate review packages, draft dry-run edit plans, suggest rollback instructions | OAuth tokens, service account keys, direct live Sheet reads/writes, final Apply Plan Gate decisions |
| Local files under `review-packages/sheets-bridge/` | Durable inspection packages, dry-run plans, approval evidence, broker policy decision summaries, before-state manifests, apply results, and rollback instructions | Service account keys, OAuth tokens, private keys, access tokens, ID tokens, `Bearer` headers, or raw credentials |

The term `review package` in this project means the local Sheets bridge package
under `review-packages/sheets-bridge/<request_id>/`. It is distinct from an
onto review session artifact.

## 5. Hard Constraints

- Do not pass OAuth access tokens, ID tokens, service account private keys,
  broker-generated access tokens, refresh tokens, cookies, `Bearer` headers, or
  raw credentials to the local agent, review packages, native messages,
  repository files, or shell logs.
- Do not distribute service account key JSON to local machines, Chrome
  extensions, local CLIs, native messages, review packages, or repository files.
  If a temporary key exists during SRE bring-up, it belongs only in the broker
  deployment secret path and must be replaced by Cloud Run keyless service
  identity as the target architecture.
- The broker must verify the user identity token or equivalent authenticated
  session on every inspect, plan, and apply call. This does not require the user
  to login every time; it means every call is authenticated and checked.
- The broker must use Domain-Wide Delegation with `subject` equal to the
  verified user principal for every Sheets API call. Direct service-account file
  access is not the target model.
- Google ACLs are evaluated as the impersonated user. The broker policy is an
  additional default-deny layer for spreadsheet id, sheet id, range, operation,
  risk level, and approval requirements.
- Every inspect, plan, and apply result must record a broker policy decision id,
  verified principal, impersonated subject, broker request id, and policy
  version/hash summary in local artifacts.
- Do not scrape grid cells from the Google Sheets DOM.
- Do not export an existing Google Sheet to `.xlsx` and re-upload it.
- Do not implement write operations before read-only inspect, native bridge,
  plan schema, plan validation, and precondition re-read are complete.
- Do not change public message or schema shapes after a phase is complete unless
  `schema_version` or `protocol_version` is bumped and compatibility tests are
  updated.
- Do not replace a working phase with a new stack. Extend the existing phase with
  adapters or versioned contracts.
- Do not let the remote broker plan with LLMs or receive raw local-agent
  prompts in the first implementation. The broker is the Google API data plane
  and policy/audit gate, not the planner.
- Do not add broad Drive scopes by default. Add Drive metadata only when a phase
  explicitly requires it.
- Do not use `googleworkspace/cli` as the broker implementation, Local CLI
  runtime engine, subprocess wrapper, or credential holder. It is reference-only
  for API exploration, request/response examples, and UX inspiration.

### Cloud Run Broker Authorization Model

Broker mode has three separate authority layers:

| Layer | Authority | Consequence |
| --- | --- | --- |
| User identity | Chrome Extension or Local CLI obtains a user token/session; broker verifies issuer, audience, expiry, hosted domain, and principal on every call | This proves who is making the request |
| Google resource access | Broker uses Cloud Run runtime service identity plus Domain-Wide Delegation to impersonate the verified user as `subject` | Google Sheets version history and ACL checks align to the impersonated user |
| Bridge authorization | Broker policy maps a user principal to allowed operations, risk levels, sheet ids, ranges, field masks, timeout/retry budgets, cell budgets, and optional spreadsheet ids. Read-only inspect may use a spreadsheet wildcard so Google ACL decides actual spreadsheet reachability for the impersonated user | Broker denies any request outside policy before calling Sheets API |

Default broker policy authority:

```text
Cloud Run broker configuration managed by SRE/Infra
```

Local development may use a non-secret policy fixture for tests only:

```text
broker/cloud-run-sheets-broker/test/fixtures/policy.allow.json
```

Policy fixtures must never contain real user tokens, access tokens, service
account keys, private keys, or production spreadsheet secrets.

Policy shape for the first implementation:

```json
{
  "policy_version": "1.0",
  "principals": [
    {
      "principal": "user@company.com",
      "display_name": "User Name",
      "roles": ["inspect", "plan", "apply_low_risk"],
      "spreadsheets": [
        {
          "spreadsheet_id": "spreadsheet-id",
          "allowed_sheet_ids": [0],
          "allowed_ranges": ["A1:Z1000"],
          "allowed_operations": ["inspect", "generate_plan", "update_values"],
          "max_risk_level": "low",
          "requires_second_approval": false
        }
      ]
    }
  ]
}
```

Policy must be interpreted conservatively:

- unknown users are denied
- unknown spreadsheets are denied
- missing ranges are denied for write operations
- unspecified operations are denied
- higher risk than `max_risk_level` is denied unless the policy explicitly
  requires and records second approval
- policy evaluation produces a `policy_decision_id`, `principal`,
  `impersonated_subject`, `policy_version`, and `policy_hash` summary for
  broker audit logs and sanitized local artifacts

Client options:

| Client | Role | Recommended use |
| --- | --- | --- |
| Chrome Extension | Primary UX: active Sheet context, visual review/approval, user identity token acquisition, broker calls | Normal user workflow |
| Local CLI | Secondary UX: smoke tests, batch inspect, artifact regeneration, operational diagnostics | Power users and operations |

Both clients must use the same broker API, policy engine, audit model, and
apply gate. Neither client may call Sheets API directly.

## 6. Target File Tree

Codex should create files only in these locations unless a phase explicitly says
otherwise.

```text
extension/chrome-sheets-bridge/
├── manifest.json
├── package.json
├── src/
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   ├── popup.js
│   ├── popup.css
│   ├── sheets_api.js
│   ├── native_bridge.js
│   ├── plan_validator.js
│   ├── apply_executor.js
│   └── constants.js
└── test/
    ├── spreadsheet_id.test.js
    ├── plan_validator.test.js
    └── fixtures/

native-host/
├── manifest/
│   └── com.day1company.sheets_bridge.json
├── src/
│   ├── host.py
│   ├── protocol.py
│   ├── review_package.py
│   └── plan_artifacts.py
├── test/
│   ├── test_protocol.py
│   └── test_review_package.py
└── install_macos.py

broker/
└── cloud-run-sheets-broker/
    ├── README.md
    ├── src/
    │   ├── auth.py
    │   ├── dwd.py
    │   ├── policy.py
    │   ├── sheets_client.py
    │   ├── broker.py
    │   └── audit.py
    └── test/
        ├── test_auth.py
        ├── test_policy.py
        └── test_sheets_client.py

cli/
└── sheets-bridge/
    ├── README.md
    ├── sheets_bridge_cli.py
    └── test/
        └── test_cli_requests.py

schemas/
├── inspection.schema.json
├── edit-plan.schema.json
├── apply-result.schema.json
└── native-message.schema.json

review-packages/
└── sheets-bridge/
```

## 7. Stable Protocol

All Native Messaging messages use this envelope:

```json
{
  "protocol_version": "1.0",
  "request_id": "uuid",
  "type": "inspect.snapshot",
  "payload": {}
}
```

Responses use:

```json
{
  "protocol_version": "1.0",
  "request_id": "uuid",
  "type": "review.result",
  "ok": true,
  "payload": {}
}
```

Error responses use:

```json
{
  "protocol_version": "1.0",
  "request_id": "uuid",
  "type": "error",
  "ok": false,
  "error": {
    "code": "invalid_message",
    "message": "Human-readable error"
  }
}
```

Allowed message types:

Request types:

- `inspect.snapshot`
- `review.generate`
- `plan.generate`
- `apply.record`

Result types:

- `review.result`
- `plan.result`
- `apply.result`

Terminal type:

- `error`

Large artifacts must be written to disk and referenced by absolute path in the
payload. Do not send large HTML, grid dumps, or review packages through Native
Messaging.

Protocol ownership:

- In broker mode, `inspect.snapshot` is an extension-to-host request carrying a
  sanitized broker inspection snapshot or a path to it. The extension or CLI
  calls the broker first; the Native Messaging host never receives user tokens
  and never calls Google APIs.
- In legacy Chrome OAuth mode, `inspect.snapshot` may carry sanitized inspection
  data or a path to it. Legacy Chrome OAuth mode is superseded for this project
  unless the user explicitly asks to restore it.
- `review.generate` is an extension-to-host request asking the host/agent to
  create a review package from the latest sanitized inspection.
- `review.result` is a host-to-extension response with a review package manifest
  path and compact summary.
- `plan.generate` is an extension-to-host request asking the local agent to
  create a dry-run edit plan from a review package and user intent.
- `plan.result` is a host-to-extension response with a dry-run plan artifact
  path and compact validation summary.
- `apply.record` is an extension-to-host request carrying the completed apply
  result, approval evidence, before-state manifest path, and rollback
  instruction payload for durable local persistence.
- `apply.result` is a host-to-extension response confirming the persisted apply
  result path and final status. It is not a request type.
- `error` is a response for invalid message, unsupported protocol, host failure,
  artifact write failure, or rejected request state.

## 8. Stable Inspection And Snapshot Authority

Phase 1 creates the normalized inspection metadata shape. Phase 3 extends it
with deep inspection data. Later phases must validate plans against this
inspection authority instead of popup-only state.

The authoritative inspection snapshot must include:

- `schema_version`
- `snapshot_id`
- `captured_at`
- `spreadsheet_id`
- spreadsheet title, locale, and time zone
- tab records with `sheet_id`, title, grid row/column counts, hidden status,
  and stable index
- named ranges, protected ranges, data validations, and formula samples when
  available
- loading/error state classifications
- request count, retry count, elapsed time, and timeout budget actually used

Sanitized snapshots must exclude OAuth tokens, ID tokens, service account keys,
private keys, signed JWTs, access tokens, cookies, raw credentials, browser
profile identifiers, `Bearer` headers, and unrelated Drive data. For medium or
large Sheets, snapshots should contain targeted samples and manifests, not
full-grid dumps. `plan_validator.js` consumes the normalized inspection
snapshot and the edit plan; it must not infer authority from currently visible
popup text. Broker-side policy decisions are separate authority records and are
included only as bounded summaries.

## 9. Stable Edit Plan Shape

The edit plan schema must include:

```json
{
  "schema_version": "1.0",
  "plan_id": "uuid",
  "spreadsheet_id": "string",
  "created_at": "ISO-8601 timestamp",
  "intent": "string",
  "risk_level": "low|medium|high",
  "timeout_budget": {
    "read_seconds": 60,
    "write_seconds": 60,
    "poll_seconds": 120
  },
  "preconditions": [],
  "operations": [],
  "readback": [],
  "rollback": {
    "before_state_required": true,
    "inverse_plan_status": "unsupported|planned|generated|not_feasible",
    "inverse_plan_ref": null
  }
}
```

`constants.js` owns runtime default timeout budgets. Edit plans copy timeout
values as auditable snapshots for the plan execution. Schemas validate timeout
shape and bounds; they do not own runtime defaults.

Allowed operation types for Phase 5:

- `update_values`
- `update_formulas`
- `repeat_cell_format`
- `set_data_validation`
- `insert_dimension`
- `delete_dimension`

Every operation must include:

- `operation_id`
- `type`
- `sheet_id`
- `range` or `dimension_range`
- `requires_explicit_approval`
- `reason`

## 10. Rollback Artifact Contract

Rollback has four separate concepts. Do not collapse them into one field.

| Concept | Canonical artifact seat | Required by |
| --- | --- | --- |
| Before-state evidence | `before-state.json` or chunk manifest inside the apply package | Phase 5 before any write |
| Rollback instructions | `rollback.md` or `rollback` object in `apply-result.json` | Phase 5 apply result |
| Generated inverse plan | `inverse-plan.json` referenced from `apply-result.json` when feasible | Phase 5 for simple value/formula edits |
| Rollback limitation | `rollback.limitations[]` in `apply-result.json` | Every Phase 5 apply result |

The edit plan declares rollback requirements and expected inverse-plan support.
The apply result records what was actually captured, generated, skipped, or not
feasible. If inverse plan generation is not feasible, the apply result must say
why and must still include before-state evidence and manual rollback
instructions when available.

## 11. Canonical Apply Plan Gate

Apply remains disabled until every gate below passes for the exact plan being
applied.

| Gate | Authority | Failure status |
| --- | --- | --- |
| Phase gate | Phase 5 implementation complete and verified | `blocked_phase_incomplete` |
| Principal gate | Broker verifies a valid user token/session and derives the principal | `rejected_unknown_principal` |
| Policy gate | Broker policy allows the principal, spreadsheet, sheet ids, ranges, operation types, and risk level | `rejected_policy` |
| Credential gate | Cloud Run runtime service identity and DWD impersonation are available for the verified principal | `stopped_credential_failed` |
| Schema gate | `edit-plan.schema.json` validation | `rejected_schema` |
| Identity gate | Active `spreadsheet_id` and known `sheet_id` values match inspection authority | `rejected_identity_mismatch` |
| Operation gate | Every operation type is allowed for Phase 5 and has range/dimension bounds | `rejected_operation` |
| Risk gate | `risk_level` and per-operation approval requirements are satisfied | `rejected_risk` |
| Approval gate | User approval evidence binds exact `plan_id`, `spreadsheet_id`, operation ids or affected ranges, risk level, timestamp, and visible confirmation text | `rejected_missing_approval` |
| Precondition gate | Broker re-reads precondition ranges immediately before write | `stopped_precondition_mismatch` |
| Protection gate | Broker checks protected ranges and validation constraints before write | `stopped_protected_range` |
| Before-state gate | Broker captures before-state evidence before the first write batch | `stopped_before_state_failed` |
| Write budget gate | Write and retry budgets are available | `stopped_timeout_or_quota` |
| Cancellation gate | User has not cancelled before or during apply | `cancelled` |
| Readback gate | Changed ranges and declared dependent ranges are re-read or explicitly marked unverified with reason | `completed_with_unverified_readback` |
| Artifact gate | `apply.record` persists broker apply result, approval evidence, before-state reference, write batches, readback, final status, and rollback fields through the native host | `completed_artifact_write_failed` |

Only `completed`, `completed_with_unverified_readback`,
`completed_artifact_write_failed`, `cancelled`, and `stopped_*` statuses may
appear in `apply-result.json`. A write batch must not start until all pre-write
gates through the cancellation gate pass.

## 12. Phase Completion Table

| Phase | Expected Result | Completion Criteria |
| --- | --- | --- |
| 0. Foundations | Directory skeleton, schemas, constants, protocol utilities | All target folders exist; schemas parse; protocol tests pass; no Google API calls yet |
| 1. Broker Auth And Detection MVP | Extension detects active Sheet; CLI can form equivalent request; broker verifies user identity and policy | URL/user detection tests pass; broker auth/policy allow/deny tests pass; broker read-only metadata smoke works by DWD impersonating the verified user; no local SA key or direct Sheets API calls |
| 2. Native Host Bridge | Extension sends broker-produced sanitized snapshot to Python host | Host receives framed snapshot, writes review package, returns manifest path; host disconnect and policy denial summaries are handled |
| 3. Deep Inspect | Broker snapshot and review package include formulas, validations, protections, loading/error states | Medium Sheet inspect avoids full-grid reads; formulas and `Loading...`/`#REF!` states classified |
| 4. Edit Plan Generation | Local agent produces schema-valid dry-run plans | Invalid/cross-spreadsheet/overbroad plans are rejected; no write calls exist |
| 5. Apply Plan | Approved low-risk range edits apply safely | Canonical gate passes; approval evidence captured; preconditions re-read; before-state captured; bounded batch write; live readback; `apply.record`/`apply.result` persist apply result and rollback fields |
| 6. Hardening | Medium/large Sheets operate within budgets | Chunking, retry telemetry, request pacing, audit log, version negotiation exist |
| 7. Managed Deployment | Pilot install path is documented and repeatable | Fixed extension id, Cloud Run broker/keyless service identity path, managed broker policy, host installer, update/rollback procedure documented |

## 13. Verification Command Matrix

Use these commands as the default verification set. If a command is not
applicable in an early phase because the files do not exist yet, say so in the
handoff instead of inventing a substitute.

```bash
git diff --check
```

```bash
python3 - <<'PY'
from pathlib import Path
import json
expected = [
    Path("schemas/native-message.schema.json"),
    Path("schemas/inspection.schema.json"),
    Path("schemas/edit-plan.schema.json"),
    Path("schemas/apply-result.schema.json"),
]
missing = [str(path) for path in expected if not path.exists()]
if missing:
    raise SystemExit("missing schemas: " + ", ".join(missing))
for path in expected:
    json.loads(path.read_text())
print("schemas parse ok")
PY
```

```bash
python3 -m unittest discover native-host/test
```

```bash
node --test extension/chrome-sheets-bridge/test/*.test.js
```

Manual verification begins when a phase touches Chrome or a live Google Sheet:

- load `extension/chrome-sheets-bridge/` as an unpacked extension
- configure the Cloud Run broker endpoint and expected client audience
- configure Workspace Domain-Wide Delegation for the broker runtime service
  account with narrow Sheets scopes
- verify the impersonated pilot user can access the target Google Sheet
- configure an explicit broker policy allowing the pilot principal and target
  spreadsheet
- run the phase-specific popup action
- confirm no OAuth token, ID token, service account key, private key, access token,
  `Bearer` header, or raw credential appears in console logs, Native Messaging
  payloads, review package files, or repository files

## 14. Standalone New-Session Handoff

This section is the handoff authority for a fresh Codex session. A new session
should be able to continue from this document alone without reading separate
handoff notes.

### Current Implementation State

- Implementation status: Phase 1 broker redesign is implemented for the Local
  CLI smoke path and still needs Chrome Extension end-to-end smoke.
  Extension-side direct Sheets API access has been removed from the tested
  Phase 1 path; the extension now detects the active Sheet, builds broker
  inspect requests, obtains broker identity evidence, and calls `/v1/inspect`.
  Broker auth, policy, DWD subject selection, keyless DWD token-provider
  composition, metadata normalization, structured failure responses, tokeninfo
  identity normalization including Chrome access-token aliases, local gcloud
  identity-token broker calls, `/v1/health` readiness, `/v1/inspect` HTTP
  dispatch, and CLI request execution are covered by unit tests.
  The Cloud Run service `run-mcp-day1-development-sheets-bridge-broker` is
  deployed in `day1-dev` / `asia-northeast3` with keyless DWD runtime identity.
  Local CLI broker smoke has verified user identity, wildcard spreadsheet
  policy, DWD `signJwt`/token exchange, and read-only Sheets metadata for
  spreadsheets the impersonated pilot user can access. Bounded parser windows
  are also implemented for `inspect.grid_window`, `inspect.values_window`, and
  `inspect.formula_window`, with policy gates for ranges, cell budgets, field
  masks, timeout, and retry. Chrome Extension authenticated broker smoke is
  still pending.
  Phase 2 local Native Host Bridge candidate is also implemented: the extension
  can send a sanitized `inspect.snapshot` message to
  `com.day1company.sheets_bridge`, the native host writes `snapshot.json` and
  `manifest.json`, and credential-like material is rejected before persistence.
  macOS and Windows Native Messaging install candidates exist. Phase 2 is not
  complete until the native host manifest is installed in Chrome and a live
  extension-to-host package recording is manually verified.
- Completed implementation phases: Phase 0.
- Next default phase: finish Chrome Extension authenticated broker smoke, then
  run Phase 2 native-host registration and live package-recording smoke.
- Apply Plan status: disabled; no write path may be implemented before Phase 5.
- Expected repo state before the next Phase 1 continuation:
  - `schemas/native-message.schema.json` exists and defines the Native
    Messaging request/result/error envelopes.
  - `schemas/inspection.schema.json` exists and defines the normalized
    inspection snapshot contract.
  - `schemas/edit-plan.schema.json` exists and defines the dry-run/apply plan
    shape and Phase 5 operation names.
  - `schemas/apply-result.schema.json` exists and defines apply result,
    approval evidence, readback, and rollback fields.
  - `extension/chrome-sheets-bridge/src/constants.js` exists and owns protocol,
    native host, message type, and timeout defaults.
  - `native-host/src/protocol.py` exists and reads/writes Chrome Native
    Messaging length-prefixed JSON.
  - `native-host/src/review_package.py` exists and writes sanitized inspection
    review packages while rejecting credential-like keys or values.
  - `native-host/src/host.py` exists and handles `inspect.snapshot` by returning
    `review.result` with local artifact refs, or `error` without writing a
    package.
  - `native-host/bin/sheets-bridge-native-host`,
    `native-host/manifest/com.day1company.sheets_bridge.template.json`,
    `native-host/install_macos.sh`, `native-host/install_windows.ps1`,
    `native-host/bin/sheets-bridge-native-host.cmd`, and
    `native-host/README.md` exist for local Chrome Native Messaging
    registration.
  - `native-host/test/test_protocol.py` and
    `native-host/test/test_review_package.py` cover frame roundtrip, invalid
    JSON, oversized message guard, unknown message type, snapshot persistence,
    credential rejection, denied response rejection, and framed host IO.
    `native-host/test/test_windows_install_artifacts.py` covers the Windows
    wrapper and HKCU Chrome Native Messaging installer contract.
  - `extension/chrome-sheets-bridge/manifest.json` exists as a Manifest V3
    extension candidate with broker host permissions, Google Sheets tab access,
    Native Messaging permission, and OpenID/profile/email identity scopes only.
    It does not request Sheets or Drive OAuth scopes. Its manifest key computes
    to Chrome extension id
    `jahlkdjaokmjbipfhlhnjggcgjmpeiij`. Its OAuth client id is currently
    `862894425240-1r90upabo0gb42t41p7gj36dp1r37j24.apps.googleusercontent.com`,
    but that client must be confirmed or replaced for the `jahl...` Application
    ID before authenticated smoke can pass.
  - `extension/chrome-sheets-bridge/package.json` exists with
    `"type": "module"` and a Node test command.
  - `extension/chrome-sheets-bridge/src/background.js` obtains broker identity
    evidence, calls the broker, and can forward a sanitized snapshot to the
    native host on explicit package-recording request. It does not call Sheets
    API directly.
  - `extension/chrome-sheets-bridge/src/native_bridge.js` builds
    `inspect.snapshot` messages and calls the configured native host.
  - `extension/chrome-sheets-bridge/src/sheets_api.js` extracts spreadsheet ids,
    builds the broker inspect request contract, calls `/v1/inspect`, unwraps a
    sanitized broker payload, and surfaces broker denial/HTTP errors.
  - `extension/chrome-sheets-bridge/src/constants.js` sets
    `DEFAULT_BROKER_BASE_URL` to
    `https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app`.
  - `extension/chrome-sheets-bridge/src/content.js` detects Google Sheets tab
    context without reading grid DOM data.
  - `extension/chrome-sheets-bridge/src/popup.html`,
    `extension/chrome-sheets-bridge/src/popup.css`, and
    `extension/chrome-sheets-bridge/src/popup.js` provide the read-only Inspect
    UI, visible error states, and an explicit package-recording action after a
    successful inspect.
  - `extension/chrome-sheets-bridge/test/spreadsheet_id.test.js` covers URL
    parsing, broker request formation, manifest broker-only scope/host
    permissions, Native Messaging snapshot message formation, absence of
    extension-side direct Sheets API/write/logging calls, broker response unwrap,
    and the Phase 1 inspection fixture.
  - `extension/chrome-sheets-bridge/test/fixtures/inspection-metadata.json`
    contains `spreadsheet_id`, `sheet_id`, grid size, title, locale, time zone,
    and capture timestamp.
  - `broker/cloud-run-sheets-broker/src/auth.py`, `dwd.py`, `policy.py`,
    `sheets_client.py`, `identity.py`, `token_provider.py`, `broker.py`, and
    `server.py` exist and are covered by unit tests.
  - `broker/cloud-run-sheets-broker/src/token_provider.py` implements keyless
    DWD access-token composition through Cloud Run runtime access token, IAM
    Credentials `signJwt`, and OAuth JWT-bearer token exchange. It does not use
    or persist a service-account private key.
  - `broker/cloud-run-sheets-broker/Dockerfile` runs the stdlib Python broker
    server with `PYTHONPATH=/app/src` and `PORT=8080`.
  - `cli/sheets-bridge/sheets_bridge_cli.py` can form dry-run broker inspect
    requests, bounded parser window requests, and can call the deployed broker
    with the current `gcloud` identity token through `X-Broker-Authorization`.
  - `docs/claude-code-sheets-bridge.md` exists and defines how Claude Code may
    consume sanitized native-host packages without credentials.
  - Empty future-phase directories are tracked only with `.gitkeep`
    placeholders where needed.
- Existing authoritative design file: this document.
- Supporting docs may summarize the plan, but they do not override this
  document.

### Latest Automated Verification

The latest automated verification for the Phase 1 broker redesign and Phase 2
local Native Host Bridge candidate passed on 2026-06-02:

- `git diff --check`
- JSON parse check for schemas, extension manifest/package, and the Phase 1
  inspection fixture
- `python3 -m unittest discover -s native-host/test` with 12 passing tests
  covering protocol framing, local review package persistence, and Windows
  install artifacts
- `node --test extension/chrome-sheets-bridge/test/*.test.js --runInBand` with
  11 passing tests covering URL parsing, broker request formation, manifest
  broker-only scope/host/native surface, Native Messaging snapshot message
  formation, absence of direct Sheets API/write/logging calls, broker response
  unwrap/error handling, and the Phase 1 inspection fixture
- `python3 -m unittest discover -s broker/cloud-run-sheets-broker/test` with 66
  passing tests covering auth validation, DWD subject selection, default-deny
  policy with spreadsheet wildcard fallback to Google ACL, metadata
  URL/normalization, bounded grid/value/formula window URL/normalization,
  policy gates for parser cell budgets and field masks, tokeninfo identity
  normalization including Chrome access-token aliases, keyless token-provider
  composition, inspect handler success, HTTP dispatch, `/v1/health` readiness,
  runtime config loading, sanitized audit events, malformed/non-object
  bad-request audit, and structured auth/credential/metadata/window failures
- `python3 -m unittest discover -s cli/sheets-bridge/test` with 7 passing tests
  covering dry-run broker request formation, bounded parser window request
  formation, and local gcloud identity-token broker calls
- `python3 -m py_compile broker/cloud-run-sheets-broker/src/*.py
  native-host/src/*.py cli/sheets-bridge/sheets_bridge_cli.py`
- Native host executable wrapper smoke with
  `native-host/bin/sheets-bridge-native-host` reads a framed
  `inspect.snapshot`, writes a temporary review package through
  `SHEETS_BRIDGE_REVIEW_ROOT`, and returns framed `review.result`
- Chrome `--pack-extension` against a temporary copy of
  `extension/chrome-sheets-bridge/` succeeds, proving the manifest parses in
  Chrome without creating repo-local package artifacts
- Live DWD read-only smoke succeeded on 2026-06-02 against spreadsheet
  `16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg` with subject
  `kangmin.lee@day1company.co.kr`, service account
  `day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com`, scope
  `https://www.googleapis.com/auth/spreadsheets.readonly`, title
  `[DB_raw] 가벼운학습지 엔진`, 8 tabs, and first tab `[ML] 매출_최종`.
  A second wildcard-policy smoke succeeded against spreadsheet
  `1gp3jl_DyB8kvxHO7m4YjsCPbFTPGi-XKyqPhGAlTZ60`, proving that broker policy can
  delegate spreadsheet reachability to the impersonated user's Google ACL.
  Bounded parser window smokes for `inspect.grid_window`,
  `inspect.values_window`, and `inspect.formula_window` succeeded on
  `'26_0601'!A1:Z80`; an oversized `A1:ZZ100` request was denied with
  `range_too_large`.
- Cloud Run deploy succeeded for service `run-mcp-day1-development-sheets-bridge-broker`;
  env vars `BROKER_AUDIENCE`, `BROKER_SERVICE_ACCOUNT_EMAIL`,
  `BROKER_HOSTED_DOMAIN`, and `BROKER_POLICY_JSON` are present. The deployed
  broker is publicly reachable at the Cloud Run front door, `GET /v1/health`
  returns `200` with a non-sensitive readiness payload, and unauthenticated
  `POST /v1/inspect` returns broker JSON `401 identity_evidence_failed`.
- Before authenticated extension smoke, the broker was updated to normalize
  Chrome OAuth access-token `tokeninfo` aliases `issued_to` and
  `verified_email`, so the same `BROKER_AUDIENCE` and verified email checks
  apply to Chrome extension access tokens.
- The latest deployed revision is
  `run-mcp-day1-development-sheets-bridge-broker-00014-v84`; it includes the
  Chrome access-token alias normalization guard, local gcloud identity-token
  broker path, spreadsheet wildcard policy fallback, bounded parser window
  operations, and `/v1/health` readiness endpoint, and serves 100 percent of
  traffic.
- Superseded Cloud Run services `run-day1-sheets-bridge-broker` and
  `run-mcp-chrome-sheets-bridge-broker` were created during naming iteration and
  should be deleted after confirming no clients use them.

### Fresh-Session Start Procedure

When starting from a new session:

1. Read this document from top to bottom.
2. Run `git status --short` and inspect existing files before editing.
3. Identify the requested phase. If the user did not name a phase, choose
   Phase 0.
4. Compare existing files with the phase's `Create` and `Completion criteria`
   lists.
5. Reuse any existing files that already satisfy this document. Do not delete or
   regenerate them only because the session is fresh.
6. Implement only the selected phase.
7. Run the applicable verification commands from Section 13.
8. Update the handoff fields in this section before ending the phase.

### Handoff Fields To Update After Each Phase

After each implementation phase, update this section in the same commit or
handoff turn:

- `Implementation status`
- `Completed implementation phases`
- `Next default phase`
- `Apply Plan status`
- `Expected repo state before Phase <next>`
- `Frozen contracts`
- `Known blockers`
- `Manual verification still required`
- `Compatible next changes`

Do not create a separate handoff document unless the user explicitly asks for
one. If detailed logs are useful, keep them in the final response or a phase
artifact, but keep the durable next-session truth here.

### Frozen Contracts

Phase 0 freezes these public contracts:

- `protocol_version`: `1.0`
- native host name: `com.day1company.sheets_bridge`
- request message types: `inspect.snapshot`, `review.generate`,
  `plan.generate`, `apply.record`
- result message types: `review.result`, `plan.result`, `apply.result`
- terminal message type: `error`
- schema file names:
  - `schemas/native-message.schema.json`
  - `schemas/inspection.schema.json`
  - `schemas/edit-plan.schema.json`
  - `schemas/apply-result.schema.json`
- `native-message` top-level fields:
  - request: `protocol_version`, `request_id`, `type`, `payload`
  - result: `protocol_version`, `request_id`, `type`, `ok`, `payload`
  - error: `protocol_version`, `request_id`, `type`, `ok`, `error`
- `inspection` top-level fields: `schema_version`, `snapshot_id`,
  `captured_at`, `spreadsheet_id`, `title`, `locale`, `time_zone`, `tabs`,
  `named_ranges`, `protected_ranges`, `data_validations`, `formula_samples`,
  `cell_states`, `telemetry`, `artifacts`
- `edit-plan` top-level fields: `schema_version`, `plan_id`,
  `spreadsheet_id`, `created_at`, `intent`, `risk_level`, `timeout_budget`,
  `preconditions`, `operations`, `readback`, `rollback`
- `apply-result` top-level fields: `schema_version`, `apply_id`, `plan_id`,
  `spreadsheet_id`, `created_at`, `status`, `approval_evidence`,
  `before_state_ref`, `changed_ranges`, `write_batches`, `readback`,
  `retry_count`, `rollback`, `error`
- runtime timeout default owner: `extension/chrome-sheets-bridge/src/constants.js`

Later phases must append their frozen public contracts here when complete.

Phase 1 candidate contracts are not frozen until Cloud Run endpoint/keyless
runtime verification succeeds. Current tested candidate contracts are:

- Chrome extension id: `jahlkdjaokmjbipfhlhnjggcgjmpeiij`
- Chrome OAuth client id / broker audience:
  `862894425240-1r90upabo0gb42t41p7gj36dp1r37j24.apps.googleusercontent.com`
- Cloud Run broker service: `run-mcp-day1-development-sheets-bridge-broker`
- Cloud Run broker URL:
  `https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app`
- broker readiness endpoint path: `/v1/health`
- broker inspect endpoint path: `/v1/inspect`
- broker inspect operation: `inspect.metadata`
- extension broker request fields: `request_id`, `operation`,
  `spreadsheet_id`, `sheet_ids`, `ranges`, `risk_level`, `created_at`,
  `identity_hint.principal`
- broker success envelope: `{"ok": true, "payload": <inspection snapshot>}`
- broker structured failure envelope: `{"ok": false, "error": {"code",
  "message"}}`, with tested Phase 1 codes `auth_failed`, `policy_denied`,
  `credential_failed`, and `sheets_metadata_failed`
- read-only DWD scope:
  `https://www.googleapis.com/auth/spreadsheets.readonly`

Phase 2 candidate contracts are not frozen until Chrome Native Messaging
registration and live package recording succeed. Current tested candidate
contracts are:

- native host executable:
  `native-host/bin/sheets-bridge-native-host`
- Windows native host wrapper:
  `native-host/bin/sheets-bridge-native-host.cmd`
- native host manifest template:
  `native-host/manifest/com.day1company.sheets_bridge.template.json`
- installed Chrome manifest path on macOS:
  `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.day1company.sheets_bridge.json`
- installed Chrome manifest path on Windows:
  `%LOCALAPPDATA%\Day1\ChromeSheetsBridge\NativeMessagingHosts\com.day1company.sheets_bridge.json`
- Windows Chrome registry key:
  `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.day1company.sheets_bridge`
- active native request: `inspect.snapshot`
- active native result: `review.result`
- review package files: `snapshot.json`, `manifest.json`
- default package root:
  `review-packages/sheets-bridge/native-host/<YYYY-MM-DD>/<request-id>/`
- override environment variable: `SHEETS_BRIDGE_REVIEW_ROOT`

Phase 0 contracts remain frozen.

### Known Blockers

- No current blocker prevents continuing Chrome Extension or Native Host
  implementation.
- Phase 1 Chrome Extension completion still requires authenticated
  allowed/denied broker smoke from the extension UI.
- Manual allowed smoke currently fails at Chrome OAuth before any broker call
  with `OAuth2 request failed: Service responded with error: 'bad client id:
  {0}'`. On 2026-06-01 the user chose to switch the canonical extension id to
  `jahlkdjaokmjbipfhlhnjggcgjmpeiij`, the id computed from the Chrome Web Store
  public key now stored in `extension/chrome-sheets-bridge/manifest.json`. The
  next required action is confirming the current Chrome App OAuth client uses
  Application ID `jahlkdjaokmjbipfhlhnjggcgjmpeiij`, or creating a replacement
  Chrome App OAuth client for that id and updating both the manifest
  `oauth2.client_id` and Cloud Run `BROKER_AUDIENCE`.
- Public Cloud Run reachability is available for revision
  `run-mcp-day1-development-sheets-bridge-broker-00014-v84`.
- Keyless runtime smoke has proved the deployed Cloud Run runtime service
  account path can mint the DWD Sheets token through the Local CLI. Chrome
  Extension identity smoke still needs live verification.
- Phase 2 Native Messaging registration must still be installed in local Chrome
  and verified from the extension UI. The manifest template already allows only
  extension id `jahlkdjaokmjbipfhlhnjggcgjmpeiij`.

### Manual Verification Still Required

Phase 1 broker redesign has manually verified:

- Workspace Admin Domain-Wide Delegation contains service account client id
  `106391233015635066062` with
  `https://www.googleapis.com/auth/spreadsheets.readonly`
- the pilot user `kangmin.lee@day1company.co.kr` can access the target
  spreadsheet
- DWD `subject` can equal the verified user principal for a read-only Sheets API
  metadata call
- the allowed pilot spreadsheet returns title, locale/time zone, tab title,
  `sheetId`, row count, column count, and hidden status through
  `includeGridData=false`
- deployed Cloud Run revision
  `run-mcp-day1-development-sheets-bridge-broker-00014-v84` serves 100 percent
  of traffic, `GET /v1/health` returns broker JSON `200`, and unauthenticated
  `POST /v1/inspect` reaches broker auth and returns
  `401 identity_evidence_failed`
- Local CLI read-only broker smoke succeeds through keyless DWD for
  `kangmin.lee@day1company.co.kr` using wildcard spreadsheet policy delegated
  to Google ACL
- Local CLI bounded parser window smoke succeeds for `inspect.grid_window`,
  `inspect.values_window`, and `inspect.formula_window` on
  `'26_0601'!A1:Z80`, while oversized ranges are denied before Sheets API reads

Phase 1 broker redesign must still manually verify:

- the Chrome Extension obtains identity evidence accepted by the deployed broker
- the deployed broker verifies a Chrome Extension user identity token/session
  on every call
- a known pilot user principal is allowed by broker policy for spreadsheets the
  impersonated user can access
- an unknown user principal is denied by the broker before any Sheets API call
- the unpacked extension can call the configured broker endpoint from a live
  Google Sheet tab
- no OAuth token, ID token, service account key, private key, signed JWT, access
  token, `Bearer` header, or raw credential appears in DevTools console logs,
  Native Messaging payloads, review package files, test fixtures, shell logs, or
  repository files

Phase 2 Native Host Bridge must still manually verify:

- `./native-host/install_macos.sh` installs the manifest to the pilot Chrome
  NativeMessagingHosts directory on macOS
- `powershell -ExecutionPolicy Bypass -File .\native-host\install_windows.ps1`
  installs the generated manifest and HKCU registry key on Windows
- `chrome://extensions` shows extension id
  `jahlkdjaokmjbipfhlhnjggcgjmpeiij`
- after a successful broker inspect, the popup `Record Package` action returns
  a `review.result`
- the package directory contains only sanitized `snapshot.json` and
  `manifest.json`
- no OAuth token, ID token, access token, bearer header, service account key,
  private key, cookie, or raw credential appears in the native host package

### Compatible Next Changes

The next compatible changes are Phase 1 authenticated deployed broker smoke and
Phase 2 native-host registration smoke:

- run deployed broker smoke for allowed and denied principals
- use `googleworkspace/cli` only as a reference for API shape and CLI ergonomics,
  not as a runtime dependency or credential path
- keep credentials and user tokens out of native messages, repository files,
  logs, and review packages
- install and verify the Phase 2 native host manifest locally before relying on
  review package recording
- keep Sheets write/apply code absent until Phase 5 starts

### Phase 1 Resume Runbook

Use this runbook to resume the active goal without path exploration,
roll-back, or reimplementation. The only target is to complete Phase 1
authenticated smoke. Do not create a new Cloud Run service, OAuth client,
Chrome extension id, DWD client, service account key path, or write/apply
surface unless the current path is proven impossible and the user explicitly
approves a design change.

#### Resume Inputs

- Cloud Run service:
  `run-mcp-day1-development-sheets-bridge-broker`
- Cloud Run URL:
  `https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app`
- Expected live revision:
  `run-mcp-day1-development-sheets-bridge-broker-00004-msn` or newer
- Chrome extension id:
  `jahlkdjaokmjbipfhlhnjggcgjmpeiij`
- Current Chrome OAuth client id / broker audience, pending replacement or
  confirmation for the `jahl...` Application ID:
  `862894425240-1r90upabo0gb42t41p7gj36dp1r37j24.apps.googleusercontent.com`
- Allowed pilot principal:
  `kangmin.lee@day1company.co.kr`
- Allowed pilot spreadsheet:
  `16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg`
- Allowed operation:
  `inspect.metadata`

#### Step 1: Static And Cloud Preflight

Run the existing automated checks first. Done when all commands pass:

```bash
git diff --check
python3 -m unittest discover broker/cloud-run-sheets-broker/test
python3 -m unittest discover native-host/test
python3 -m unittest discover cli/sheets-bridge/test
node --test extension/chrome-sheets-bridge/test/*.test.js
python3 -m py_compile broker/cloud-run-sheets-broker/src/*.py cli/sheets-bridge/sheets_bridge_cli.py
```

Then confirm the deployed broker front door. Done when `/v1/health` returns
broker JSON `200` and unauthenticated `/v1/inspect` returns broker JSON
`401 identity_evidence_failed`:

```bash
curl -sS 'https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app/v1/health'
curl -sS -X POST \
  'https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app/v1/inspect' \
  -H 'Content-Type: application/json' \
  -d '{}'
```

#### Step 2: Chrome Extension Preflight

Load or select the already-created Chrome extension. Done when Chrome shows the
extension id `jahlkdjaokmjbipfhlhnjggcgjmpeiij`, the extension is enabled, and
the user is signed into Chrome as `kangmin.lee@day1company.co.kr`.

If Chrome shows a different extension id for the unpacked extension, stop the
smoke and reload the extension after confirming the manifest `"key"` is present.
Do not broaden OAuth scopes or change DWD/service-account settings as a
shortcut.

Before retrying OAuth, confirm the Google Cloud Chrome App OAuth client uses
Application ID `jahlkdjaokmjbipfhlhnjggcgjmpeiij`. If the current client cannot
be changed, create a replacement Chrome App OAuth client for that Application
ID, then update `extension/chrome-sheets-bridge/manifest.json`
`oauth2.client_id` and Cloud Run `BROKER_AUDIENCE` to the new client id.

Open the pilot spreadsheet in a regular Chrome tab:

```text
https://docs.google.com/spreadsheets/d/16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg/edit
```

Done when the popup detects the spreadsheet id and shows the Inspect action as
available. The extension must not request Sheets or Drive OAuth scopes.

#### Step 3: Allowed Authenticated Inspect Smoke

Run the extension Inspect action from the pilot spreadsheet tab. If browser
automation is blocked from opening `chrome-extension://...` pages, the user must
perform this popup click manually; do not bypass Chrome extension page security
with raw browser protocol calls or alternate credential extraction. Done when:

- the popup reports Inspect complete
- the returned sanitized snapshot includes title
  `[DB_raw] 가벼운학습지 엔진`
- the snapshot includes 8 tabs
- the first tab metadata includes `[ML] 매출_최종`
- no OAuth token, access token, ID token, signed JWT, private key,
  `Authorization` header, or `Bearer` value is printed in browser console,
  shell output, Native Messaging payloads, fixtures, review packages, or repo
  files

This step also proves the deployed keyless Cloud Run runtime path if the
response succeeds, because the extension never calls Sheets API directly.

#### Step 4: Denied Broker Policy Smoke

Run one denied live request before marking Phase 1 complete. Preferred order:

1. Use a second verified Google principal outside broker policy and confirm the
   broker returns `403 policy_denied`.
2. If no second principal is available, open a spreadsheet not listed in
   `BROKER_POLICY_JSON` with the pilot principal and confirm the broker returns
   `403 policy_denied`.

Done when at least one denied request reaches the broker and is rejected before
any Sheets API call. If only the unknown-spreadsheet fallback is available,
record that unknown-principal live denial remains a residual manual check; do
not mark that specific manual check complete.

#### Step 5: Phase 1 Completion Gate

Phase 1 may be marked complete only when all of the following are true:

- automated checks from Step 1 pass
- deployed readiness and unauthenticated-auth failure checks pass
- allowed authenticated inspect returns the expected sanitized metadata through
  the deployed broker
- at least one live denied policy request returns `403 policy_denied`
- keyless Cloud Run runtime DWD path is the successful data path
- Section 14 is updated with the revision, smoke evidence, remaining risks, and
  frozen Phase 1 contracts

After Phase 1 completion, freeze the tested Phase 1 contracts in this section
and set the next default phase to Phase 2 Native Host Bridge. Do not begin
Phase 2 in the same change until Phase 1 completion evidence has been recorded.

#### Failure Routing

- `GET /v1/health` is not broker JSON `200`: inspect Cloud Run service URL,
  traffic target, and revision readiness before touching extension code.
- unauthenticated `POST /v1/inspect` is not broker JSON
  `401 identity_evidence_failed`: inspect Cloud Run routing and broker server
  dispatch before touching OAuth configuration.
- extension auth fails before broker call: check extension id, OAuth client id,
  OAuth consent state, Chrome signed-in account, and `openid email profile`
  scopes only. For `bad client id: {0}`, verify or recreate the Google Cloud
  OAuth client as Application type `Chrome App` with Application ID
  `jahlkdjaokmjbipfhlhnjggcgjmpeiij`, then ensure
  `extension/chrome-sheets-bridge/manifest.json` contains the Chrome extension
  public `"key"` that yields that same extension id. Compute the id from the
  public key before editing the manifest; a mismatch means the key came from a
  different Chrome Web Store item. If the generated client id changes, update
  both `extension/chrome-sheets-bridge/manifest.json` and Cloud Run
  `BROKER_AUDIENCE`, then reload the unpacked extension and redeploy/update the
  broker revision.
- broker returns `401 identity_evidence_failed`: inspect token audience,
  hosted domain, verified email, issuer, and tokeninfo alias normalization.
- broker returns `403 policy_denied`: inspect `BROKER_POLICY_JSON` principal,
  spreadsheet id, operation, sheet ids, ranges, and risk level.
- broker returns `502 credential_failed`: inspect Cloud Run runtime service
  account and IAM Credentials `signJwt` permission for the broker service
  account path.
- broker returns `502 dwd_subject_failed`: inspect Workspace DWD client id,
  read-only Sheets scope, and subject principal.
- broker returns `502 sheets_metadata_failed`: inspect spreadsheet ACL,
  spreadsheet id, Sheets API availability, and transient Google API failures.

## 15. Copy-Paste Codex Phase Goal Template

Use this template when starting an implementation phase:

```text
Implement Phase <N> from docs/codex-goal-chrome-extension-sheets-bridge.md only.
Do not implement later phases.
Use the fixed paths, schemas, protocol, and hard constraints from that document.
Do not expose service account keys, private keys, access tokens, OAuth tokens,
or raw credentials outside the browser auth flow or Cloud Run broker runtime;
never pass them into the native host, local agent, artifacts, logs, or repo.
Do not replace existing design choices or change completed phase contracts.
If <N> is omitted, implement Phase 0 only.
When done, run the applicable verification commands from the document and report:
files changed, commands run, completion criteria met/unmet, manual checks needed,
frozen public contracts, compatible next changes, and the next phase entry
condition. Also update Section 14 so a fresh session can continue from this
document alone.
```

## 16. Phase 0: Foundations

Create:

- `schemas/native-message.schema.json`
- `schemas/inspection.schema.json`
- `schemas/edit-plan.schema.json`
- `schemas/apply-result.schema.json`
- `extension/chrome-sheets-bridge/src/constants.js`
- `native-host/src/protocol.py`
- `native-host/test/test_protocol.py`

Expected outputs:

- JSON schemas define required top-level fields.
- `constants.js` exports protocol version, native host name, allowed message
  types, and default timeout budgets.
- `protocol.py` can read and write Chrome Native Messaging length-prefixed JSON.
- Tests cover valid frame roundtrip, invalid JSON, oversized message guard, and
  unknown message type.

Completion criteria:

- `python3 -m unittest discover native-host/test` passes.
- Every schema parses as JSON.
- `git diff --check` passes.
- No extension write/apply code exists yet.
- Handoff lists frozen protocol and schema names.

## 17. Phase 1: Broker Auth And Detection MVP

Create:

- `extension/chrome-sheets-bridge/manifest.json`
- `extension/chrome-sheets-bridge/package.json` with `"type": "module"`
- `extension/chrome-sheets-bridge/src/background.js`
- `extension/chrome-sheets-bridge/src/content.js`
- `extension/chrome-sheets-bridge/src/popup.html`
- `extension/chrome-sheets-bridge/src/popup.js`
- `extension/chrome-sheets-bridge/src/popup.css`
- `extension/chrome-sheets-bridge/src/sheets_api.js`
- `broker/cloud-run-sheets-broker/README.md`
- `broker/cloud-run-sheets-broker/src/auth.py`
- `broker/cloud-run-sheets-broker/src/dwd.py`
- `broker/cloud-run-sheets-broker/src/policy.py`
- `broker/cloud-run-sheets-broker/src/sheets_client.py`
- `broker/cloud-run-sheets-broker/test/test_auth.py`
- `broker/cloud-run-sheets-broker/test/test_policy.py`
- `broker/cloud-run-sheets-broker/test/test_sheets_client.py`
- `cli/sheets-bridge/README.md`
- `cli/sheets-bridge/sheets_bridge_cli.py`
- `cli/sheets-bridge/test/test_cli_requests.py`
- `extension/chrome-sheets-bridge/test/spreadsheet_id.test.js`

Required behavior:

- Extract `spreadsheetId` from active Google Sheets URLs.
- Reject non-Google-Sheets tabs with a clear message.
- Do not use `chrome.identity.getAuthToken` to call Sheets API directly from the
  extension.
- Extension-side code may obtain user identity evidence only to authenticate to
  the broker. Broker must verify it; local code must not trust it as authority.
- CLI can form the same broker inspect request shape as the extension for smoke
  and batch workflows.
- Broker auth module verifies issuer, audience, expiry, hosted domain, and
  principal for user identity evidence.
- Broker policy module evaluates default-deny allow/deny decisions for
  principal, optional spreadsheet id or spreadsheet wildcard, sheet ids, ranges,
  operations, and max risk.
- Broker DWD module selects `subject` equal to the verified user principal.
- Broker Sheets client can perform read-only `spreadsheets.get` metadata smoke
  through DWD impersonation for an allowed principal and a spreadsheet the
  impersonated user can access.
- Broker metadata smoke uses `includeGridData=false` and a narrow `fields` mask.
- Broker returns the normalized inspection metadata shape defined in Section 8
  plus bounded broker policy/audit summaries.
- Do not implement extension-to-host Native Messaging integration in Phase 1;
  that remains Phase 2.
- Do not implement write/apply API calls in Phase 1.

Completion criteria:

- URL parsing tests pass.
- Extension loads unpacked in Chrome without manifest errors and does not
  request Sheets OAuth scopes.
- Broker auth tests prove invalid issuer/audience/expiry/domain/principal are
  denied.
- Broker policy tests prove unknown users/spreadsheets/operations/ranges are
  denied.
- Broker policy tests prove an allowed pilot principal can inspect only the
  configured spreadsheet/range scope.
- CLI tests prove it sends the same broker request contract as the extension.
- Broker read-only smoke on one accessible Sheet returns tab metadata while DWD
  subject equals the verified user.
- Failed credential, policy denial, inaccessible spreadsheet, expired token, and
  non-Sheets-tab paths produce visible or structured user messages.
- DevTools, shell logs, broker fixtures, native payload fixtures, review package
  fixtures, and repository search confirm no service account key, private key,
  signed JWT, access token, ID token, `Bearer` header, OAuth token, or raw
  credential is logged or persisted.
- Inspection metadata fixture contains `spreadsheet_id`, `sheet_id`, tab grid
  sizes, title, locale, time zone, and capture timestamp.

## 18. Phase 2: Native Host Bridge

Create:

- `extension/chrome-sheets-bridge/src/native_bridge.js`
- `native-host/manifest/com.day1company.sheets_bridge.template.json`
- `native-host/src/host.py`
- `native-host/src/review_package.py`
- `native-host/test/test_review_package.py`
- `native-host/test/test_windows_install_artifacts.py`
- `native-host/install_macos.sh`
- `native-host/install_windows.ps1`
- `native-host/bin/sheets-bridge-native-host`
- `native-host/bin/sheets-bridge-native-host.cmd`

Required behavior:

- Extension sends an `inspect.snapshot` message to the native host with a
  sanitized broker inspection snapshot or a path to it.
- Host validates protocol version and message type.
- Host never receives user tokens and never calls Google Sheets APIs.
- Host persists broker policy decision summaries and sanitized inspection
  metadata, not raw credentials.
- Host writes a review package under
  `review-packages/sheets-bridge/native-host/<YYYY-MM-DD>/<request-id>/`.
- Review package contains `snapshot.json` and `manifest.json`.
- Host returns only a compact `review.result` with manifest path and summary.
- `review.generate` and `review.result` follow the request/result ownership
  rules from Section 7.

Completion criteria:

- Python host tests pass.
- Native host manifest contains the fixed host name and placeholder extension
  origin.
- macOS and Windows install scripts register the fixed native host name for the
  fixed extension origin.
- A local host invocation with a broker-allowed sanitized fixture writes a valid
  review package.
- A local host invocation with a broker-denied sanitized fixture writes only a
  denial summary and no inspection package.
- Extension handles host missing, host crash, invalid host response, and policy
  denial.
- Service account keys, private keys, access tokens, ID tokens, `Bearer`
  headers, and OAuth tokens are not included in any native message fixture.

## 19. Phase 3: Deep Inspect And Risk Scan

Extend:

- `broker/cloud-run-sheets-broker/src/sheets_client.py`
- `native-host/src/review_package.py`
- `schemas/inspection.schema.json`

Required behavior:

- Read targeted cell metadata with field masks.
- Inventory named ranges, protected ranges, data validations, hidden sheets, and
  formula samples.
- Classify formulas containing `IMPORTRANGE`, import functions, `QUERY`,
  `ARRAYFORMULA`, `INDIRECT`, or custom-function-like names.
- Classify cell states as `loaded`, `loading`, `permission_blocked`,
  `source_blocked`, `broken`, `oversized`, or `stale_unverified`.
- Record timeout, retry, and request count telemetry.
- Extend the normalized inspection snapshot without changing Phase 1 field
  meanings.

Completion criteria:

- Fixture inspection produces deterministic classification output.
- Review package includes `formulas.json`, `risks.json`, and
  `operational-health.json`.
- No full-grid read is used for medium Sheets.
- `Loading...`, `#REF!`, `#ERROR!`, and `#N/A` are never marked as verified
  success.

## 20. Phase 4: Edit Plan Generation

Create or extend:

- `schemas/edit-plan.schema.json`
- `extension/chrome-sheets-bridge/src/plan_validator.js`
- `extension/chrome-sheets-bridge/test/plan_validator.test.js`
- `native-host/src/plan_artifacts.py`

Required behavior:

- Agent/host can emit a dry-run edit plan artifact.
- Extension validates schema, spreadsheet id, known `sheetId` values, operation
  allowlist, preconditions, and high-risk approval flags.
- Broker validates policy eligibility for the plan target before returning live
  precondition samples or plan-read data.
- `plan_validator.js` validates against the normalized inspection snapshot, not
  popup-only state.
- Dry-run plan generation is owned by the local agent; durable plan artifact
  writing is owned by the native host.
- Plan preview displays target ranges, operations, risk level, rollback
  requirement, and readback ranges.
- No Sheets write API calls are implemented in this phase.

Completion criteria:

- Plan validator tests pass for valid plan, wrong spreadsheet id, unknown
  `sheetId`, missing preconditions, formula-to-value overwrite without explicit
  approval, and whole-sheet replacement attempt.
- Dry-run plan artifact is written to review package.
- Popup can show plan summary and `Apply disabled until Phase 5` state.

## 21. Phase 5: Apply Plan

Create:

- `extension/chrome-sheets-bridge/src/apply_executor.js`
- apply result writer in `native-host/src/plan_artifacts.py`
- `schemas/apply-result.schema.json`

Required behavior:

- Apply button is enabled only for schema-valid plans with explicit user
  approval and a passing Canonical Apply Plan Gate.
- Extension/CLI sends the exact approved plan and approval evidence to the
  broker; neither client writes directly to Sheets.
- Broker verifies user identity, policy, DWD subject, schema, identity, risk,
  approval evidence, and operation allowlist before any write.
- Broker re-reads precondition ranges immediately before writing.
- Broker captures before-state for every changed range.
- Broker executes only allowed operation types.
- Broker chunks writes into bounded batches.
- Broker polls readback ranges within `timeout_budget.poll_seconds`.
- Broker returns a sanitized apply result.
- Extension sends `apply.record`; native host persists the broker apply result
  artifact and returns `apply.result`.
- Broker stops on precondition mismatch, protected range failure, repeated
  `429`, repeated `503`, timeout, or user cancellation.

Completion criteria:

- Controlled test Sheet accepts low-risk `update_values` and `update_formulas`
  plans.
- Precondition mismatch test stops without writing.
- Formula-to-value overwrite requires explicit high-risk approval.
- Apply result contains changed ranges, before-state manifest, write batches,
  approval evidence, broker policy decision id, verified principal,
  impersonated subject, readback values, retry count, final status, rollback
  instructions, rollback limitations, and inverse-plan status/ref.
- Inverse plan is generated for simple value/formula edits or recorded as
  `not_feasible` with a reason.

## 22. Phase 6: Hardening

Create or extend:

- request budget manager in `broker/cloud-run-sheets-broker/src/sheets_client.py`
- audit log writer in native host
- protocol version negotiation
- host version check

Required behavior:

- Per-spreadsheet request pacing.
- Chunk size selection based on estimated payload.
- Truncated exponential backoff for `429`, `503`, and transient network errors.
- Broker audit log records request id, verified principal, impersonated subject,
  policy decision id, plan id, spreadsheet id, operation, changed ranges, and
  apply result reference.
- Native host audit/artifact log records local artifact paths and broker result
  summaries.
- Extension and host refuse incompatible protocol versions with a clear error.

Completion criteria:

- Synthetic large fixture completes phased inspect without unbounded reads.
- Retry telemetry appears in review package.
- Audit logs exclude service account keys, private keys, access tokens, ID
  tokens, OAuth tokens, `Bearer` headers, and raw credentials.
- Manual medium-sheet pilot completes within the selected timeout budget or
  reports a phased-inspect fallback.

## 23. Phase 7: Managed Deployment

Create:

- `docs/chrome-extension-managed-deployment.md`
- broker deployment checklist
- production native host manifest template
- macOS installer instructions or script
- extension release checklist

Required behavior:

- Document private/internal Chrome Web Store packaging.
- Document fixed extension id handling.
- Document Cloud Run broker deployment and runtime service account.
- Document Workspace Admin Domain-Wide Delegation with the broker service
  account client id, narrow scopes, and verified-user subject behavior.
- Document managed broker policy distribution/update.
- Document Local CLI distribution for smoke/batch/ops workflows.
- Document Chrome Enterprise allowlist or force install policy.
- Document Native Messaging host install, update, and uninstall.

Completion criteria:

- Fresh-machine install checklist exists.
- Broker DWD scopes are listed and justified.
- DWD subject behavior is documented and verified.
- Broker policy install/update verification exists.
- `chrome://policy` verification step exists.
- Native host registration verification step exists.
- Rollback procedure exists for extension and native host.

## 24. Per-Phase Handoff Format

At the end of every phase, Codex should report:

- files created or changed
- exact verification commands run
- manual verification still required
- phase completion criteria met or unmet
- frozen public contracts and compatibility tests
- compatible next-phase changes
- next phase entry condition

Do not mark a phase complete if any completion criterion is unverified.

In addition to reporting the handoff, Codex must update Section 14 so the next
fresh session can continue without reading any other handoff document.

## 25. Blocker Rules

If a phase is blocked:

- Do not redesign the architecture.
- Do not implement a different stack.
- Do not skip to a later phase.
- Record the blocker, failing command, and the smallest missing input.
- Continue only with tasks from the same phase that do not depend on the
  blocker.

The only valid reasons to stop are missing Cloud Run broker endpoint, missing
user identity verification setup, missing Domain-Wide Delegation setup, missing
pilot user principal/policy entry, missing extension id for Native Messaging
registration, missing test spreadsheet access, or security policy rejection.
