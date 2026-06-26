import { DEFAULT_BROKER_BASE_URL } from "./constants.js";

const SHEETS_URL_PATTERN =
  /^https:\/\/docs\.google\.com\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/;

export function parseSpreadsheetId(url) {
  if (typeof url !== "string") {
    return null;
  }
  const match = SHEETS_URL_PATTERN.exec(url);
  return match ? match[1] : null;
}

export function buildBrokerInspectRequest({
  spreadsheetId,
  userEmail = "",
  sheetIds = [],
  ranges = [],
  requestId = cryptoRandomId(),
  createdAt = new Date().toISOString(),
} = {}) {
  if (!spreadsheetId) {
    throw new Error("spreadsheetId is required");
  }

  return {
    request_id: requestId,
    operation: "inspect.metadata",
    spreadsheet_id: spreadsheetId,
    sheet_ids: sheetIds,
    ranges,
    risk_level: "low",
    created_at: createdAt,
    identity_hint: {
      principal: userEmail,
    },
  };
}

export async function fetchBrokerInspection({
  brokerBaseUrl = DEFAULT_BROKER_BASE_URL,
  request,
  identityEvidenceToken,
  fetchFn = fetch,
}) {
  if (!request) {
    throw new Error("request is required");
  }
  if (!identityEvidenceToken) {
    throw new Error("identityEvidenceToken is required");
  }

  const startedAt = Date.now();
  const response = await fetchFn(new URL("/v1/inspect", brokerBaseUrl).toString(), {
    method: "POST",
    headers: {
      "X-Broker-Authorization": `Bearer ${identityEvidenceToken}`,
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const body = await safeResponseText(response);
    throw new Error(
      `Broker inspection request failed (${response.status}): ${body || response.statusText}`,
    );
  }

  const brokerBody = await response.json();
  if (brokerBody?.ok === false) {
    const message =
      brokerBody?.error?.message ?? brokerBody?.error?.code ?? "Broker denied inspection request";
    throw new Error(message);
  }
  const snapshot = brokerBody?.payload ?? brokerBody;
  return {
    ...snapshot,
    telemetry: {
      ...(snapshot?.telemetry ?? {}),
      client_elapsed_ms: Date.now() - startedAt,
    },
  };
}

function cryptoRandomId() {
  const cryptoObject = globalThis.crypto;
  if (cryptoObject?.randomUUID) {
    return cryptoObject.randomUUID();
  }
  return `request-${Date.now()}`;
}

async function safeResponseText(response) {
  try {
    return await response.text();
  } catch {
    return "";
  }
}
