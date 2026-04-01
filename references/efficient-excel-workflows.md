# Efficient Excel Workflows

Use this reference when the Excel task is not just "edit a few cells" but "stabilize a recurring workbook workflow without losing auditability."

## 1. Start With Problem Type

Before changing formulas, classify the problem:

- logic bug: the workbook applies the wrong rule
- source gap: the workbook is missing input data needed to reproduce the target result
- manual override: the target workbook contains row-level edits not reproducible from current source inputs
- explainability gap: the math may be right, but reviewers cannot follow it
- Excel behavior gap: Python-side output and Excel-side recalculation disagree

Do not treat every mismatch as a formula bug. Many expensive Excel investigations are really source-gap or manual-override problems.
Do not treat the task as "make the final gap smaller" either.
The goal is to identify source differences, logic differences, and behavior differences accurately, not to numerically chase the target output.

## 2. Preserve The Right Grain

When reversals, refunds, reallocations, or mixed bundles exist, do not collapse too early.

- prefer row-level logic over `transaction_id -> single value` shortcuts
- preserve sign at the row level
- keep refund rows distinct from original purchase rows when their treatment differs
- avoid aggregating by `imp_uid`, `transaction_id`, or customer too early if one identifier can contain both positive and negative rows

If a result differs only on special cases, the problem is often that the data was collapsed before the special-case rule could be applied.

When comparing workbook formulas to code, also compare selection semantics, not just formulas.
If Excel uses first-match behavior and code uses last-write-wins behavior, outputs can drift even when both appear to apply the same business rule.

## 3. Separate Source Of Truth From Working Surfaces

Recurring Excel work usually has several artifacts:

- raw source inputs
- derived CSV or helper tables
- workbook generator code
- the workbook itself
- a prior approved workbook used for comparison

Treat them differently:

- raw inputs are the real inputs
- generator code is the repeatable implementation surface
- the workbook is the explanation and validation surface
- prior approved workbooks are comparison artifacts, not always live inputs

If a current-period derived workbook is not guaranteed to exist every cycle, do not make it a required input.
Do not mix prior-period carry-ins with current-period computed rows in one opaque table if reviewers need to understand period movement.
Keep carry-in, current-period computation, and carry-out visible as distinct surfaces whenever period rollforward is material.

## 4. Debug Totals By Decomposition

When a final total is off, do not keep staring at the final total.

Break it down by:

- category
- brand or business unit
- transaction type
- period bucket
- sign
- inclusion or exclusion reason

Useful pattern:

1. compare final totals
2. decompose by major category
3. isolate the largest unexplained bucket
4. compare row sets for only that bucket
5. classify the residual into logic bug, source gap, or override

This is usually faster than broad workbook spelunking.

Important caution:

- do not search only for errors that would move the result in the net-gap direction
- a net understatement can hide a large overstatement plus a larger understatement
- a small final gap does not imply small underlying errors
- always inspect gross overstatement and understatement buckets separately before trusting the net residual
- treat output-gap reduction as a byproduct of root-cause analysis, not as the search strategy itself
- compare source-row coverage and logic-path differences before proposing any formula tweak meant to "move the total"

For recurring monthly workbooks, a strong default comparison pattern is:

1. approved or golden workbook
2. code or script source of truth
3. newly generated workbook

Use this to classify the residual into:

- source gap
- logic bug
- workbook wiring bug
- Excel behavior gap
- manual override

This is usually more informative than comparing only approved workbook to generated workbook.

## 5. Prefer Bridges Over Dense Final Formulas

If an output depends on several drivers, add a bridge sheet instead of making one dense final formula.

Bridge sheets are especially useful when you need to show:

- seed or opening balance
- immediate recognition
- refund or reversal effect
- prior-period carryover
- deferred opening or release
- inclusion and exclusion classification

If the reviewer asks "why is this amount here," a bridge sheet should answer that without requiring code access.

If a bridge can legitimately have zero rows in some periods, treat that as a first-class design case.

Preferred pattern:

1. make the bridge structurally present every period
2. ensure aggregates coerce empty inputs to numeric zero
3. sample an empty-month case in real Excel, not just a populated month

Many workbook defects only appear in zero-row months.

## 6. Turn Repeated Manual Fixes Into Code

If the same cleanup appears every cycle, it belongs in code or a documented rule, not in a human-only Excel step.

Examples:

- duplicate bundle removal
- choosing the primary row among similar rows
- fallback price allocation rules
- normalized text join keys
- carryover extraction logic

But only codify it when it is reproducible from legitimate inputs. If it depends on hidden human judgment or missing source data, classify it as a limitation instead.

## 7. Known Limitations Should Be Visible

When some rows cannot be reconstructed from current inputs:

- do not bury them in hidden formulas
- do not invent workbook-only logic to make the totals match
- list them explicitly in a known limitation area or sheet
- state whether they are source gaps, overrides, or unresolved business-policy questions

This protects trust in the workbook. Silent patches destroy trust faster than an explicit limitation note.

## 8. Use Excel For Truth, Code For Control

