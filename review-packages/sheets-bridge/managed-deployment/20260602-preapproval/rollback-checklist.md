# Rollback Checklist

Prepare these rollback levers before expanding beyond the pilot target.

## Admin Console

- Remove the pilot install policy from the target group or OU.
- Confirm `chrome://policy` no longer lists the extension policy.
- Confirm Chrome removes or stops enforcing the extension according to policy.

## Broker Policy

- Remove the pilot principal allowlist, or replace the broker policy with a
  deny-all policy.
- Confirm an authenticated pilot inspect request is denied with a structured
  policy error.

## Cloud Run

- Keep the current known-ready revision:
  `run-mcp-day1-development-sheets-bridge-broker-00004-msn`.
- If a later revision fails, shift traffic back to the known-ready revision or
  deploy a deny-only configuration.
- Confirm `/v1/health` and unauthenticated `/v1/inspect` after rollback.

## Web Store

- If the extension package is wrong, submit a fixed version.
- Use server-side broker policy to disable risky behavior while the Web Store
  review lifecycle completes.

## Rollback Gate

Do not expand rollout unless at least one fast server-side disable path has
been tested.
