# Document-Shaped Excel Understanding Design

## 0. Living Design Rule

This document is the current design baseline, not a frozen specification.

Update it whenever workbook evidence, parser tuning, user review, deterministic gates, ontology boundaries, or implementation results change the intended behavior. In particular, keep this document aligned when a working term is narrowed, renamed, or replaced, such as treating `row_band` as an early seed and promoting the final concept to a two-dimensional cell region.

Generated artifacts and review viewers may show temporary implementation terms. This design document should preserve the intended model and explain how temporary terms map to stable concepts.

The current top-level architecture is now recorded in `docs/evidence-backed-spreadsheet-claim-ledger-design.md` and accepted by `docs/adr/0001-evidence-backed-claim-ledger.md`. The stage history in this document remains useful implementation evidence, but future design work should treat evidence, candidate claims, gate decisions, adjudicated claim status, projections, governed retrieval, and action contracts as the primary architecture.

## 1. Purpose

This design treats an Excel workbook as a visual document canvas, not only as a row and column data store.

The system must understand worksheets where structured tables, free-form text, images, charts, formulas, notes, and visually grouped sections coexist. It must recover both document structure and semantic meaning while keeping every conclusion traceable to the original workbook.

The final output is not a flat extraction result. It is a validated workbook understanding package that contains document structure, data projections, semantic ontology candidates, source evidence, validation results, and review items.

## 2. Scope

The design covers:

- Workbooks used as visual documents.
- Sheets that mix row/column tables with text blocks, images, charts, and notes.
- Hierarchies such as text blocks describing tables, tables explaining prior text, images with attached tables, and sections containing mixed child blocks.
- Formula-aware interpretation of summary, total, and derived values.
- Evidence-based ontology use and ontology generation.
- Deterministic validation of LLM-generated interpretation proposals.

The design does not assume that every workbook follows a normalized tabular structure.

## 3. Core Decisions

### 3.1 Document Structure Ontology Is Used

The document structure ontology is a stable lens for interpreting layout. It should be predefined and reused across domains.

Representative concepts:

- Workbook
- Sheet
- Section
- Title
- TextBlock
- Table
- PivotTable
- Header
- DataRegion
- KeyValueGroup
- ImageBlock
- ChartBlock
- Caption
- Note
- SummaryBlock
- SignatureBlock

Representative relations:

- contains
- part_of
- precedes
- follows
- describes
- explains
- caption_of
- table_of
- same_visual_group_as
- supports

This ontology constrains the document graph and prevents arbitrary structure names from being invented per workbook.

### 3.2 Semantic Ontology Is Generated

The semantic ontology is generated from source workbooks and promoted over time. Semantic generation requires domain knowledge, but domain knowledge must be separated into two layers.

General domain knowledge contains rules, concepts, and constraints that are reusable across organizations in the same broad domain. For accounting workbooks, examples include revenue, expense, receivable, payable, accrual, recognition period, fee, tax, settlement, journal timing, and generally applicable accounting principles. These concepts can constrain interpretation, but every workbook claim must still point back to workbook evidence.

Local domain knowledge contains terminology, policies, categories, operational exceptions, and internal aliases that are valid only inside a declared boundary. The boundary may be an organization, tenant, project, department, team, workflow, workbook family, partner program, or other governed context. Examples include terms that only one boundary uses for a product line, payment flow, instructor fee rule, internal revenue-recognition sheet, or business-specific adjustment. Local domain knowledge cannot be assumed to apply outside its declared boundary.

Lifecycle:

```text
Observed Term
-> Semantic Concept Candidate
-> General Domain Alignment Candidate
-> Local Domain Concept
-> Cross-Workbook Aligned Concept
-> Shared Ontology Concept
```

Local semantic concepts must not be promoted directly into the shared ontology. Promotion requires repeated source evidence, usually across original Excel pairs or workbook groups, and a clear decision about whether the promoted concept belongs to the general domain layer or remains scoped to a local domain.

Domain knowledge is evidence, not hidden model intuition. A semantic claim may be supported by a glossary, accounting policy, boundary-scoped policy document, reviewed workbook pair, historical ontology version, competency question, or human review note. The source and applicability boundary must be recorded.

General-domain evidence is document-specific. A parser must not attach an available domain pack merely because it exists locally. For the current connected Google Sheets sample, `/Users/kangmin/.onto/domains/accounting-kr` is not applicable: the document is a cash-basis payment/status operational report, not a K-IFRS/K-GAAP revenue-recognition workbook. Existing connected-Sheets artifacts that reference `accounting-kr` are stale and must be regenerated before semantic acceptance.

### 3.3 Original Excel Is the Source of Truth

All graph nodes, relationships, extracted values, semantic candidates, and validation decisions must point back to source evidence:

- workbook hash
- sheet name
- cell range
- object anchor
- rendered capture bbox
- formula reference
- visual feature evidence
- validation gate result

Derived outputs are projections over the evidence package, not replacements for the workbook.

### 3.4 LLMs Produce Proposals, Not Final Truth

The LLM may classify blocks, infer hierarchy, propose relationships, and generate semantic concept candidates.

The LLM output is accepted only after deterministic gates validate that the proposal is structurally possible, source-traceable, ontology-compatible, and consistent with workbook, visual, and formula evidence.

### 3.5 Evidence-Backed Claim Ledger Is The New Top-Level Model

The stable architecture is claim-centric and ledger-backed:

```text
CQ / Purpose Registry
-> Authority Policy & Source Boundary
-> Bitemporal Evidence Ledger
-> Authority Resolution
-> Derived Structural Layer
-> Candidate Claim Store
-> Validation Gates
-> Adjudicated Claim Graph
-> Concept Resolution Bridge
-> Ontology Governance Plane
-> Read Models / Projections
-> Governed Retrieval Context Builder
-> LLM / Product Workflow
```

Important changes from the earlier pipeline framing:

- Use `Adjudicated Claim Graph`, not `Validated Claim Graph`, because classified claims include accepted, review-required, blocked, contradicted, and conflicting statuses.
- Treat layout segmentation, document grouping, dataflow role, semantic meaning, ontology alignment, and actionability as claim classes.
- Treat deterministic gates as claim-status classifiers, not truth creators.
- Preserve blocked and contradicted claims for review, suppression, and process learning.
- Use ontology as both upstream constraint and downstream projection.
- Store semantic concepts with semantic signatures and scope governance, not bare labels.
- Serve LLMs through governed retrieval context packs with status, authority, provenance, and version pins.

## 4. High-Level Pipeline

The execution status for these stages is tracked in `docs/document-shaped-excel-understanding-tasklist.md`. Update the tasklist whenever the pipeline order, stage boundary, artifact set, or next step changes.

The stage list below records the current implemented pipeline history. The next architecture iteration should remap these stages into the claim-ledger model rather than adding more late-stage projections onto the old linear pipeline.

```text
0. Fast ZIP/XML Manifest
1. Workbook View-State Preflight
2. Read-Only Targeted Row Sampling
3. Pivot Cache / Formula / External Reference Profiling and Formula/Dataflow Graph Extraction
4. Initial Document Block Candidate Generation
5. 2D Cell Region Segmentation
6. Structural Style Profile
7. Adjacent Split / Merge Boundary Gate Ranking
8. Table I/O Pipeline Extraction
9. Pipeline Graph Review Visualization
10. Cross-Validation Target Planning
11. First-Batch Excel Render Capture
12. Capture Quality Checks
13. Recapture Candidate Experiment / Tiling
14. View-State / Capture Reconciliation
15. Coordinate Normalization
16. Visual Feature Detection
17. Visual/Data/Formula Gate Execution
18. Boundary Acceptance / Rejection
19. Pipeline Role Validation
20. Workbook Evidence Package Assembly
21. Document Ontology Mapping
22. Action Contract Layer
23. Domain Knowledge Source Modeling
24. LLM Proposal Generation
25. Deterministic Validation of LLM Proposals
26. Validated Document Graph Assembly
27. Data View Projection
28. Local Semantic Ontology Candidate Generation
29. Shared Ontology Alignment / Human Review
30. Process Redesign Review
```

The fast manifest stage reads workbook package metadata and selected worksheet XML signals before expensive workbook loading. It identifies oversized sheets, shared strings, drawing/image anchors, pivot caches, external links, calculation chains, and target sheets that need focused extraction. Large workbooks should not enter full structural extraction until this stage decides which sheets and regions are safe or useful to scan.

The view-state preflight stage runs early because hidden rows, hidden columns, filters, outline/collapse state, panes, and sheet view offsets determine what a human currently sees. The parser must inventory this state without changing it. Revealing hidden rows or clearing filters is allowed only as a later diagnostic projection, never as the default source view.

The read-only targeted row sampling stage uses a streaming workbook reader for values and formula text in selected sheets or row windows. It is especially useful for very large sheets where full object-model loading is too expensive. This stage is not a formula-result authority because formula cells expose formula text unless validated through the real Excel engine.

The document block candidate generation stage combines deterministic evidence such as drawing anchors, sampled rows, row-oriented region seeds, formulas, and coarse grid proximity. Its output is a candidate set for later validation and ontology mapping, not the final document graph. A row band is only an early seed. The final document block must be a two-dimensional cell region with both row and column boundaries, because side-by-side tables can share the same rows and vertically adjacent tables can share or touch the same columns.

Physical adjacency is not enough to merge blocks. Two ranges that touch each other can still be separate tables when their headers, formula signatures, pivot/cache sources, styles, merged-cell structure, external references, or surrounding explanatory text indicate different semantic units. Conversely, ranges separated by whitespace can still be merged when they share one source authority, one formula family, or one visual/document hierarchy.

Pivot tables are not plain tables. They must be detected from pivot table definitions and pivot cache settings. The displayed pivot range is a rendered aggregation/filter view, while the pivot cache source identifies the upstream range or table that provides data. A sampled row band that overlaps a pivot table location may be useful evidence, but it should be classified as pivot-rendered values rather than a raw table.

Formula pattern profiling is a pre-split step for oversized sheets. Before dividing a very large sheet into many candidate tables, the system profiles formula signatures using relative references. Repeated signatures can indicate one continuous formula-driven region, while a single summary formula band above dense values suggests a summary/header layer over a large raw table.

2D cell region segmentation projects row-oriented seeds into bounded cell regions. The first implementation splits a seed by blank column gaps and flags touching repeated header sequences as adjacent-but-separate candidates. This is still a deterministic candidate layer, not the final document graph. Later passes should add style boundaries, merged-cell boundaries, render-capture whitespace, and formula locality.

The adjacent-but-separate split gate prevents physical adjacency from becoming an automatic merge. It accepts split evidence such as blank columns, repeated touching headers, style discontinuities, different formula families, pivot/source changes, or surrounding text boundaries. The merge gate handles the inverse case: separated regions can still form one logical block when they share one source authority, formula family, pivot cache, or visual/document hierarchy.

Formula/dataflow graph extraction operates below and across document blocks. It captures cell/range references, cross-sheet formulas, external workbook references, pivot cache dependencies, `GETPIVOTDATA` references, repeated formula signatures, and recalculation evidence when available.

Table I/O pipeline extraction is the table-level projection over the formula/dataflow graph. It identifies which tables, pivot tables, summary blocks, and formula regions act as inputs, transformations, outputs, reports, or bridge/intermediate stages. This stage is required because visually separate blocks may be one calculation pipeline, while visually adjacent blocks may have unrelated dataflow.

Render capture / cross-validation target planning chooses which workbook regions should be captured first and which gates should evaluate them. The plan should prioritize unresolved formula inputs, pivot-cache reports, boundary-review candidates, repeated formula families, and image/table hierarchy candidates. This target plan is not visual evidence by itself; it is the deterministic work order for the next render capture pass.

## 5. Input Model: Workbook Evidence Package

The input model should be an evidence package, not a simple parsed workbook.

```text
WorkbookEvidencePackage
├─ source_workbook
├─ workbook_hash
├─ sheet_models
├─ cell_values
├─ formulas
├─ formula_graph
├─ formula_pattern_profiles
├─ cell_region_candidates
├─ cell_region_split_candidates
├─ pivot_tables
├─ pivot_caches
├─ styles
├─ merged_ranges
├─ object_anchors
├─ rendered_captures
├─ coordinate_maps
├─ visual_features
├─ general_domain_knowledge_refs
├─ local_domain_knowledge_refs
├─ extracted_text_index
├─ parser_observations
└─ validation_inputs
```

The package combines workbook data, formula information, visual rendering, layout coordinates, and parser observations. This allows later stages to cross-check claims instead of trusting a single extraction source.

Domain knowledge references are included as separate evidence inputs. General domain references provide broad constraints such as accounting principles, while local domain references provide boundary-scoped meanings and policies. The evidence package must not collapse these two layers into one undifferentiated "domain context".

## 6. Required Workbook Signals

The structural extractor should collect at least:

- cell values
- formulas
- cached formula values
- recalculated formula values when available
- number formats
- merged ranges
- borders
- fill colors
- font size and weight
- alignment
- wrapped text state
- row heights
- column widths
- hidden rows and columns
- freeze panes
- print areas
- sheet zoom or view metadata when available
- images
- shapes
- charts
- comments or notes
- hyperlinks

These signals are used together. For example, a visually bordered region with dense values and bold top row is stronger table evidence than values alone.

## 7. Render Capture Model

Visual information should be captured from a real rendering path whenever possible.

Preferred authority:

- Excel engine render capture.

Secondary evidence:

