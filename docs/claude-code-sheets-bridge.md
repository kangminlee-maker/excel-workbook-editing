# Claude Code Sheets Bridge Handoff

This handoff lets Claude Code work with Chrome Sheets Bridge artifacts without
receiving Google credentials or depending on Codex-only tools.

## Authority Boundary

Claude Code may read and analyze only sanitized bridge artifacts:

- native-host review package `manifest.json`
- native-host review package `snapshot.json`
- local design docs and tests in this repository

Claude Code must not ask for, store, echo, or derive:

- OAuth tokens
- ID tokens
- access tokens
- bearer headers
- service account keys
- private keys
- cookies
- raw DWD credentials

Google identity, DWD impersonation, Sheets API calls, and broker policy
evaluation are owned by the Chrome Extension, Local CLI, and Cloud Run broker.
Claude Code must not call Google Sheets API directly for this bridge unless the
user explicitly starts a separate connector/API task and provides a safe
credential path outside the bridge.

## Normal Claude Code Flow

1. Read `AGENTS.md` and `CLAUDE.md`.
2. For connected Google Sheets behavior, read
   `references/connected-google-sheets-principles.md`.
3. For bridge architecture, read
   `docs/chrome-extension-sheets-bridge-design.md`.
4. For native-host install and package paths, read `native-host/README.md`.
5. Locate a review package under one of these roots:

```text
review-packages/sheets-bridge/native-host/<YYYY-MM-DD>/<request-id>/
~/Library/Application Support/Day1/ChromeSheetsBridge/review-packages/sheets-bridge/native-host/<YYYY-MM-DD>/<request-id>/
```

6. Read `manifest.json` first, then read only the referenced `snapshot.json`.
7. Treat `snapshot.json` as a sanitized point-in-time read model, not as live
   spreadsheet authority.
8. Produce analysis, review notes, or edit-plan drafts as local artifacts only.

## Do Not Cross These Lines

- Do not request the extension's identity token.
- Do not inspect Chrome profile cookies or extension storage.
- Do not use service account keys.
- Do not write credentials into review packages, logs, prompts, shell history,
  or repository files.
- Do not export a connected Google Sheet to `.xlsx`, edit it, and reupload it
  as a replacement.
- Do not treat LLM-generated plans as applied spreadsheet changes.

## Local Installation References

macOS Native Messaging install:

```bash
./native-host/install_macos.sh
```

Windows Native Messaging install:

```powershell
powershell -ExecutionPolicy Bypass -File .\native-host\install_windows.ps1
```

Both installers register the same native host name:

```text
com.day1company.sheets_bridge
```

Both installers allow only this Chrome extension origin:

```text
chrome-extension://jahlkdjaokmjbipfhlhnjggcgjmpeiij/
```

## Verification Expectations

Before relying on a handoff package:

- `manifest.json` exists and references `snapshot.json`.
- `snapshot.json` contains no credential-like fields.
- `snapshot.json` includes broker policy and broker auth summaries when
  produced by the broker.
- The broker auth summary `principal` and `impersonated_subject` match for
  user-owned reads.
- Any write plan remains a proposal until a future broker apply path records an
  approved `apply.result`.
