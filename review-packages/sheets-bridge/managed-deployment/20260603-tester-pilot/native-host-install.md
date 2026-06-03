# Native Host Install

Captured: 2026-06-03 KST

## Problem

`Record Package` failed in the Chrome Sheets Bridge popup with:

```text
Specified native messaging host not found.
```

## Cause

The macOS Chrome Native Messaging manifest for
`com.day1company.sheets_bridge` was not present under:

```text
/Users/kangmin/Library/Application Support/Google/Chrome/NativeMessagingHosts/
```

## Action

Installed the native host manifest by running:

```bash
./native-host/install_macos.sh
```

Installed manifest:

```text
/Users/kangmin/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.day1company.sheets_bridge.json
```

The manifest points to:

```text
/Users/kangmin/Documents/excel-workbook-editing/native-host/bin/sheets-bridge-native-host
```

Allowed origin:

```text
chrome-extension://jahlkdjaokmjbipfhlhnjggcgjmpeiij/
```

## Verification

- Manifest exists.
- Host executable exists and is executable.
- `python3 -m py_compile native-host/src/*.py` passed.
- `python3 -m unittest discover -s native-host/test` passed with 12 tests.

## Follow-up Fix

After manifest installation, Chrome found the native host but reported:

```text
Native host has exited.
```

The native host launcher was changed from a Python shebang script to a shell
launcher that:

- chooses `/usr/bin/python3` or `/opt/homebrew/bin/python3` explicitly;
- keeps stdout reserved for the Native Messaging protocol;
- writes only start/exit status to
  `review-packages/sheets-bridge/native-host/native-host.log`;
- does not log message payloads or credentials.

Because Chrome did not update `native-host.log` during the failing retry, the
macOS installer was changed to copy the runtime out of the repository and into:

```text
/Users/kangmin/Library/Application Support/Day1/ChromeSheetsBridge/native-host/
```

The Chrome manifest now points to:

```text
/Users/kangmin/Library/Application Support/Day1/ChromeSheetsBridge/native-host/bin/sheets-bridge-native-host
```

Chrome-like environment verification passed with:

- `PATH=/usr/bin:/bin:/usr/sbin:/sbin`
- framed `inspect.snapshot` native message
- `review.result` response
- generated `snapshot.json` and `manifest.json`

Installed-runtime verification also passed under the same restricted `PATH`.
Installed packages and logs are written under:

```text
/Users/kangmin/Library/Application Support/Day1/ChromeSheetsBridge/review-packages/sheets-bridge/native-host/
```

## Next Step

Restart Chrome, then open the Chrome Sheets Bridge popup and click
`Record Package` again.
If Chrome still reports `Native host has exited`, inspect:

```text
/Users/kangmin/Library/Application Support/Day1/ChromeSheetsBridge/review-packages/sheets-bridge/native-host/native-host.log
```
