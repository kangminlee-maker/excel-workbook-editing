# Sheets Bridge CLI

Secondary client for smoke tests, batch inspection, and artifact regeneration.
The CLI must call the Cloud Run broker contract only. It must not call Google
Sheets API directly and must not hold service account keys or DWD credentials.

Phase 1 supports dry-run request construction and local Codex/gcloud broker
inspect calls.

Dry-run request:

```bash
python3 cli/sheets-bridge/sheets_bridge_cli.py inspect \
  --spreadsheet-id 16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg \
  --principal kangmin.lee@day1company.co.kr \
  --dry-run
```

Broker-backed read smoke from the current `gcloud` account:

```bash
python3 cli/sheets-bridge/sheets_bridge_cli.py inspect \
  --spreadsheet-id 16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg \
  --principal kangmin.lee@day1company.co.kr
```

Bounded parser window smoke:

```bash
python3 cli/sheets-bridge/sheets_bridge_cli.py inspect \
  --spreadsheet-id 1gp3jl_DyB8kvxHO7m4YjsCPbFTPGi-XKyqPhGAlTZ60 \
  --principal kangmin.lee@day1company.co.kr \
  --operation inspect.formula_window \
  --range "'26_0601'!A1:Z80" \
  --total-cell-count 2080 \
  --timeout-seconds 60 \
  --retry-count 0
```

The CLI sends the current `gcloud auth print-identity-token` output only to the
Cloud Run broker over HTTPS, using `X-Broker-Authorization` so Cloud Run/IAM
does not consume the identity evidence. It prints the broker JSON response and
never writes the token to disk.

If the response is `credential_failed` with
`iam.serviceAccounts.signJwt denied`, SRE must grant
`roles/iam.serviceAccountTokenCreator` to
`serviceAccount:day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com` on the
`day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com` service account.