- Library-derived layout approximation.
- OCR over captured images when direct workbook text extraction is insufficient.
- Computer vision features such as bounding boxes, lines, color regions, and whitespace.

Render capture is necessary because workbook libraries often fail to fully reproduce what a user sees, especially with images, shapes, charts, merged cells, fonts, row heights, wrapping, and print layout.

## 8. Coordinate Model

The system needs explicit coordinate conversion between workbook and visual spaces.

Required coordinate systems:

```text
Cell address       Example: B12:H30
Grid coordinate    row/column index
Canvas coordinate  sheet-level x/y/w/h
Capture coordinate screenshot pixel bbox
Page coordinate    printed page bbox
Object anchor      image/chart/shape anchor
```

Example:

```json
{
  "sheet": "Inspection",
  "cell_range": "B12:H30",
  "canvas_bbox": { "x": 120, "y": 340, "w": 680, "h": 420 },
  "capture_bbox": { "x": 240, "y": 680, "w": 1360, "h": 840 },
  "confidence": 0.98
}
```

Coordinate maps are required for deterministic validation. If the LLM claims that a table belongs below an image, the system must verify the claim using actual bounding boxes.

## 9. Evidence Authorities

The system uses four primary authorities.

### 9.1 Workbook Structure Authority

This includes cell values, styles, merges, tables, objects, and workbook metadata.

It answers questions such as:

- Does this source range exist?
- Does the range contain values, formulas, borders, or merged cells?
- Is the area dense enough to be a table?
- Does the top row look like a header?
- Is a displayed table actually a pivot table view backed by a pivot cache source?

### 9.2 Rendered Visual Authority

This includes screenshots, page captures, OCR, and visual features.

It answers questions such as:

- Is the claimed block visually present?
- Is one block above, below, inside, or near another block?
- Are several blocks visually grouped by border, background, alignment, or whitespace?
- Does an image visually correspond to a nearby caption or table?

### 9.3 Formula/Dataflow Authority

This includes formula expressions, dependency graph, recalculated values, and formula-derived dataflow.

It answers questions such as:

- Is a summary block derived from the claimed data region?
- Does a total row depend on the table body?
- Does a displayed value match the recalculated value?
- Does the LLM's semantic claim conflict with the formula graph?
- Does a formula depend on another workbook, an unresolved workbook range, or a pivot table view such as `GETPIVOTDATA`?
- Which tables or regions are upstream inputs to this table?
- Which tables, summaries, pivots, or reports consume this table's outputs?
- Is a block a raw input, bridge/intermediate transform, summary output, report view, or policy/parameter table?
- Do formulas connect visually separate tables into one pipeline?
- Are visually adjacent tables actually independent because they have different upstream/downstream dependencies?

Table-level I/O pipelines are derived from this authority. A table I/O pipeline should include:

- source table or region
- input dependencies
- transformation formulas or pivot cache operations
- output table, pivot, summary, or report block
- external workbook dependencies
- pipeline role, such as `input`, `parameter`, `bridge`, `transform`, `summary`, `report`, or `audit_check`
- confidence and gate status
- source evidence references

### 9.4 View-State Authority

This includes hidden rows, hidden columns, filters, outline/collapse state, frozen panes, active top-left cells, and sheet view metadata.

It answers questions such as:

- What did the workbook intend the human to see in the current visible state?
- Which rows or columns are structurally present but visually hidden?
- Is a blank or thin capture explained by hidden or filtered rows?
- Should a reveal/clear-filter capture be treated as diagnostic rather than source-authoritative evidence?

The source workbook visible state must be preserved. A preflight inventory is required near the start of the pipeline, before sampling, capture planning, and visual interpretation rely on row or column visibility.

## 10. Visual Block Detection

The visual block detector groups low-level workbook and capture evidence into candidate document blocks.

Useful signals:

- whitespace boundaries
- border boxes
- fill color regions
- merged cell title regions
- repeated row and column patterns
- value density
- font hierarchy
- text alignment
- object anchors
- image and chart placement
- formula dependency clusters
- print area boundaries

Candidate block types should be constrained by the document structure ontology.

## 11. Document Graph

The document graph represents both hierarchy and cross-links.

Example:

```text
Sheet
└─ Section
   ├─ TextBlock
   │  └─ describes -> Table
   ├─ Table
   │  └─ explained_by -> Note
   └─ ImageBlock
      └─ table_of <- Table
```

The graph must preserve:

- parent/child structure
- reading order
- relation type
- source range or anchor
- visual bbox
- confidence
- validation status
- evidence references

## 12. LLM Proposal Layer

The LLM receives bounded evidence, not the entire workbook as unstructured context.

It may propose:

- block type classifications
- hierarchy candidates
- description, caption, support, and table-of relationships
- semantic concept candidates
- alias candidates
- shared ontology alignment candidates
- ambiguity notes

LLM output should use stable proposal IDs so deterministic gates can accept, reject, quarantine, or request review for each claim.

## 13. Deterministic Gates

Deterministic gates validate LLM and parser proposals before they are accepted into the final package.

| Gate | Purpose |
|---|---|
| Schema Gate | Checks that the output matches the required schema. |
| Source Trace Gate | Ensures every node and relation has source evidence. |
| Coordinate Gate | Validates cell, canvas, capture, page, and anchor mappings. |
| Visual Consistency Gate | Checks bbox-based claims such as above, below, inside, near, grouped, and captioned. |
| 2D Region Boundary Gate | Verifies that table/text/summary candidates have both row and column boundaries and are not accepted from row continuity alone. |
| Adjacent Split Gate | Checks whether physically touching ranges are still separate blocks because of headers, styles, formulas, pivot sources, or surrounding text. |
| Merge Gate | Checks whether physically separated ranges should be one logical block because they share source authority, formula family, pivot cache, or hierarchy. |
| Table Structure Gate | Verifies header/body structure, density, repeated patterns, and table boundaries. |
| Pivot Table Gate | Verifies pivot table locations, cache sources, fields, filters, and whether sampled values are only a rendered pivot view. |
| Formula Consistency Gate | Checks dependency graph, recalculated values, totals, summaries, and derived claims. |
| External Reference Gate | Checks formulas that depend on other workbooks or unresolved external link package metadata. |
| Formula Pattern Gate | Checks repeated formula signatures before deciding whether a large sheet is one table, a split table set, or a summary band over raw data. |
| Table I/O Pipeline Gate | Checks whether table-level input, transform, output, pivot, report, and bridge roles are supported by formula, pivot cache, external reference, and block-boundary evidence. |
| General Domain Gate | Checks semantic claims against reusable domain principles such as accounting concepts, expected value roles, and broad policy constraints. |
| Local Domain Gate | Checks semantic claims against boundary-scoped glossary, policy, workbook-pair evidence, and reviewed internal meanings. |
| Ontology Constraint Gate | Ensures document block types and relation types are allowed by the structure ontology. |
| Conflict Gate | Detects incompatible labels, overlapping ranges, duplicate ownership, and contradictory relations. |
| Confidence Gate | Prevents low-confidence claims from becoming accepted final results. |
| Replay Gate | Verifies that the same input package produces stable output. |

Gate outcomes:

- accepted
- rejected
- warning
- quarantined
- requires_human_review

Boundary gate results use a separate process-facing status because boundary evidence often starts as noisy parser evidence before becoming an accepted graph claim:

- `strong_candidate`: strong deterministic evidence such as blank-column separation; eligible for automatic split candidate projection.
- `review_candidate`: useful evidence that needs visual, formula, merged-cell, or human review before final acceptance.
- `weak_signal`: high-recall evidence such as style-only discontinuity; keep for review/ranking but do not split automatically.

Merged ranges are treated as title/header/section evidence first. They may strengthen a nearby boundary, but they should not automatically split a table without supporting evidence.

## 14. Cross-Validation Examples

### Text Describes Table

LLM claim:

```text
TextBlock A describes Table B.
```

Validation checks:

- A and B exist in the same sheet or document section.
- A is above or near B in capture coordinates.
- A and B are in the same visual group or reading-order segment.
- B passes table structure checks.
- A contains referential language such as "below", "following", or a topic matching B headers.
- The relation is allowed by the document structure ontology.

### Table Summarizes Formula Region

LLM claim:

```text
SummaryBlock S summarizes Table T.
```

Validation checks:

- S contains formulas or calculated values.
- Formula dependencies point into T or its child data region.
- Recalculated values match displayed or cached values within tolerance.
- S is visually near T or inside the same section.

### Image Has Attached Table

LLM claim:

```text
Table T is attached to ImageBlock I.
```

Validation checks:

- I has a valid object anchor and visual bbox.
- T is below, beside, or visually grouped with I.
- No closer competing image has stronger evidence.
- Caption or nearby title supports the relationship.
- The relation is not contradicted by section hierarchy.

## 15. Output: Workbook Understanding Package

After validation, the system emits a package with accepted results and reviewable unresolved items.

```text
WorkbookUnderstandingPackage
├─ validated_document_graph
├─ extracted_data_views
├─ table_io_pipelines
├─ cross_validation_plan
├─ render_captures
├─ local_semantic_ontology_candidates
├─ evidence_index
├─ validation_ledger
├─ process_ledger
└─ review_queue
```

### 15.1 Validated Document Graph

The document graph is the primary understanding artifact.

It contains:

- validated blocks
- hierarchy
- reading order
- accepted relations
- source evidence
- confidence
- gate references

### 15.2 Extracted Data Views

Data views are projections from the document graph.

Examples:

- tables
- pivot tables and pivot cache sources
- key-value fields
- text blocks
- image references
- chart references
- summary values
- formula-derived values

Data views should not become the source of truth. They must point back to document graph nodes and original workbook evidence.

### 15.3 Table I/O Pipelines

Table I/O pipelines explain how workbook regions exchange data.

They are projections over validated blocks, formulas, pivot caches, and external references. They do not replace the document graph or formula graph.

Example:

```json
{
  "id": "pipeline_sales_from_payment_detail",
  "role": "summary_output",
  "output_block_id": "매출_cell_region_1",
  "input_refs": [
    {
      "kind": "table_or_region",
      "sheet": "결제상세",
      "range": "AF:AF",
      "evidence": "SUMIFS"
    }
  ],
  "transform_refs": [
    {
      "kind": "formula_signature_group",
      "signature": "SUMIFS(결제상세!$AF:$AF,결제상세!$D:$D,매출!R[0]C[-3])"
    }
  ],
  "pipeline_status": "candidate",
  "requires_review": true
}
```

Pipeline roles should remain conservative until gates validate the evidence. A visual report table can be downstream output, a calculation bridge, or a manual audit table depending on formulas and pivot/source authority.

Current candidate implementation:

- `scripts/workbook_table_io_pipeline.py` projects formula relation groups and pivot cache source relations into output-centered table I/O pipeline candidates.
- `schemas/workbook-table-io-pipeline.schema.json` validates the candidate artifact shape.
- `review-packages/workbook-understanding/mbp-2026-02-table-io-pipelines.json` is the current sample artifact.
- `review-packages/workbook-understanding/index.html` includes a Table I/O Pipelines review section with Mermaid sheet-level and pipeline-level input/output graphs.

Current sample result:

- 45 candidate pipelines.
- 21 formula-backed pipelines.
- 24 pivot-cache-backed report pipelines.
- 10 summary-role pipelines.
- 1 unresolved input-region pipeline that needs a later region-boundary or visual review pass.

Implementation learning: formula reference parsing must treat arithmetic before unquoted sheet names carefully. A formula such as `B26-누적!DA1` must be parsed as the current-sheet cell `B26` minus the `누적!DA1` reference, not as a reference to a fake `B26-누적` sheet.

### 15.4 Cross-Validation Plan

The cross-validation plan is a reviewable work order for capture and deterministic gate execution.

It should include:

- capture targets with sheet, range, expanded capture window, priority, and score
- related pipeline, block, region, and boundary-gate IDs
- pending gate checks
- pass conditions and failure signals
- reviewer-facing questions

Current candidate implementation:

- `scripts/workbook_cross_validation_plan.py` builds the target plan from block candidates and table I/O pipelines.
- `schemas/workbook-cross-validation-plan.schema.json` validates the artifact shape.
- `review-packages/workbook-understanding/mbp-2026-02-cross-validation-plan.json` is the current sample artifact.
- The HTML viewer includes a Cross-Validation Plan section with a sheet-diverse recommended first capture batch.

Current sample result:

- 63 capture targets across all 14 sheets.
- 40 high-priority targets, 13 medium-priority targets, and 10 low-priority targets.
- 45 pipeline-linked targets.
- 24 pivot/report targets.
- 21 boundary-linked targets.
- 11 image hierarchy targets.
- 79 pending visual/formula gate checks.
- 12 targets in the recommended first capture batch.

This stage exists to avoid opening Excel blindly. It lets the parser and reviewer decide which visual evidence will be most useful before expensive capture and coordinate normalization.

### 15.5 Render Captures

Render captures are visual evidence acquired from an actual rendering path.

Current candidate implementation:

- `scripts/workbook_render_capture.py` opens a sandbox copy of the source workbook in Microsoft Excel on macOS.
- `scripts/excel_copy_ranges_png.applescript` uses Excel `copy picture` with screen appearance to export each target range as a PNG.
- `schemas/workbook-render-captures.schema.json` validates the capture result artifact.
- `review-packages/workbook-understanding/mbp-2026-02-render-captures.json` is the current sample artifact.
- The HTML viewer includes a Render Captures section with the captured PNGs.

