# Current Broker Check

Run date: 2026-06-09 KST

## Tokeninfo Evidence

The local `gcloud auth print-identity-token` tokeninfo response exposed these
non-sensitive identity facts:

```json
{
  "aud": "32555940559.apps.googleusercontent.com",
  "iss": "https://accounts.google.com",
  "email": "kangmin.lee@day1company.co.kr",
  "hd": "day1company.co.kr",
  "email_verified": "true"
}
```

No token value was stored.

## Broker URL

```text
https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app
```

`GET /v1/health` currently returns:

```json
{"ok": true, "service": "cloud-run-sheets-broker"}
```

The deployed revision has not yet been updated to the newer Workload Identity
readiness health payload.

## Inspect Probe

Request summary:

```json
{
  "request_id": "local-current-broker-audience-check-001",
  "operation": "inspect.values_window",
  "spreadsheet_id": "16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg",
  "sheet_ids": [1116370414],
  "ranges": ["'[ML] 매출_최종'!A1:AN20"],
  "risk_level": "low"
}
```

Result summary:

```json
{
  "ok": false,
  "error_code": "credential_failed",
  "reason": "IAM_PERMISSION_DENIED",
  "missing_permission": "iam.serviceAccounts.signJwt"
}
```

## Interpretation

The broker accepted enough identity/policy evidence to reach the DWD authority
step. The current blocker is IAM Credentials authority from the hosted runtime
identity to the delegated identity.

The next SRE action is to grant the runtime identity authority to call IAM
Credentials `signJwt` for the delegated identity, then rerun the same inspect
probe.
