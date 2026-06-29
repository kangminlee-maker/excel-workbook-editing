# AGENTS.md

## Purpose

This repo contains the `spreadsheet-processing` skill, spreadsheet helpers,
schemas, active runtime designs, review artifacts, and ADRs. Keep runtime
artifacts aligned with current behavior.

## Repo Authority

- `SKILL.md`: main skill entrypoint.
- `references/`: spreadsheet CRUD, workbook preservation, connected Sheets, and
  review-package principles.
- `docs/`: active processing designs, work plans, runbooks, and ADRs.
- `schemas/`: machine-checkable artifact contracts.
- `projects/`: per-spreadsheet or workbook-family continuity workspaces.
- `review-packages/`: generated evidence for human review.
- `development-record/`: tracked placeholder for record handoff.
- `IMPLEMENTATION_MAP.html`: current architecture, roadmap, decisions, and
  risks.
- `archive/`: local ignored product development records, pilot evidence,
  decision trail, and record diagrams.

## Product Direction

The current connected-spreadsheet product path is processing-first.

- Approved external spreadsheet access surfaces own Google Drive and Google
  Sheets access, authentication, policy, write gates, and Google API calls.
- This repository consumes local Excel files and credential-free spreadsheet
  evidence/results.
- Spreadsheet writes use approved external access results plus this
  repository's processing plans, validation artifacts, and review packages.
- Google Sheets edits preserve `spreadsheetId`, tab `sheetId`, formulas,
  protections, validations, Apps Script bindings, and external dependencies.
- Excel workbooks remain first-class artifacts and use real Microsoft Excel for
  formula-result authority when values matter.

## Excel And Spreadsheet CRUD

Before changing how Excel files or spreadsheets are read, created, updated,
reconciled, or validated, consult the active references:

- `references/spreadsheet-principles.md`
- `references/excel-workbook-principles.md`
- `references/spreadsheet-review-package.md`
- `references/connected-google-sheets-principles.md`

Default handling:

- Treat the workbook or spreadsheet as the source artifact.
- Use fast ZIP/XML manifesting before expensive full workbook loading on large
  Excel files.
- Use `openpyxl` `read_only=True` or targeted XML parsing for large read paths
  when values and formula text are enough.
- Use deterministic workbook tooling such as `openpyxl` or generator scripts for
  structural writes.
- Validate formula-dependent Excel results with the real Microsoft Excel engine.
- Preserve identity, formulas, names, formatting, layout, reviewability, and
  connected behavior.
- Replacement, flattening, export/import, and source-artifact removal require an
  explicit user request or an agreed safe-copy workflow.

## Project Workspaces

Before continuing analysis on a workbook or connected Sheet, locate or create a
project folder under `projects/`.

- Google Sheets projects use `spreadsheetId + gid` as the canonical identity.
- Excel projects use workbook-family folders and exact file revision tracking.
- Excel revision identity uses exact SHA-256.
- Excel workbook-family candidates use normalized workbook manifests and
  formula-structure fingerprints.
- Similar Excel fingerprints with unclear local boundaries receive
  review-required status.
- Project folders hold continuity state, local domain notes, linked artifact
  roots, and unresolved questions.
- Reviewer-facing packages are published under `review-packages/`.

## Active Runtime Designs

Use these active design baselines:

- `docs/data-processing-spreadsheet-package-design.md`
- `docs/document-shaped-excel-understanding-design.md`
- `docs/evidence-backed-spreadsheet-claim-ledger-design.md`
- `docs/sheets-formula-dataflow-discovery-design.md`
- `docs/document-shaped-excel-understanding-tasklist.md`
- `docs/adr/0001-evidence-backed-claim-ledger.md`
- `docs/adr/0002-data-processing-spreadsheet-package.md`

The top-level model is a bitemporal evidence/claim ledger with adjudicated claim
statuses and projections.

Current next work:

- Decompose claim-ledger contracts for evidence records, claim records, gate
  results, semantic signatures, projections, retrieval context packs, and
  review/action state transitions.
- Define package contracts for the data-processing spreadsheet analysis path
  across Excel workbooks and connected Sheets evidence.
- Continue formula/dataflow discovery as read-only evidence work until a
  refactoring or writeback design is approved.

## MCP And MCPB Authoring

Before designing or changing MCP servers, MCP tool definitions, MCPB manifests,
Claude-compatible tool surfaces, or repository JSON schemas intended to be
projected into those surfaces, consult `docs/mcp-mcpb-authoring-guide.md`.

