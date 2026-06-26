# Pilot Decision

Status: keep pilot enabled; do not expand company-wide yet

## Decision

Keep the Chrome Sheets Bridge tester pilot enabled for the current pilot user.
The read-only metadata inspect and native-host package recording path passed.

Do not expand company-wide yet. The next safe step is a small second-tester or
managed-policy pilot after the remaining expansion blockers are resolved.

## Passed Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Web Store tester gate | Passed | User reported tester publication; extension installed and executed |
| Identity gate | Passed | Broker accepted `kangmin.lee@day1company.co.kr` |
| DWD gate | Passed | `impersonated_subject` equals verified principal |
| Policy gate | Passed for allowed path | `policy_reason: allowed` |
| Data boundary gate | Passed | Sanitized metadata only; credential scan clean |
| Native host gate | Passed | `manifest.json` and `snapshot.json` recorded |
| Reliability gate | Passed for first run | broker elapsed 2193 ms, client elapsed 2863 ms, retry 0 |
| Spreadsheet identity gate | Passed | Active spreadsheet id matched recorded snapshot |

## Open Before Wider Rollout

| Gate | Current state | Required next action |
| --- | --- | --- |
| Version gate | Behavior matches `0.1.1`; exact Chrome details version not copied | Record installed version from `chrome://extensions` if audit requires exact UI evidence |
| Admin policy gate | Manual tester install path used | Verify allowed/force install only for pilot group or OU |
| Live deny-path gate | Unauthenticated deny passed; second-principal deny not run | Run one live unauthorized user or inaccessible spreadsheet check |
| Cloud Logging audit gate | Broker-returned summaries captured; Cloud Logging not queried | SRE should query logs without exporting credentials |
| Rollback ownership | Rollback levers documented | Assign named SRE/Admin owners |

## Final Pilot Result

```text
request_id: f5fb141c-4439-4968-b663-12b2161459ee
principal: kangmin.lee@day1company.co.kr
impersonated_subject: kangmin.lee@day1company.co.kr
spreadsheet_id: 16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg
spreadsheet_title: [DB_raw] 가벼운학습지 엔진
tab_count: 8
policy_version: parser-readonly-windows-2026-06-02
policy_reason: allowed
native_package: /Users/kangmin/Library/Application Support/Day1/ChromeSheetsBridge/review-packages/sheets-bridge/native-host/2026-06-03/f5fb141c-4439-4968-b663-12b2161459ee/
```

## Recommended Next Step

Run a second-tester pilot with a managed install policy targeted to a small
group or OU. Include one live deny-path check before expanding beyond that
group.
