# Data-Processing Spreadsheet Analysis Package Design

## Purpose

This design packages the data-processing analysis approach that proved useful
during the connected Google Sheets tests, while preserving the existing
Excel/spreadsheet editing principles in this repository.

- understand data-processing-centered spreadsheets;
- separate source truth, processed tables, result projections, and annotation
  text;
- trace formula-backed table I/O;
- answer business questions through deterministic calculations plus
  domain-scoped semantic rules;
- publish reviewer-friendly HTML with SVG flows and sortable tables.

This is an added capability layer, not a fixed product boundary. The first
packaged workflow focuses on formula/dataflow-heavy spreadsheets because that
path has current evidence, but the repository should continue expanding across
Excel workbooks, connected Google Sheets, document-shaped spreadsheets, visual
layouts, ontology workflows, and future write/refactoring workflows.

## Existing Authority Must Remain

The existing spreadsheet and Excel CRUD guidance remains the base contract. This
package must include and comply with these references instead of replacing them:

| Reference | Applies To |
| --- | --- |
| `references/spreadsheet-principles.md` | General spreadsheet handling, authority, reviewability, and validation. |
| `references/excel-workbook-principles.md` | Excel workbook identity, formulas, formatting, layout, and real Excel-engine validation. |
| `references/spreadsheet-review-package.md` | Review package structure and evidence presentation. |
| `references/connected-google-sheets-principles.md` | Connected Google Sheets identity, credential-free evidence/result handling, read/write scope, timeouts, and safe operation. |

Required consequences:

- Excel workbooks and Google Sheets should share the same analysis concepts
  where possible: source surfaces, processing tables, result projections, table
  I/O, labels, formulas, gates, domain packs, and HTML answers.
- File editing, workbook generation, reconciliation, validation, and future
  writeback must follow the existing CRUD references.
- Formula-dependent Excel results still require real Microsoft Excel-engine
  validation when results, not only formula text, matter.
- Connected Google Sheets access goes through an approved external access
  surface. This repository consumes credential-free spreadsheet
  evidence/results and owns the processing, validation, and review-package
  layer.

## Applicability

Current strongest fit:

- Excel or Google Sheets workbooks with raw/source tabs, formula-backed
  processing regions, result projection tabs, and repeated metric labels.
- Category/product/date/metric analyses such as payment decline, ROAS trend,
  ad-spend attribution candidates, and source/result reconciliation.
- Local review packages that can be reopened without live API access.
- Domain customization through selected domain packs.

Expanding fit:

- Document-shaped Excel pages where visual hierarchy, images, merged blocks,
  pivot tables, and free text matter.
- Refactoring, automation, writeback, and workbook-edit workflows after they are
  explicitly designed against the existing CRUD references.
- Shared ontology workflows after separate governance and review contracts are
  in place.

This document describes the first packaging shape; it must not be used to freeze
future repository boundaries.

## Package Identity

```text
spreadsheet-dataflow-inspector
```

Primary promise:

```text
Given an accessible spreadsheet, produce a local, evidence-backed review
package that explains source tables, processing tables, output tables, table I/O
flows, metric definitions, and question-specific answers.
```

The working name can change. The durable concept is the extensible dataflow
analysis capability.

## Architecture

```text
Input evidence intake
  -> Excel workbook reader / connected-Sheets evidence intake / stored packages
  -> Project workspace identity
  -> Local evidence package storage
  -> Local analysis engine
  -> Domain pack loader
  -> Evidence and table/dataflow extractor
  -> Question runner
  -> Gate runner
  -> HTML answer package renderer
```

Layer responsibilities:

