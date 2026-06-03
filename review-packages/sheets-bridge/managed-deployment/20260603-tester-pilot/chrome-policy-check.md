# Chrome Policy Check

Status: not required for current tester-published manual install; required for managed rollout

## Current Pilot

The first tester pilot succeeded without confirming a managed Chrome policy in
`chrome://policy`.

## Required Before Managed Expansion

When Workspace Admin applies allowed install or force install:

1. Open `chrome://policy`.
2. Click reload policies.
3. Confirm the policy includes extension id
   `jahlkdjaokmjbipfhlhnjggcgjmpeiij`.
4. Confirm the policy targets only the pilot group or OU.
5. Record the policy name, target group or OU, and install mode.

Do not paste browser cookies, tokens, or profile internals.