Current sample result:

- 12 recommended first-batch targets selected.
- 12 PNG captures succeeded.
- 0 capture failures.
- 30 pending gate checks now have capture evidence and remain `captured_pending_review`.

Known tuning observation: some wide or sparse ranges produce very short or hard-to-review PNGs, such as a 19px-tall capture for `포도 A1:R22`. Capture quality checks now make this issue explicit before downstream visual gates use the PNG as evidence.

Render captures do not by themselves accept semantic claims. They move gate checks from `pending_capture` to a captured evidence state. Later bbox normalization, visual feature detection, and review/gate execution decide pass/fail.

### 15.6 Capture Quality Checks

Capture quality checks determine whether a render capture is usable for downstream visual gates.

They are deterministic checks over the rendered PNG and the requested workbook range. They do not accept or reject semantic claims.

Current candidate implementation:

- `scripts/workbook_capture_quality.py` evaluates render capture PNG dimensions, row/column pixel density, aspect ratio, visible pixel ratio, and tiling/expanded-window needs.
- `schemas/workbook-capture-quality.schema.json` validates the capture quality artifact.
- `review-packages/workbook-understanding/mbp-2026-02-capture-quality.json` is the current sample artifact.
- The HTML viewer includes a Capture Quality section after Render Captures.

Current sample result:

- 12 captures evaluated.
- 8 captures are usable for the next visual gate.
- 2 captures require human review because they are wide enough that tiling may improve inspection.
- 2 captures require recapture because rendered row height and aspect ratio are too poor for reliable visual gates.
- `당월산식 A1:BA22` and `포도 A1:R22` need view-state handling before bbox normalization should trust them.

### 15.7 Recapture Candidate Experiments

Recapture candidates are alternative evidence-acquisition attempts, not final selected capture plans.

The deterministic layer may generate candidates such as same-window control captures, column tiles for wide ranges, expanded row context, and visible-row context ranges. It must not claim that one candidate is correct before Excel capture and quality gates evaluate the result.

Current candidate implementation:

- `scripts/workbook_recapture_candidate_plan.py` generates candidate capture targets from render capture quality results.
- `schemas/workbook-recapture-candidate-plan.schema.json` validates the candidate plan artifact.
- `review-packages/workbook-understanding/mbp-2026-02-recapture-candidate-plan.json` is the current candidate plan.
- `review-packages/workbook-understanding/mbp-2026-02-recapture-candidate-captures.json` contains the Excel render captures for those candidates.
- `review-packages/workbook-understanding/mbp-2026-02-recapture-candidate-quality.json` scores the candidate captures.
- The HTML viewer includes Recapture Candidates and Recapture Candidate Results sections.

Current sample result:

- 12 recapture candidates were generated and captured.
- Column tiling fixed the wide-range review cases for `결제상세` and `유하다요_강사료`.
- Hidden or collapsed row cases did not improve through simple expansion or visible-row shifting.
- `당월산식` and `포도` need a separate hidden row / view-state handling decision before coordinate normalization.

### 15.8 View-State Preflight and Capture Reconciliation

View-state handling records what Excel currently shows separately from what the workbook structurally contains. It has two positions in the process: early preflight before sampling/capture planning, and later reconciliation after capture quality checks.

Current implementation:

- `scripts/workbook_view_state_profile.py` extracts hidden row spans, hidden column spans, outline column spans, `filterMode`, `autoFilter`, panes, and sheet view signals from workbook XML.
- `schemas/workbook-view-state-profile.schema.json` validates the view-state profile artifact.
- `review-packages/workbook-understanding/mbp-2026-02-view-state-preflight.json` is the early preflight inventory.
- `review-packages/workbook-understanding/mbp-2026-02-view-state-profile.json` is the capture-window reconciliation artifact.
- The HTML viewer includes View-State Preflight and Hidden Row / View-State sections.

Current sample result:

- 14 sheets were scanned in preflight.
- 12 capture-relevant sheets were scanned in capture reconciliation.
- 3 sheets have `filterMode=1`.
- 3 sheets contain hidden rows.
- 6,506 hidden rows and 18 hidden columns were identified across the capture-relevant sheets.
- 24 capture windows were analyzed against view-state evidence.
- 9 capture windows are explained by view-state, and 1 additional usable window is affected by filtered rows.
- `당월산식` and `포도` failures are not transient capture failures; they are current visible-state effects from hidden or filtered rows.

Authority decision:

- Visible render evidence remains authoritative for what a user currently sees.
- Structural workbook data remains authoritative for hidden rows and dataflow extraction.
- Unhidden or cleared-filter captures may be created only as diagnostic evidence and must be labeled non-authoritative.
- Revealing hidden rows or clearing filters must not replace the source visible state.

### 15.9 Coordinate Normalization

Coordinate normalization maps capture-range bboxes back to workbook cell ranges.

Current implementation:

- `scripts/workbook_coordinate_normalization.py` combines render captures, capture quality, and view-state reconciliation.
- `schemas/workbook-coordinate-normalization.schema.json` validates the coordinate normalization artifact.
- `review-packages/workbook-understanding/mbp-2026-02-coordinate-normalization.json` is the current sample artifact.
- The HTML viewer includes a Coordinate Normalization section.

Current sample result:

- 24 capture windows were mapped.
- 12 mappings passed as normalized visible ranges.
- 1 mapping normalized with a view-state warning.
- 2 mappings require review.
- 9 mappings are blocked by hidden/filter view-state.

Coordinate normalization is range-level evidence only. It does not detect internal visual features and does not turn hidden rows into visual absence claims.

### 15.10 Visual Feature Detection

Visual feature detection extracts deterministic image features from normalized visible captures.

Current implementation:

- `scripts/workbook_visual_feature_detection.py` reads coordinate normalization and render capture artifacts.
- `schemas/workbook-visual-feature-detection.schema.json` validates the visual feature artifact.
- `review-packages/workbook-understanding/mbp-2026-02-visual-features.json` is the current sample artifact.
- The HTML viewer includes a Visual Feature Detection section.

Current sample result:

- 24 coordinate mappings were evaluated.
- 12 captures produced detected visual features.
- 1 capture produced features with a view-state warning.
- 2 captures were skipped because capture quality still requires review.
- 9 captures were skipped because hidden/filter view-state blocks visual absence claims.
- 13 captures produced grid/table-like line structure signals.

This stage does not assign document semantics. It only prepares visual evidence such as content bboxes, whitespace ratios, line candidates, dominant colors, and grid/table-like signals for later cross-validation gates.

### 15.11 Cross-Validation Gate Execution

Cross-validation gate execution converts planned pending gates into evidence statuses.

Current implementation:

- `scripts/workbook_cross_validation_gate_execution.py` combines the cross-validation plan with visual feature results.
- `schemas/workbook-cross-validation-gate-execution.schema.json` validates the gate execution artifact.
- `review-packages/workbook-understanding/mbp-2026-02-gate-execution.json` is the current sample artifact.
- The HTML viewer includes a Cross-Validation Gate Execution section.

Current sample result:

- 79 planned gate checks were executed against current evidence.
- 17 gates were accepted from deterministic visual evidence.
- 0 gates were rejected.
- 62 gates remain review-required.
- 49 review-required gates need capture evidence.
- 4 gates are blocked by hidden/filter view-state.
- 6 gates require capture quality review before deterministic acceptance.

An accepted gate is not yet a final document graph claim. It only means the current evidence package satisfies that gate's deterministic pass criteria. Boundary acceptance and document graph assembly still happen in later stages.

### 15.12 Boundary Acceptance / Rejection

Boundary acceptance resolves ranked boundary candidates into accepted, rejected, or review-required decisions for later document graph assembly.

Current implementation:

- `scripts/workbook_boundary_decisions.py` combines block candidates with cross-validation gate execution results.
- `schemas/workbook-boundary-decisions.schema.json` validates the boundary decision artifact.
- `review-packages/workbook-understanding/mbp-2026-02-boundary-decisions.json` is the current sample artifact.
- The HTML viewer includes a Boundary Acceptance / Rejection section.

Current sample result:

- 117 boundary candidates were evaluated.
- 6 boundaries were accepted.
- 0 boundaries were rejected.
- 111 boundaries remain review-required.
- 6 accepted boundaries are split boundaries backed by strong blank-column structural evidence.
- 110 review-required boundaries are style-only candidates needing corroborating visual, formula, header, or human evidence.
- 17 decisions are linked to missing-capture review signals.
- 39 decisions are linked to view-state warning or blocked signals.

This stage is intentionally conservative. Accepted boundaries may be used by document graph assembly, but style-only boundaries, merged-title boundaries, missing-capture cases, and view-state-risk cases remain review items. A region-level accepted gate does not automatically prove every style discontinuity inside that region.

### 15.13 Pipeline Role Validation

Pipeline role validation decides whether a candidate table I/O pipeline's role is supported by deterministic evidence.

Current implementation:

- `scripts/workbook_pipeline_role_validation.py` combines table I/O pipelines, gate execution results, and boundary decisions.
- `schemas/workbook-pipeline-role-validation.schema.json` validates the role validation artifact.
- `review-packages/workbook-understanding/mbp-2026-02-pipeline-role-validation.json` is the current sample artifact.
- The HTML viewer includes a Pipeline Role Validation section.

Current sample result:

- 45 pipeline roles were evaluated.
- 44 roles were accepted.
- 0 roles were rejected.
- 1 role remains review-required.
- 24 report roles were accepted from pivot-cache transform evidence.
- 10 summary roles were accepted from summary formula evidence such as `SUBTOTAL` or `SUMIFS`.
- 10 transform roles were accepted from formula-signature evidence.
- 1 pipeline remains review-required because its input range is not yet mapped to an owning region.
- 34 accepted or review-required role decisions are linked to gate results that still need visual capture or review; this does not invalidate the role when formula or pivot authority is sufficient.

This stage validates the role label, not the final graph. Missing visual capture is retained as a review annotation unless it contradicts the role evidence. Pivot reports are validated from pivot cache settings rather than from displayed values, because pivot output cells are report views over cache/source definitions.

### 15.14 Workbook Evidence Package Assembly

Workbook evidence package assembly creates the parser input authority for later ontology and graph work.

Current implementation:

- `scripts/workbook_evidence.py` supports artifact-first assembly through manifest, read-only sample, formula, style, block, pipeline, capture, view-state, gate, boundary, pipeline-role, and domain-reference artifacts.
- `schemas/workbook-evidence.schema.json` validates both the older direct workbook observation package and the artifact-assembled evidence package.
- `review-packages/workbook-understanding/mbp-2026-02-evidence-package.json` is the current sample artifact.
- The HTML viewer includes a Workbook Evidence Package section.

Current sample result:

- 19 deterministic artifacts were inventoried into one package.
- 14 sheets are represented.
- 24 normalized capture mappings are included.
- 17 accepted gate results and 62 review-required gate results are indexed.
- 6 accepted boundary decisions and 111 review-required boundary decisions are indexed.
- 44 accepted pipeline-role validations and 1 review-required pipeline-role validation are indexed.
- 174 review queue items are exposed for later capture planning, human review, or process tuning.
- In the earlier Excel workbook sample, 8 `accounting-kr` general-domain references are attached as separate domain evidence refs.

This stage does not reopen or mutate the source workbook. It assembles prior evidence and decision artifacts into one traceable authority surface. General-domain references remain separate evidence inputs and do not replace workbook evidence or boundary-scoped local-domain evidence.

### 15.15 Document Ontology Mapping

Document ontology mapping applies the document-structure ontology to the evidence package.

Current implementation:

- `scripts/workbook_document_ontology_mapping.py` reads the workbook evidence package and follows only its `source_artifacts` refs.
- `schemas/workbook-document-ontology-mapping.schema.json` validates the mapping artifact.
- `review-packages/workbook-understanding/mbp-2026-02-document-ontology-mapping.json` is the current sample artifact.
- The HTML viewer includes a Document Ontology Mapping section with node class counts, relation counts, data views, review queue items, and a Mermaid data-view graph.

Current sample result:

- 3,459 ontology nodes were produced.
- 3,653 ontology relations were produced.
- 45 data views were produced.
- 14 sheet nodes, 54 document block nodes, and 31 cell region nodes are represented.
- 45 pipeline nodes and 928 transform-step nodes are represented.
- 24 visual evidence nodes and 2,245 range reference nodes are represented.
- 44 data views are accepted and 1 data view remains review-required.
- 174 unresolved evidence items remain attached to the ontology review queue.

This stage is ontology utilization, not ontology generation. It maps workbook structure to classes such as `WorksheetSurface`, `ImageBlock`, `PivotTableBlock`, `CellRegion`, `WorkbookDataPipeline`, `WorkbookTransformStep`, and `RenderedVisualEvidence`. It does not create local or shared semantic concepts.

Pivot tables remain pivot report views backed by pivot cache/source evidence, not raw data tables. Formula and pivot-derived data views remain tied to pipeline role validation evidence. Candidate relations and review-required items remain visible instead of being guessed into accepted hierarchy.

### 15.16 Action Contract Layer

The action contract layer makes the document ontology actionable.

Current implementation:

- `scripts/workbook_action_contracts.py` reads the document ontology mapping and evidence package.
- `schemas/workbook-action-contracts.schema.json` validates the action contract artifact.
- `review-packages/workbook-understanding/mbp-2026-02-action-contracts.json` is the current sample artifact.
- The HTML viewer includes an Action Contract Layer section with action counts, owner counts, high-priority items, and a Mermaid action flow graph.

