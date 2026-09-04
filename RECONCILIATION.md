# Pilot reconciliation — 4 September 2026

## Source and accounting reconciliation

| Measure | Result |
|---|---:|
| XML members | 10 |
| Elements | 52,313 |
| Attributes | 249,774 |
| Non-whitespace text nodes | 0 |
| Expressions | 2,084 |
| Lookup conditions | 235 |
| Filter conditions | 5 |
| Join conditions | 11 |
| SQL queries | 194 |
| Dynamic-cache conditions | 235 |
| Parseable records | 2,324 |
| Parse complete | 2,324 |
| Parse partial / opaque | 0 / 0 |

`accounting.json` independently reconciles the element, attribute and text denominators into mapped / evidence-only / marked-unknown / explicitly-ignored classifications. Unknown source constructs are counted rather than discarded.

## Rule discovery and R08 ambiguity

- Selected-mapping `rule_*` invocations: **128**.
- Single-primary validation invocations: **106**.
- Helper/non-outcome invocations: **21**.
- Ambiguous invocation: **1** — `m_Material_Master / rule_Standard_Lead_Time`.
- Defensible readings: `rule_Standard_Lead_Time_ARIBA` and `rule_Standard_Lead_Time_COMM`.
- Emitted primary-endpoint candidates: **108** — 106 normal candidates plus both ambiguity readings.

The two ambiguity candidates share one `ambiguity_id`, state the assumed primary endpoint in plain words, remain `recovery_status=semantic_ambiguity`, and are never silently promoted to matched/approved rules.

## Verification and determinism

Current verification over 108 candidates:

- `passed`: **11**
- `blocked_external`: **97**
- `failed`: **0**

Round-trip is render → parse → bind → normalise → canonical-byte compare for every expression in a closure that is otherwise verifiable: primary, supporting expressions and companion outputs. Native/non-expression operations or unresolved evidence keep the candidate `blocked_external`.

Two complete runs produce **117 byte-identical files under `output/`**. `run-event.json` is deliberately outside `output/` and carries operational timestamp/performance metadata.

Coverage metrics currently report:

- Discovery: **128 / 128 = 100%** accounted invocations.
- Parse completeness: **2,324 / 2,324 = 100%**.
- Canonical matched recovery: **0 / 108 = 0%** because no human descriptor set was supplied.
- Round-trip verification: **11 / 108 = 10.185185%**.
- Truth-table verification: **0 / 108, not run**.
- External blockers: **97**.

## Descriptor/matcher mechanics exercised

A temporary mechanics-only descriptor was used outside the repository to exercise the generic loader/matcher without inventing a governed rule type:

- valid same-shape descriptor → deterministic match;
- duplicate fully-binding same-shape descriptors → `descriptor_conflict`, non-zero exit;
- later run with lower matched percentage than prior output → coverage-regression gate, non-zero exit;
- invalid shape declaration → load failure.

These mechanics tests are not normative acceptance fixtures.

## Open questions and construct evidence

`open-questions.json` contains **107** domain-addressed entries: one for each unresolved single-primary rule plus the one ambiguous invocation. Where a rule has both identifier-binding and rule-type gaps they are consolidated into one entry rather than duplicated.

`construct-matrix.json` records record kinds, transformation types, expression operators, recognised/unknown calls, external invocations, source-neutral semantic operations and external dependency types, each with occurrence count, support status and example source location. When `--previous` points to a prior output directory, newly unsupported constructs are flagged.

## R18

Raw wall time and maximum RSS are measured into `run-event.json`. An externally supplied `--budget` JSON can enforce `max_wall_seconds` and/or `max_rss_kb`; exceeding either exits non-zero. No production ceiling is invented in this repository.

## Explicit blockers to final Stream 1 acceptance

1. Human acceptance fixtures and expected golden outputs specified by DQ-RCV-URS-001 have not been supplied.
2. A ratified governed descriptor set / rule-type naming input has not been supplied.
3. REQ-R12A's reviewed Informatica evaluation-semantics specification, truth-table vectors and required reference-data snapshots have not been supplied.
4. R00 still requires Architecture to ratify the governed rule denominator; V2 reports the mechanical evidence as 108 primary-endpoint candidates but does not ratify it on Architecture's behalf.
5. Cross-transformation/instance-level closure is still conservative where source evidence cannot be bound mechanically; those cases remain blocked rather than guessed.