Default working pattern:

1. change the generator or workbook structure in code
2. open and recalculate in Excel
3. sample a narrow set of cells
4. compare against the authoritative logic
5. repeat

Use code for:

- deterministic edits
- repeatability
- large-scale changes
- artifact generation

Use Excel for:

- authoritative formula results
- human review
- layout and inspectability
- confirming behavior of Excel-native features

Use AppleScript only to automate the validation loop around Excel when manual repetition becomes the bottleneck.

## 9. Optimize For Resume-ability

Excel projects lose time when the next session has to rediscover context.

After any meaningful debugging pass, record:

- the current known-good totals
- the remaining unexplained deltas
- the top unresolved row ids or labels
- whether each unresolved item is a logic bug, source gap, or override
- the exact commands needed to rerun the comparison
- which files are the first files to open next time

Good handoff notes are a force multiplier for recurring Excel work.

## 10. Promote Only Reusable Learnings

When capturing lessons from a project, separate:

- project-specific facts
- reusable Excel working patterns

Project-specific facts belong in local docs.
Reusable patterns belong in the generic Excel skill or its references.

If a lesson still includes product names, month labels, or one-off file names, it probably is not generic enough yet.

## 11. Find The Real Bottleneck First

Do not assume formula complexity is the main problem.
In recurring Excel workflows, the real blocker is often undocumented human judgment.

Common examples:

- manual classification columns
- manually chosen carryover rows
- copied values whose selection rule is outside the workbook
- row-level overrides that cannot be reconstructed from current inputs

Practical rule:

1. map which fields are formula-derived
2. map which fields are manual or policy-derived
3. ask which of those manual decisions can be formalized
4. leave the rest as explicit limitations, not hidden workbook logic

If a workflow depends on human judgment, more formula tracing alone will not automate it.

## 12. Declare Read Paths And Compute Paths

Many Excel pipelines mix two kinds of rows:

- rows whose monthly or derived values are read from an upstream artifact
- rows whose monthly or derived values are computed in the current logic

If both paths merge into one output table, declare that explicitly.

What to record:

- which rows use read-path behavior
- which rows use compute-path behavior
- why each path exists
- which invariants apply to all rows versus only computed rows

Without this, reviewers may incorrectly assume one function or formula covers every row.

## 13. Check Measurement Basis Before Comparing Totals

Before reconciling `seed + stream = total` or comparing one workbook total to another, verify that both sides are measured on the same basis.

Typical basis mismatches:

- pre-allocation amount versus post-allocation amount
- payment amount versus recognized revenue
- current-month view versus cumulative carryover view
- gross amount versus tax-adjusted amount

Do not trust total agreement by itself.
First confirm that the row-level meaning of the compared columns matches.
When possible, compare representative transaction IDs before comparing aggregates.

## 14. Separate Existence From Wiring

In workbook analysis, these are different questions:

- does a sheet exist
- is that sheet referenced by formulas
- is a rule documented
- is that rule actually enforced in formulas or code
- does an aggregate cell exist
- is there row-level structure that makes the aggregate auditable
- does a config value exist
- does every implementation path actually read it

This distinction catches false confidence.
A workbook can appear complete while still having pipeline breaks, disconnected sheets, or unenforced validation rules.

Practical test:

1. confirm the sheet exists
2. confirm named ranges point at it
3. confirm a downstream bridge reads from it
4. confirm an output cell changes when a representative upstream value changes

A workbook can contain the right-looking sheet names and still have a broken calculation path.

## 15. Dual Representation Needs Reconciliation

Sometimes the same business rule legitimately exists twice:

- code or Python for generation and control
- Excel formulas for auditability and human review

This is acceptable only when the two representations are kept in sync deliberately.

Default safeguards:

- keep one explicit source for each literal or parameter when possible
- have code read config from the same authoritative location used by Excel
- add reconciliation checks or validation identities between the two surfaces
- treat silent divergence as a structural risk even if current totals still look right

The problem is not "two surfaces exist."
The problem is "two surfaces can drift without detection."

## 16. Validate Generality Separately From Logic Correctness

A workflow can have correct formulas and still fail as a recurring monthly process.

Check separately:

- business logic generality
- input-file binding generality
- column-schema resilience
- environment-specific Excel behavior

Typical failure modes:

- CLI parameters are generic but file paths are hard-coded to one month
- header labels exist but code still relies on fixed column indexes
- workbook formulas are generic but the template still expects one-off manual inputs

Treat "works for this month" and "works as a general monthly workflow" as different claims.

## 17. Auditability Depends On Implemented Identities

A design document may define validation identities, but auditability only improves when those identities are implemented where reviewers can actually inspect them.

Useful distinction:

- rule exists in design
- rule is structurally representable
- rule is enforced by formula or code
- rule is visible to the reviewer

For recurring Excel systems, track validation identities explicitly and check implementation coverage.
Missing identities create future manual proof work even when current output totals seem plausible.

## 18. Minimize Failure Cost With A Discovery Ladder

