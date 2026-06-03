# Architecture Decision Records

Store repository architecture decision records in this directory.

## Naming

Use a sortable number and short slug:

```text
0001-fast-workbook-manifest.md
0002-readonly-targeted-row-sampling.md
```

## Template

```markdown
# ADR 0000: Decision Title

## Status

Accepted

## Context

What problem, constraint, or discovery led to this decision?

## Decision

What are we choosing now?

## Consequences

What improves, what becomes harder, and what must be verified?

## Alternatives Considered

What other options were considered and why were they not selected?

## Verification

Which tests, schema checks, workbook checks, or Excel-engine checks prove this decision is working?
```

## Rules

- Keep ADRs focused on durable decisions.
- If a decision changes, add a new ADR or mark the previous ADR as superseded.
- Keep active docs and runtime behavior aligned with accepted ADRs.