Current sample result:

- 219 action contracts were produced.
- 44 accepted data views are `ready` for downstream graph assembly.
- 171 contracts are `open`.
- 4 contracts are `blocked` by view-state authority separation.
- 12 contracts are high priority.
- 49 contracts require render capture.
- 6 contracts require recapture or tiling.
- 4 contracts require view-state authority reconciliation.
- 2 contracts require unresolved input-region ownership resolution.
- 110 contracts require correlated boundary evidence for style-only boundary candidates.

This layer does not accept new ontology claims. It converts existing statuses and review reasons into explicit next actions:

- action owner
- priority
- required evidence
- deterministic gate
- completion condition
- completion effect

Example:

```json
{
  "action_type": "resolve_input_region_ownership",
  "action_owner": "deterministic_parser",
  "required_evidence": [
    "formula_relation_group",
    "candidate_input_range",
    "owning_cell_region_or_new_region",
    "boundary_decision"
  ],
  "deterministic_gate": "input_region_ownership_gate",
  "completion_effect": "promote_or_reject_data_view_after_role_validation"
}
```

The action contract layer is the handoff between evidence-backed document ontology and the next parser/review step. It prevents `review_required` from remaining a passive label.

### 15.17 Domain Knowledge Source Model

The domain knowledge source model separates reusable general-domain evidence from boundary-scoped local-domain evidence before semantic ontology proposal generation.

Current implementation:

- `scripts/workbook_domain_source_model.py` reads the evidence package, document ontology mapping, action contracts, and optional domain roots.
- `schemas/workbook-domain-source-model.schema.json` validates the domain source model artifact.
- `review-packages/workbook-understanding/mbp-2026-02-domain-source-model.json` is the current sample artifact.
- The HTML viewer includes a Domain Knowledge Source Model section with semantic readiness, general-domain sources, local-domain boundaries, governance rules, and domain review items.

Current sample result:

- In the earlier Excel workbook sample, 8 general-domain sources are available from `/Users/kangmin/.onto/domains/accounting-kr`.
- 0 explicit local-domain policy or vocabulary sources are available.
- 1 local workbook-sample boundary was created as a boundary candidate.
- The local boundary is `review_required`.
- Semantic readiness is `proposal_only_local_boundary_pending`.
- Shared ontology promotion is not allowed from this single workbook.
- Readiness blocking factors are `local_domain_boundary_not_confirmed`, `blocked_action_contracts`, and `high_priority_structural_actions`.

This stage does not generate semantic ontology concepts. It defines what evidence future semantic proposals may use.

General-domain sources can constrain proposals, for example by providing accounting concepts, rules, structure specs, dependency rules, conciseness rules, competency questions, and extension cases. They cannot replace workbook evidence.

Local-domain concepts require an explicit boundary such as organization, project, team, tenant, workbook family, or policy scope. Because the current sample has no explicit local-domain source document, local semantic candidates must remain proposal-only with a boundary warning until that boundary is confirmed.

### 15.18 LLM Proposal Generation

LLM proposal generation materializes bounded interpretation proposals without accepting them as final ontology claims.

Current implementation:

- `scripts/workbook_llm_proposals.py` reads the document ontology mapping, action contracts, domain source model, read-only sample, and table I/O pipelines.
- `schemas/workbook-llm-proposals.schema.json` validates the proposal package artifact.
- `review-packages/workbook-understanding/mbp-2026-02-llm-proposals.json` is the current sample artifact.
- The HTML viewer includes an LLM Proposal Generation section with semantic concepts, hierarchy candidates, semantic relations, aliases, ambiguity notes, and next gate counts.

Current sample result:

- 10 semantic concept proposals were generated.
- 11 hierarchy proposals were generated.
- 7 semantic relation proposals were generated from table I/O pipeline evidence.
- 175 alias proposals were generated from observed workbook terms and concept templates.
- 2 ambiguity notes were generated.
- 4 semantic concept proposals are local-domain sensitive.
- All proposals remain `proposed` with status `proposal_only_pending_deterministic_validation`.

This stage is intentionally not deterministic acceptance. It uses LLM interpretation to name likely meanings, but each proposal carries:

- workbook evidence refs
- domain source refs where applicable
- local boundary refs where applicable
- required deterministic gates
- confidence and review flags

Because the current semantic readiness is `proposal_only_local_boundary_pending`, local-domain concepts and shared ontology promotion remain blocked until Stage 25 validates or quarantines each proposal.

### 15.19 Deterministic Validation of LLM Proposals

Deterministic validation converts LLM proposals into explicit gate outcomes without reinterpreting workbook meaning.

Current implementation:

- `scripts/workbook_llm_proposal_validation.py` reads the LLM proposal package, document ontology mapping, table I/O pipelines, and domain source model.
- `schemas/workbook-llm-proposal-validation.schema.json` validates the proposal validation artifact.
- `review-packages/workbook-understanding/mbp-2026-02-llm-proposal-validation.json` is the current sample artifact.
- The HTML viewer includes a Deterministic Validation section with status counts, gate summary, and review/quarantine queue.

Current sample result:

- 205 proposal results were validated.
- 39 proposal results were accepted.
- 83 proposal results require human review.
- 83 proposal results were quarantined.
- 0 proposal results were rejected.
- `source_trace_gate` accepted all 205 proposal results.
- `local_domain_gate` quarantined unconfirmed local-boundary claims.
- `conflict_gate` sent duplicate alias ownership to human review.

This stage validates proposal claims, not final graph membership. Accepted proposal results become eligible inputs for validated document graph assembly. Quarantined, rejected, and review-required results must remain visible and must not be promoted into the final graph without their required action.

Formula gates in this stage validate formula or pivot topology evidence from parser artifacts. They do not validate calculated Excel results; Excel recalculation remains a separate authority when numeric formula results are claimed.

### 15.20 Validated Document Graph Assembly

Validated document graph assembly creates the first graph body that downstream consumers may treat as accepted workbook structure plus accepted semantic proposals.

Current implementation:

- `scripts/workbook_validated_document_graph.py` reads the document ontology mapping, LLM proposal package, LLM proposal validation, and action contracts.
- `schemas/workbook-validated-document-graph.schema.json` validates the graph artifact.
- `review-packages/workbook-understanding/mbp-2026-02-validated-document-graph.json` is the current sample artifact.
- The HTML viewer includes a Validated Document Graph section with graph counts, semantic concepts, semantic relations, accepted aliases, filtered document relations, and carry-forward queues.

Current sample result:

- 1,078 graph nodes were assembled.
- 1,197 graph relations were assembled.
- 44 accepted data views were carried into the graph.
- 5 accepted semantic concept nodes were added.
- 6 accepted semantic relations were added.
- 28 accepted aliases were added.
- 174 document ontology review items were carried forward.
- 166 proposal validation review/quarantine items were carried forward.
- 1 accepted document relation was filtered because one endpoint was outside the accepted graph body.

This stage is a projection boundary. It promotes only accepted deterministic document ontology artifacts and accepted proposal validation results into the graph body. It does not resolve review items, confirm local-domain boundaries, recalculate formulas, or promote quarantined proposals.

The validated graph becomes the input authority for data view projection. Carry-forward queues remain process-visible and must stay attached to downstream outputs as warnings or required actions.

### 15.21 Data View Projection

Data view projection creates reviewable read models from the accepted graph body.

Current implementation:

- `scripts/workbook_data_view_projection.py` reads the validated document graph and read-only sample artifact.
- `schemas/workbook-data-view-projection.schema.json` validates the projection artifact.
- `review-packages/workbook-understanding/mbp-2026-02-data-view-projection.json` is the current sample artifact.
- The HTML viewer includes a Data View Projection section with projection kind counts, role counts, preview status, document object counts, semantic coverage, formula warnings, and selected preview rows.

Current sample result:

- 44 accepted data views were projected.
- 24 pivot view projections were produced.
- 10 formula summary projections were produced.
- 10 formula transform projections were produced.
- All 44 projections have read-only preview rows.
- 58 accepted document objects were projected: 5 image refs, 24 pivot table blocks, 18 row bands, and 11 pivot value regions.
- 28 data views have accepted semantic context; 16 data views remain structurally accepted but do not yet have accepted semantic context.
- 669 sampled formula cells are retained as formula text only.
- 174 document review items and 166 proposal review/quarantine items remain attached as carry-forward queues.

This stage is a read-model projection. It does not recalculate Excel formulas, accept numeric formula results, resolve carry-forward queues, or promote review-required semantic claims. Formula text may help a reviewer understand the table surface, but calculated formula-result authority still requires the real Excel engine.

The data view projection becomes the practical review input for local semantic ontology candidate generation. It makes the accepted table/pivot/formula surfaces compact enough to inspect without reopening the entire validated graph.

### 15.22 Local Semantic Ontology Candidates

Semantic candidates represent meaning inferred from the workbook.

Current implementation:

- `scripts/workbook_local_semantic_candidates.py` reads data view projections, the domain source model, and the validated document graph.
- `schemas/workbook-local-semantic-candidates.schema.json` validates the candidate artifact.
- `review-packages/workbook-understanding/mbp-2026-02-local-semantic-candidates.json` is the current sample artifact.
- The HTML viewer includes a Local Semantic Ontology Candidates section with local boundary status, source kind counts, candidate statuses, promotion blockers, candidate relations, required actions, and review queue items.

Current sample result:

- 21 local semantic candidates were generated.
- 5 candidates came from accepted semantic context in the validated graph.
- 16 candidates came from accepted data views that do not yet have accepted semantic context.
- All 44 accepted data views are covered by candidate relations.
- 49 candidate relations were generated.
- 0 candidates are promotable to shared ontology.
- 25 review queue entries remain, including local boundary confirmation and semantic label assignment.
- Local boundary is still `review_required`, and no local policy or vocabulary source is available.

This stage is deterministic candidate projection. It may reuse accepted semantic context as seed labels, but it does not accept local-domain truth, confirm a local boundary, resolve unassigned semantic labels, validate formula results, or promote anything into the shared ontology.

Shared ontology alignment and human review consumes these candidates. In the current sample, that stage mostly surfaces blockers and review questions because shared promotion is intentionally blocked until local boundary, local sources, repeated workbook-family evidence, conflict checks, and human review are satisfied.

Example:

```json
{
  "id": "candidate_measurement_value",
  "label": "Measurement Value",
  "aliases": ["Measured Value", "Actual Value"],
  "observed_in": ["table_1.header.D12"],
  "value_type": "measurement",
  "source_ranges": ["Inspection!D12:D30"],
  "promotion_status": "local_candidate",
  "confidence": 0.87
}
```

Semantic candidates should carry explicit domain-layer evidence.

Example:

```json
{
  "id": "candidate_revenue_recognition_60_day",
  "label": "60-Day Revenue Recognition",
  "observed_terms": ["수익인식60일"],
  "domain_layer": "local",
  "general_domain_alignment": {
    "candidate": "Revenue Recognition",
    "evidence_refs": ["general_domain:accounting/revenue-recognition"]
  },
  "local_domain_evidence_refs": [
    "workbook:sheet:수익인식60일",
    "policy:local-boundary/revenue-recognition-60-day",
    "review_note:finance-owner-2026-05-31"
  ],
  "promotion_status": "local_candidate",
  "requires_human_review": true
}
```

The general-domain alignment says the candidate belongs near a reusable accounting concept. The local-domain layer says the exact 60-day rule and workbook terminology are valid only inside the declared boundary until repeated evidence and review justify broader promotion.

### 15.23 Shared Ontology Alignment / Human Review

Shared ontology alignment checks whether local semantic candidates can be promoted, mapped, or held for review.

Current implementation:

- `scripts/workbook_shared_ontology_alignment_review.py` reads local semantic candidates, the domain source model, and the data view projection.
- `schemas/workbook-shared-ontology-alignment-review.schema.json` validates the review artifact.
- `review-packages/workbook-understanding/mbp-2026-02-shared-ontology-alignment-review.json` is the current sample artifact.
- The HTML viewer includes a Shared Ontology Alignment / Human Review section with preconditions, blocker counts, conflict risks, candidate-level evidence requirements, K-GAAP/K-IFRS basis review, and human review questions.

Current sample result:

- 21 alignment review items were generated from 21 local semantic candidates.
- 0 candidates were promoted.
- 21 candidates remain blocked by unconfirmed local boundary.
- 21 candidates remain blocked by missing local-domain source evidence.
- 16 candidates still need human-confirmed semantic labels.
- 14 candidates require K-GAAP versus K-IFRS basis separation before any revenue-related shared concept can be promoted.
- 12 candidates require Excel engine recalculation before formula-result numeric claims.
- 6 global review questions were generated.
- 0 shared ontology updates were emitted.

This stage is a review packet, not a shared ontology writer. It does not create canonical shared concepts, map candidates into an existing shared ontology target, accept K-IFRS revenue output claims, or resolve local vocabulary truth.

Promotion remains blocked until all of the following are available:

- confirmed organization/project/team/tenant/workbook-family boundary
- local policy, glossary, or owner-approved vocabulary source
- repeated workbook-pair or workbook-family evidence
- shared ontology target for duplicate and conflict checks
- K-GAAP versus K-IFRS output definition when revenue basis is ambiguous
- Excel engine recalculation evidence for formula-result claims
- human approval record

The current sample has K-GAAP-labeled output surfaces and K-IFRS-relevant revenue recognition surfaces. Therefore, the parser must keep these as related but not identical meanings until a human reviewer defines the official output basis and aggregation rule.

