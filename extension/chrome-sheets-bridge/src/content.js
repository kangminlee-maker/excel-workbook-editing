const SHEETS_URL_PATTERN =
  /^https:\/\/docs\.google\.com\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/;

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "sheetContext") {
    return false;
  }

  const spreadsheetId = parseSpreadsheetId(window.location.href);
  sendResponse({
    ok: Boolean(spreadsheetId),
    payload: {
      spreadsheet_id: spreadsheetId,
      url: window.location.href,
      title: document.title,
    },
  });
  return false;
});

function parseSpreadsheetId(url) {
  const match = SHEETS_URL_PATTERN.exec(url);
  return match ? match[1] : null;
}
