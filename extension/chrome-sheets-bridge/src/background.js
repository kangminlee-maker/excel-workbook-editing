import { BROKER_IDENTITY_SCOPES } from "./constants.js";
import { recordInspectionSnapshot } from "./native_bridge.js";
import {
  buildBrokerInspectRequest,
  fetchBrokerInspection,
} from "./sheets_api.js";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "inspectActiveSheet") {
    inspectActiveSheet(message.spreadsheetId)
      .then((snapshot) => sendResponse({ ok: true, payload: snapshot }))
      .catch((error) =>
        sendResponse({
          ok: false,
          error: {
            code: "inspect_failed",
            message: error instanceof Error ? error.message : String(error),
          },
        }),
      );
    return true;
  }

  if (message?.type === "recordInspectionSnapshot") {
    recordInspectionSnapshot({
      snapshot: message.snapshot,
      requestId: message.requestId,
    })
      .then((result) => sendResponse({ ok: true, payload: result }))
      .catch((error) =>
        sendResponse({
          ok: false,
          error: {
            code: "review_package_failed",
            message: error instanceof Error ? error.message : String(error),
          },
        }),
      );
    return true;
  }

  return false;
});

async function inspectActiveSheet(spreadsheetId) {
  if (!spreadsheetId) {
    throw new Error("Active tab is not a Google Sheet");
  }
  const identity = await getBrokerIdentity();
  const request = buildBrokerInspectRequest({
    spreadsheetId,
    userEmail: identity.email,
  });
  return fetchBrokerInspection({
    request,
    identityEvidenceToken: identity.token,
  });
}

async function getBrokerIdentity() {
  const [token, profile] = await Promise.all([
    getBrokerAuthToken(),
    getProfileUserInfo(),
  ]);
  return {
    token,
    email: profile.email ?? "",
  };
}

function getBrokerAuthToken() {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken(
      {
        interactive: true,
        scopes: [...BROKER_IDENTITY_SCOPES],
      },
      (token) => {
        const lastError = chrome.runtime.lastError;
        if (lastError) {
          reject(new Error(lastError.message));
          return;
        }
        if (!token) {
          reject(new Error("No broker identity token returned"));
          return;
        }
        resolve(token);
      },
    );
  });
}

function getProfileUserInfo() {
  return new Promise((resolve) => {
    chrome.identity.getProfileUserInfo((profile) => {
      resolve(profile ?? {});
    });
  });
}
