# MCP Sheets Bridge Remote Auth Runbook

## Purpose

The remote MCP HTTP server uses a user/session authorization boundary for live
Google Sheets access. The model-visible MCP result contains sanitized authority
summaries only. Access tokens remain inside the remote session provider.

## HTTP Runtime

Start the development HTTP entrypoint:

```bash
PYTHONPATH=mcp python3 mcp/sheets_bridge_http_server.py --host 127.0.0.1 --port 8766
```

The runtime exposes:

- `GET /healthz`
- `POST /mcp`

The MCP request uses the same tool names and JSON-RPC shape as the local stdio
server.

## Session Handle

Each live Google Sheets HTTP request includes a remote session handle in one of
these headers:

```text
Authorization: Bearer <remote-session-id>
```

or:

```text
X-Sheets-Bridge-Session: <remote-session-id>
```

The session id is a server-side handle. It is resolved by the remote session
store to an access token, granted scopes, user identity, authority mode, and
expiry.

## Development Session Store

For local development and smoke tests, configure a JSON session store:

```bash
export SHEETS_BRIDGE_REMOTE_AUTH_SESSIONS_PATH=/secure/path/sheets-bridge-remote-sessions.json
```

Example shape:

```json
{
  "sessions": {
    "session-read": {
      "access_token": "<stored in approved runtime storage>",
      "scopes": ["https://www.googleapis.com/auth/spreadsheets.readonly"],
      "user_email": "user@example.com",
      "authority": "remote_user_oauth",
      "expires_at": "2026-06-08T12:00:00+00:00"
    }
  }
}
```

Production deployments should replace the file store with approved
infrastructure storage or a host session provider. The visible MCP contract stays
the same.

## Required Scopes

| Tool family | Required remote authority |
| --- | --- |
| Metadata, values, formulas, grid reads | `spreadsheets.readonly` or `spreadsheets` |
| Values apply and values rollback | `spreadsheets` |
| Formula-table sheet creation | `spreadsheets` |
| Google spreadsheet copy or copied-file delete | `spreadsheets` plus `drive.file` or `drive` |
| Chrome current-tab resolution | Desktop runtime |
| Local workbook paths and Excel recalculation | Desktop runtime |

## Credential-Free Results

Remote auth tool outputs and review packages may include:

- authority mode;
- user email or subject when supplied by the session provider;
- granted scope names;
- expiry timestamp;
- operation status;
- package paths and sanitized spreadsheet evidence.

They include sanitized authority summaries only, not credential material or
local OAuth cache paths.

## Status Results

Common structured statuses:

| Status | Meaning | Next action |
| --- | --- | --- |
| `authenticated` | Session exists, has scopes, and is active | Proceed with the requested MCP tool. |
| `remote_auth_required` | No session handle was supplied | Authorize the remote MCP session and retry. |
| `remote_session_not_found` | Session handle is absent from approved storage | Refresh or recreate the remote session. |
| `remote_session_expired` | Session expiry is in the past | Refresh or reauthorize the session. |
| `remote_permission_denied` | Session exists but lacks a required scope | Reauthorize with the requested access level. |
| `remote_google_api_error` | Google rejected the live API call | Check spreadsheet ACLs, scopes, and requested ranges. |
| `local_runtime_required` | The request needs desktop-local files, Chrome, or Excel | Use the local stdio MCP runtime or an approved uploaded-artifact workflow. |

## Enterprise Variant

Cloud Run or another hosted deployment can use an enterprise provider that
verifies the user/session and mints Google authority through the approved
organization path. For Domain-wide Delegation deployments, use Workload
Identity / runtime identity plus IAM Credentials. Runtime and smoke-test outputs
remain credential-free.

See `docs/workload-identity-runtime-contract.md` for the hosted broker
authority flow, readiness contract, and verification gates.