### 15.24 Evidence Index

The evidence index makes source lookup cheap and auditable.

It should index:

- workbook ranges
- visual bboxes
- object anchors
- formulas
- OCR spans
- visual features
- parser observations
- LLM proposals
- validation gate results

### 15.25 Validation Ledger

The validation ledger records how the result was produced and why claims were accepted or rejected.

It should include:

- gate version
- input package hash
- proposal IDs
- accepted claims
- rejected claims
- warnings
- quarantined items
- replay hash

### 15.26 Process Ledger

The process ledger records how the parsing process itself evolved.

It is not a validation ledger for a single claim. It is a process-redesign artifact that tracks which stages, heuristics, gates, and review surfaces were useful, noisy, redundant, or missing.

Each ledger entry should include:

- stage
- hypothesis
- actions
- artifact references
- result summary
- effectiveness signals
- process decision
- process learning
- next adjustment

The ledger is used later to decide which steps should remain, be changed, be merged, or be removed from the final process.

### 15.27 Review Queue

The review queue contains unresolved, ambiguous, or risky claims.

Examples:

- competing parent sections
- ambiguous caption ownership
- low-confidence table boundary
- formula mismatch
- possible semantic alias requiring approval
- shared ontology promotion candidate requiring review

### 15.28 Process Redesign Review

Process redesign review uses the process ledger and generated evidence to decide how the parser process should change.

Current implementation:

- `scripts/workbook_process_redesign_review.py` reads the process ledger, tasklist, design doc, AGENTS.md, implementation map, and generated workbook-understanding artifacts.
- `schemas/workbook-process-redesign-review.schema.json` validates the review artifact.
- `review-packages/workbook-understanding/mbp-2026-02-process-redesign-review.json` is the current sample artifact.
- The HTML viewer includes a Process Redesign Review section with final assessment, redesign decisions, recommended pipeline, stage reviews, open evidence gaps, and next iteration plan.

Current sample result:

- 33 process ledger entries were reviewed as the session log.
- 31 tasklist stages were reviewed.
- 57 generated files were inventoried, including 29 JSON artifacts.
- 31 stage reviews were generated.
- 24 recommended next-pipeline positions were generated.
- 6 redesign decisions were accepted for the next iteration.
- 7 open evidence gaps remain.

Accepted redesign decisions:

- Keep view-state preflight at the beginning.
- Treat row bands as seeds and two-dimensional cell regions as the durable boundary object.
- Model render capture, quality checks, recapture, view-state reconciliation, coordinate normalization, and visual feature detection as one visual evidence loop.
- Keep shared ontology alignment review-only until promotion prerequisites pass.
- Add an explicit Excel-engine recalculation gate before numeric formula-result claims.
- Add a lightweight viewer layout gate for dense review sections.

Open evidence gaps:

- local domain boundary is not confirmed
- local policy, glossary, or owner-approved vocabulary source is missing
- 16 accepted data-view surfaces need semantic labels
- 14 candidates need K-GAAP/K-IFRS basis separation
- 12 candidates need Excel-engine formula-result validation
- repeated workbook-pair or workbook-family evidence is missing
- 62 gate results remain review-required

The next process iteration should apply the redesigned ordering to a second workbook or workbook pair, while collecting local-domain evidence and formula-result authority evidence.

### 15.29 Google Sheets Live Access Preflight

Connected Google Sheets must establish live-document authority before workbook-shaped parsing begins.

Current implementation:

- The Sheets Bridge repository paths and inspection contract are used as the access baseline.
- Read-only Sheets API access is performed through Domain-Wide Delegation with the verified user as the impersonated subject.
- Service-account direct access is recorded separately from DWD access.
- `spreadsheetId`, tab `sheetId` values, hidden tab state, metadata counts, and top-left formula/display samples are stored as review artifacts.
- No write, export/import, `.xlsx` round trip, credential copy, or source document replacement is performed.

Current sample result:

- `[Day 1] 1.0 (from 20250707)` was accessed as live Google Sheet `1gp3jl_DyB8kvxHO7m4YjsCPbFTPGi-XKyqPhGAlTZ60`.
- The document has 52 tabs, including 3 hidden tabs.
- The read-only top-left sample captured 335 formula cells and 7 external or dynamic formula signals.
- The HTML preflight viewer is stored under `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/`.

The next Google Sheets iteration should build a live manifest/profile stage over metadata and sampled ranges, then adapt view-state, formula/dataflow, and block-candidate stages to Sheets API evidence.

### 15.30 Google Sheets Live Manifest/Profile

The Google Sheets live manifest/profile stage turns the live access preflight into parser-facing structural evidence.

Current implementation:

- `scripts/google_sheets_live_manifest.py` reads the preflight artifacts and can fetch narrow Sheets API `includeGridData` windows using the same read-only DWD authority.
- `schemas/google-sheets-live-manifest.schema.json` validates the profile artifact.
- `tests/test_google_sheets_live_manifest.py` covers schema-valid fixture output, hidden sheet handling, dynamic formula flags, view-state counts, and permission-gap reporting.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-manifest.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated as the human review viewer for this stage.
- `docs/google-sheets-parser-permission-requirements.md` records the permission and broker-contract requirements that must be satisfied before later connected-Sheets stages use grid windows, Drive metadata, Apps Script metadata, source spreadsheets, or write/apply paths.

Current sample result:

- 52 tabs were profiled over `A1:Z80` windows using 7 read-only Sheets API requests.
- 3 tabs are hidden.
- 335 formula cells, 40 cross-sheet formulas, 6 dynamic formula signals, and 1 `IMPORTRANGE` signal were identified in profile windows.
- 215 hidden rows, 321 merged ranges, 953 charts, 370 banded ranges, and 6 error cells were identified in profile windows or sheet metadata.
- Apps Script bindings/triggers and Drive sharing/revision metadata remain explicit permission gaps and must not be inferred through DOM scraping or export snapshots.

This stage does not assign final document semantics. It produces parser-facing evidence for the next Google Sheets stages: view-state profile, formula/dataflow profile, and document block candidate generation.

### 15.31 Google Sheets Live View-State / Formula Dependency Profile

The Google Sheets live view-state / formula dependency profile separates parser-facing view-state risk from formula dependency candidates before block and region generation.

Current implementation:

- `scripts/google_sheets_live_view_formula_profile.py` consumes the existing `live-manifest.json`, `top-left-sample.json`, and optional parser-window smoke artifact.
- `schemas/google-sheets-live-view-formula-profile.schema.json` validates the profile artifact.
- `tests/test_google_sheets_live_view_formula_profile.py` covers schema validity, known-sheet dependency edges, repeated signature groups, IMPORTRANGE blockers, and parser-window policy status.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-view-formula-profile.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live View-State / Formula Dependency Profile section.

Current sample result:

- No new Google Sheets live read was performed in this stage.
- Bounded broker grid/value/formula window operations are verified for current policy limits through `parser-window-permission-smoke.json`.
- 52 sheet view-state surfaces were projected; 40 surfaces carry hidden or filtered view-state risk inside the current profile evidence.
- 335 formula observations were projected into 50 signature groups, including 29 repeated signature groups.
- 23 formula dependency edge candidates were generated, including 18 cross-sheet dependency edge candidates.
- 1 `IMPORTRANGE` external dependency was identified at `FC_DATA!A5`; its source argument is `B1`, so source resolution and source spreadsheet allowlisting remain required.

Authority boundaries:

- Formula text is dependency evidence only; formula-result authority remains `not_established`.
- View-state evidence explains visible vs structural parsing differences but does not remove hidden structural data from extraction authority.
- Expanded row/column windows must use broker-backed bounded grid/value/formula operations and stay within policy limits.
- Source spreadsheet reads for `IMPORTRANGE` dependencies remain blocked until source IDs are resolved and allowed by broker policy.
- DOM scraping, export/import, service-account direct sharing, and local credential handling remain disallowed.

The next Google Sheets stage should generate block and 2D region candidates from existing display samples, style/object signals, view-state risks, formula signature groups, dependency edges, and bounded broker reads where needed.

### 15.32 Google Sheets Block / Region Candidate Generation

The Google Sheets block / region candidate generation stage converts profile-window evidence into document-shaped parser seeds.

Current implementation:

- `scripts/google_sheets_live_block_candidates.py` consumes `live-manifest.json`, `top-left-sample.json`, `live-view-formula-profile.json`, and optional parser-window smoke evidence.
- `schemas/google-sheets-live-block-candidates.schema.json` validates the candidate artifact.
- `tests/test_google_sheets_live_block_candidates.py` covers schema validity, table candidates, formula dependency relations, and parser-window policy status.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-block-candidates.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Block / Region Candidates section.

Current sample result:

- 52 sheets were projected into 539 block candidates and 539 cell-region candidates.
- Candidate composition: 107 table candidates, 231 text blocks, 129 section headings, 22 formula-region candidates, 49 object surfaces, and 1 support surface.
- 212 candidate relations were generated, including section-containment and formula-dependency relations.
- 74 bounded read candidates were emitted for later tuning; no expanded live read was performed in this stage.

Authority boundaries:

- Blocks, regions, and relations are candidate seeds only, not accepted document graph claims.
- Candidate generation uses current profile-window evidence and does not claim full-sheet segmentation.
- Bounded read candidates may be executed only through broker-backed parser-window operations within policy limits.
- `IMPORTRANGE` source-spreadsheet reads remain blocked until source IDs are resolved and allowed by broker policy.

The next Google Sheets stage should prioritize a small set of bounded read candidates, execute them through the broker, and use returned value/formula windows to tune candidate boundaries before table I/O pipeline extraction.

### 15.33 Google Sheets Bounded Candidate-Window Sampling

The Google Sheets bounded candidate-window sampling stage executes a small, policy-bounded subset of Stage 34 read candidates through the broker.

Current implementation:

- `scripts/google_sheets_bounded_window_sample.py` prioritizes Stage 34 read candidates and can execute broker-backed `inspect.values_window` and `inspect.formula_window` requests.
- `schemas/google-sheets-bounded-window-sample.schema.json` validates the sampling artifact.
- `tests/test_google_sheets_bounded_window_sample.py` covers schema validity, fake broker execution, URL/error/formula observation extraction, and response summarization.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-bounded-window-sample.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Bounded Candidate-Window Sampling section.

Current sample result:

- 2 broker-backed requests were executed successfully: one values-window request and one formula-window request.
- 6 bounded windows were returned.
- Returned windows contain 1,649 non-empty cells, 68 formula cells, 3 displayed error values, and 2 URL-like source samples.
- `FC_DATA!A1:Z80` values-window returned a Google Sheet URL candidate and displayed `#REF!` values.
- `FC_DATA!A1:Z80` formula-window confirmed 64 formula cells.
- `'25_1110'!A81:Z160` and `'25_1103'!A81:Z160` formula-window samples each confirmed 2 formula cells.

Authority boundaries:

- Broker-backed bounded samples improve candidate tuning evidence but still do not establish formula-result authority.
- Displayed errors are observed states, not final failure diagnoses.
- URL-like source samples can help resolve `IMPORTRANGE` source IDs, but source spreadsheet reads remain blocked until source IDs and broker allowlists are explicitly confirmed.

The next Google Sheets stage should use these returned windows to tune block/region candidate boundaries, candidate confidence, and remaining read queues before table I/O pipeline extraction.

### 15.34 Google Sheets Block / Region Candidate Tuning

The Google Sheets block / region candidate tuning stage converts bounded sample windows into deterministic candidate update actions.

Current implementation:

- `scripts/google_sheets_block_candidate_tuning.py` consumes `live-block-candidates.json` and `live-bounded-window-sample.json`.
- `schemas/google-sheets-block-candidate-tuning.schema.json` validates the tuning artifact.
- `tests/test_google_sheets_block_candidate_tuning.py` covers schema validity, sampled-region extraction, source URL candidates, formula error annotations, and remaining read queue generation.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-block-candidate-tuning.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Block / Region Candidate Tuning section.

Current sample result:

- 41 sampled regions were derived from bounded broker windows.
- 37 candidate tuning actions were generated.
- 21 display-region update actions and 11 formula-surface confirmation actions were generated.
- 2 external source URL candidate actions were generated from bounded samples.
- 3 formula error annotation actions were generated.
- 66 bounded read candidates remain queued for later sampling.

Authority boundaries:

- Tuning actions are candidate updates only and are not accepted document graph claims.
- URL candidates can guide `IMPORTRANGE` source review but do not authorize source spreadsheet reads.
- Displayed error annotations keep formula-result authority unestablished.

The next Google Sheets stage should project tuned candidates and formula dependency evidence into table-level input/output pipeline candidates while carrying source-spreadsheet blockers forward.

### 15.35 Google Sheets Table I/O Pipeline Extraction

The Google Sheets table I/O pipeline extraction stage projects formula dependency edges, tuned block/region evidence, sampled source URL candidates, formula-error annotations, and remaining read queues into table-level input/output pipeline candidates.

Current implementation:

- `scripts/google_sheets_table_io_pipelines.py` consumes `live-block-candidates.json`, `live-view-formula-profile.json`, and `live-block-candidate-tuning.json`.
- `schemas/google-sheets-table-io-pipelines.schema.json` validates the pipeline artifact.
- `tests/test_google_sheets_table_io_pipelines.py` covers schema validity, cross-sheet report pipelines, external `IMPORTRANGE` blockers, sampled source URL propagation, formula-error flags, and Mermaid graph generation.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-table-io-pipelines.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Table I/O Pipelines section and Mermaid review graph.

