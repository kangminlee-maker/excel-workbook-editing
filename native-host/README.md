# Sheets Bridge Native Host

Phase 2 Native Messaging host for Chrome Sheets Bridge.

The host receives sanitized `inspect.snapshot` messages from the extension,
rejects credential-like material, writes a local review package, and returns a
`review.result` manifest reference. It never calls Google APIs and never handles
OAuth tokens, service account keys, DWD credentials, or bearer headers.

The macOS executable wrapper is a shell launcher that chooses `/usr/bin/python3`
or `/opt/homebrew/bin/python3` explicitly so Chrome does not depend on an
interactive shell `PATH`. Windows uses a `.cmd` launcher. Both paths call the
same Python native host entrypoint.

## Install For Local Chrome On macOS

```bash
./native-host/install_macos.sh
```

The installer copies the macOS runtime to:

```text
~/Library/Application Support/Day1/ChromeSheetsBridge/native-host/
```

It writes a generated manifest to:

```text
~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.day1company.sheets_bridge.json
```

The manifest path points to:

```text
~/Library/Application Support/Day1/ChromeSheetsBridge/native-host/bin/sheets-bridge-native-host
```

The manifest allows only this extension origin:

```text
chrome-extension://jahlkdjaokmjbipfhlhnjggcgjmpeiij/
```

## Install For Local Chrome On Windows

Run PowerShell from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\native-host\install_windows.ps1
```

The installer writes a generated manifest to:

```text
%LOCALAPPDATA%\Day1\ChromeSheetsBridge\NativeMessagingHosts\com.day1company.sheets_bridge.json
```

It registers the current-user Chrome Native Messaging host key:

```text
HKCU\Software\Google\Chrome\NativeMessagingHosts\com.day1company.sheets_bridge
```

The manifest path points to:

```text
native-host\bin\sheets-bridge-native-host.cmd
```

## Package Output

When the host is run from this repository, packages are written under:

```text
review-packages/sheets-bridge/native-host/<YYYY-MM-DD>/<request-id>/
```

When installed through `install_macos.sh`, packages and the native-host log are
written under:

```text
~/Library/Application Support/Day1/ChromeSheetsBridge/review-packages/sheets-bridge/native-host/
```

Set `SHEETS_BRIDGE_REVIEW_ROOT` before launching Chrome if a different package
root is required.

Each package contains:

- `snapshot.json`
- `manifest.json`

## Verify

```bash
python3 -m unittest discover -s native-host/test
python3 -m py_compile native-host/src/*.py
```
