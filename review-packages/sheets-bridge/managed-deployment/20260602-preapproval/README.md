# Chrome Sheets Bridge Managed Deployment Pre-Approval Evidence

Captured at: `2026-06-02T08:16:39+0900`

This package records the work that can be completed before Chrome Web Store
approval is granted. It is intentionally credential-free.

## Contents

| File | Purpose |
| --- | --- |
| `admin-policy.md` | Workspace Admin request draft for pilot extension distribution |
| `broker-health.json` | Live `/v1/health` readiness response |
| `unauthenticated-deny.json` | Live unauthenticated `/v1/inspect` deny response |
| `broker-runtime-summary.md` | Non-secret Cloud Run runtime summary |
| `broker-audit-contract.md` | Sanitized broker audit event contract |
| `dwd-readiness-check.md` | Authenticated DWD readiness evidence checklist |
| `oauth-client-binding-check.md` | Managed Chrome App OAuth binding checklist |
| `pilot-policy.md` | First pilot allowlist and deny-path requirements |
| `chrome-policy-check.md` | Approval-day `chrome://policy` verification checklist |
| `rollback-checklist.md` | Disable and rollback levers before expanding rollout |
| `pilot-decision.md` | Pending pilot decision record |

## Credential Boundary

Do not add OAuth tokens, ID tokens, access tokens, bearer headers, service
account keys, private keys, cookies, refresh tokens, or raw credentials to this
directory.
