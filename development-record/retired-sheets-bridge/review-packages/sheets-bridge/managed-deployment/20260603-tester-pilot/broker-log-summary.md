# Broker Log Summary

Status: broker-returned audit fields captured; Cloud Logging query pending

## Broker-Returned Evidence

The successful native-host package contains broker policy and auth summaries:

```text
request_id: f5fb141c-4439-4968-b663-12b2161459ee
principal: kangmin.lee@day1company.co.kr
impersonated_subject: kangmin.lee@day1company.co.kr
spreadsheet_id: 16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg
operation: inspect.metadata
policy_version: parser-readonly-windows-2026-06-02
policy_reason: allowed
broker_elapsed_ms: 2193
client_elapsed_ms: 2863
retry_count: 0
```

## Cloud Logging

Cloud Logging was not queried in this run. The local `gcloud` identity-token
path was previously blocked by Context-Aware Access, so log retrieval should be
done by SRE or from an allowed managed-device session.

Expected log fields:

- request id
- principal
- impersonated subject
- spreadsheet id
- operation
- policy version or decision id
- HTTP status
- broker error code, if any

Do not export bearer tokens, OAuth tokens, service account credentials, cookies,
or raw authorization headers from Cloud Logging.
