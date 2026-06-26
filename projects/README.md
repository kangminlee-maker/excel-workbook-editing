# Projects

`projects/` is the continuity workspace for spreadsheet understanding and
analysis work.

Use one project folder for the same source spreadsheet surface or workbook
family. Generated review packages may still be published under
`review-packages/`, but ongoing evidence, analysis pointers, local domain rules,
questions, and project state should be organized here.

## Folder Shape

```text
projects/
  _registry.json
  google-sheets/
    <spreadsheetId>/
      gid-<sheetGid>/
        project.json
  excel/
    <workbook-family-id>/
      project.json
      instances/
        <exact-revision-id>/
          identity.json
```

## Google Sheets Identity

Google Sheets projects use the canonical pair:

```text
spreadsheetId + gid
```

The project folder should preserve the canonical URL and any linked artifact
roots. Keep project artifacts credential-free.

## Excel Workbook Identity

Excel files are often copied, renamed, or moved. Do not rely on path or filename
alone.

Use two layers:

| Layer | Purpose | Example |
| --- | --- | --- |
| Exact revision id | Identifies the exact file bytes. | `sha256:<file-bytes>` |
| Workbook family id | Groups likely copies or revisions of the same workbook design. | `wbfp:<normalized-manifest-fingerprint>` |

Recommended workbook-family fingerprint inputs:

- workbook part inventory from ZIP central directory;
- workbook sheet names, order, sheet ids, dimensions, and hidden states;
- defined names, table names, pivot definitions, chart/object anchors;
- merged ranges, validations, protections, and print/layout metadata;
- normalized formula signatures and formula-pattern counts;
- stable custom document property or hidden named project id when an approved
  generator intentionally provides one.

Matching policy:

- Exact raw-file SHA-256 match: same exact revision.
- Same family fingerprint: same workbook family candidate.
- High similarity but not identical fingerprint: review-required family match.
- Different local/organization boundary: keep separate until the user confirms
  the boundary should merge.
