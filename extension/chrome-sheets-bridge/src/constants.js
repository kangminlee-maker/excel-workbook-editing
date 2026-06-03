export const PROTOCOL_VERSION = "1.0";

export const NATIVE_HOST_NAME = "com.day1company.sheets_bridge";

export const ACTIVE_REQUEST_MESSAGE_TYPES = Object.freeze([
  "inspect.snapshot",
  "review.generate",
]);

export const PLANNED_REQUEST_MESSAGE_TYPES = Object.freeze([
  "plan.generate",
  "apply.record",
]);

export const ACTIVE_RESULT_MESSAGE_TYPES = Object.freeze([
  "review.result",
]);

export const PLANNED_RESULT_MESSAGE_TYPES = Object.freeze([
  "plan.result",
  "apply.result",
]);

export const REQUEST_MESSAGE_TYPES = ACTIVE_REQUEST_MESSAGE_TYPES;
export const RESULT_MESSAGE_TYPES = ACTIVE_RESULT_MESSAGE_TYPES;
export const TERMINAL_MESSAGE_TYPES = Object.freeze(["error"]);

export const ALLOWED_MESSAGE_TYPES = Object.freeze([
  ...ACTIVE_REQUEST_MESSAGE_TYPES,
  ...ACTIVE_RESULT_MESSAGE_TYPES,
  ...TERMINAL_MESSAGE_TYPES,
]);

export const DEFAULT_TIMEOUT_BUDGET = Object.freeze({
  read_seconds: 60,
  write_seconds: 60,
  poll_seconds: 120,
});

export const DEFAULT_BROKER_BASE_URL =
  "https://run-mcp-day1-development-sheets-bridge-broker-ty6iw5bb6a-du.a.run.app";

export const BROKER_IDENTITY_SCOPES = Object.freeze([
  "openid",
  "email",
  "profile",
]);
