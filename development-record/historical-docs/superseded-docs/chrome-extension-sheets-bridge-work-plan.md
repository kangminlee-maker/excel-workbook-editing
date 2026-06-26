# Chrome Extension Sheets Bridge Work Plan

This work plan breaks the Chrome Extension Sheets bridge into staged releases.
Each stage has a clear completion condition and verification loop. The plan
covers read-only inspection through approved `apply plan` execution.

For implementation, treat
[codex-goal-chrome-extension-sheets-bridge.md](codex-goal-chrome-extension-sheets-bridge.md)
as the controlling goal spec. This file is the roadmap summary; the goal spec
contains fixed paths, contracts, and per-phase completion criteria.

For Chrome Web Store tester publication and internal pilot rollout, use
[chrome-extension-managed-deployment.md](chrome-extension-managed-deployment.md)
as the managed deployment runbook.

When no implementation phase is explicitly selected, start with Phase 0 only.
The repository-wide target tree is an allowed path inventory; each phase decides
which files may actually be created or changed.

## 0. Working Assumptions

- Existing Google Sheets must be edited in place.
- User-level CLI OAuth setup is not acceptable.
- Infra/SRE will deploy a Cloud Run broker.
- The broker uses Cloud Run keyless service identity and Workspace Domain-Wide
  Delegation to impersonate the verified user for Sheets API calls.
- No service account key is distributed to local machines, Chrome extensions,
  native messages, local CLIs, review packages, or repository files.
- The broker calls Google APIs and enforces user-specific default-deny policy
  before every inspect, plan, or apply action.
- Chrome Extension OAuth for Sheets API access is superseded for this project
  unless explicitly restored later.
- Local Native Messaging host receives sanitized broker snapshots/results and
  local artifact requests; it must not receive user tokens, raw browser
  credentials, or authority claims used by the broker.
- Local CLI is a secondary client for smoke tests, batch inspect, artifact
  regeneration, and operations; it uses the same broker API as the extension.
- `googleworkspace/cli` is reference-only for API exploration and CLI ergonomics.
  It is not a runtime dependency, subprocess backend, or credential path.
- Large Sheets require chunking, timeout budgets, retry budgets, and bounded
  polling.

## 1. Target Repository Shape

```text
excel-workbook-editing/
├── extension/
│   └── chrome-sheets-bridge/
│       ├── manifest.json
│       ├── src/
│       │   ├── background.js
│       │   ├── content.js
│       │   ├── popup.html
│       │   ├── popup.js
│       │   ├── popup.css
│       │   ├── sheets_api.js
│       │   ├── plan_validator.js
│       │   ├── native_bridge.js
│       │   ├── apply_executor.js
│       │   └── constants.js
│       └── test/
├── native-host/
│   ├── manifest/
│   ├── src/
│   │   ├── host.py
│   │   ├── protocol.py
│   │   ├── review_package.py
│   │   └── plan_artifacts.py
│   ├── test/
│   └── install_macos.py
├── broker/
│   └── cloud-run-sheets-broker/
│       ├── src/
│       │   ├── auth.py
│       │   ├── dwd.py
│       │   ├── policy.py
│       │   ├── sheets_client.py
│       │   ├── broker.py
│       │   └── audit.py
│       └── test/
├── cli/
│   └── sheets-bridge/
│       ├── sheets_bridge_cli.py
│       └── test/
├── schemas/
│   ├── inspection.schema.json
│   ├── edit-plan.schema.json
│   ├── apply-result.schema.json
│   └── native-message.schema.json
└── docs/
    ├── chrome-extension-sheets-bridge-design.md
    └── chrome-extension-sheets-bridge-work-plan.md
```

## 2. Phase 0: Foundations

Goal: define boundaries before building.

Deliverables:

- Broker DWD scope list for read-only and write modes.
- Cloud Run broker service identity and DWD subject strategy.
- Default-deny broker policy shape for principal, spreadsheet id, sheet id,
  range, operation, risk level, and approval requirements.
- Chrome Extension and Local CLI client roles.
- Extension id strategy for local, pilot, and managed deployment.
- Native Messaging host name and registration paths.
- Message protocol draft.
- Edit plan schema draft.
- Actor ownership table for extension, native host, local agent, popup/content,
  and local artifacts.
- Apply Plan Gate draft, disabled until Phase 5.
- Rollback artifact seats for before-state, rollback instructions, inverse
  plan, and rollback limitations.
- Test spreadsheet set:
  - small plain sheet
  - medium sheet with formulas
  - sheet with validations/protections
  - sheet with `IMPORTRANGE` or loading/error fixtures

Done when:

- Security boundary is documented.
- Credential handling rule is explicit: tokens/credentials stay in the browser
  auth flow or broker runtime and out of repository/artifacts/logs/native
  messages/local agent prompts.
- Admin deployment decision is recorded.
- Default phase-selection rule and frozen-contract handoff rule are recorded.

