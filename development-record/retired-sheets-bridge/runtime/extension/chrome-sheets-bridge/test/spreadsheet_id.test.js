import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import test from "node:test";
import {
  ALLOWED_MESSAGE_TYPES,
  NATIVE_HOST_NAME,
  PLANNED_REQUEST_MESSAGE_TYPES,
  PLANNED_RESULT_MESSAGE_TYPES,
} from "../src/constants.js";
import {
  buildInspectSnapshotMessage,
  recordInspectionSnapshot,
} from "../src/native_bridge.js";
import {
  buildBrokerInspectRequest,
  fetchBrokerInspection,
  parseSpreadsheetId,
} from "../src/sheets_api.js";

const fixtureSnapshot = JSON.parse(
  readFileSync(
    new URL("./fixtures/inspection-metadata.json", import.meta.url),
    "utf8",
  ),
);

const manifest = JSON.parse(
  readFileSync(new URL("../manifest.json", import.meta.url), "utf8"),
);

test("parseSpreadsheetId extracts ids from standard Google Sheets URLs", () => {
  assert.equal(
    parseSpreadsheetId(
      "https://docs.google.com/spreadsheets/d/16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg/edit#gid=0",
    ),
    "16vSTLkSxs-j3NxRJ8g_PNYGPuskQkJOWYBss_BDYQJg",
  );
  assert.equal(
    parseSpreadsheetId(
      "https://docs.google.com/spreadsheets/d/sheet-id_123-ABC/view",
    ),
    "sheet-id_123-ABC",
  );
});

test("parseSpreadsheetId rejects non-Sheets URLs", () => {
  assert.equal(parseSpreadsheetId("https://example.com/spreadsheets/d/abc"), null);
  assert.equal(parseSpreadsheetId("not a url"), null);
  assert.equal(parseSpreadsheetId(null), null);
});

test("buildBrokerInspectRequest matches the broker inspect contract", () => {
  assert.deepEqual(
    buildBrokerInspectRequest({
      spreadsheetId: "spreadsheet-1",
      userEmail: "Pilot.User@DAY1COMPANY.co.kr",
      sheetIds: [10],
      ranges: ["Input!A1:B10"],
      requestId: "request-1",
      createdAt: "2026-06-01T00:00:00.000Z",
    }),
    {
      request_id: "request-1",
      operation: "inspect.metadata",
      spreadsheet_id: "spreadsheet-1",
      sheet_ids: [10],
      ranges: ["Input!A1:B10"],
      risk_level: "low",
      created_at: "2026-06-01T00:00:00.000Z",
      identity_hint: {
        principal: "Pilot.User@DAY1COMPANY.co.kr",
      },
    },
  );
});

test("manifest keeps broker-backed Phase 2 extension surface narrow", () => {
  assert.equal(manifest.manifest_version, 3);
  assert.deepEqual(manifest.permissions.toSorted(), [
    "activeTab",
    "identity",
    "identity.email",
    "nativeMessaging",
  ]);
  assert.deepEqual(manifest.oauth2.scopes.toSorted(), [
    "email",
    "openid",
    "profile",
  ]);
  assert.equal(manifest.background.service_worker, "src/background.js");
  assert.equal(manifest.background.type, "module");
  assert.equal(
    manifest.oauth2.client_id,
    "862894425240-1r90upabo0gb42t41p7gj36dp1r37j24.apps.googleusercontent.com",
  );
  assert.equal(extensionIdFromManifestKey(manifest.key), "jahlkdjaokmjbipfhlhnjggcgjmpeiij");
  assert.ok(manifest.host_permissions.includes("https://*.run.app/*"));
  assert.ok(manifest.host_permissions.includes("http://localhost/*"));
  assert.ok(manifest.host_permissions.includes("https://docs.google.com/spreadsheets/*"));
  assert.ok(
    manifest.oauth2.scopes.every(
      (scope) => !scope.includes("spreadsheets") && !scope.includes("drive"),
    ),
  );
  assert.ok(
    manifest.host_permissions.every((host) => !host.includes("sheets.googleapis.com")),
  );
});

test("Phase 2 active protocol excludes future plan and apply messages", () => {
  assert.deepEqual(ALLOWED_MESSAGE_TYPES, [
    "inspect.snapshot",
    "review.generate",
    "review.result",
    "error",
  ]);
  assert.deepEqual(PLANNED_REQUEST_MESSAGE_TYPES, ["plan.generate", "apply.record"]);
  assert.deepEqual(PLANNED_RESULT_MESSAGE_TYPES, ["plan.result", "apply.result"]);
});

test("buildInspectSnapshotMessage wraps sanitized snapshots for native host", () => {
  assert.deepEqual(
    buildInspectSnapshotMessage({
      snapshot: fixtureSnapshot,
      requestId: "request-1",
    }),
    {
      protocol_version: "1.0",
      request_id: "request-1",
      type: "inspect.snapshot",
      payload: {
        snapshot: fixtureSnapshot,
      },
    },
  );
});

