# Admin Policy

Status: manual tester install path used; managed policy not yet verified

## Current Pilot Path

The pilot succeeded through a tester-published Chrome Web Store install. No
company-wide managed deployment was required for this first tester run.

## Managed Install Values

Use this entry if Workspace Admin enables allowed install or force install:

```text
jahlkdjaokmjbipfhlhnjggcgjmpeiij;https://clients2.google.com/service/update2/crx
```

Recommended next target:

```text
pilot Google Group or small OU only
```

Do not deploy company-wide until the remaining expansion blockers in
`pilot-decision.md` are resolved.

## Rollback Owner

Pending: name Workspace Admin or SRE owner who can remove the extension install
policy or tester assignment.