Verification:

- Review design against Cloud Run service identity, DWD, Native Messaging, and
  Sheets API docs.
- Validate schemas with a JSON schema parser.

## 3. Phase 1: Broker Auth And Detection MVP

Goal: inspect the active Google Sheet through the Cloud Run broker using
verified user identity, broker policy, and DWD impersonation, without
extension-side direct Sheets API access.

Build:

- `manifest.json` with active tab/content script access and no direct Sheets
  OAuth dependency.
- Content script that extracts `spreadsheetId` from Sheets URLs.
- User identity token/session acquisition for broker authentication.
- Broker auth verifier.
- Broker DWD subject selector where subject equals the verified user principal.
- Broker policy loader and evaluator.
- Local CLI request builder for the same broker inspect contract.
- Broker read-only metadata smoke:
  - spreadsheet title, locale, time zone
  - tabs, `sheetId`, grid size, hidden status
  - named ranges
  - protected ranges
- Popup UI with `Inspect` button and compact result summary.
- Normalized inspection metadata fixture for later plan validation.

Done when:

- A pilot principal allowed by policy can run a broker read-only metadata smoke
  against a Sheet the user can access and see tab list and grid dimensions.
- Broker DWD subject equals the verified pilot user.
- Unknown users, unknown spreadsheets, disallowed operations, and out-of-policy
  ranges are denied before a Sheets API call.
- No local service account key configuration is required.
- The extension handles non-Sheets tabs clearly.
- The broker handles invalid/expired token, missing DWD, missing policy, and
  inaccessible spreadsheet states gracefully.

Verification:

- Test auth token validation and allow/deny policy fixtures.
- Test one live Sheet that the impersonated pilot user can access.
- Test Local CLI request formation.
- Confirm `googleworkspace/cli` is not part of the runtime path and no credential
  flow depends on it.
- Confirm no service account key, private key, signed JWT, access token, ID
  token, `Bearer` header, OAuth token, or raw credential appears in source,
  fixtures, logs, native payloads, or review packages.
- Confirm failed credential/policy paths give clear messages.

## 4. Phase 2: Native Host Bridge

Goal: send broker-produced sanitized snapshots to the local host and receive
review outputs.

Build:

- Native Messaging host manifest.
- Host process with length-prefixed JSON protocol.
- Extension `native_bridge.js`.
- Message types:
  - `inspect.snapshot`
  - `review.generate`
  - `review.result`
  - `error`
- Local review package writer.

Done when:

- Extension can send sanitized broker snapshots to the host.
- Host writes a local review package and returns a manifest path.
- Denied principals receive a structured policy error and no API-derived review
  package is written.
- Large review output is passed by file reference, not one oversized message.
- Request/result ownership follows the stable protocol in the goal spec.

Verification:

- Unit test native protocol framing.
- Test host registration on macOS and Windows.
- Kill host mid-request and confirm extension handles disconnect.
- Confirm native fixtures and review packages contain broker policy summaries
  but no credentials or user tokens.

## 5. Phase 3: Deep Inspect And Risk Scan

Goal: classify spreadsheet structure and connected risks.

Build:

- Targeted range readers with field masks.
- Formula scanner for:
  - `IMPORTRANGE`
  - import functions
  - `QUERY`
  - `ARRAYFORMULA`
  - `INDIRECT`
  - custom function-looking formulas
- Cell state classifier:
  - loaded
  - loading
  - permission-blocked
  - source-blocked
  - broken
  - oversized
  - stale-unverified
- Validation and protection inventory.
- Timeout, quota, and retry telemetry.

Done when:

- Review package includes structure, formulas, connected risks, and loading/error
  states.
- The extension avoids full-grid reads on medium Sheets.

Verification:

- Fixture Sheet with known formulas produces expected classifications.
- Simulated `429` and `503` paths use bounded backoff.
- `Loading...` and `#REF!` are not marked as successful readback.

## 6. Phase 4: Edit Plan Generation

Goal: produce reviewable edit plans before any write.

Build:

- `edit-plan.schema.json`.
- Local plan generator interface.
- Plan validator in the extension.
- Plan preview UI with:
  - target spreadsheet
  - target tabs and ranges
  - operations
  - preconditions
  - risk level
  - rollback snapshot plan
  - readback ranges
- Dry-run mode that reads preconditions but performs no writes.
- `plan_validator.js` uses the normalized inspection snapshot as authority, not
  popup-only state.
- Local agent drafts plans; native host persists plan artifacts; extension
  validates and previews plans.

Done when:

- Agent can produce a valid edit plan from an inspection package.
- Extension rejects malformed, cross-spreadsheet, or overbroad plans.
- User can inspect or cancel the plan preview; Apply remains disabled until
  Phase 5.

Verification:

- Schema validation tests for valid and invalid plans.
- Plan validator tests for:
  - wrong `spreadsheetId`
  - unknown `sheetId`
  - missing preconditions
  - formula-to-value overwrite without explicit approval
  - whole-sheet replacement attempt

## 7. Phase 5: Apply Plan

Goal: safely apply approved, range-scoped edits.

Build:

- Before-state capture for changed ranges.
- Canonical Apply Plan Gate.
- Approval evidence bound to exact plan id, spreadsheet id, operation ids or
  affected ranges, risk level, timestamp, and visible confirmation text.
- Apply executor for allowed operation families:
  - values
  - formulas
  - formatting
  - data validation
  - row/column insert
  - row/column delete with high-risk approval
- Batch chunking.
- Precondition re-read immediately before write.
- Readback after write.
- Bounded polling for dependent outputs and external loading states.
- Apply result artifact.
- `apply.record` request and `apply.result` response path through native host.
- Inverse plan generation where feasible, with explicit `not_feasible` reason
  when not possible.

Done when:

- Low-risk value/formula updates apply successfully.
- Protected/validated cells are respected.
- Precondition mismatch stops the apply.
- Apply result records changed ranges, readback values, retry count, and rollback
  status.
- Apply result records approval evidence, before-state reference, rollback
  instructions, inverse-plan status/ref, and rollback limitations.

Verification:

- E2E test on a controlled test spreadsheet.
- Test precondition mismatch by editing the sheet between plan and apply.
- Test formula preservation and formula-to-value guard.
- Test rollback inverse plan on simple value/formula operations.

## 8. Phase 6: Hardening

Goal: make the bridge reliable for medium and large connected Sheets.

Build:

- Request budget manager.
- Per-spreadsheet request pacing.
- Chunk size tuning.
- Retry telemetry.
- Native host version check.
- Extension/host protocol version negotiation.
- Audit log:
  - who
  - spreadsheet id
  - plan id
  - changed ranges
  - approval timestamp
  - apply result
- Contract-lock handoff records protocol/schema/operation names frozen by each
  completed phase.

Done when:

- Medium Sheets complete inspect within the chosen budget.
- Large Sheets degrade into phased inspect rather than timing out silently.
- Audit log is enough to explain what changed.

Verification:

- Load test with synthetic large metadata/range fixtures.
- Manual pilot on a real medium spreadsheet.
- Confirm no raw service account key, private key, access token, ID token,
  `Bearer` header, OAuth token, or credential is logged.

## 9. Phase 7: Managed Deployment

Goal: reduce setup friction for users.

Build:

- Private or internal Chrome Web Store package.
- Fixed extension id.
- Cloud Run broker deployment with keyless runtime service identity.
- Workspace Admin Domain-Wide Delegation with narrow scopes.
- Managed broker policy distribution.
- Local CLI package for smoke/batch/ops workflows.
- Chrome Enterprise allowlist or force install policy.
- Native Messaging host installer.
- Update and rollback procedure for extension and host.
- Managed deployment runbook in
  `docs/chrome-extension-managed-deployment.md`.

Done when:

- Pilot user receives the extension without manual developer-mode install.
- Native host is installed and registered.
- Broker DWD scopes are limited to expected read/write needs.
- Broker policy denies unauthorized users and ranges.
- Chrome Web Store tester-pilot runbook, pilot evidence package shape, and
  rollback levers are documented before rollout expands.

Verification:

- Fresh-machine install test.
- Extension update test.
- Native host uninstall/reinstall test.
- Admin policy check in `chrome://policy`.
- Workspace Admin delegation check if domain-wide delegation is enabled.
- Managed broker policy check.

## 10. Apply Plan Guardrails

The Apply Plan feature must not ship until these are true:

- Read-only inspect is stable.
- Plan schema is versioned.
- Extension validates every operation.
- User approval is explicit and bound to the exact plan, ranges, risk level, and
  timestamp.
- Precondition re-read exists.
- Before-state capture exists.
- Readback exists.
- Timeout/retry telemetry exists.
- High-risk operations require separate explicit approval.
- `apply.record` persistence and `apply.result` response are implemented.
- Rollback instructions, inverse-plan status, and limitations are persisted.
- Service account key, private key, access token, ID token, `Bearer` header,
  OAuth token, or raw credential never enters native messages, local agent
  prompts, review packages, repository files, or logs.

## 11. Minimum MVP Cut

The first useful MVP should include only:

1. Broker auth/DWD/policy.
2. Active spreadsheet detection.
3. Metadata and tab inspection.
4. Local CLI smoke path.
5. Native host bridge.
6. Review package generation.

Apply Plan starts only after the read-only bridge is stable.

## 12. Open Questions

- Should review packages later move from the repository-style output root to a
  managed app data directory?
- Should remote planning be introduced after the local MVP is stable?
- Is Drive metadata scope acceptable in the organization?
- How should team-level operation policies be configured?
- Should high-risk apply operations require a second reviewer?
