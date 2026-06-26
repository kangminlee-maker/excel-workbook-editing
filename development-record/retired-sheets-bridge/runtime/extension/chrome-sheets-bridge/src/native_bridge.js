import { NATIVE_HOST_NAME, PROTOCOL_VERSION } from "./constants.js";

export function buildInspectSnapshotMessage({
  snapshot,
  requestId = crypto.randomUUID(),
}) {
  if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)) {
    throw new Error("snapshot is required");
  }
  return {
    protocol_version: PROTOCOL_VERSION,
    request_id: requestId,
    type: "inspect.snapshot",
    payload: {
      snapshot,
    },
  };
}

export function recordInspectionSnapshot({
  snapshot,
  requestId,
  sendNativeMessageFn = chrome.runtime.sendNativeMessage,
}) {
  const message = buildInspectSnapshotMessage({ snapshot, requestId });
  return new Promise((resolve, reject) => {
    sendNativeMessageFn(NATIVE_HOST_NAME, message, (response) => {
      const lastError = chrome.runtime.lastError;
      if (lastError) {
        reject(new Error(lastError.message));
        return;
      }
      if (!response) {
        reject(new Error("Native host returned no response"));
        return;
      }
      if (response.ok !== true) {
        reject(new Error(response.error?.message ?? "Native host failed"));
        return;
      }
      if (response.type !== "review.result") {
        reject(new Error(`Unexpected native host response: ${response.type}`));
        return;
      }
      resolve(response.payload);
    });
  });
}
