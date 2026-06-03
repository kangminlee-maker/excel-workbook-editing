# Pilot Decision Record

Status: `pending_web_store_approval`

## Decision Inputs

| Gate | Current state |
| --- | --- |
| Web Store approval | Pending |
| Admin policy target | Pending |
| Broker health | Passed pre-approval check |
| Unauthenticated deny | Passed pre-approval check |
| Policy evaluator authority | Local code updated to require `verified_identity`; live deploy pending |
| Pilot allowlist | Prepared for principal and spreadsheet; metadata sheet/range semantics clarified |
| Broker audit logging | Local code updated; live deploy and log query evidence pending |
| OAuth client binding | Pending Console evidence |
| DWD authenticated inspect | Pending authenticated pilot |
| Chrome policy check | Pending approval and Admin policy |
| Extension smoke test | Pending approval and install |
| Unauthorized deny test | Pending authenticated pilot path |
| Rollback owners | Pending Admin and broker owner names |
| Rollback path | Prepared, not yet tested end to end |

## Approval-Day Decision

Record the decision after running the pilot smoke test:

```text
Decision:
Reason:
Request id:
Verified principal:
Impersonated subject:
Policy decision:
Spreadsheet id:
Sanitized result summary:
Rollback path tested:
Admin target and install mode:
Admin rollback owner:
Broker rollback owner:
Next rollout target:
```
