# Cloud Run Sheets Broker

This broker is the only Google API data plane for the Sheets bridge.
Chrome Extension and Local CLI clients send identity evidence and bounded
inspect requests to the broker; local agents and native messages receive only
sanitized snapshots/results. Apply operations are a later protocol and policy
phase, not part of the active Phase 1 broker surface.

Phase 1 implements:

- user identity claim validation helpers
- default-deny bridge policy evaluation
- DWD subject selection where `subject` equals the verified user principal
- keyless DWD token minting via Cloud Run runtime identity and IAM Credentials
  `signJwt`
- read-only Sheets metadata URL/normalization helpers
- bounded read-only grid/value/formula window URL/normalization helpers for
  parser samples
- a composable inspect handler tested with fake metadata transport
- a minimal `/v1/health` readiness endpoint and `/v1/inspect` HTTP entrypoint
  for Cloud Run
- sanitized JSON audit events for `/v1/inspect` outcomes

Runtime notes:

- `GET /v1/health` is unauthenticated and returns only a non-sensitive broker
  readiness signal.
- `POST /v1/inspect` is the broker data-plane endpoint and requires
  `X-Broker-Authorization: Bearer ...`. The broker still accepts
  `Authorization: Bearer ...` as a compatibility fallback, but clients should
  use the broker-specific header so Cloud Run/IAM handling does not interfere
  with user identity evidence.
- Broker policy evaluation uses only `verified_identity.principal`, which is
  derived by the broker from validated identity evidence. Client-provided
  `identity_hint` is advisory and must not authorize policy decisions.
- `/v1/inspect` emits sanitized audit events containing request id, operation,
  spreadsheet id, HTTP status, error code, verified principal, impersonated
  subject, and policy decision fields. It must not log bearer tokens, OAuth
  tokens, service account keys, private keys, cookies, or raw credentials.
- Do not place service account keys in this repository.
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
    (`862894425240-1r90upabo0gb42t41p7gj36dp1r37j24.apps.googleusercontent.com`
    was the initial Phase 1 Chrome Sheets Bridge OAuth client; replace it with
    the Chrome App OAuth client id whose Application ID matches the canonical
    extension id `jahlkdjaokmjbipfhlhnjggcgjmpeiij`)
  - optional `BROKER_ADDITIONAL_AUDIENCES`, comma-separated. For local Codex or
    CLI smoke tests with `gcloud auth print-identity-token`, include the Google
    Cloud SDK OAuth client id `32555940559.apps.googleusercontent.com`.
  - `BROKER_SERVICE_ACCOUNT_EMAIL`
  - `BROKER_POLICY_JSON`
  - optional `BROKER_HOSTED_DOMAIN`
  - optional `BROKER_ACCEPTED_ISSUERS`
- If a temporary key is used for an SRE smoke test, it must live outside
  clients and repository artifacts, and should be removed after keyless
  verification.
- `googleworkspace/cli` is reference-only and is not a runtime dependency.

Pre-public readiness:

- Missing or malformed `Authorization` must return `identity_evidence_failed`.
- Valid Google identity evidence must match `BROKER_AUDIENCE`,
  `BROKER_HOSTED_DOMAIN`, and a verified email principal.
- Chrome OAuth access-token `tokeninfo` responses may use `issued_to` and
  `verified_email`; the broker normalizes those before auth validation.
- Unknown principals, operations, sheet ids, ranges, or risk levels must be
  denied by broker policy before any Sheets API call. Spreadsheet ids may be
  exact allowlist entries or `"*"` wildcard entries; wildcard entries leave
  actual spreadsheet access to the impersonated user's Google ACL.
- Parser window operations `inspect.grid_window`, `inspect.values_window`, and
  `inspect.formula_window` must stay bounded by policy limits for ranges, cell
  budgets, field masks, timeout, and retry.
- A request containing only `identity_hint` must be denied by broker policy.
- Managed deployment must verify that `BROKER_AUDIENCE` matches the Chrome App
  OAuth client id whose Application ID is the canonical extension id
  `jahlkdjaokmjbipfhlhnjggcgjmpeiij`.
- Public Cloud Run invoker access should be requested only after the deployed
  revision contains these guards.
