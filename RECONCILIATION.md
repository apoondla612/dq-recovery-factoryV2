# Pilot reconciliation — 4 September 2026

## Source reconciliation

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
| Parse status complete | 2,324 |
| Parse partial / opaque | 0 / 0 |

## Rule discovery

- Selected-mapping `rule_*` invocations: **128**.
- Exactly one bounded primary endpoint: **106**.
- Helper/non-outcome invocations: **21**.
- Semantic ambiguities: **1**.
- Ambiguous invocation: `m_Material_Master / rule_Standard_Lead_Time`.
- Defensible primary readings: `rule_Standard_Lead_Time_ARIBA` and `rule_Standard_Lead_Time_COMM`.

The implementation emits the ambiguous case separately and does not choose a reading.

## Determinism and gates

Two complete runs against the supplied pilot ZIP exited 0 and produced byte-identical output directories. Current technical gates: structural/accounting baseline pass, pilot parser totality pass, vendor-neutral `semantics` pass, and no round-trip mismatch on rules eligible for the expression-only round-trip gate.

R02C binding resolves identifiers only within the owning transformation and attaches source field ID, datatype, precision/scale and input/output role. At rule level, 79 primary endpoints are fully bound/parse-complete and 27 are partial because evidence cannot resolve every identifier. Eleven rules have no remaining external/non-expression blocker and all 11 pass render → parse → bind → normalise canonical-byte round-trip. The remaining 95 are `blocked_external`; none are counted as a pass.

All 106 discovered primary endpoints remain `unmatched` because no human-owned rule-type descriptor set was supplied.

## First full-run budget measurement

A measured full run after R02C binding completed in **1.33 seconds** wall clock with **111,548 kB** maximum resident set size in the current Linux runtime. This is the R18 measurement baseline; no enforcement ceiling is invented in this implementation commit.

## Explicit blockers to final acceptance

1. Human acceptance fixtures/expected outputs required by DQ-RCV-URS-001 have not been supplied; implementation does not author them.
2. A ratified descriptor set / rule-type naming input has not been supplied; implementation therefore clusters candidates but does not invent names.
3. REQ-R12A's reviewed Informatica evaluation-semantics specification and truth-table vectors/reference snapshots have not been supplied; the independent truth-table oracle is therefore not claimed.
4. R00 requires the ratified rule-identity decision to state its resulting denominator. The current mechanical result is 106 single-primary invocations plus one ambiguous invocation, but this report does not silently ratify that number for Architecture.

## Run command used

```bash
PYTHONPATH=src python -m dq_recovery.cli recover \
  --export "Test-Mappings-Export (2)(2).zip" \
  --out <run-directory>
```
