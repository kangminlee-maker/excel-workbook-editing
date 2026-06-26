# Rollback Checklist

Status: ready for pilot-scale rollback

## Fast Disable Paths

1. Broker policy disable:
   - Remove the pilot principal from `BROKER_POLICY_JSON`, or deploy a deny-only
     policy version.
   - Expected effect: extension remains installed but broker denies work.

2. Chrome Web Store tester disable:
   - Remove the user or test group from tester access.
   - Expected effect: new installs and updates stop for that tester target.

3. Managed install disable, if Admin Console policy is later used:
   - Remove extension id
     `jahlkdjaokmjbipfhlhnjggcgjmpeiij` from allowed/force install policy.
   - Expected effect: managed installation no longer applies.

4. Native host disable:
   - Remove:

```text
~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.day1company.sheets_bridge.json
```

   - Expected effect: `Record Package` fails, but broker inspect can still run.

## Data Safety

Rollback does not require editing, exporting, replacing, or re-uploading the
Google Sheet. No spreadsheet writes are enabled in this pilot.

## Owners

- Broker rollback owner: pending SRE assignment.
- Admin/Web Store rollback owner: pending Workspace/Admin assignment.
