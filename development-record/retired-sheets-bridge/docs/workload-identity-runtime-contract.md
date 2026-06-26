# Workload Identity Runtime Contract

## Purpose

This contract defines the hosted Sheets broker authority path for environments
that use Workload Identity. The goal is to keep Google authority inside the
approved runtime while returning only sanitized evidence to MCP clients, review
packages, and LLM-visible outputs.

## Authority Flow

```text
verified user/session evidence
-> broker identity and policy gates
-> hosted runtime identity
-> IAM Credentials signJwt
-> OAuth JWT bearer exchange
-> bounded Google Sheets operation
-> sanitized broker result or review artifact
```

## Required Runtime Inputs

- `BROKER_AUDIENCE`
- `BROKER_SERVICE_ACCOUNT_EMAIL`
- `BROKER_POLICY_JSON`
- optional `BROKER_ADDITIONAL_AUDIENCES`
- optional `BROKER_HOSTED_DOMAIN`
- optional `BROKER_ACCEPTED_ISSUERS`

The hosted runtime identity must be allowed to call IAM Credentials `signJwt`
for the delegated identity named by `BROKER_SERVICE_ACCOUNT_EMAIL`. Domain-wide
Delegation scopes must match the broker operation surface.

## Readiness Contract

`load_runtime_config()` fails fast when required runtime inputs are missing or
malformed. When configuration loads successfully, it attaches a
`workload_identity` readiness summary with:

- `authority_mode: workload_identity`
- `delegation_mode: domain_wide_delegation`
- configured runtime gates
- token-flow steps
- a non-sensitive readiness boolean

`GET /v1/health` exposes this summary without delegated identity values,
access tokens, policy bodies, or local machine paths. Live authority probes are
performed through authorized `/v1/inspect` requests or SRE smoke tests, not by
public health checks.

## Verification Gates

- Config gate: required environment and JSON policy parse.
- Identity gate: verified user/session evidence matches accepted issuer,
  audience, optional hosted domain, and verified principal.
- Policy gate: requested spreadsheet, tab, range, operation, and risk are
  allowed before any Sheets call.
- Authority gate: runtime identity can mint delegated Google authority through
  IAM Credentials.
- Sheets gate: Google ACL and API response validate the requested operation.
- Output gate: broker responses, audit events, and review packages contain only
  sanitized summaries and evidence.

## Runtime Boundary

The broker remains the only Google API data plane for this hosted path. MCP
clients submit bounded requests and receive bounded results. Spreadsheet writes
remain limited to explicitly approved apply/rollback operations with live
readback.
