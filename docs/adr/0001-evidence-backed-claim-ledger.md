# ADR 0001: Evidence-Backed Claim Ledger For Spreadsheet Understanding

## Status

Accepted

## Context

Document-shaped spreadsheets mix text, tables, formulas, pivots, images, charts, hidden/view-state behavior, repeated tabs, and external references. Earlier pipeline work showed that row/column/table extraction is not enough, and that visual grouping, formula/dataflow, ontology mapping, semantic interpretation, and human review must be tied to source evidence.

Multi-perspective review by Codex subagents and Claude Code Opus 4.8 identified recurring issues in the previous top-level design:

- A late deterministic gate layer is insufficient; gates must operate across structure, authority, semantics, ontology, and action readiness.
- LLM output should be candidate claims, not ontology truth.
- Formula text, visual capture, pivot renders, and external references have different authority classes.
- Layout grouping is itself a defeasible structural claim.
- Accepted, review-required, blocked, contradicted, and conflicting items must remain distinguishable.
- Ontology is both an upstream constraint plane and a downstream projection.
- LLM/product retrieval needs governed context packs, not raw graph dumps.
- Version, provenance, identity, authority, and lineage must be cross-cutting concerns.

## Decision

Use an evidence-backed, bitemporal claim ledger as the canonical architecture for document-shaped spreadsheet understanding.

The canonical record is an append-only ledger of observations, evidence, candidate claims, gate decisions, reviewer decisions, and action outcomes. Graphs and ontology outputs are projections over that record.

Top-level structure:

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

Control-plane review/action decisions feed new evidence and claim versions back into the ledger.

Use `Adjudicated Claim Graph`, not `Validated Claim Graph`, because the graph must preserve all classified statuses, including blocked and contradicted claims.

## Consequences

Improvements:

- Claims become auditable, replayable, and versionable.
- Blocked and contradicted claims are preserved for suppression, review, and learning.
- Deterministic extraction and LLM semantic proposals can be separated.
- Ontology projection cannot silently merge bare labels such as `결제액`, `매출`, and `순매출`.
- Read models can enforce accepted-only or review-aware retrieval boundaries.
- Human review and writeback become explicit action contracts.

Costs:

- More schema design is required before implementation.
- Bitemporal and append-only storage is heavier than a simple extraction artifact.
- Gate maintenance requires a claim-kind to authority-requirement matrix.
- Projections must be tested to prevent review-required or blocked claims from leaking as accepted truth.

Required follow-up:

- Define claim schema and statuses.
- Define evidence and authority taxonomy.
- Define gate result schema and status propagation rules.
- Define semantic signature and concept resolution rules.
- Define projection/read-model contracts.
- Define review/action contract state machine.

## Alternatives Considered

### Linear Pipeline To Validated Ontology Graph

Rejected as the main architecture because it hides claim lifecycle, risks treating gate output as truth, and makes blocked/review-required material easy to drop.

### Query-First Architecture

Useful for narrow one-off questions, but insufficient as the durable shared architecture because the current goal includes storage, review, ontology maturation, and repeatable retrieval.

### Task-First Architecture

Useful when a downstream automation target is already fixed. Not selected as the primary architecture because the parser is still being tuned across document structure, dataflow, semantics, and ontology readiness.

### Human-In-The-Loop-First Architecture

Important for early tuning and review, but not enough by itself. Human decisions must be represented as ledger events and action contracts inside the broader architecture.

### Evidence Ledger Without Claims

Rejected because observations alone do not provide semantic grouping, dataflow roles, or ontology-ready statements. Claims are the unit that connects evidence, gates, review, and projections.

## Verification

This decision is verified when:

- Every accepted projection node or relation traces to evidence ids and adjudicated claim ids.
- Structural layout, dataflow, semantic, and ontology assertions are stored as claims with status.
- Deterministic-derived claims and LLM-generated claims are distinguishable.
- Formula result authority, pivot authority, external reference authority, and visual evidence authority are explicitly gated.
- Blocked, contradicted, and conflicting claims remain queryable.
- LLM retrieval context packs include status, authority, provenance, and version pins.
- Review decisions produce auditable events and can trigger re-gating.
