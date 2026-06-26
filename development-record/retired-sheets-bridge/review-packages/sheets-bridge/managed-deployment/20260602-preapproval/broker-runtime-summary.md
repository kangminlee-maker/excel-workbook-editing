# Broker Runtime Summary

Captured at: `2026-06-02T08:16:39+0900`

Command used:

```bash
gcloud run services describe run-mcp-day1-development-sheets-bridge-broker \
  --project=day1-dev \
  --region=asia-northeast3 \
  --format='json(status.url,status.latestReadyRevisionName,status.traffic,spec.template.spec.serviceAccountName,spec.template.spec.containers[0].env)'
```

## Cloud Run Service

| Field | Value |
| --- | --- |
| Service | `run-mcp-day1-development-sheets-bridge-broker` |
| Project | `day1-dev` |
| Region | `asia-northeast3` |
| URL | `https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app` |
| Latest ready revision | `run-mcp-day1-development-sheets-bridge-broker-00004-msn` |
| Traffic | `100%` to latest ready revision |
| Runtime service account | `862894425240-compute@developer.gserviceaccount.com` |

## Runtime Environment Summary

| Variable | Observed value |
| --- | --- |
| `BROKER_AUDIENCE` | `862894425240-1r90upabo0gb42t41p7gj36dp1r37j24.apps.googleusercontent.com` |
| `BROKER_SERVICE_ACCOUNT_EMAIL` | `day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com` |
| `BROKER_HOSTED_DOMAIN` | `day1company.co.kr` |
| `BROKER_POLICY_JSON` | Present; pilot allowlist summarized in `pilot-policy.md` |
| Structured audit logging | Local code now emits sanitized `/v1/inspect` audit events; live Cloud Run redeploy and log query evidence are pending |

## Readiness Result

- `/v1/health` returned HTTP 200 JSON.
- Unauthenticated `/v1/inspect` returned HTTP 401 JSON with
  `identity_evidence_failed`.
- The broker did not return an HTML platform error page for the checked paths.
- Authenticated inspect, IAM `signJwt`, DWD token minting, and audit log query
  evidence are pending approval-day or pre-pilot validation.

## Credential Boundary

No service account key, OAuth token, ID token, access token, bearer header,
cookie, refresh token, or private key was recorded in this summary.