| Layer | Responsibility | Must Not Do |
| --- | --- | --- |
| Excel workbook input | Read local `.xlsx` workbooks using existing Excel guidance, preserving identity, formulas, formatting, layout, and reviewability. | Flatten, replace, or round-trip user workbooks unless explicitly requested or using an agreed safe copy. |
| Project workspace | Bind repeated work to `projects/` using Google Sheets `spreadsheetId + gid` or Excel workbook-family identity. | Merge copied Excel files by filename/path alone or mix project-local boundaries silently. |
| Connected-Sheets evidence intake | Consume bounded connected-Sheets metadata, value, formula, grid, preview-write, write-result, and readback evidence produced by an approved external access surface. | Own Google authentication, scopes, policy gates, write gates, or Google API calls. |
| Connected Sheets authority path | Treat the approved external access surface as the authority for user/session identity, scopes, bounded ranges, redaction, operation limits, write gates, and live API calls. | Store model-visible credentials, broaden access silently, or recreate repo-local access-runtime components. |
| Local analysis engine | Build surface inventory, table candidates, formula/dataflow graph, label dictionary, and query artifacts across Excel and Sheets evidence packages. | Mutate the spreadsheet unless a future write path is explicitly invoked and governed by CRUD references. |
| Domain pack loader | Inject selected general/local domain knowledge, aliases, metrics, comparison windows, and classification rules. | Apply a domain pack automatically without document selection. |
| Gate runner | Validate ranges, source/result reconciliation, freshness, double counting, formula lineage, metric basis, and domain rule applicability. | Promote LLM or domain guesses to truth without evidence. |
| Renderer | Produce self-contained HTML with SVG flows and sortable tables. | Hide unresolved questions or gate failures. |

## Domain Knowledge Customization

Domain knowledge must be a replaceable input, not code baked into the parser.
The package should support both repo-local and user-global domain packs:

```text
domains/
  <domain-id>/
    domain.yaml
    metrics.yaml
    aliases.csv
    classification-rules.yaml
    question-presets.yaml
    README.md

~/.spreadsheet-dataflow-inspector/domains/
  <domain-id>/
    ...
```

Recommended domain pack contracts:

| File | Purpose |
| --- | --- |
| `domain.yaml` | Domain name, version, owner, applicability scope, general/local layer, and review status. |
| `metrics.yaml` | Metric definitions, accepted labels, basis rules, numerator/denominator rules, and incompatible meanings. |
| `aliases.csv` | Local aliases such as product/course/category names and their accepted semantic targets. |
| `classification-rules.yaml` | Deterministic or review-required rules for category/product/metric classification. |
| `question-presets.yaml` | Reusable question types such as decline analysis, ROAS trend, source/result reconciliation, and attribution candidates. |
| `README.md` | Human explanation of applicability, assumptions, local boundaries, and known limitations. |

Domain layers:

| Layer | Meaning | Example |
| --- | --- | --- |
| General domain | Reusable outside one organization or workbook family. | Standard marketing metrics such as ROAS definition variants. |
| Local domain | Valid only inside a declared organization, team, project, or workbook family. | `류스펜나` is treated as a Japanese course inside a specific reporting boundary. |

Rules:

- No domain pack is loaded by default unless the user or run config selects it.
- Local-domain rules must carry boundary metadata.
- Domain rules create candidate semantic claims; gates decide accepted,
  review-required, contradicted, or blocked status.
- Domain packs must be versioned so historical review packages can be replayed.

## Question And Answer Contract

Every question should produce a structured answer package:

```text
projects/<project-id>/runs/<run-id>/
  index.html
  answer.json
  evidence-summary.json
  table-map.json
  table-io-graph.json
  label-dictionary.json
  gate-results.json
  assets/
    table-io-flow.svg
    query-flow.svg
```

Reviewer-facing copies may also be published under `review-packages/`, but the
project folder is the continuity authority for repeated work on the same
spreadsheet surface or workbook family.

Answer sections:

| Section | Required Content |
| --- | --- |
| Executive summary | Direct answer, metric basis, current limitations, and review-required items. |
| Evidence surfaces | Source truth tabs, result projection tabs, annotation surfaces, hidden/automation surfaces. |
| Table map | User-friendly table names, spreadsheet ranges, roles, and boundary status. |
| SVG flow | Source-to-output table I/O flow, plus query-specific calculation flow when useful. |
| Sortable tables | Category/product/metric results with numeric sort, text filter, and status filters. |
| Formula/source chains | Processed labels and the raw/source lineage used to compute them. |
| Gate results | Passed, review-required, blocked, contradicted, and excluded claims. |
| Questions | Targeted questions tied to specific ranges, metrics, or domain assumptions. |

HTML renderer requirements:

- self-contained HTML;
- inline or local SVG, not Mermaid-only source text;
- sortable tables with plain JavaScript and no network dependency;
- visible Korean display labels by default, while preserving source identifiers;
- clear distinction between accepted facts, candidates, and review-required
  assumptions.

