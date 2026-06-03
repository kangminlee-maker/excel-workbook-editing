# AGENTS.md

## Purpose

This repo contains the `excel-workbook-editing` skill, spreadsheet helpers, schemas, design docs, review artifacts, and ADRs. Keep these artifacts aligned with current behavior.

## Repo Authority

- `SKILL.md`: main skill entrypoint.
- `references/`: spreadsheet CRUD and validation principles.
- `scripts/`: inspection, sampling, validation, and artifact helpers.
- `schemas/`: machine-checkable artifact contracts.
- `docs/`: active designs, work plans, and ADRs.
- `review-packages/`: generated evidence for human review.
- `IMPLEMENTATION_MAP.html`: update when architecture or roadmap changes meaningfully.

## Excel And Spreadsheet CRUD

Before changing how Excel or spreadsheet files are read, created, updated, deleted, reconciled, or validated, consult the relevant files in `references/`.

Primary references:

- `references/spreadsheet-principles.md`
- `references/excel-workbook-principles.md`
- `references/spreadsheet-review-package.md`

For connected Google Sheets work, also consult:

- `references/connected-google-sheets-principles.md`

Default Excel file handling principles:

- Treat the workbook as the source artifact.
- Use fast ZIP/XML manifesting before expensive full workbook loading on large files.
- Use `openpyxl` `read_only=True` or targeted XML parsing for large read paths when values and formula text are enough.
- Use deterministic workbook tooling such as `openpyxl` or generator scripts for structural writes.
- Validate formula-dependent results with the real Microsoft Excel engine.
- Preserve identity, formulas, names, formatting, layout, and reviewability unless explicitly changing them.
- Do not delete, replace, flatten, or round-trip a user workbook unless explicitly requested or working on an agreed safe copy.

## Document-Shaped Excel Understanding

For document-shaped Excel parsing and ontology work, use `docs/document-shaped-excel-understanding-design.md` as the current design baseline.

For the current top-level architecture, use `docs/evidence-backed-spreadsheet-claim-ledger-design.md` and ADR `docs/adr/0001-evidence-backed-claim-ledger.md`. The stable model is now a bitemporal evidence/claim ledger with adjudicated claim statuses and projections, not a linear pipeline that directly produces a final validated ontology graph.

Treat that design as a living baseline. Update it in the same change when parser terms, block boundaries, ontology roles, validation gates, pipeline order, or review conclusions change the intended behavior.

Use `docs/document-shaped-excel-understanding-tasklist.md` as the active execution tasklist. Update it in the same change when stages are added, removed, reordered, renamed, split, merged, or materially re-scoped.

Current implementation-history pipeline direction:

```text
Fast ZIP/XML Manifest
-> Workbook View-State Preflight
-> Read-Only Targeted Row Sampling
-> Pivot / Formula / External Reference Profiling + Formula/Dataflow Graph
-> Block / Region / Boundary Candidate Generation
-> Table I/O Pipeline Extraction
-> Cross-Validation Target Planning
-> Excel Render Capture
-> Capture Quality Checks
-> Recapture Candidate Experiment
-> View-State / Capture Reconciliation
-> Coordinate Normalization
-> Visual Feature Detection
-> Visual / Data / Formula Gate Execution
-> Boundary / Pipeline Role Acceptance
-> Document Item Grouping / Hierarchy Checkpoint
-> Evidence Package Assembly
-> Document Ontology Mapping
-> Action Contract Layer
-> Domain Knowledge Source Model
-> LLM Proposal Generation
-> Deterministic Gate Validation
-> Validated Document Graph
-> Data View Projection
-> Local Semantic Ontology Candidates
-> Shared Ontology Alignment / Human Review
-> Process Redesign Review
-> Blocker Resolution Update
```

Current sample implementation has completed through:

```text
Manifest/Sampling
-> View-state preflight
-> Formula/Style/Block/Region candidates
-> Boundary gate ranking
-> Table I/O pipeline candidates
-> Mermaid pipeline graph review
-> Cross-validation target planning
-> First-batch Excel render capture
-> Capture quality checks
-> Recapture candidate experiment
-> View-state / capture reconciliation
-> Coordinate normalization
-> Visual feature detection
-> Visual / data / formula gate execution
-> Boundary acceptance / rejection
-> Pipeline role validation
-> Workbook evidence package assembly
-> Document ontology mapping
-> Action contract layer
-> Domain knowledge source model
-> LLM proposal generation
-> Deterministic validation of LLM proposals
-> Validated document graph assembly
-> Data view projection
-> Local semantic ontology candidate generation
-> Shared ontology alignment / human review
-> Process redesign review
-> Blocker resolution update
-> Formula-result authority checkpoint
-> Document item grouping / hierarchy checkpoint
-> Version breakpoint detection
-> Semantic / gate iteration
-> Carry-forward review packet
-> Onto MCP reconstruct attempt
-> Manual onto seed draft validation
-> Onto direct-call auth recovery
-> Onto seed prompt / timeout mitigation
-> Official onto seed review / maturation frontier
-> Evidence-backed claim ledger architecture documentation
```

Next intended stage:

```text
Decompose the claim ledger architecture into first implementation contracts: evidence records, claim records, gate results, semantic signatures, projections, retrieval context packs, and review/action state transitions
```

Important boundaries:

- LLM output is a proposal, not final truth.
- LLM output must enter as candidate claims with provenance, prompt hash when available, and gate requirements.
- Deterministic gates classify claim status; they do not create truth.
- Use `Adjudicated Claim Graph`, not `Validated Claim Graph`, when preserving accepted, review-required, blocked, contradicted, and conflicting claims.
- Document, dataflow, ontology, review queue, and retrieval outputs are projections over evidence and adjudicated claims.
- Identity/anchoring, provenance/lineage, version/time, and authority labels are cross-cutting axes across every document-understanding layer.
- Formula text is not formula-result authority.
- Semantic ontology generation must separate reusable general domain knowledge from local domain knowledge that is valid only inside a declared organization/project/team/tenant/workbook-family boundary.
- Do not assume a general-domain pack for a workbook or connected Sheet. Use a general-domain source only when it is selected for that document; otherwise keep semantic candidates local/process-scoped until an appropriate domain source is provided.
- Document-shaped parsing work must maintain a process ledger that records hypotheses, actions, artifacts, observations, process decisions, and next adjustments.
- Formula/dataflow work must project table-level input/output pipelines, not only raw formula references.
- Deterministic gates validate ranges, coordinates, formulas, ontology constraints, and conflicts.
- Render capture and Excel recalculation are separate authorities.
- Preserve the original visible workbook state. Hidden/revealed or clear-filter variants are diagnostic projections, not replacements for source-visible authority.
- Hidden or filtered workbook view-state explains current visible render behavior but does not remove hidden structural data from extraction authority.
- Visual feature detection produces image evidence only; it does not assign document semantics by itself.
- Gate execution produces evidence statuses only; accepted gates are not final document graph claims.
- Boundary acceptance produces graph-boundary candidates only; style-only and view-state-risk boundaries remain review items.
- Document item grouping is the structural authority checkpoint before semantic storage. It must group text, table, chart/image/object, formula, and explanation surfaces only when spatial, visual, formula/dataflow, style, view-state, and textual evidence support the grouping.
- Physical adjacency alone must not merge document items; adjacent ranges can remain separate items when headers, formulas, sources, styles, object anchors, or explanatory text conflict.
- Pipeline role validation accepts role labels only; missing visual capture can remain a review annotation when formula or pivot authority supports the role.
- Workbook evidence package assembly bundles prior deterministic artifacts; it must not reopen or mutate the source workbook for this sample path.
- Document ontology mapping applies the document-structure ontology deterministically; it must not generate semantic ontology concepts.
- Action contract layer converts ontology statuses into next actions; it must not accept new structural or semantic claims by itself.
- Domain source model separates general-domain evidence from boundary-scoped local-domain evidence before semantic ontology proposals.
- LLM proposal generation materializes evidence-bounded proposals only; it must not accept semantic concepts, hierarchy edges, aliases, or relations.
- LLM proposal validation assigns deterministic proposal outcomes only; it must not assemble the final document graph by itself.
- Semantic proposal and deterministic gate execution must alternate until concepts are accepted, split into scoped variants, or left review-required. Same visible labels are not enough to merge semantic concepts.
- For repeated metrics such as 결제액, store a shared parent only when useful, then keep scoped variants separate unless gates prove matching basis, period, filters, aggregation, source lineage, transformation role, and formula/result authority.
- Validated document graph assembly promotes only accepted deterministic/proposal-validation results; review-required and quarantined items remain carry-forward queues.
- Data view projection is a read-model projection over the accepted graph; it must not recalculate formulas, resolve carry-forward queues, or promote review-required semantic claims.
- Local semantic ontology candidates are boundary-scoped candidates only; shared ontology promotion remains blocked until local boundary, local sources, repeated evidence, conflict checks, and human review are satisfied.
- Shared ontology alignment review is review-only until local boundary, local sources, repeated workbook-family evidence, shared ontology target checks, formula-result authority, and human approval are available; it must emit 0 shared ontology updates while those blockers remain.
- K-GAAP-labeled workbook outputs and K-IFRS-relevant revenue recognition surfaces must remain separate or explicitly mapped until a human reviewer defines the official output basis and aggregation rule.
- Process redesign recommendations are not parser truth; apply them to the next workbook iteration and validate with generated artifacts, HTML review, schemas, tests, and ledger entries.
- Blocker resolution updates are control artifacts for reruns; they do not mutate prior semantic artifacts or create parser truth by themselves.
- For the current connected Google Sheets sample, direct FC_DATA source authority is resolved for `1CPfJoD6VlChrev00xmagW6qJ2x7eNoJnlQeKe9AMYrs`, while nested `IMPORTRANGE` lineage, formula-result authority, and version breakpoint validation remain follow-up work.
- Google Sheets formula-result authority is accepted only at probed range level through broker-backed `grid_formula_v1` effective values. In the current sample, the 24_0102/24_0108/24_0115 calculation ranges are accepted, while current/source FC_DATA and FC_DATA-dependent report pipelines remain blocked by effective errors or missing output probes.
- The current connected Google Sheets sample is cash-basis payment/status reporting, not K-IFRS or K-GAAP revenue reporting.
- For the current connected Google Sheets sample, `/Users/kangmin/.onto/domains/accounting-kr` is not an applicable domain source. Existing artifacts that reference it are stale and must be regenerated before semantic acceptance.
- For the current connected Google Sheets sample, `onto-mcp` reconstruct now has an official direct reconstruct seed from `.onto/reconstruct/20260602-sheets-local-actionable-ontology-seed-min/ontology-seed.yaml`. It validates with 0 ontology-seed violations and all runtime validation artifacts are valid. Treat it as a local seed with `ontology_handoff.readiness_claim=limited` and `handoff_readiness_projection=not_ready`; it is not action-ready, writeback-ready, shared, K-IFRS/K-GAAP, or `accounting-kr`-aligned ontology. Keep shared ontology updates at 0.
- `onto-seed-maturation-review.json` is the current control artifact for the official seed review. It accepts the seed only as local seed authority and keeps instance binding, relation binding, metric equivalence, review governance, runtime proof, and writeback contract as open maturation lanes.
- Dense HTML review sections must pass a layout/overflow check before being treated as reviewer-ready.
- Every accepted node, relation, data view, and semantic candidate must point back to workbook evidence.

## Verification Discipline

After meaningful changes:

- Run the narrowest useful tests.
- Validate JSON artifacts against their schemas when schemas exist.
- Syntax-check changed scripts when practical.
- Use the real Excel engine for formula-dependent workbook results, or report the gap.

Common local checks:

```bash
python3 -m unittest discover -s tests
python3 -m unittest discover -s native-host/test
python3 -m py_compile scripts/*.py
```

Use narrower commands when only one path changed.

## ADRs

Store architecture decision records in `docs/adr/`.

ADR rules:

- One file per decision.
- Name files like `0001-fast-workbook-manifest.md`.
- Record context, decision, consequences, alternatives, and verification.
- If a decision changes, add a new ADR or mark the old one superseded.

## Documentation Hygiene

- Active docs should describe current behavior and contracts.
- Keep design docs aligned with evolving implementation and review feedback.
- Historical rationale and rejected alternatives belong in ADRs or isolated docs.
- Generated review artifacts belong in `review-packages/`.
