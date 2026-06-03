# Broker Audit Contract

Status: `local_code_updated_pending_deploy`

`/v1/inspect` should emit one sanitized audit event per request outcome.
Malformed JSON and non-object JSON request bodies should also emit exactly one
sanitized `bad_request` audit event before returning HTTP 400.

## Required Fields

| Field | Meaning |
| --- | --- |
| `event` | Fixed event name, `sheets_broker.inspect` |
| `logged_at` | Broker-side timestamp |
| `request_id` | Client request id when supplied |
| `operation` | Requested broker operation |
| `spreadsheet_id` | Target spreadsheet id |
| `http_status` | HTTP status returned by broker |
| `ok` | Broker result boolean |
| `error_code` | Structured error code, if any |
| `principal` | Verified policy/auth principal when available |
| `impersonated_subject` | DWD subject when available |
| `policy_decision_id` | Broker policy decision id when available |
| `policy_version` | Broker policy version when available |
| `policy_allowed` | Broker policy allow/deny result when available |
| `policy_reason` | Broker policy reason when available |

## Must Not Appear

- `Authorization` headers
- bearer token values
- OAuth access tokens
- ID tokens
- refresh tokens
- service account keys
- private keys
- cookies
- raw credentials

## Pending Evidence

After redeploy, capture a Cloud Logging query result showing one success or deny
event with the required fields and no credential material.
