# Cloud Run Sheets Broker

This broker is the only Google API data plane for the Sheets bridge.
MCP servers or approved broker callers send identity evidence and bounded
inspect requests to the broker; local agents receive only sanitized
snapshots/results. Apply operations are enabled only through the bounded Phase
2 values path and a write-enabled broker policy.

Phase 1 implements:

- user identity claim validation helpers
- default-deny bridge policy evaluation
- DWD subject selection where `subject` equals the verified user principal
- keyless DWD token minting via Cloud Run runtime identity and IAM Credentials
  `signJwt`
- read-only Sheets metadata URL/normalization helpers
- bounded read-only grid/value/formula window URL/normalization helpers for
  parser samples
- bounded `apply.values_update` and `rollback.values_restore` helpers for
  value/formula writes through Sheets `values:batchUpdate`
- apply-before rollback snapshot capture and apply-after live readback
- a composable inspect handler tested with fake metadata transport
- a minimal `/v1/health` readiness endpoint and `/v1/inspect` HTTP entrypoint
  for Cloud Run
- sanitized JSON audit events for `/v1/inspect` outcomes

Runtime notes:

- `GET /v1/health` is unauthenticated and returns only a non-sensitive broker
  readiness signal, including the Workload Identity authority mode and token
  flow configured for the runtime. The contract is defined in
  `../../docs/workload-identity-runtime-contract.md`.
- `POST /v1/inspect` is the broker data-plane endpoint and requires
  `X-Broker-Authorization: Bearer ...`. The generic `Authorization` header is
  reserved for platform layers and is not accepted as user identity evidence.
- Broker policy evaluation uses only `verified_identity.principal`, which is
  derived by the broker from validated identity evidence. Client-provided
  `identity_hint` is advisory and must not authorize policy decisions.
- `/v1/inspect` emits sanitized audit events containing request id, operation,
  spreadsheet id, HTTP status, error code, verified principal, impersonated
  subject, and policy decision fields. Audit events must stay credential-free.
- Preferred production path is Cloud Run keyless service identity plus DWD.
- The Cloud Run runtime service account needs permission to call IAM
  Credentials `signJwt` for the broker service account.
- When the Cloud Run runtime service account and broker DWD service account are
  both `day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com`, SRE must grant the
  service account token creator role to itself:

```bash
gcloud iam service-accounts add-iam-policy-binding \
  day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com \
  --project=day1-dev \
  --member=serviceAccount:day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com \
  --role=roles/iam.serviceAccountTokenCreator
```

- Required runtime environment:
  - `BROKER_AUDIENCE`
  - optional `BROKER_ADDITIONAL_AUDIENCES`, comma-separated. For controlled
    local smoke tests with `gcloud auth print-identity-token`, include the
    Google Cloud SDK OAuth client id `32555940559.apps.googleusercontent.com`.
  - `BROKER_SERVICE_ACCOUNT_EMAIL`
  - `BROKER_POLICY_JSON`
  - optional `BROKER_HOSTED_DOMAIN`
  - optional `BROKER_ACCEPTED_ISSUERS`
- SRE smoke tests must use Workload Identity / runtime identity / IAM
  Credentials and must produce credential-free evidence.
- `googleworkspace/cli` is reference-only and is not a runtime dependency.

Readiness:

- Missing or malformed `X-Broker-Authorization` must return
  `identity_evidence_failed`.
- Valid Google identity evidence must match `BROKER_AUDIENCE`,
  `BROKER_HOSTED_DOMAIN`, and a verified email principal.
- Google OAuth tokeninfo responses may use `issued_to` and `verified_email`;
  the broker normalizes those before auth validation.
- Unknown principals, operations, sheet ids, ranges, or risk levels must be
  denied by broker policy before any Sheets API call. Spreadsheet ids may be
  exact allowlist entries or `"*"` wildcard entries; wildcard entries leave
  actual spreadsheet access to the impersonated user's Google ACL.
- Enterprise read-only rollout may use a domain principal entry such as
  `"*@day1company.co.kr"` together with spreadsheet `"*"`. This allows any
  verified company user to inspect spreadsheets they already can access,
  including spreadsheets owned outside Day1company, while Google ACL remains
  the final access authority. Exact principal entries override domain entries.
- Parser window operations `inspect.grid_window`, `inspect.values_window`, and
  `inspect.formula_window` must stay bounded by policy limits for ranges, cell
  budgets, field masks, timeout, and retry.
- Test apply operations use `apply.values_update` and `rollback.values_restore`
  only. They must stay bounded by explicit A1 ranges, exact values shape,
  write-cell budgets, timeout, and retry. `apply.values_update` must include
  `rollback_required=true`; the broker captures rollback values before writing
  and reads back the changed range after writing.
- Structural edits, tab deletion, row/column deletion, formatting writes, and
  Apps Script mutation are outside the active test deployment surface.
- A request containing only `identity_hint` must be denied by broker policy.
- Public Cloud Run invoker access should be requested only after the deployed
  revision contains these guards.
