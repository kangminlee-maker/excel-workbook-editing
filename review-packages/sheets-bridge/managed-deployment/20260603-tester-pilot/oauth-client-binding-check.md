# OAuth Client Binding Check

Status: passed by live extension inspect behavior; exact console binding remains admin-verifiable

## Expected Values

```text
extension_id: jahlkdjaokmjbipfhlhnjggcgjmpeiij
chrome_oauth_client_id: 862894425240-1r90upabo0gb42t41p7gj36dp1r37j24.apps.googleusercontent.com
hosted_domain: day1company.co.kr
```

## Evidence

The tester-installed extension obtained Google identity evidence accepted by
the broker. The broker returned a successful policy/auth summary for:

```text
principal: kangmin.lee@day1company.co.kr
impersonated_subject: kangmin.lee@day1company.co.kr
policy_reason: allowed
```

This is sufficient to prove the live extension OAuth flow is compatible with
the broker audience and domain checks for the pilot user.

## Remaining Admin Evidence

For broader rollout, Workspace/GCP Admin can still confirm in Google Cloud
Console that the Chrome App OAuth client Application ID maps to:

```text
jahlkdjaokmjbipfhlhnjggcgjmpeiij
```

Do not export OAuth tokens or client secrets.
