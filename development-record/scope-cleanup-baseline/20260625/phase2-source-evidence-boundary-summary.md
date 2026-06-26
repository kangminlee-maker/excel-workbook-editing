# Phase 2 Source Evidence Boundary Summary

## Scope

Phase 2 changed Google Sheets processing scripts from direct access execution to
local source-evidence artifact processing.

## Active Boundary

Live Google Sheets access belongs to Day1 MCP or another approved host. This
repository now expects credential-free source evidence/result JSON for the
bounded-window and validation-batch stages.

## Runtime Changes

- Added `scripts/google_sheets_source_evidence.py`.
- Removed `scripts/google_sheets_broker_client.py` from active scripts.
- Updated bounded-window sampling to:
  - create planned source-evidence requests;
  - accept `source_evidence_results` directly or via `--source-evidence-results`;
  - summarize supplied windows without performing live access.
- Updated validation-batch execution to:
  - read `source_evidence_read_plan`;
  - accept `source_evidence_results` directly or via `--source-evidence-results`;
  - emit validation evidence updates from supplied windows.
- Updated block-candidate tuning, cross-validation plan, table I/O, gate
  execution, evidence package, ontology mapping, and related schemas/tests to
  use source-evidence vocabulary.

## Contract Vocabulary

Current active terms:

- `source_evidence_results`
- `evidence_backed_read`
- `source_evidence_read_plan`
- `source_evidence_batch`
- `bounded_source_evidence`
- `required_source_evidence_operations`
- `source_access_policy_evidence`
- `blocked_until_source_access_evidence`

## Verification

Passed:

```bash
python3 -m py_compile scripts/google_sheets_*.py
python3 -m unittest discover -s tests -p 'test_google_sheets_*.py'
python3 - <<'PY'
import json
from pathlib import Path
for path in sorted(Path('schemas').glob('google-sheets-*.schema.json')):
    json.loads(path.read_text())
print('google sheets schemas json ok')
PY
rg -n "broker|Broker|DEFAULT_BROKER_URL|gcloud auth print-identity-token|X-Broker-Authorization|google_sheets_broker_client|--broker-url|--execute" scripts schemas tests --glob '!development-record/**'
```

The final grep returned no matches.
