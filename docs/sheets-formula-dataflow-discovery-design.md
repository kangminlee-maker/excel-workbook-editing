# Formula Dataflow Discovery Design

## Purpose

Discover table- and region-level data connections from spreadsheet formulas
before any refactoring, automation, or writeback work.

This design applies to connected Google Sheets evidence packages and local Excel
workbooks where formula text and related value/layout evidence are available.

Before discovery, locate or create the project workspace under `projects/` so
later chunks, gates, and reviewer decisions attach to the same source identity.

## Runtime Scope

In scope:

- read-only formula, value, grid, metadata, and workbook-manifest evidence;
- formula inventory;
- parsed formula references;
- normalized formula-pattern groups;
- region and table candidates;
- table-level input/output pipeline candidates;
- connected automation signals when available;
- deterministic gate rollups;
- HTML review packages with SVG or other rendered visual flows.

Not enabled by default:

- formula rewrites;
- refactoring plans;
- automated edits;
- writeback;
- semantic ontology promotion;
- direct credential or API bypasses.

## Authority Rules

- Formula text is evidence, not formula-result authority.
- Formula-result authority requires effective values, recalculation, or another
  approved result source.
- Connected Google Sheets evidence must come through an approved external
  access surface. This repository consumes the resulting credential-free
  evidence and does not own live Google access.
- Excel workbook evidence must follow the existing Excel workbook principles and
  real Excel-engine validation when formula results matter.
- Observed references, region boundaries, table roles, and table I/O edges are
  claims that require gates.

## Discovery Flow

```text
Input evidence
-> project identity
-> formula inventory
-> parsed reference edges
-> normalized formula pattern groups
-> region/table candidates
-> table I/O pipeline candidates
-> gate results
-> HTML/SVG review package
```

## Claim-Ledger Framing

| Item | Treatment |
| --- | --- |
| Formula text observed in a cell | Evidence |
| Parsed cell/range reference | Derived evidence or deterministic claim |
| Contiguous formula-pattern region | Structural candidate claim |
| Referenced range as an input | Role candidate claim |
| Formula region as calculation/output | Role candidate claim |
| Table-level I/O edge | Dataflow candidate claim |
| External, dynamic, unresolved, or hidden dependency | Blocked or review-required claim |

## Required Gates

- formula parse gate;
- reference resolution gate;
- range existence gate;
- dynamic reference gate;
- external reference gate;
- formula-pattern stability gate;
- formula drift gate;
- view-state relevance gate;
- pivot, array, and spill detection gate;
- sampled-coverage gate;
- formula-result value-pair gate;
- whole-column self-reference gate;
- connected automation context gate when automation evidence exists.

## Review Output

The review package should show:

- source artifact identity and authority path;
- project folder and identity key;
- analyzed ranges and coverage limits;
- formula inventory summary;
- formula-pattern groups;
- table/region candidates with spreadsheet ranges;
- table I/O pipeline candidates with user-facing names;
- rendered visual flow, preferably SVG for reviewer readability;
- gate outcomes and unresolved blockers;
- next evidence reads needed to reduce review-required claims.
