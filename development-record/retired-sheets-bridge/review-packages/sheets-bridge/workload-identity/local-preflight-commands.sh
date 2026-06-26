#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

echo "== Broker source syntax =="
python3 -m py_compile broker/cloud-run-sheets-broker/src/*.py

echo "== Broker tests =="
python3 -m unittest discover -s broker/cloud-run-sheets-broker/test

echo "== Pilot policy JSON parse =="
python3 -m json.tool \
  review-packages/sheets-bridge/workload-identity/readonly-policy.pilot.template.json \
  >/dev/null

echo "== Active credential wording scan =="
if rg -n \
  "service account key|service-account-key|service_account_key|SA key|SA 키|key file|key files|from_service_account_file|GOOGLE_APPLICATION_CREDENTIALS|private key|private keys|private_key" \
  AGENTS.md CLAUDE.md README.md IMPLEMENTATION_MAP.html SKILL.md docs references mcp packaging broker scripts schemas tests projects \
  --glob '!docs/archive/**' \
  --glob '!development-record/**' \
  --glob '!review-packages/**'
then
  echo "Unexpected active credential wording found." >&2
  exit 1
fi

echo "== SVG XML parse =="
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET

path = Path("review-packages/sheets-bridge/workload-identity/sre-security-workload-identity-flow.svg")
ET.parse(path)
print(path)
PY

echo "preflight ok"
