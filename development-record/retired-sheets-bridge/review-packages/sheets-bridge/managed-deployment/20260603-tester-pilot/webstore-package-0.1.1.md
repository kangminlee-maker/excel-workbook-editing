# Web Store Package 0.1.1

Captured: 2026-06-03 KST

## Why This Package Is Needed

The tester-installed extension showed only the `Inspect` button after reinstall.
The current repository popup contains both:

- `Inspect`
- `Record Package`

Therefore the installed Web Store package does not match the current repository
candidate, or the previously uploaded zip was created before the native-host
recording button was added.

## Upload Candidate

```text
review-packages/sheets-bridge/managed-deployment/20260603-tester-pilot/chrome-sheets-bridge-0.1.1-webstore.zip
```

SHA-256:

```text
25ecbd40be2043d8526137abb9795213bc464ad3781102ca93200cc8dec128a9
```

## Package Verification

- Manifest version: `0.1.1`
- Extension name: `Chrome Sheets Bridge`
- Contains `src/popup.html` with `Record Package` button.
- Uses `X-Broker-Authorization` for broker identity evidence.
- Excludes test files.
- Excludes `.DS_Store`.
- Credential scan found no private key, service account key, OAuth token,
  access token, refresh token, or API key pattern.

## After Upload

1. Upload the zip to the existing Chrome Web Store item
   `jahlkdjaokmjbipfhlhnjggcgjmpeiij`.
2. Submit to testers.
3. Wait until Chrome updates the tester extension, or remove/reinstall after the
   new version is available.
4. Confirm `chrome://extensions` shows version `0.1.1`.
5. Open the pilot Sheet, run `Inspect`, then click `Record Package`.
