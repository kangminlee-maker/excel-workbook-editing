import { parseSpreadsheetId } from "./sheets_api.js";

const inspectButton = document.querySelector("#inspect");
const recordPackageButton = document.querySelector("#record-package");
const statusText = document.querySelector("#status");
const sheetIdText = document.querySelector("#sheet-id");
const resultSection = document.querySelector("#result");
const packageResultSection = document.querySelector("#package-result");

let activeSpreadsheetId = null;
let latestSnapshot = null;

init();

async function init() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    activeSpreadsheetId = parseSpreadsheetId(tab?.url);
    if (!activeSpreadsheetId) {
      setStatus("Open a Google Sheet tab.", true);
      return;
    }
    sheetIdText.textContent = activeSpreadsheetId;
    inspectButton.disabled = false;
    setStatus("Ready.");
  } catch (error) {
    setStatus(errorMessage(error), true);
  }
}

inspectButton.addEventListener("click", async () => {
  inspectButton.disabled = true;
  recordPackageButton.disabled = true;
  resultSection.hidden = true;
  packageResultSection.hidden = true;
  latestSnapshot = null;
  setStatus("Inspecting...");
  try {
    const response = await chrome.runtime.sendMessage({
      type: "inspectActiveSheet",
      spreadsheetId: activeSpreadsheetId,
    });
    if (!response?.ok) {
      throw new Error(response?.error?.message ?? "Inspection failed");
    }
    latestSnapshot = response.payload;
    renderSnapshot(latestSnapshot);
    recordPackageButton.disabled = false;
    setStatus("Inspect complete.");
  } catch (error) {
    setStatus(errorMessage(error), true);
  } finally {
    inspectButton.disabled = !activeSpreadsheetId;
  }
});

recordPackageButton.addEventListener("click", async () => {
  recordPackageButton.disabled = true;
  packageResultSection.hidden = true;
  setStatus("Recording package...");
  try {
    const response = await chrome.runtime.sendMessage({
      type: "recordInspectionSnapshot",
      requestId: latestSnapshot?.request_id,
      snapshot: latestSnapshot,
    });
    if (!response?.ok) {
      throw new Error(response?.error?.message ?? "Package recording failed");
    }
    renderPackageResult(response.payload);
    setStatus("Package recorded.");
  } catch (error) {
    setStatus(errorMessage(error), true);
  } finally {
    recordPackageButton.disabled = !latestSnapshot;
  }
});

function renderSnapshot(snapshot) {
  const tabs = snapshot.tabs ?? [];
  resultSection.innerHTML = `
    <div class="grid">
      ${metric("Title", snapshot.title)}
      ${metric("Tabs", String(tabs.length))}
      ${metric("Locale", snapshot.locale)}
      ${metric("Time zone", snapshot.time_zone)}
    </div>
    <ul class="tabs">
      ${tabs.map(renderTab).join("")}
    </ul>
  `;
  resultSection.hidden = false;
}

function renderPackageResult(result) {
  packageResultSection.innerHTML = `
    <div class="grid">
      ${metric("Package", result.package_dir)}
      ${metric("Manifest", result.artifact_path)}
    </div>
  `;
  packageResultSection.hidden = false;
}

function renderTab(tab) {
  const hidden = tab.hidden ? "hidden" : "visible";
  return `
    <li>
      <span>${escapeHtml(tab.title)} (${tab.sheet_id})</span>
      <span>${tab.row_count}x${tab.column_count}, ${hidden}</span>
    </li>
  `;
}

function metric(label, value) {
  return `
    <div class="metric">
      <strong>${escapeHtml(label)}</strong>
      <span>${escapeHtml(value ?? "")}</span>
    </div>
  `;
}

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.classList.toggle("error", isError);
}

function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
