# Deny Path Check

Status: partial pass; live second-principal check still pending before wider rollout

## Passed

Unauthenticated broker request was denied:

```text
endpoint: /v1/inspect
status: 401
broker_error_code: identity_evidence_failed
message: Authorization header is required
```

This proves the broker does not serve inspect requests without identity
evidence.

## Covered By Tests

Broker policy unit tests cover:

- unknown principal denied;
- identity hint cannot override verified identity;
- unknown operation denied;
- policy risk above allowed level denied;
- out-of-policy bounded parser windows denied.

Latest local verification:

```text
python3 -m unittest discover -s broker/cloud-run-sheets-broker/test
```

## Pending Before Expansion

A live unauthorized user or unauthorized spreadsheet check has not been executed
in the tester environment because the current local CLI identity path is blocked
by Context-Aware Access and no second test principal was used through the
extension.

For the next tester group, run one of:

- an extension inspect as a second user who is not allowed by broker policy;
- an extension inspect on a spreadsheet the impersonated user cannot access;
- a broker call from SRE using a controlled non-pilot principal.

Do not request or record tokens while running the deny-path check.
