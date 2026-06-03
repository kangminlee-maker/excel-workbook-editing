# DWD Readiness Check

Status: `pending_authenticated_pilot`

Health and unauthenticated deny checks are not enough to prove authenticated
Google Sheets inspect readiness.

## Required Evidence Before Pilot Expansion

- Workspace Admin DWD entry includes service account client id for
  `day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com`.
- Workspace Admin DWD scope includes only
  `https://www.googleapis.com/auth/spreadsheets.readonly` for the current
  inspect path.
- Cloud Run runtime service account can call IAM Credentials `signJwt` for the
  DWD service account.
- Broker can mint a DWD access token with subject equal to
  `kangmin.lee@day1company.co.kr`.
- Authenticated `/v1/inspect` returns sanitized metadata for spreadsheet
  `16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg`.
- Broker audit event records the verified principal and impersonated subject.

## Credential Boundary

Record only status, request id, principal, impersonated subject, policy decision,
spreadsheet id, and sanitized metadata summary. Do not record tokens, signed
JWTs, access tokens, bearer headers, service account keys, or private keys.