Current sample result:

- 23 table I/O pipeline candidates were projected.
- 18 report pipelines project weekly sheets using `FC_DATA` as a sampled input surface.
- 1 source-ingestion pipeline projects `FC_DATA!A5` `IMPORTRANGE` as an external source dependency.
- 1 input-staging pipeline projects `FC_DATA` same-sheet formula/data movement.
- 3 calculation pipelines project same-sheet formula families in early period tabs.
- 1 external source candidate spreadsheet ID was extracted from bounded sample evidence: `1CPfJoD6VlChrev00xmagW6qJ2x7eNoJnlQeKe9AMYrs`.
- 3 review queue items remain: external source authority, displayed formula errors, and 66 unsampled bounded read candidates.

Authority boundaries:

- Pipeline candidates are not accepted graph claims.
- Formula text establishes dependency candidates only; formula-result authority remains unestablished.
- Displayed `#REF!` or error surfaces are blockers for treating outputs as calculated values.
- The extracted source spreadsheet URL/ID is a candidate only. Source spreadsheet data must not be read until source argument resolution, Google ACL, and broker allowlist are confirmed.
- Remaining bounded read candidates mean pipeline coverage is partial.

The next Google Sheets stage should convert these pipeline candidates and blockers into prioritized cross-validation targets and deterministic gate plans.

### 15.36 Google Sheets Cross-Validation Target Planning

The Google Sheets cross-validation target planning stage converts pipeline candidates, formula-error evidence, external-source blockers, and remaining bounded-read queues into validation targets and deterministic gate plans.

Current implementation:

- `scripts/google_sheets_cross_validation_plan.py` consumes `live-table-io-pipelines.json` and `live-block-candidate-tuning.json`.
- `schemas/google-sheets-cross-validation-plan.schema.json` validates the validation-plan artifact.
- `tests/test_google_sheets_cross_validation_plan.py` covers schema validity, blocked external-source gates, blocked formula-error gates, planned bounded broker batches, and no unauthorized source reads.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-cross-validation-plan.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Cross-Validation Plan section.

Current sample result:

- 26 validation targets were generated.
- 23 targets correspond to table I/O pipeline flows.
- 1 target blocks external `IMPORTRANGE` source authority.
- 1 target blocks formula-error surface reconciliation.
- 1 target plans remaining current-workbook bounded sampling.
- 65 deterministic gates were planned: 43 planned gates and 22 blocked gates.
- 2 broker batches were planned for later execution, with 16 current-workbook bounded ranges total.
- 0 unauthorized source reads were planned.

Authority boundaries:

- This stage performs no new live reads.
- Planned broker batches may include only current-workbook bounded parser windows.
- Source spreadsheet reads remain blocked until source argument resolution, Google ACL, and broker allowlist are available.
- Formula-error reconciliation gates remain blocked until formula/result authority gaps are resolved.

The next Google Sheets stage should execute only the planned current-workbook broker-bounded batches and summarize returned evidence. It must not read the external `IMPORTRANGE` source spreadsheet.

### 15.37 Google Sheets Planned Bounded Validation Batch Execution

The Google Sheets planned bounded validation batch execution stage executes only the current-workbook broker batches planned by Stage 38 and summarizes returned evidence for deterministic gate execution.

Current implementation:

- `scripts/google_sheets_validation_batch_execution.py` consumes `live-cross-validation-plan.json` and executes planned broker batches when `--execute` is set.
- `schemas/google-sheets-validation-batch-execution.schema.json` validates the execution artifact.
- `tests/test_google_sheets_validation_batch_execution.py` covers fake-broker execution, window summary generation, evidence updates, formula/error observations, and zero source-spreadsheet reads.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-validation-batch-execution.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Validation Batch Execution section.

Current sample result:

- 2 current-workbook broker requests were executed successfully.
- 16 bounded windows were returned.
- Returned windows contain 4,546 non-empty cells.
- Formula windows confirmed 14 formula cells in planned validation ranges.
- The execution emitted 22 candidate evidence updates.
- No displayed errors were returned in this validation batch.
- Source spreadsheet reads performed: 0.

Authority boundaries:

- This stage executes current-workbook bounded parser-window reads only.
- Returned formula text improves formula dependency evidence but does not establish formula-result authority.
- External `IMPORTRANGE` source spreadsheet reads remain blocked.
- Evidence updates are candidate evidence for gates, not accepted document graph claims.

The next Google Sheets stage should evaluate deterministic gates using the validation-batch evidence, table I/O candidates, tuning evidence, and explicit source/formula-result blockers.

### 15.38 Google Sheets Deterministic Gate Execution

The Google Sheets deterministic gate execution stage evaluates planned gates using validation-batch evidence, tuning evidence, table I/O candidates, and explicit authority blockers.

Current implementation:

- `scripts/google_sheets_gate_execution.py` consumes `live-cross-validation-plan.json`, `live-validation-batch-execution.json`, `live-table-io-pipelines.json`, and `live-block-candidate-tuning.json`.
- `schemas/google-sheets-gate-execution.schema.json` validates the gate execution artifact.
- `tests/test_google_sheets_gate_execution.py` covers accepted, blocked, and review-required deterministic gate outcomes.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-gate-execution.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Gate Execution section.

Current sample result:

- 65 deterministic gate results were generated.
- 43 gates were accepted.
- 22 gates remain blocked.
- 0 gates require additional review under the current deterministic executor.
- 26 target results were generated.
- 4 targets were accepted.
- 22 targets remain blocked.

Authority boundaries:

- Accepted gates are evidence checks only and are not graph-promotion decisions.
- Formula-result authority remains unestablished.
- External source authority remains blocked until source argument resolution, Google ACL, and broker allowlist are available.
- Formula-error reconciliation remains blocked for affected `FC_DATA`-dependent pipelines.

The next Google Sheets stage should assemble a connected-Sheets evidence package that promotes only accepted deterministic evidence into the package body while carrying blocked target/gate results as review queues.

### 15.39 Google Sheets Evidence Package Assembly

The Google Sheets evidence package assembly stage bundles accepted deterministic evidence, workbook facts, candidate structures, validation-batch evidence, blocked evidence, review queues, and lineage references into a connected-Sheets parser input authority package.

Current implementation:

- `scripts/google_sheets_evidence_package.py` consumes live manifest, block candidates, table I/O pipelines, cross-validation plan, validation batch execution, and gate execution artifacts.
- `schemas/google-sheets-evidence-package.schema.json` validates the evidence package artifact.
- `tests/test_google_sheets_evidence_package.py` covers accepted body assembly, review queue separation, and zero source-spreadsheet read propagation.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-evidence-package.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Evidence Package section.

Current sample result:

- 52 sheets are represented in workbook facts.
- 40 sheets have view-state risk surfaces.
- 539 candidate blocks and 539 candidate regions are represented.
- 43 accepted gates and 4 accepted targets are carried into accepted evidence.
- 3 accepted calculation pipelines are carried into accepted evidence.
- 22 blocked gates and 22 blocked targets remain outside the accepted body.
- 5 review queue items remain.
- Source spreadsheet reads performed: 0.

Authority boundaries:

- The evidence package is not graph promotion.
- Accepted evidence is limited to accepted deterministic gate/target/pipeline evidence.
- Blocked source authority, formula-error, and remaining coverage gaps remain in the review queue.
- Formula-result authority remains unestablished.

The next Google Sheets stage should map this connected-Sheets evidence package into the document-structure ontology without generating semantic ontology concepts.

### 15.40 Google Sheets Document Ontology Mapping

The Google Sheets document ontology mapping stage deterministically maps the connected-Sheets evidence package into document-structure ontology nodes, relations, statuses, and review items.

Current implementation:

- `scripts/google_sheets_document_ontology_mapping.py` consumes `live-evidence-package.json`.
- `schemas/google-sheets-document-ontology-mapping.schema.json` validates the mapping artifact.
- `tests/test_google_sheets_document_ontology_mapping.py` covers document-structure-only mapping, review queue node preservation, and 0 semantic concepts.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-document-ontology-mapping.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Document Ontology Mapping section.

Current sample result:

- 10 ontology nodes were generated.
- 5 nodes are accepted.
- 5 nodes are review-required.
- 9 ontology relations were generated.
- 4 relations are accepted.
- 5 relations are review-required.
- 5 review items are carried forward.
- Semantic concept count: 0.

Authority boundaries:

- This stage uses the document-structure ontology only.
- It does not generate semantic ontology concepts.
- Review queue items remain review-required nodes and relations.
- Formula-result and external-source authority remain unresolved.

The next Google Sheets stage should convert ontology statuses and review reasons into actionable contracts.

### 15.41 Google Sheets Action Contract Layer

The Google Sheets action contract layer converts review-required ontology items into owner, action, required evidence, deterministic gate, completion condition, and completion effect contracts.

Current implementation:

- `scripts/google_sheets_action_contracts.py` consumes `live-document-ontology-mapping.json`.
- `schemas/google-sheets-action-contracts.schema.json` validates the action contract artifact.
- `tests/test_google_sheets_action_contracts.py` covers owner/action/gate mapping for source authority and formula-error review items.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-action-contracts.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Action Contracts section.

Current sample result:

- 5 action contracts were generated.
- 5 contracts remain open.
- 4 contracts are high priority.
- 1 contract is medium priority.
- 2 contracts route to sheet owner or broker/source authority owners.
- 2 contracts route to parser operator.
- Semantic concept count: 0.

Authority boundaries:

- This stage creates action contracts only.
- It does not add graph claims.
- It does not generate semantic ontology concepts.
- Completion effects describe what may be re-run or refreshed after evidence is available; they do not auto-close blockers.

The next Google Sheets stage should separate domain source evidence into general-domain, local-boundary, and unavailable source layers before semantic ontology proposals.

### 15.42 Google Sheets Domain Knowledge Source Model

The Google Sheets domain knowledge source model separates general-domain references, local-boundary evidence, unavailable sources, and semantic readiness before semantic proposal generation.

Current implementation:

- `scripts/google_sheets_domain_source_model.py` consumes `live-action-contracts.json` and `live-evidence-package.json`.
- `schemas/google-sheets-domain-source-model.schema.json` validates the domain source model artifact.
- `tests/test_google_sheets_domain_source_model.py` covers general/local/unavailable source separation and shared-promotion blockers.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-domain-source-model.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Domain Source Model section.

Current sample result:

- The current connected-Sheets artifact still shows 8 `accounting-kr` references, but this is a stale classification and must be removed on rerun.
- Local boundary is not confirmed.
- 2 unavailable source authorities remain: external `IMPORTRANGE` source and formula-result authority.
- Semantic proposal generation is not performed in this stage.
- Shared ontology promotion is blocked.

Authority boundaries:

- General-domain sources are references, not workbook truth.
- Local-domain candidates must remain boundary-scoped until boundary and local evidence are confirmed.
- Source spreadsheet and formula-result authority are unavailable.
- Shared ontology promotion remains blocked.

The next Google Sheets stage may validate proposal-only semantic candidates from accepted document evidence and domain references, but must keep shared promotion blocked until source, boundary, repeated-evidence, and formula-result authorities are available.

### 15.43 Google Sheets Semantic Proposal Generation

The Google Sheets semantic proposal generation stage creates evidence-bounded semantic concept and relation proposals from accepted document ontology evidence, accepted pipeline evidence, and domain source readiness.

Current implementation:

- `scripts/google_sheets_semantic_proposals.py` consumes `live-domain-source-model.json`, `live-evidence-package.json`, and `live-document-ontology-mapping.json`.
- `schemas/google-sheets-semantic-proposals.schema.json` validates the semantic proposal artifact.
- `tests/test_google_sheets_semantic_proposals.py` covers proposal-only status, document-mapping evidence refs, blocker propagation, and zero shared ontology updates.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-semantic-proposals.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Semantic Proposals section.

Current sample result:

- 3 semantic concept proposals were generated.
- 2 semantic relation proposals were generated.
- 6 validation-plan items were generated for the next deterministic validation stage.
- 0 semantic concepts were accepted.
- 0 shared ontology updates were emitted.

Authority boundaries:

- Proposals are not accepted graph truth.
- The local-domain period-tab calculation surface remains blocked by missing local boundary confirmation and source authority.
- General K-IFRS/revenue-recognition references are not applicable to this connected-Sheets document unless a separate reviewer-approved accounting output surface is identified.
- Source authority and formula-result authority remain unavailable.
- Shared ontology promotion remains blocked.

The next Google Sheets stage should assemble a validated connected-Sheets graph from accepted document-structure evidence while carrying blocked semantic validation items as review queue entries.

### 15.44 Google Sheets Deterministic Validation of Semantic Proposals

The Google Sheets semantic proposal validation stage deterministically validates proposal-only semantic concepts and relations before any graph assembly.

Current implementation:

- `scripts/google_sheets_semantic_proposal_validation.py` consumes `live-semantic-proposals.json`, `live-domain-source-model.json`, `live-evidence-package.json`, and `live-document-ontology-mapping.json`.
- `schemas/google-sheets-semantic-proposal-validation.schema.json` validates the semantic proposal validation artifact.
- `tests/test_google_sheets_semantic_proposal_validation.py` covers blocked proposal outcomes when local boundary, source authority, and formula-result authority are missing.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-semantic-proposal-validation.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Semantic Proposal Validation section.

Current sample result:

