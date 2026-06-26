# Document-Shaped Spreadsheet Understanding Design

## Purpose

This is the active runtime design baseline for understanding non-standard Excel
workbooks and connected spreadsheets.

The parser must treat a spreadsheet as a document, calculation surface, and
review surface at the same time. It should extract evidence-backed claims about
structure, formulas, visual grouping, dataflow, semantic meaning, and unresolved
review questions without mutating the source artifact.

## Current Architecture

Use the evidence-backed claim ledger model as the top-level architecture:

- source observations are evidence records;
- parser, visual, formula, ontology, and LLM outputs enter as candidate claims;
- deterministic gates classify claims as accepted, review-required, blocked,
  contradicted, or rejected;
- document structure, dataflow, ontology, review queues, retrieval packs, and
  action states are projections over evidence and adjudicated claims.

Primary references:

- `docs/evidence-backed-spreadsheet-claim-ledger-design.md`
- `docs/adr/0001-evidence-backed-claim-ledger.md`
- `docs/document-shaped-excel-understanding-tasklist.md`
- `projects/README.md`

## Runtime Contract

The understanding flow must preserve these boundaries:

- The original workbook or connected Sheet remains the source artifact.
- Repeated work must attach to a `projects/` workspace before new claims or
  project-local domain notes are accumulated.
- Hidden, filtered, or revealed views are diagnostic projections unless the user
  explicitly selects them as the source-visible authority.
- Formula text is evidence, not formula-result authority.
- Excel formula-dependent results require real Microsoft Excel-engine
  validation when result values matter.
- Connected Google Sheets evidence must come from an approved external access
  surface. This repository consumes credential-free evidence/results and does
  not own live Google access, direct keys, export/import shortcuts, or raw
  credential handling.
- LLM output is proposal evidence only. It cannot create final truth without
  deterministic gates and provenance.
- Semantic ontology generation must separate reusable general-domain knowledge
  from local-domain knowledge scoped to a declared organization, project, team,
  tenant, or workbook family.
- Repeated labels such as `결제액` must remain scoped variants unless gates prove
  matching basis, period, filters, aggregation, source lineage, transformation
  role, and formula/result authority.

## First-Access Protocol

For a new workbook or connected Sheet:

1. Locate or create the project workspace for the spreadsheet surface or Excel
   workbook family.
2. Separate raw/source truth, processed/intermediate tables, final projections,
   and annotation text.
3. Discover tables by coherent ranges, shared label structure, shared formula
   structure, and visual/layout evidence. A table is not necessarily a sheet.
4. Map table I/O with user-facing names and spreadsheet ranges.
5. Classify labels as raw input, processed output, final output, annotation, or
   review-required.
6. Show formula/source chains for processed labels where evidence allows.
7. Ask targeted questions for unclear meanings, metric basis, scope, or lineage.
8. Publish an HTML review package with an executive summary, SVG flow, sortable
   tables, label dictionary, gate results, and unresolved questions.

## Active Branches

- Formula/dataflow discovery:
  `docs/sheets-formula-dataflow-discovery-design.md`
- Data-processing spreadsheet analysis package:
  `docs/data-processing-spreadsheet-package-design.md`
- Existing Excel/spreadsheet CRUD rules:
  `references/spreadsheet-principles.md`,
  `references/excel-workbook-principles.md`,
  `references/spreadsheet-review-package.md`,
  `references/connected-google-sheets-principles.md`