## Connected-Sheets Evidence Intake Model

Target local workflow:

1. An approved external access surface performs live connected-Sheets access.
2. The access surface returns bounded, credential-free metadata, value, formula,
   grid, structure, preview-write, write-result, or readback evidence.
3. The agent stores or references those evidence/results under the project or
   review-package workspace.
4. The local analysis engine consumes the stored evidence/results and produces
   the HTML review answer.

Global config:

```text
~/.spreadsheet-dataflow-inspector/
  config.json
  projects/
  domains/
  review-packages/
  logs/
```

Packaging principles:

- Approved external access surfaces own connected-Sheets acquisition, policy,
  write gates, live API calls, and readback evidence.
- The analysis engine owns renderer, schema validation, gates, and stored
  artifact processing.
- Excel workbook analysis owns local file inputs and must keep existing workbook
  CRUD principles as the authority.
- Connected-Sheets workflows in this repository start from credential-free
  evidence/results or existing credential-free review packages.
- Future writeback, refactoring, formula rewriting, and workbook editing can be
  added only through explicit design and the existing CRUD references.

## Gates

Minimum gates before a question answer is reviewer-ready:

| Gate | Purpose |
| --- | --- |
| Authority gate | Confirm approved external evidence and no repo-local credential, direct API, key, export, or import bypass. |
| Surface split gate | Separate source truth, result projection, annotation, hidden, and automation surfaces. |
| Table boundary gate | Confirm coherent ranges by labels, formulas, and spatial continuity. |
| I/O lineage gate | Connect processed tables to source tables through formula/reference evidence. |
| Metric basis gate | Confirm labels such as `매출` map to the intended metric, such as 결제액. |
| Freshness gate | Exclude current/future zero rows or stale automation outputs from trend claims. |
| Double-count gate | Prevent totals and child columns from being counted together. |
| Domain applicability gate | Confirm selected domain pack applies to this workbook boundary. |
| Result reconciliation gate | Compare result projections with raw/source sums when possible. |
| Presentation gate | Verify HTML contains SVG flow and sortable result tables without layout overflow. |

## Implementation Phases

| Phase | Goal | Done When |
| --- | --- | --- |
| 1. Capability contract | Define the extensible analysis capability without freezing future boundaries. | This document and ADR are accepted; AGENTS links to the capability design and existing CRUD references remain authoritative. |
| 2. Domain pack schema | Define and validate `domain.yaml`, `metrics.yaml`, aliases, and question presets. | Sample domain pack validates and can be selected by run configuration. |
| 3. Query artifact schemas | Formalize answer, evidence, gate, table map, and query result JSON schemas. | Current MLL decline analysis validates against schemas. |
| 4. HTML renderer | Add reusable sortable-table and SVG-flow renderer. | Generated review package contains sortable tables and local SVG. |
| 5. Excel input path | Package local workbook evidence extraction for the same analysis contracts. | A local `.xlsx` sample can produce the same surface/table/I/O/answer artifacts while preserving workbook identity. |
| 6. Connected-Sheets evidence intake | Normalize values/formulas/structure/readback results and stored review-package inputs into the same processing evidence model. | The analysis engine can run against credential-free spreadsheet evidence/results without owning Google access. |
| 7. Analysis engine packaging | Wrap stored-artifact analysis, rendering, schema validation, and doctor checks behind agent-invoked library boundaries. | The same analysis contract runs against stored Sheets packages and local workbooks. |
| 8. Processing hardening | Add logs, replay, redaction checks, version checks, and fixture validation for credential-free evidence packages. | Approved users can run analyses from local workbooks or credential-free spreadsheet evidence/results. |

## Relationship To Broader Repo

This package is an extensible analysis layer inside the existing Excel workbook
editing and spreadsheet understanding repository:

- It reuses evidence, claims, gates, and review-package discipline.
- It currently prioritizes formula/dataflow and metric analysis because those
  contracts are the most mature.
- It should also support Excel workbook inputs, not only connected Google
  Sheets.
- It can feed the broader claim ledger and document-shaped parser as those
  capabilities mature.
- It must not replace the existing Excel/spreadsheet CRUD guidelines.

Do not use this document to reject future expansion. Use it to package the
tested capability while keeping extension points explicit.
