# ADR 0002: Extensible Data-Processing Spreadsheet Analysis Package

## Status

Accepted

## Context

Recent connected Google Sheets tests showed that the current approach is useful
for data-processing-centered spreadsheets: sheets with raw source tabs,
formula-backed processing regions, result projection tabs, metric labels, and
business questions such as payment decline, ROAS trend, and ad-spend
attribution candidates.

The repository already has Excel and spreadsheet editing principles. Those
principles must remain authoritative for workbook identity, formulas,
formatting, layout, CRUD, reconciliation, and validation. The new analysis path
should be added on top of that base, not replace it.

The approach should also apply to Excel workbooks, not only connected Google
Sheets. Approved external access surfaces are the connected-Sheets access
authority, and this repository consumes credential-free spreadsheet
evidence/results. The product boundary is the evidence-backed analysis contract
for local processing, validation artifacts, and review packages.

The tests also showed four durable needs:

- package the data-processing analysis approach;
- inject domain knowledge through configurable domain packs;
- structure answers as HTML review packages with SVG visualizations and
  sortable tables;
- support local operation from Excel workbooks, credential-free spreadsheet
  evidence/results, and sanitized review packages.
- keep boundaries extensible because the repository will continue adding
  document-shaped parsing, Excel analysis, ontology, refactoring, automation,
  and writeback capabilities.

## Decision

Create an extensible data-processing spreadsheet analysis package direction,
currently using the working name `spreadsheet-dataflow-inspector`.

The package will be read-only for the first connected-Sheets workflow. It will
use approved inputs such as local Excel workbook evidence packages,
credential-free spreadsheet evidence/results, existing sanitized review
packages, local analysis scripts, selected domain packs, deterministic gates,
and self-contained HTML answer packages.

Domain knowledge will be loaded from explicit domain packs, not hardcoded into
the parser or automatically assumed from the workbook.

Question answers will default to structured review packages:

- direct answer summary;
- source/projection/annotation split;
- table map;
- SVG table I/O or query flow;
- sortable result tables;
- formula/source chains;
- gate results;
- targeted review questions.

The intended operation model is:

```text
Excel workbook files or credential-free spreadsheet evidence/results
  -> local analysis engine
  -> review packages
```

The package will operate locally through a global config and review-package
directory while preserving the applicable authority model: Excel workbook
principles for local `.xlsx` files, and approved external access surfaces for
connected Google Sheets.

## Consequences

Benefits:

- The useful tested path can ship without waiting for every broader parser
  capability to mature.
- Business-question answering becomes reproducible and reviewable.
- Domain customization becomes explicit and versioned.
- HTML answers become a standard artifact instead of ad hoc reports.
- Excel and Google Sheets can share analysis contracts where their evidence
  models align.

Costs and risks:

- The package must avoid accidentally freezing repository scope around the first
  tested workflow.
- Domain pack contracts need schemas and review rules.
- Credential-free evidence/result contracts and sanitized package handoff need
  hardening.
- Causal claims remain candidates until gates and domain evidence support them.

Required boundaries:

- The first connected-Sheets workflow must not mutate live spreadsheets.
- Future writeback/refactoring/edit workflows must be added only through
  explicit design and the existing Excel/spreadsheet CRUD references.
- It must use approved external access surfaces instead of repo-local
  credential handling, direct API, export, or import shortcuts.
- It must not auto-load a domain pack without selection.
- It must not treat local-domain aliases as shared ontology truth.
- It must not weaken existing Excel workbook preservation, recalculation, and
  validation principles.

## Alternatives Considered

1. Freeze the package as a dataflow-only product boundary.
   - Rejected because the repository is expected to keep expanding. The package
     should start with dataflow-heavy workflows but remain extensible.

2. Keep everything inside the full document-shaped parser.
   - Rejected as the only organizing model because the data-processing workflow
     needs a shippable package shape now, but it should still interoperate with
     the broader parser and claim ledger.

3. Build only one-off scripts per question.
   - Rejected because repeated tests showed the same pattern: bounded evidence,
     domain rules, gates, JSON artifacts, HTML answer, ledger.

4. Hardcode domain logic into scripts.
   - Rejected because domain knowledge differs by organization, project,
     workbook family, and metric basis.

5. Output JSON only.
   - Rejected because reviewer feedback worked best through HTML, SVG, and
     tables.

## Verification

Initial evidence:

- MLL Dashboard review package generated a Korean HTML answer with SVG table
  I/O flow and structured result tables.
- Payment decline driver analysis was reproduced from stored sanitized
  connected-Sheets artifacts generated through the approved authority path at
  the time of the run.
- Category result projections reconciled against RAW product-group sums for 24
  sampled category/window gates.
- Domain-dependent interpretation remained explicit: 결제액, not accounting
  revenue; no automatic accounting-domain pack.
- Existing Excel/spreadsheet CRUD references remain linked from the design and
  are not superseded.

Future verification:

- Validate domain pack schemas.
- Validate query artifact schemas.
- Run the same analysis contract against a local Excel workbook evidence
  package.
- Run stored-artifact analysis, doctor checks, and HTML generation in a clean
  local processing environment.
- Confirm credential-free spreadsheet evidence/result -> sanitized package ->
  local analysis package end to end.
- Run HTML layout and sortable-table checks before reviewer handoff.
