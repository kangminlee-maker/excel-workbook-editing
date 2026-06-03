# Workspace Admin Pilot Distribution Request

## Request

After Chrome Web Store approval, apply a pilot Chrome extension policy for
Chrome Sheets Bridge.

## Extension

| Field | Value |
| --- | --- |
| Extension name | `Chrome Sheets Bridge` |
| Extension id | `jahlkdjaokmjbipfhlhnjggcgjmpeiij` |
| Update URL | `https://clients2.google.com/service/update2/crx` |
| Raw force-install entry | `jahlkdjaokmjbipfhlhnjggcgjmpeiij;https://clients2.google.com/service/update2/crx` |

## Recommended Pilot Scope

- Target a small pilot Google Group or OU first.
- Do not deploy company-wide until the pilot smoke test passes.
- Start with install allowed or normal installed when possible.
- Move to force installed only after broker, identity, and policy gates pass.

## Admin Completion Criteria

- The pilot target group or OU is named.
- The install mode is recorded.
- The policy is visible in `chrome://policy` for the pilot Chrome profile.
- The extension details page shows id
  `jahlkdjaokmjbipfhlhnjggcgjmpeiij`.
- The extension version matches the approved Web Store version.

## Notes For Admin

The extension is intended for internal Day1 spreadsheet review workflows. It
does not call Google Sheets API directly from Chrome. The extension sends the
active spreadsheet id and user identity evidence to the Cloud Run broker, and
the broker enforces Workspace identity, Domain-Wide Delegation subject matching,
and broker policy.
