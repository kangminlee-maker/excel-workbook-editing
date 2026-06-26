# Chrome Precheck

Captured: 2026-06-03 12:03-12:05 KST

## Chrome Profile

- Chrome automation connection: available
- Selected profile name: `day1company`
- Profile was reported as last-used by the Chrome control surface.

## Pilot Sheet

- Spreadsheet id: `16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg`
- Loaded URL:
  `https://docs.google.com/spreadsheets/d/16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg/edit?gid=1116370414#gid=1116370414`
- Loaded title: `[DB_raw] 가벼운학습지 엔진 - Google Sheets`
- Result: Chrome profile can open the pilot spreadsheet.

## Extension Automation Boundary

Attempting to open the extension internal popup URL directly was blocked by the
Chrome control security policy. The pilot must continue through the normal
human-visible Chrome extension popup flow:

1. Keep the pilot Google Sheet open in Chrome.
2. Open the `Chrome Sheets Bridge` extension from the Chrome toolbar.
3. Confirm the extension id and installed version from Chrome extension details.
4. Click `Inspect`.
5. Record only the sanitized result summary, request id, principal,
   spreadsheet id, broker policy decision/version, and visible extension status.

Do not copy OAuth tokens, ID tokens, access tokens, bearer headers, cookies, or
raw browser internals into the evidence package.
