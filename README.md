# DQ Recovery Factory V2

Stream 1 recovery implementation for the IDQ decommissioning programme.

**Authority:** DQ-RCV-URS-001 v1.0 and DQ-RCV-DS-001 v1.0, fingerprinted in `specs/authority-hashes.json`.

## Run

```bash
python -m dq_recovery.cli recover --export Test-Mappings-Export.zip --out out
```

For a source checkout without installation:

```bash
PYTHONPATH=src python -m dq_recovery.cli recover --export Test-Mappings-Export.zip --out out
```

The command fingerprints and extracts the sealed ZIP, reconciles structure and technical-logic record kinds, parses all parseable records, discovers primary validation endpoints from selected mapping invocations, emits source-neutral candidate rules and evidence, generates coverage/construct/ambiguity/helper reports, performs conservative round-trip checks where verification is not externally blocked, and exits non-zero on a run-level gate failure.

## Pilot reconciliation (4 Sep 2026)

The supplied ten-mapping pilot reconciles to 52,313 XML elements, 249,774 attributes and zero non-whitespace text nodes. Record kinds: 2,084 expressions, 235 lookup conditions, 5 filters, 11 join conditions, 194 SQL queries and 235 dynamic-cache conditions. The 2,324 parseable records parse completely.

The ten selected mappings contain 128 `rule_*` reusable invocations. The R00 bounded-outcome test currently finds 106 invocations with exactly one primary outcome endpoint, 21 helper/non-outcome invocations, and one semantic ambiguity (`rule_Standard_Lead_Time`, with ARIBA and COMM endpoints). The ambiguity is emitted, not guessed.

## Important acceptance boundary

This repository does not invent the human-owned acceptance fixtures, rule-type descriptor names, or Informatica evaluation-semantics specification. Until those normative inputs are supplied and reviewed, candidates remain `unmatched` and truth-table verification is not claimed. `blocked_external` is not counted as a pass.
