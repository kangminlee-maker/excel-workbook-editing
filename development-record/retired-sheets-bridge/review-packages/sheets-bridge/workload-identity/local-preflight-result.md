# Local Preflight Result

Run date: 2026-06-09 KST

## Commands

```bash
python3 -m json.tool review-packages/sheets-bridge/workload-identity/readonly-policy.pilot.draft.json
bash -n review-packages/sheets-bridge/workload-identity/sre-smoke-commands.draft.sh
bash review-packages/sheets-bridge/workload-identity/local-preflight-commands.sh
```

## Result

```text
draft-policy-json-ok
draft-smoke-shell-ok

== Broker source syntax ==
== Broker tests ==
Ran 79 tests OK
== Pilot policy JSON parse ==
== Active credential wording scan ==
== SVG XML parse ==
review-packages/sheets-bridge/workload-identity/sre-security-workload-identity-flow.svg
preflight ok
```

## Remaining External Check

Current local gcloud tokeninfo confirms this smoke audience:

```text
32555940559.apps.googleusercontent.com
```

The current live broker inspect probe reached IAM Credentials and failed with:

```text
credential_failed / IAM_PERMISSION_DENIED / iam.serviceAccounts.signJwt
```

See `current-broker-check.md`.

SRE still needs to grant the hosted runtime identity IAM Credentials `signJwt`
authority for the delegated identity and redeploy or update the broker runtime
to expose the newer Workload Identity readiness health payload.