- 5 proposal results were produced: 3 semantic concept results and 2 semantic relation results.
- 0 proposal results were accepted.
- 5 proposal results remain blocked.
- 1 shared-promotion gate result remains blocked.
- 0 semantic concepts were accepted.
- 0 shared ontology updates were emitted.

Authority boundaries:

- Validation results are gate outcomes, not graph assembly.
- Blocked semantic proposals must remain review queue items until local boundary, source authority, formula-result authority, and human promotion approval are available.
- General-domain references can pass source availability checks while the workbook-level semantic claim remains blocked.
- Shared ontology promotion remains blocked and emits no updates.

The next Google Sheets stage should project reviewer-facing data views from accepted graph nodes only, without recalculating formulas or promoting blocked semantic items.

### 15.45 Google Sheets Validated Graph Assembly

The Google Sheets validated graph assembly stage promotes only accepted document-structure ontology nodes and accepted document relations into the graph body.

Current implementation:

- `scripts/google_sheets_validated_document_graph.py` consumes `live-document-ontology-mapping.json`, `live-evidence-package.json`, `live-action-contracts.json`, and `live-semantic-proposal-validation.json`.
- `schemas/google-sheets-validated-document-graph.schema.json` validates the graph artifact.
- `tests/test_google_sheets_validated_document_graph.py` covers accepted document node assembly and blocked semantic carry-forward behavior.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-validated-document-graph.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Validated Document Graph section.

Current sample result:

- 5 accepted document graph nodes were assembled.
- 4 accepted document relations were assembled.
- 0 semantic graph nodes were assembled.
- 0 semantic graph relations were assembled.
- 5 document review items remain carried forward.
- 6 semantic validation review items remain carried forward.
- 0 shared ontology updates were emitted.

Authority boundaries:

- The graph body is accepted document structure only.
- Blocked semantic validation results remain carry-forward review items.
- Data views remain a projection to be generated in a later stage.
- Formula-result authority remains unavailable.

The next Google Sheets stage should generate boundary-scoped local semantic candidate records from projected views and blocked semantic validation evidence while keeping promotion blocked.

### 15.46 Google Sheets Data View Projection

The Google Sheets data view projection stage turns accepted graph nodes into reviewer-facing read-model projections.

Current implementation:

- `scripts/google_sheets_data_view_projection.py` consumes `live-validated-document-graph.json`, `live-evidence-package.json`, and `top-left-sample.json`.
- `schemas/google-sheets-data-view-projection.schema.json` validates the projection artifact.
- `tests/test_google_sheets_data_view_projection.py` covers pipeline preview generation and formula-result authority warnings.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-data-view-projection.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Data View Projection section.

Current sample result:

- 5 data view projections were generated.
- 3 projections are calculation pipeline projections.
- 2 projections are document summary projections.
- 3 projections have top-left sample previews.
- 3 projections carry formula-text-only warnings.
- 5 document review items and 6 semantic review items remain carried forward.
- 0 shared ontology updates were emitted.

Authority boundaries:

- Projection is a read model over accepted graph nodes.
- Formula text and displayed sample values are evidence only, not recalculated formula-result authority.
- Semantic review queues are preserved and not resolved.
- Shared ontology promotion remains blocked.

The next Google Sheets stage should review local semantic candidates against shared-promotion prerequisites and emit a blocker-focused human review packet with 0 shared ontology updates.

### 15.47 Google Sheets Local Semantic Ontology Candidate Generation

The Google Sheets local semantic candidate stage creates boundary-scoped local candidate records from projected calculation surfaces and semantic validation blockers.

Current implementation:

- `scripts/google_sheets_local_semantic_candidates.py` consumes `live-data-view-projection.json`, `live-semantic-proposal-validation.json`, and `live-domain-source-model.json`.
- `schemas/google-sheets-local-semantic-candidates.schema.json` validates the local semantic candidate artifact.
- `tests/test_google_sheets_local_semantic_candidates.py` covers blocked boundary-scoped candidates and candidate relations.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-local-semantic-candidates.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Local Semantic Candidates section.

Current sample result:

- 3 local semantic candidates were generated.
- 0 local semantic candidates were accepted.
- 3 local semantic candidates remain blocked.
- 2 candidate relations were generated.
- 2 candidate relations remain blocked.
- 5 review queue items were generated.
- 0 shared ontology updates were emitted.

Authority boundaries:

- Local semantic candidates are boundary-scoped records only.
- Local boundary is not confirmed.
- Source and formula-result authorities remain unavailable.
- Candidates must not become shared ontology updates until promotion prerequisites are satisfied.

The next Google Sheets stage should review the connected-Sheets iteration itself and decide which pipeline stages should remain, merge, reorder, or require permission/process changes.

### 15.48 Google Sheets Shared Ontology Alignment / Human Review

The Google Sheets shared ontology alignment review stage evaluates local semantic candidates against shared-promotion prerequisites and produces a human review packet.

Current implementation:

- `scripts/google_sheets_shared_ontology_alignment_review.py` consumes `live-local-semantic-candidates.json`, `live-data-view-projection.json`, and `live-domain-source-model.json`.
- `schemas/google-sheets-shared-ontology-alignment-review.schema.json` validates the shared alignment review artifact.
- `tests/test_google_sheets_shared_ontology_alignment_review.py` covers blocked shared promotion and 0 shared ontology updates.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-shared-ontology-alignment-review.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Shared Ontology Alignment Review section.

Current sample result:

- 3 alignment items were reviewed.
- 3 alignment items remain blocked.
- 0 alignment items were promoted.
- 5 review questions were generated.
- 0 shared ontology updates were emitted.

Authority boundaries:

- This stage is review-only.
- Shared ontology writes are not performed.
- Promotion remains blocked by local boundary, source authority, repeated evidence, formula-result authority, and human approval gaps.

The connected-Sheets iteration is complete through process redesign review. The next practical work is recording blocker-resolution evidence and then rerunning authority-aware stages instead of mutating prior semantic artifacts in place.

### 15.49 Google Sheets Process Redesign Review

The Google Sheets process redesign review stage evaluates the connected-Sheets iteration itself.

Current implementation:

- `scripts/google_sheets_process_redesign_review.py` consumes the live inspection directory, process ledger, active tasklist, and design baseline.
- `schemas/google-sheets-process-redesign-review.schema.json` validates the redesign review artifact.
- `tests/test_google_sheets_process_redesign_review.py` covers process-review authority boundaries and summary counts.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-process-redesign-review.json` is the current sample artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Process Redesign Review section.

Current sample result:

- 25 JSON artifacts are present in the live inspection package.
- 21 Google Sheets process ledger entries are present.
- 6 stage groups were reviewed.
- 5 redesign decisions were recorded.
- 6 open evidence gaps were recorded.
- 0 shared ontology updates were emitted.

Process redesign decisions:

- Move external source authority resolution earlier when `IMPORTRANGE` blockers appear.
- Add a dedicated formula-result authority checkpoint before semantic acceptance.
- Keep data view projection before shared alignment review.
- Treat broker policy and Google ACL requirements as process inputs.
- Run HTML layout/overflow checks for dense review sections before reviewer handoff.

### 15.50 Google Sheets Blocker Resolution Update

The blocker resolution update records reviewer-provided decisions and broker source-smoke evidence after the process redesign review. It is a control artifact for the next rerun, not a silent mutation of prior semantic or shared-alignment outputs.

Current implementation:

- `scripts/google_sheets_blocker_resolution_update.py` reads the FC_DATA source broker smoke artifacts and writes `live-blocker-resolution-update.json`.
- `schemas/google-sheets-blocker-resolution-update.schema.json` validates the update artifact.
- `tests/test_google_sheets_blocker_resolution_update.py` covers resolved source/boundary/reporting-basis status, open formula-result authority, version breakpoint candidates, and 0 shared ontology updates.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-blocker-resolution-update.json` is the current update artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Blocker Resolution Update section.

Current update result:

- Direct FC_DATA source authority is resolved for the user-provided source spreadsheet `1CPfJoD6VlChrev00xmagW6qJ2x7eNoJnlQeKe9AMYrs`.
- Broker metadata, values-window, and formula-window smoke all passed for the source spreadsheet.
- The source workbook title is `[Day 1] 1.0 (from 20241216)`.
- The source has 90 tabs, including 3 hidden tabs, and `FC_DATA` is present as sheet ID `1221520043`.
- `FC_DATA!A5` contains `=IMPORTRANGE(B1,"지표!T4:AH175")`; full raw lineage still needs a nested source authority follow-up if required.
- Formula-result authority remains open and requires targeted range-level validation.
- Local boundary is resolved by user as `전사레벨 현황 보고 문서`.
- Repeated workbook-family evidence is partially resolved: all period tabs are repeated documents, but format updates and organization/department restructuring require version breakpoint detection.
- Reporting basis is resolved by user as cash-basis payment/status reporting, not K-IFRS or K-GAAP revenue.
- 18 preliminary version groups and 17 version breakpoint candidates were detected from adjacent period-tab column-count changes.
- 0 shared ontology updates were emitted.

Authority boundaries:

- This update does not accept semantic concepts, graph nodes, or shared ontology updates by itself.
- Prior Stage 42-50 artifacts remain snapshots of the earlier blocker state until regenerated.
- K-IFRS/K-GAAP accounting references should be excluded from this connected-Sheets semantic rerun. This document's operative basis is cash-basis payment/status reporting.
- Formula text and displayed values are not formula-result authority.
- Version grouping by column count is preliminary; the next stage must also check header bands, formula signatures, and organization/department labels.

The next Google Sheets stage should run the formula-result authority checkpoint, then version breakpoint detection, and then regenerate the authority-aware domain/semantic/shared-alignment artifacts using this update as input.

### 15.51 Google Sheets Formula-Result Authority Checkpoint

The formula-result authority checkpoint uses broker-backed Google Sheets `grid_formula_v1` probes to distinguish formula text from formula results. For connected Google Sheets, the accepted formula-result authority is the Google Sheets API grid `effective_value` for a probed range, not exported Excel recalculation.

Current implementation:

- `scripts/google_sheets_formula_result_authority_checkpoint.py` reads current/source grid probes, table I/O pipelines, data view projections, and blocker resolution evidence.
- `schemas/google-sheets-formula-result-authority-checkpoint.schema.json` validates the checkpoint artifact.
- `tests/test_google_sheets_formula_result_authority_checkpoint.py` covers accepted clean effective-value ranges, blocked error ranges, and 0 shared ontology updates.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/formula-result-grid-current-probes.json` stores current-workbook `grid_formula_v1` probes.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/source-fc-data-grid-formula-window.json` stores source-workbook `FC_DATA!A1:Z80` `grid_formula_v1` probe.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-formula-result-authority-checkpoint.json` is the current checkpoint artifact.
- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/index.html` is regenerated with a Live Formula Result Authority Checkpoint section.

Current checkpoint result:

- 5 range-level formula-result authority results were generated.
- 3 current-workbook calculation ranges were accepted: `24_0102!B8:T67`, `24_0108!B8:M56`, and `24_0115!B8:M57`.
- These 3 accepted ranges contain 232 formula cells with Google Sheets effective values and 0 formula/effective errors.
- Current workbook `FC_DATA!A1:Z80` is blocked: 64 formula cells were observed, with 3 formula/effective error cells.
- Source workbook `FC_DATA!A1:Z80` is blocked: 64 formula cells were observed, with 17 effective errors and 2 formula error cells.
- 23 pipeline authority results were generated.
- 3 same-sheet calculation pipelines were accepted.
- 20 FC_DATA-dependent input/report/source-ingestion pipelines remain blocked by formula-error reconciliation, missing output probes, or nested/external lineage follow-up.
- The reporting-basis gate is accepted as cash-basis payment/status reporting.
- 0 shared ontology updates were emitted.

Authority boundaries:

- Accepted formula-result authority is range-level only. It does not accept semantic concepts, reporting-basis mappings beyond the user decision, graph nodes, or shared ontology updates.
- Effective values from `grid_formula_v1` are the Google Sheets calculation authority for connected Sheets, but only for the probed ranges.
- Formula text remains dependency evidence. It is not result authority by itself.
- FC_DATA-dependent report pipelines remain blocked until FC_DATA effective errors are reconciled and report outputs are probed or otherwise justified.
- Source FC_DATA and current FC_DATA can differ; both must be tracked as separate authority surfaces.

The next Google Sheets stage should first validate document item grouping and hierarchy before semantic reruns. Version breakpoint detection should then check repeated period tabs using column counts as a seed plus header bands, formula signatures, organization/department label changes, and grouping-layout drift.

## 15.52 Google Sheets Document Item Grouping / Hierarchy Checkpoint

This stage validates whether sheet content is grouped into the same document items a human reviewer would perceive: explanatory text with the table it describes, chart/image/object surfaces with the table or section they belong to, formula regions with their visible output panel, and adjacent tables that should remain separate.

Inputs:

- `live-block-candidates.json`
- `live-block-candidate-tuning.json`
- `live-table-io-pipelines.json`
- `live-formula-result-authority-checkpoint.json`
- `live-manifest.json`
- `live-view-formula-profile.json`
- bounded validation-batch evidence when available

Planned output:

- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-document-item-grouping-checkpoint.json`

The output should contain:

- `document_items`: grouped units with sheet, bounds, member block IDs, member surface types, structural role hints, evidence scores, status, and review reasons.
- `document_item_relations`: relations such as `contains`, `caption_of`, `explains`, `visual_group`, `formula_feeds`, `same_report_panel`, and `separate_from`.
- `grouping_gate_results`: deterministic evidence checks for each accepted, review-required, or rejected grouping.
- `orphan_surfaces`: tables, text blocks, charts/images/objects, or formula regions that cannot yet be confidently grouped.

Deterministic gates:

- Spatial gate: checks containment, proximity, whitespace, row/column band boundaries, and two-dimensional separation.
- Text gate: checks headings, captions, comments, explanatory bullet blocks, and repeated labels.
- Visual/style gate: checks merge ranges, borders, fills, banded ranges, alignment, object anchors, and chart/image/object proximity.
- Formula/dataflow gate: checks formula dependencies, pivot/source references, external lineage, and accepted formula-result authority where available.
- Conflict gate: prevents merging adjacent surfaces with incompatible headers, formula signatures, source authority, pivot/cache source, or repeated-layout evidence.
- Review gate: keeps low-evidence or conflicting groupings as review-required rather than forcing a semantic interpretation.

Authority boundaries:

- This stage is structural grouping only. It must not assign business semantics, local-domain truth, shared ontology concepts, or reporting-basis interpretations.
- Physical adjacency is evidence, not authority.
- Semantic storage and semantic ontology generation may consume accepted or review-required grouping evidence, but they must not repair or invent grouping by themselves.

Current connected-Sheets result:

- `scripts/google_sheets_document_item_grouping_checkpoint.py` generated `live-document-item-grouping-checkpoint.json`.
- 129 document items were generated.
- 3 formula/dataflow-backed document item groups were accepted.
- 126 document item groups remain review-required.
- 49 object surfaces remain orphan/review-required because chart/image/object anchors are coarse profile-window evidence only.
- 0 shared ontology updates were emitted.

## 15.53 Google Sheets Version Breakpoint Detection

Version detection separates repeated period tabs into structural workbook-family versions before repeated evidence is used for semantic promotion.

Inputs:

- `live-manifest.json`
- `live-block-candidates.json`
- `live-view-formula-profile.json`
- `live-blocker-resolution-update.json`
- `live-document-item-grouping-checkpoint.json`

Output:

- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-version-breakpoint-detection.json`

The stage uses column count as a seed and then attaches block, formula-signature, and document-grouping drift. Column count alone can produce a review-required breakpoint; accepted breakpoints require stronger multi-signal drift.

Current connected-Sheets result:

- 18 version groups were generated.
- 16 version groups were accepted.
- 2 version groups remain review-required because intra-group drift remains.
- 17 version breakpoints were generated.
- 2 version breakpoints were accepted with stronger structural drift.
- 15 version breakpoints remain review-required because evidence is mostly column-count based.
- 0 shared ontology updates were emitted.

## 15.54 Semantic / Gate Iteration And Metric Equivalence

Semantic interpretation and deterministic gates must run as an alternating loop, not as a single proposal followed by one final validation pass.

Loop shape:

1. Semantic proposal: proposes labels, candidate parent concepts, scoped variants, aliases, and possible equivalence groups from accepted document-item groupings and pipeline evidence.
2. Gate execution: checks whether proposed concepts can be accepted, must be split, must be merged under a shared parent, or must remain review-required.
3. Semantic refinement: rewrites the proposal using gate outcomes without losing source evidence.
4. Repeat until no accepted/split/merge decision changes, or until unresolved items are explicitly carried as review-required.

For repeated labels such as `결제액`, the system must not assume identity from label similarity. It should compare these dimensions before treating two surfaces as the same metric:

- reporting basis: cash-basis payment/status reporting, accounting revenue, target, forecast, or another basis
- amount treatment: gross amount, net amount, refund-adjusted amount, cancellation-adjusted amount, tax-inclusive/exclusive amount
- time axis: payment date, service period, report cutoff date, weekly tab period, monthly period, cumulative period
- filters: department, product, project, status, channel, cohort, refund/cancel status, hidden/filter state
- aggregation: row-level value, subtotal, pivot output, chart series, formula result, manually entered summary
- source lineage: current workbook range, FC_DATA, source FC_DATA, nested IMPORTRANGE, external workbook, pivot/cache source
- transformation role: raw input, staging input, calculated intermediate, report output, commentary evidence
- formula/result authority: formula text, effective value, accepted formula-result range, blocked error range, or unprobed output

Gate outcomes:

- `same_metric`: dimensions match or a deterministic mapping proves equivalence.
- `scoped_variant`: the parent label is shared, but one or more dimensions differ and must be stored as a qualified child concept.
- `different_metric`: the label is similar but basis, source, filter, aggregation, or formula lineage conflicts.
- `review_required`: evidence is insufficient, stale, blocked, or contradictory.

Storage rule:

- Store the broad label such as `결제액` only as a parent or alias unless gates prove a fully equivalent metric.
- Store qualified variants such as `cash_basis_payment_amount_by_week`, `refund_adjusted_payment_amount`, or `fc_data_source_payment_amount` as separate local candidates when dimensions differ.
- Shared ontology promotion may use the parent concept, but local-domain variants must keep their boundary and evidence.

Current connected-Sheets result:

- `scripts/google_sheets_semantic_gate_iteration.py` generated `live-semantic-gate-iteration.json`.
- `accounting-kr` is excluded; selected general-domain source count is 0.
- Local boundary is confirmed as 전사레벨 현황 보고 문서.
- Reporting basis is confirmed as cash-basis 결제액 기반 운영 현황, not K-IFRS/K-GAAP revenue reporting.
- 5 semantic candidates were generated: 2 accepted, 2 review-required, and 1 blocked.
- 8 semantic gates were generated: 4 accepted, 2 review-required, and 2 blocked.
- 3 metric-equivalence checks were generated for visible 결제/매출/순매출 label buckets.
- 0 shared ontology updates were emitted.

## 15.55 Google Sheets Carry-forward Review Packet

The carry-forward review packet groups unresolved queues into reviewer decision lanes. It is a review surface only and must not create parser truth, semantic acceptance, or shared ontology updates.

Inputs:

- `live-document-item-grouping-checkpoint.json`
- `live-version-breakpoint-detection.json`
- `live-formula-result-authority-checkpoint.json`
- `live-semantic-gate-iteration.json`

Output:

- `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/live-carry-forward-review-packet.json`

Current connected-Sheets result:

- 4 review lanes were generated: document item grouping, formula result authority, metric equivalence, and version breakpoints.
- 10 decision items were generated.
- 7 decision items are high priority.
- 352 raw evidence items are folded into reviewer-facing decision items with sample evidence.
- Suggested review order is formula authority, document item grouping, metric equivalence, then version breakpoints.
- 0 parser truth claims and 0 shared ontology updates were emitted.

## 15.56 Onto MCP Reconstruct Attempt

`onto-mcp` reconstruct can be used as an external ontology-seeding path only when the input packet exposes accepted claims, review-required queues, blocked claims, and forbidden promotions within the source observation boundary.

Current connected-Sheets attempt:

- Reconstruct source packets were prepared from the current evidence package, domain source model, document item grouping checkpoint, formula-result authority checkpoint, version breakpoint detection, semantic/gate iteration, and carry-forward review packet.
- `onto.observe_source` and `onto.reconstruct` were available in the session.
- The run intentionally omitted a domain pack. `accounting-kr`, K-IFRS, K-GAAP active semantics, label-only metric merging, shared ontology promotion, and shared ontology writes were explicitly forbidden.
- Large JSON source packets were not suitable because current `onto-mcp` source observation exposes bounded excerpts rather than full JSON claim depth.
- The useful reconstruct input shape is a micro packet that fits the current prompt excerpt limit and states only accepted truth, blocked truth, review queues, ontology shape, and forbidden claims.
- Direct-call reconstruct initially did not produce an accepted `ontology-seed.yaml`. The original `invalid_grant` came from stale global `miro-mcp` OAuth loaded by child `codex exec`, not from Codex ChatGPT OAuth itself.
- A temporary isolated `CODEX_HOME` with only Codex auth removed the `invalid_grant` warning and confirmed direct-call auth is usable without mutating global MCP config.
- The isolated retry reused authored artifacts, kept `invalid_grant` absent, regenerated valid candidate disposition output, and then timed out in the ontology-seed stage after `ONTO_LLM_TIMEOUT_MS=360000`.
- Earlier partial reconstruct artifacts are evidence of integration behavior only. They are not accepted parser truth, semantic ontology truth, or shared ontology updates.
- A 951-byte micro code packet allowed `onto.reconstruct` to reach valid candidate disposition generation. The resulting `candidate-disposition-validation.yaml` is valid.
- A manual `manual-ontology-seed.yaml` draft was generated from the same micro observation and validated with the active `onto-mcp` runtime seed validator. `manual-ontology-seed-validation.yaml` is valid with 0 violations.
- The manual seed draft remains a validated draft artifact, not official direct reconstruct output. It must not be treated as an accepted `ontology-seed.yaml` from `onto.reconstruct`.
- A seed-min source packet (`onto-reconstruct-seed-min-source-packet.json`, 802 bytes) removed the long shape list and kept only minimal seed authority: local document, calculation surfaces, review queues, reporting basis, formula authority status, validation queues, and local-only policies.
- The seed-min run reduced auto candidate inventory from 52 to 33 and promoted candidates from 19 to 6.
- Rerunning direct reconstruct with `ONTO_LLM_TIMEOUT_MS=480000` produced the official direct reconstruct `ontology-seed.yaml`.
- `ontology-seed-validation.yaml` is valid with 0 violations. Candidate disposition, claim realization, seed confirmation, competency questions, competency assessment, failure classification, revision proposal, manifest, handoff, and final-output provenance validations are all valid with 0 violations.
- The official seed is a local seed only. `ontology_handoff.readiness_claim=limited`, `handoff_decision_validation.readiness_projection=not_ready`, and `stop_decision=continue`.
- The seed preserves shared ontology update count 0, excludes `accounting-kr`, and keeps K-IFRS/K-GAAP revenue semantics out of scope.
- Stage 62 reviewed the official seed and generated `onto-seed-maturation-review.json`. The review accepts the seed only as local seed authority and keeps six frontier lanes open: instance binding, relation binding, metric equivalence, review governance, runtime proof, and writeback contract.
- The live HTML viewer now includes an Official Onto Seed Review / Maturation Frontier section so reviewers can see the valid/not-ready boundary, acceptance decisions, frontier questions, and artifact refs without opening the raw YAML.

Process decision:

- Keep `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/onto-reconstruct-micro-source-packet.txt` as the next reconstruct input candidate.
- Prefer `review-packages/sheets-bridge/live-inspections/20260602-day1-1-0/onto-reconstruct-micro-code-source-packet.json` for the next reconstruct input because it stays under the prompt excerpt limit and uses the partially supported code/config source profile.
- Treat `.onto/reconstruct/20260602-sheets-local-actionable-ontology-seed-min/ontology-seed.yaml` as the official direct reconstruct seed artifact for this sample.
- Review the seed's maturation frontier before any action/writeback/shared use. Remaining frontier items include live instances not enumerated, structural relation edges missing, metric equivalence unresolved, review actor unspecified, runtime proof artifacts not active, and writeback not action-ready.
- Use `onto-seed-maturation-review.json` as the control artifact for the next maturation loop. The next loop should resolve carry-forward feedback for metric equivalence, FC_DATA authority, document grouping/object/version decisions, review ownership, runtime proof, and explicit writeback denial or writeback contract.
- Keep the older manual seed draft as historical fallback evidence only.

## 16. Shared Ontology Promotion

Local semantic concepts can be promoted to shared ontology concepts only after evidence-based alignment.

Promotion evidence:

- repeated occurrence across original Excel pairs or workbook groups
- similar structural position
- similar surrounding headers, section titles, or explanatory text
- compatible value type and value distribution
- no conflicting usage
- existing shared concept alias match when applicable
- traceable source evidence

Promotion must preserve domain layer. A concept can be promoted as:

- `general_domain`: reusable across organizations in the broad domain.
- `local_domain`: reusable only inside a specific organization, business unit, workbook family, or policy context.
- `mapped_local_to_general`: a local concept mapped to a general concept without becoming identical to it.

The shared ontology should store canonical concepts, aliases, domain layer, applicability scope, source evidence, confidence, review status, and version history.

## 17. Open Design Areas

The following areas need further specification:

- exact JSON schemas for evidence package, proposal, graph, gate result, and final package
- capture strategy for desktop Excel, web Excel, LibreOffice, and headless environments
- tolerance rules for coordinate conversion and visual proximity
- OCR requirements and fallback behavior
- formula recalculation authority by platform
- confidence scoring model
- human review workflow
- shared ontology merge and conflict policy
- general-domain knowledge source format, versioning, and applicability rules
- local-domain knowledge source format, boundary scoping, tenant scoping, and confidentiality rules
- mapping rules between local-domain concepts and general-domain concepts
- replay and cache invalidation policy
- privacy and redaction rules for captured images and source workbook contents
- benchmark corpus design for document-shaped workbooks

## 18. Completion Criteria

The design is implemented successfully when:

- a workbook can be converted into a workbook evidence package
- visual capture, workbook structure, and formula graph are cross-referenced
- document blocks are mapped to the document structure ontology
- LLM proposals are validated through deterministic gates
- accepted results form a validated document graph
- data views are projected from the document graph
- semantic ontology candidates are generated as local candidates
- all results remain traceable to original workbook evidence
- ambiguous or failed claims are preserved in the review queue