- Use canonical tool names in `namespace_verb` form matching
  `^[a-zA-Z0-9_-]{1,64}$`.
- Use underscore-separated names for tool names, user config keys, and tool
  input property names.
- Keep MCP tool `input_schema` values as direct top-level object schemas.
- Express multi-operation tools with an `operation` enum and server-side
  validation instead of top-level `oneOf`, `anyOf`, or `allOf`.
- Keep MCP-projectable repository schemas free of `oneOf`, `anyOf`, and
  `allOf`; use explicit fields plus deterministic validation code for variant
  behavior.

## Evidence And Claim Boundaries

- LLM output enters as candidate claims with provenance, prompt hash when
  available, and gate requirements.
- Deterministic gates classify claim status.
- The current graph concept is `Adjudicated Claim Graph`.
- Document, dataflow, ontology, review queue, and retrieval outputs are
  projections over evidence and adjudicated claims.
- Identity, anchoring, provenance, lineage, version, time, and authority labels
  are cross-cutting axes across every document-understanding layer.
- Formula text is evidence. Formula-result authority comes from live Google
  Sheets effective values or real Excel recalculation.
- Formula/dataflow work projects table-level input/output pipelines.
- General-domain knowledge is selected per document boundary.
- Local semantic candidates stay boundary-scoped until local sources, repeated
  evidence, conflict checks, and human review support promotion.
- Same visible labels require basis, period, filter, aggregation, source
  lineage, transformation role, and formula/result authority gates before merge.

## Connected Sheets Understanding Protocol

On first access to a connected Sheet or workbook:

1. Create or reuse the project folder.
2. Separate raw/source truth, result/final projection, and annotation text.
3. Discover tables by shared formula structure, shared label structure, and
   coherent ranges.
4. Map table I/O with user-friendly table names and spreadsheet ranges.
5. Classify labels as raw input, processed/intermediate output, final output,
   annotation, or review-required.
6. Show processed labels' formula/source chains where evidence allows.
7. Ask targeted questions for unclear meanings.
8. Publish an executive summary, table map, I/O flow, label dictionary, formula
   chains, and unresolved questions in an HTML review package.

## Structural And Semantic Checkpoints

- Deterministic gates validate ranges, coordinates, formulas, ontology
  constraints, and conflicts.
- Render capture and Excel recalculation are separate authorities.
- Source-visible workbook state is preserved. Hidden, revealed, or clear-filter
  variants are diagnostic projections.
- Hidden or filtered workbook view-state explains visible render behavior while
  structural data remains extraction evidence.
- Visual feature detection produces image evidence.
- Gate execution produces evidence statuses.
- Boundary acceptance produces graph-boundary candidates.
- Document item grouping is the structural authority checkpoint before semantic
  storage.
- Adjacent ranges can remain separate items when headers, formulas, sources,
  styles, object anchors, or explanatory text conflict.
- Pipeline role validation accepts role labels when formula, pivot, or visual
  authority supports the role.
- Workbook evidence packages bundle deterministic artifacts.
- Document ontology mapping applies the document-structure ontology
  deterministically.
- Action contract layer converts ontology statuses into next actions.
- Domain source model separates general-domain evidence from boundary-scoped
  local-domain evidence before semantic proposals.
- LLM proposal generation materializes evidence-bounded proposals.
- LLM proposal validation assigns deterministic proposal outcomes.
- Semantic proposal and deterministic gate execution alternate until concepts
  reach accepted, split, or review-required status.
- Dense HTML review sections pass layout and overflow checks before
  reviewer-ready status.
- Accepted nodes, relations, data views, and semantic candidates point back to
  workbook evidence.

## Verification Discipline

After meaningful code, config, data, spreadsheet, ontology, or documentation
changes:

- Run the narrowest useful tests.
- Validate JSON artifacts against schemas when schemas exist.
- Syntax-check changed scripts when practical.
- Use the real Excel engine for formula-dependent workbook results, or report
  the validation gap.

Common local checks:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile scripts/*.py
```

Use narrower commands when only one path changed.

## ADRs

Store architecture decision records in `docs/adr/`.

ADR rules:

- One file per decision.
- Name files like `0001-fast-workbook-manifest.md`.
- Record context, decision, consequences, alternatives, and verification.
- When a decision changes, add a new ADR.

## Documentation Hygiene

- Active docs describe current behavior, contracts, authority, validation, and
  implementation intent.
- Runtime code, active docs, and `IMPLEMENTATION_MAP.html` stay aligned.
- Current review artifacts live under `review-packages/`.
- Development records live under local ignored `archive/`.
