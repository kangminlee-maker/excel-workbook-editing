#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/pilot-values.draft.env"

if [[ -z "${BROKER_AUDIENCE:-}" ]]; then
  echo "BROKER_AUDIENCE must be set before SRE runs this smoke." >&2
  exit 1
fi

POLICY_FILE="$(dirname "${BASH_SOURCE[0]}")/readonly-policy.pilot.draft.json"

gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  iamcredentials.googleapis.com \
  sheets.googleapis.com \
  --project "$PROJECT_ID"

gcloud iam service-accounts add-iam-policy-binding "$DELEGATED_IDENTITY" \
  --project "$PROJECT_ID" \
  --member "serviceAccount:$RUNTIME_IDENTITY" \
  --role "roles/iam.serviceAccountTokenCreator"

gcloud iam service-accounts get-iam-policy "$DELEGATED_IDENTITY" \
  --project "$PROJECT_ID" \
  --flatten "bindings[].members" \
  --filter "bindings.role=roles/iam.serviceAccountTokenCreator AND bindings.members=serviceAccount:$RUNTIME_IDENTITY" \
  --format "table(bindings.role, bindings.members)"

cat > /tmp/sheets-broker-env.yaml <<EOF
BROKER_AUDIENCE: "$BROKER_AUDIENCE"
BROKER_SERVICE_ACCOUNT_EMAIL: "$DELEGATED_IDENTITY"
BROKER_HOSTED_DOMAIN: "$BROKER_HOSTED_DOMAIN"
BROKER_POLICY_JSON: '$(jq -c . "$POLICY_FILE")'
EOF

echo "Deploy/update Cloud Run with /tmp/sheets-broker-env.yaml and runtime identity:"
echo "  service: $BROKER_SERVICE"
echo "  region: $REGION"
echo "  runtime identity: $RUNTIME_IDENTITY"
echo
echo "After deploy, run:"

cat <<'EOF'
if [[ -z "${BROKER_URL:-}" ]]; then
  BROKER_URL="$(gcloud run services describe "$BROKER_SERVICE" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --format='value(status.url)')"
fi

BROKER_TOKEN="$(gcloud auth print-identity-token)"

curl -s "$BROKER_URL/v1/health" | jq .

curl -s -X POST "$BROKER_URL/v1/inspect" \
  -H "X-Broker-Authorization: Bearer $BROKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"request_id\": \"sre-readonly-pilot-001\",
    \"operation\": \"inspect.values_window\",
    \"spreadsheet_id\": \"$PILOT_SPREADSHEET_ID\",
    \"sheet_ids\": [$PILOT_SHEET_ID],
    \"ranges\": [\"$PILOT_RANGE\"],
    \"risk_level\": \"low\"
  }" | jq .
EOF

echo
echo "If Cloud Run invoker auth is enabled, SRE should run the same request from"
echo "an approved runtime or service identity that can mint the platform identity"
echo "token for the Cloud Run service URL, then include it as Authorization."
