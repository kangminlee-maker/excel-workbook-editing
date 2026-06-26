# Workload Identity Pilot Request Draft

## Summary

Sheets Broker를 keyless Workload Identity 방식으로 운영하기 위한 첫
read-only pilot 승인을 요청드립니다. 이 pilot은 특정 사용자, 특정
spreadsheet, 특정 sheet/range로 제한합니다.

첨부:

- `sre-security-workload-identity-flow.svg`
- `pre-request-prep.md`
- `readonly-policy.pilot.draft.json`
- `local-preflight-commands.sh` 실행 결과

## Pilot Runtime Values

| 항목 | 값 |
| --- | --- |
| GCP project | `day1-dev` |
| region | `asia-northeast3` |
| Cloud Run service | `cloud-run-sheets-broker` |
| runtime identity | `day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com` |
| delegated identity | `day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com` |
| broker audience | `32555940559.apps.googleusercontent.com` |
| hosted domain | `day1company.co.kr` |
| pilot principal | `kangmin.lee@day1company.co.kr` |
| pilot spreadsheet id | `16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg` |
| pilot sheet id | `1116370414` |
| pilot range | `'[ML] 매출_최종'!A1:AN20` |

## SRE Request

1. Enable required APIs:
   - Cloud Run
   - IAM Credentials
   - Google Sheets

2. Configure Cloud Run:
   - service: `cloud-run-sheets-broker`
   - runtime identity: `day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com`
   - env:
     - `BROKER_AUDIENCE=32555940559.apps.googleusercontent.com`
     - `BROKER_SERVICE_ACCOUNT_EMAIL=day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com`
     - `BROKER_HOSTED_DOMAIN=day1company.co.kr`
     - `BROKER_POLICY_JSON=<readonly-policy.pilot.draft.json as compact JSON>`

3. Grant runtime authority:
   - allow `day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com` to call IAM
     Credentials `signJwt` for
     `day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com`.

4. Run smoke:
   - `GET /v1/health`
   - authorized `POST /v1/inspect` against the pilot spreadsheet/range

## Security Request

1. Approve Domain-wide Delegation for the delegated identity OAuth client.

2. Approve initial scope:
   - `https://www.googleapis.com/auth/spreadsheets.readonly`

3. Approve pilot policy boundary:
   - default deny
   - principal: `kangmin.lee@day1company.co.kr`
   - spreadsheet: `16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg`
   - sheet id: `1116370414`
   - range: `'[ML] 매출_최종'!A1:AN20`
   - read-only inspect operations only

4. Approve audit fields:
   - request id
   - principal
   - operation
   - spreadsheet id
   - HTTP status
   - policy decision
   - error code

## Pilot Success Criteria

- `/v1/health` reports `authority_mode: workload_identity`.
- unauthorized or out-of-policy requests are denied before Sheets API calls.
- authorized pilot inspect returns sanitized spreadsheet evidence.
- audit logs show request, principal, policy decision, and error/success status.
- output contains no credential material.

## Current Live Check

Current local tokeninfo confirms the user identity evidence audience as:

```text
32555940559.apps.googleusercontent.com
```

An inspect request against the current broker reached the DWD authority step and
failed at IAM Credentials `signJwt`:

```text
error_code: credential_failed
reason: IAM_PERMISSION_DENIED
missing permission: iam.serviceAccounts.signJwt
```

This means the pilot request is currently blocked on the runtime identity's IAM
Credentials authority for the delegated identity. If SRE/security want a
different production broker audience, they can configure that later; this pilot
request uses the verified gcloud smoke audience above.