When Excel work goes wrong, the biggest waste is often not the wrong fix.
It is spending time, context, and tokens on an expensive investigation before ruling out cheaper explanations.

Use this order by default:

1. classify the mismatch type before reading formulas in depth
2. compare source coverage and input-row membership first
3. compare totals by category, sign, and inclusion reason
4. check whether the compared artifacts use the same measurement basis
5. inspect whether the relevant sheet, config, and input are actually wired into formulas or code
6. inspect whether the problem is caused by a manual decision, override, or missing source input
7. inspect for duplicated rule paths, hard-coded literals, or hard-coded file and column bindings
8. recalculate in real Excel and sample only a few representative cells
9. only then do formula-by-formula tracing or structural refactors

This order is cheaper because many recurring failures are not deep formula bugs.
They are usually one of:

- source-row mismatch
- wrong comparison basis
- disconnected input
- manual-only logic
- duplicated rule paths
- environment-specific Excel behavior
- month-specific or column-specific hard-coding

If a cheap falsification step can rule out a whole class of causes, do that before loading more workbook detail into context.

## 19. Use Symptom-To-Test Shortcuts

Treat recurring Excel debugging as pattern matching.
Start from the symptom, then run the cheapest discriminating test.

### Symptom: totals differ a lot, across many rows

High-probability causes:

- measurement basis mismatch
- duplicated pipeline path
- seed plus current-period overlap

Cheapest checks:

- compare which source rows exist on each side before touching formulas
- compare category-level subtotals before row tracing
- check whether both sides are pre-allocation or post-allocation values
- verify whether one side already includes carryover or current-period rows
- split the delta into over-counted rows and under-counted rows instead of inspecting only the net gap

### Symptom: the final gap is small, but the workbook still feels wrong

High-probability causes:

- offsetting overstatements and understatements
- wrong inclusion on one bucket and wrong exclusion on another
- row-level classification errors hidden by aggregate netting

Cheapest checks:

- compute gross positive and gross negative deltas separately
- compare row membership, not just aggregate totals
- inspect whether one category is overstated while another is understated
- treat a small net gap as inconclusive until the gross error mass is understood

### Symptom: only a few rows differ, usually edge cases

High-probability causes:

- manual override
- source gap
- grain collapsed too early

Cheapest checks:

- inspect unresolved row IDs directly
- compare whether the row exists in both source surfaces before checking formulas
- preserve original sign and row count
- compare special-case rows before comparing the entire table

### Symptom: Python-side output looks right, Excel-side output does not

High-probability causes:

- Excel behavior gap
- function compatibility issue
- named-range aggregation issue
- text-versus-number key mismatch

Cheapest checks:

- recalculate in Excel first
- sample only the affected cells and a few upstream cells
- replace fragile patterns such as `XLOOKUP`, CSE-dependent formulas, or named-range `SUMIFS`

### Symptom: a sheet exists but changing it does nothing

High-probability causes:

- pipeline break
- disconnected formulas
- unused input sheet

Cheapest checks:

- search formula references to that sheet
- inspect named ranges that should bridge into outputs
- verify that an output cell changes when the supposed driver cell changes

### Symptom: changing Config updates some outputs but not others

High-probability causes:

- duplicated rule implementation
- hard-coded literals in code
- duplicated calculations in multiple surfaces

Cheapest checks:

- search for the literal value in code and formulas
- look for the same rule being recomputed outside the main config path
- identify which outputs read Config directly versus indirectly

### Symptom: one month works, another month fails

High-probability causes:

- hard-coded input files
- hard-coded labels
- hard-coded column indexes
- current-period-only assumptions hidden in the template

Cheapest checks:

- inspect loader constants before reviewing formulas
- confirm that CLI month parameters also affect file discovery
- confirm that header labels are actually used to derive indexes

### Symptom: validation says everything is fine, but trust is still low

High-probability causes:

- formal or vacuous validation formula
- missing validation identities
- aggregate-only checks without row-level structure

Cheapest checks:

- see whether the validation formula can ever fail
- map each design identity to an implemented formula or check
- confirm that key aggregates have row-level support behind them

### Symptom: AppleScript or Excel automation is flaky

High-probability causes:

- concurrent Excel interaction
- focus-dependent automation
- broad workbook scanning

Cheapest checks:

- ensure no other Excel workflow is touching the file
- rerun in read-only mode
- reduce the automation to recalc plus a narrow cell sample

## 20. Escalate Context Only When The Cheap Tests Fail

A practical token-saving rule:

- do not paste or inspect large formula regions first
- do not diff whole workbooks first
- do not load every sheet into context first

Prefer this escalation path:

1. inspect handoff notes and known-good totals
2. inspect source-file coverage, loader paths, and row membership
3. inspect config bindings and named ranges
4. inspect one output cell, one upstream bridge cell, and one input row
5. inspect a tiny row sample around the mismatch
6. only then expand to full sheet or formula-chain review

This keeps failure-cost low in three ways:

- less time spent on the wrong hypothesis
- less context wasted on irrelevant workbook detail
- less token burn from broad exploratory dumps
