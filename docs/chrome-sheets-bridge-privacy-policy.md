# Chrome Sheets Bridge Privacy Policy

Last updated: 2026-06-01

Chrome Sheets Bridge is a Day1 internal Chrome extension for broker-backed Google Sheets inspection workflows. It helps an approved user inspect metadata for the Google Sheets spreadsheet currently open in Chrome through a controlled Cloud Run broker.

## Data handled

The extension may handle the following data only when the user opens the extension on a Google Sheets tab and starts an inspection:

- Google account identity information: email address and short-lived Google identity token used to authenticate the user to the broker.
- Google Sheets document metadata: spreadsheet ID, spreadsheet title, locale, time zone, sheet names, sheet IDs, row counts, column counts, hidden state, request ID, timestamps, and inspection status.
- Active tab context: the URL of the current Google Sheets tab, used only to extract the spreadsheet ID.
- Basic diagnostic timing: client-side elapsed time for the broker inspection request.

The extension does not collect health information, financial or payment information, personal communications, location data, browsing history, or general user activity. The current inspection flow does not read or transmit spreadsheet cell values.

## How data is used

Data is used only to:

- verify the signed-in user;
- confirm that the user and spreadsheet are allowed by broker policy;
- perform the requested spreadsheet metadata inspection;
- display the sanitized inspection result to the user;
- maintain security and auditability of broker requests.

The extension does not use user data for advertising, credit eligibility, profiling, resale, or unrelated analytics.

## Data sharing

The extension sends bounded inspection requests over HTTPS to the Day1 Cloud Run broker configured for this extension. The broker verifies the user's identity and policy before calling Google Sheets APIs. The broker may use Google Cloud and Google Workspace infrastructure to process authorized requests.

User data is not sold. User data is not transferred to third parties except as required to provide the extension's single purpose, comply with security requirements, or satisfy legal obligations.

The use of information received from Google APIs will adhere to the Chrome Web Store User Data Policy, including the Limited Use requirements.

## Storage and retention

The extension does not persist user data in Chrome local storage or Chrome sync storage.

Broker-side operational logs may include request ID, user email, spreadsheet ID, timestamps, request status, and error status for security, troubleshooting, and audit purposes. These logs are managed under Day1's internal operational controls.

## Security

Requests to the broker use HTTPS. Google OAuth tokens, service account keys, and raw credentials are not exposed to local tools or LLM agents by the extension.

## Contact

For questions about this extension's privacy handling, contact the Chrome Web Store publisher account or the Day1 Workspace administrator responsible for Chrome Sheets Bridge.
