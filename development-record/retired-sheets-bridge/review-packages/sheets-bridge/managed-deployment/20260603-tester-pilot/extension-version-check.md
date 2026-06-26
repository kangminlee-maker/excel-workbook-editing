# Extension Version Check

Status: behavior verified; Chrome details version text still optional evidence

## Expected Identity

- Extension name: `Chrome Sheets Bridge`
- Extension id: `jahlkdjaokmjbipfhlhnjggcgjmpeiij`
- Repository candidate version: `0.1.1`

## Manual Check

Open Chrome extension details for `Chrome Sheets Bridge` and record:

```text
installed_extension_id:
installed_version:
install_source:
enabled:
```

## Observed Behavior

- `Record Package` button appeared in the tester popup.
- `Record Package` successfully sent a native message and persisted a package.
- This behavior matches the repository `0.1.1` candidate because the earlier
  tester package showed only `Inspect`.

Exact `chrome://extensions` version text was not copied into this file. If
needed for audit closure, record it manually from Chrome extension details.

## Decision Rule

- If the installed version is `0.1.1`, continue pilot normally.
- If the installed version is `0.1.0`, metadata-only pilot may continue because
  the broker accepts both `Authorization` and `X-Broker-Authorization`, but
  expansion should wait for the `0.1.1` package.
- If the extension id is not `jahlkdjaokmjbipfhlhnjggcgjmpeiij`, stop and do
  not run pilot inspect.

Do not record OAuth tokens, ID tokens, access tokens, cookies, or raw browser
profile data.