test("recordInspectionSnapshot sends to the configured native host", async () => {
  globalThis.chrome = { runtime: { lastError: null } };
  let requestedHost = "";
  let requestedMessage = {};

  const result = await recordInspectionSnapshot({
    snapshot: fixtureSnapshot,
    requestId: "request-1",
    sendNativeMessageFn: (host, message, callback) => {
      requestedHost = host;
      requestedMessage = message;
      callback({
        ok: true,
        type: "review.result",
        payload: {
          artifact_path: "/tmp/review/manifest.json",
        },
      });
    },
  });

  assert.equal(requestedHost, NATIVE_HOST_NAME);
  assert.equal(requestedMessage.type, "inspect.snapshot");
  assert.equal(requestedMessage.request_id, "request-1");
  assert.equal(requestedMessage.payload.snapshot.spreadsheet_id, "spreadsheet-1");
  assert.equal(result.artifact_path, "/tmp/review/manifest.json");
});

function extensionIdFromManifestKey(key) {
  const digest = createHash("sha256").update(Buffer.from(key, "base64")).digest();
  return Array.from(digest.subarray(0, 16), (byte) => {
    const alphabet = "abcdefghijklmnop";
    return alphabet[byte >> 4] + alphabet[byte & 15];
  }).join("");
}

test("Phase 2 extension source has no direct Sheets API, write API, or logging calls", () => {
  const sourceRoot = new URL("../src/", import.meta.url);
  const sourceText = readdirSync(sourceRoot, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".js"))
    .map((entry) => readFileSync(new URL(entry.name, sourceRoot), "utf8"))
    .join("\n");

  assert.doesNotMatch(sourceText, /sheets\.googleapis\.com/);
  assert.doesNotMatch(sourceText, /spreadsheets\.readonly/);
  assert.doesNotMatch(
    sourceText,
    /batchUpdate|values\.update|values\.batchUpdate|spreadsheets\.batchUpdate/,
  );
  assert.doesNotMatch(sourceText, /console\.|log\(/);
});

test("fetchBrokerInspection posts to the broker and unwraps sanitized payloads", async () => {
  let requestedUrl = "";
  let requestedMethod = "";
  let requestedBrokerAuthorization = "";
  let requestedBody = {};
  const snapshot = await fetchBrokerInspection({
    brokerBaseUrl: "https://broker.example.run.app",
    request: { request_id: "request-1", spreadsheet_id: "spreadsheet-1" },
    identityEvidenceToken: "identity-token-1",
    fetchFn: async (url, options) => {
      requestedUrl = url;
      requestedMethod = options.method;
      requestedBrokerAuthorization = options.headers["X-Broker-Authorization"];
      requestedBody = JSON.parse(options.body);
      return {
        ok: true,
        json: async () => ({
          ok: true,
          payload: fixtureSnapshot,
        }),
      };
    },
  });

  assert.equal(requestedUrl, "https://broker.example.run.app/v1/inspect");
  assert.equal(requestedMethod, "POST");
  assert.match(requestedBrokerAuthorization, /^Bearer identity-token-1$/);
  assert.equal(requestedBody.request_id, "request-1");
  assert.equal(snapshot.spreadsheet_id, "spreadsheet-1");
  assert.equal(snapshot.title, "Ops Sheet");
  assert.equal(typeof snapshot.telemetry.client_elapsed_ms, "number");
});

test("fetchBrokerInspection surfaces missing identity, HTTP, and broker denial errors", async () => {
  await assert.rejects(
    () =>
      fetchBrokerInspection({
        request: { request_id: "request-1" },
      }),
    /identityEvidenceToken is required/,
  );
  await assert.rejects(
    () =>
      fetchBrokerInspection({
        request: { request_id: "request-1" },
        identityEvidenceToken: "identity-token-1",
        fetchFn: async () => ({
          ok: false,
          status: 403,
          statusText: "Forbidden",
          text: async () => "policy denied",
        }),
      }),
    /Broker inspection request failed \(403\): policy denied/,
  );
  await assert.rejects(
    () =>
      fetchBrokerInspection({
        request: { request_id: "request-1" },
        identityEvidenceToken: "identity-token-1",
        fetchFn: async () => ({
          ok: true,
          json: async () => ({
            ok: false,
            error: { code: "policy_denied", message: "spreadsheet_not_allowed" },
          }),
        }),
      }),
    /spreadsheet_not_allowed/,
  );
});

test("inspection metadata fixture contains required Phase 1 fields", () => {
  assert.equal(fixtureSnapshot.schema_version, "1.0");
  assert.equal(fixtureSnapshot.spreadsheet_id, "spreadsheet-1");
  assert.equal(fixtureSnapshot.title, "Ops Sheet");
  assert.equal(fixtureSnapshot.locale, "en_US");
  assert.equal(fixtureSnapshot.time_zone, "Asia/Seoul");
  assert.match(fixtureSnapshot.captured_at, /^\d{4}-\d{2}-\d{2}T/);
  assert.equal(fixtureSnapshot.tabs[0].sheet_id, 10);
  assert.equal(fixtureSnapshot.tabs[0].row_count, 100);
  assert.equal(fixtureSnapshot.tabs[0].column_count, 20);
});
