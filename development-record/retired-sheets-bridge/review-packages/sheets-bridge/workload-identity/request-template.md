# SRE / Security Request Template

## Summary

Sheets Broker를 keyless Workload Identity 방식으로 운영하기 위한 pilot
승인을 요청드립니다. MCP/LLM-visible 결과에는 sanitized evidence만
반환하고, Google authority 생성과 사용은 hosted broker runtime 내부에서
수행합니다.

첨부:

- `sre-security-workload-identity-flow.svg`
- `pre-request-prep.md`
- `readonly-policy.pilot.template.json`
- 로컬 테스트 결과

## Pilot Runtime Values

| 항목 | 값 |
| --- | --- |
| GCP project | `<PROJECT_ID>` |
| region | `<REGION>` |
| Cloud Run service | `<BROKER_SERVICE>` |
| runtime identity | `<RUNTIME_IDENTITY>` |
| delegated identity | `<DELEGATED_IDENTITY>` |
| broker audience | `<BROKER_AUDIENCE>` |
| hosted domain | `<HOSTED_DOMAIN>` |
| pilot spreadsheet id | `<SPREADSHEET_ID>` |
| pilot sheet id | `<SHEET_ID>` |
| pilot range | `<A1_RANGE>` |

## SRE Request

1. Enable required APIs:
   - Cloud Run
   - IAM Credentials
   - Google Sheets

2. Configure Cloud Run:
   - service: `<BROKER_SERVICE>`
   - runtime identity: `<RUNTIME_IDENTITY>`
   - env:
     - `BROKER_AUDIENCE`
     - `BROKER_SERVICE_ACCOUNT_EMAIL`
     - `BROKER_HOSTED_DOMAIN`
     - `BROKER_POLICY_JSON`

3. Grant runtime authority:
   - allow `<RUNTIME_IDENTITY>` to call IAM Credentials `signJwt` for
     `<DELEGATED_IDENTITY>`.

4. Run smoke:
   - `GET /v1/health`
   - authorized `POST /v1/inspect` against the pilot spreadsheet/range

## Security Request

1. Approve Domain-wide Delegation for the delegated identity OAuth client.

2. Approve initial scope:
   - `https://www.googleapis.com/auth/spreadsheets.readonly`

3. Approve pilot policy boundary:
   - default deny
   - explicitly allowed principal
   - explicitly allowed spreadsheet
   - explicitly allowed sheet/range
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
