# Pilot Inspect Result

Status: passed

## User Report

- 2026-06-03 KST: User reported that `Inspect` completed in the Chrome Sheets
  Bridge extension popup.
- Local native-host `snapshot.json` / `manifest.json` was not found yet under
  `review-packages/sheets-bridge/`, so broker-auth/policy details remain
  unrecorded in this evidence package.
- 2026-06-03 KST: `Record Package` initially failed with
  `Specified native messaging host not found.`
- 2026-06-03 KST: macOS Native Messaging manifest was installed for
  `com.day1company.sheets_bridge`; retry `Record Package`.
- 2026-06-03 KST: User reported `Package recorded`.
- 2026-06-03 KST: Native host wrote sanitized review packages under the
  installed App Support package root.

## Recorded Package

Latest package:

```text
/Users/kangmin/Library/Application Support/Day1/ChromeSheetsBridge/review-packages/sheets-bridge/native-host/2026-06-03/f5fb141c-4439-4968-b663-12b2161459ee/
```

Earlier duplicate package from the same snapshot:

```text
/Users/kangmin/Library/Application Support/Day1/ChromeSheetsBridge/review-packages/sheets-bridge/native-host/2026-06-03/0edb4105-904f-4b38-beca-d6b10d569ff1/
```

## Expected Action

From the pilot Google Sheet tab:

1. Open the `Chrome Sheets Bridge` extension popup.
2. Confirm it detects spreadsheet id
   `16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg`.
3. Click `Inspect`.
4. Record the sanitized result below.

## Result Fields

```text
executed_at: 2026-06-03T05:45:41.617150+00:00
extension_status_text: Package recorded
request_id: f5fb141c-4439-4968-b663-12b2161459ee
principal: kangmin.lee@day1company.co.kr
impersonated_subject: kangmin.lee@day1company.co.kr
spreadsheet_id: 16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg
spreadsheet_title: [DB_raw] 가벼운학습지 엔진
tab_count: 8
locale: ko_KR
time_zone: Asia/Tokyo
policy_version: parser-readonly-windows-2026-06-02
policy_reason: allowed
broker_status: ok
user_visible_error: none
```

## Pass Criteria

- `principal` and `impersonated_subject` are
  `kangmin.lee@day1company.co.kr`.
- `spreadsheet_id` matches the active pilot Sheet.
- Extension displays sanitized metadata such as title, tab count, locale, and
  time zone.
- No token, credential, cookie, service account key, private key, or bearer
  header is recorded.

## Current Blocking Note

Codex could confirm Chrome and Sheet access automatically, but direct automation
of the extension internal popup was blocked by Chrome control security policy.
Continue with the normal visible extension popup operated by the user.

Do not paste or record OAuth tokens, ID tokens, access tokens, bearer headers,
cookies, service account keys, private keys, or raw browser profile data.

## Verification

- `manifest.json` and `snapshot.json` exist in the latest package.
- Snapshot source is `chrome_native_messaging`.
- `principal` and `impersonated_subject` both match the pilot user.
- Spreadsheet id matches the pilot Sheet.
- Credential scan found no private key, service account key, OAuth token,
  access token, refresh token, API key, bearer header, or cookie pattern.
