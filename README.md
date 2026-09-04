# DQ Recovery Factory V2

Stream 1 recovery implementation for the IDQ decommissioning programme.

**Authority:** DQ-RCV-URS-001 v1.0 and DQ-RCV-DS-001 v1.0. Approved-document fingerprints and the status of required standalone specifications are pinned in `specs/authority-hashes.json`.

## Run end to end

```bash
PYTHONPATH=src python -m dq_recovery.cli recover \
  --export Test-Mappings-Export.zip \
  --out out
```

## Manifest-first flow

```bash
PYTHONPATH=src python -m dq_recovery.cli source register Test-Mappings-Export.zip --out registered
PYTHONPATH=src python -m dq_recovery.cli recover \
  --manifest registered/pilot-source.manifest.json \
  --out recovered
```

Optional inputs:

- `--descriptors <dir>`: human-owned JSON rule-type descriptors.
- `--previous <prior-output-dir|coverage.json|run-manifest.json>`: enables matched-coverage regression and newly-unsupported construct comparison.
- `--budget <json>`: enforces an externally chosen R18 wall-time / RSS ceiling.
- `--code-sha <sha>`: pins a code revision explicitly; otherwise `GITHUB_SHA` or the current git commit is used when available.

## What V2 currently does

The pipeline registers and fingerprints the sealed ZIP, performs three-denominator XML accounting, classifies technical-logic record kinds, form-URL decodes native text with `unquote_plus`, parses expression records with comments as lexer trivia, binds identifiers within evidence-backed transformation scope, normalises to canonical bytes, computes semantic and shape signatures, discovers reusable-rule invocations and bounded primary endpoints, emits semantic ambiguity candidates without choosing a reading, loads/validates declarative descriptors when supplied, evaluates every shape-matching descriptor, emits deterministic source-neutral rule candidates, creates construct/coverage/open-question evidence, and round-trips every expression in a verifiable primary closure.

Operational timing and memory are written to `run-event.json` outside `output/`; deterministic `output/` can therefore be compared literally between two runs.

## Pilot reconciliation — 4 Sep 2026

The supplied ten-mapping pilot reconciles to **52,313 XML elements, 249,774 attributes and zero non-whitespace text nodes**. It contains **2,084 expressions, 235 lookup conditions, 5 filter conditions, 11 join conditions, 194 SQL queries and 235 dynamic-cache conditions**. All **2,324 grammar-parseable records** parse `complete`.

The selected mappings contain **128 `rule_*` reusable invocations**. The current mechanical R00 test finds **106 single-primary validation invocations**, **21 helper/non-outcome invocations**, and **one two-reading semantic ambiguity** (`rule_Standard_Lead_Time`). R08 now emits both `ARIBA` and `COMM` readings as candidate rules sharing one ambiguity identifier. Consequently the current mechanical primary-endpoint denominator is **108** (106 resolved single-primary endpoints + 2 ambiguity readings), pending Architecture ratification under R00.

Current verification status over the 108 emitted candidates is **11 passed / 97 blocked_external / 0 failed**. No descriptor set was supplied, so recovery status is **106 unmatched + 2 semantic_ambiguity**; `blocked_external` is never counted as a pass.

## Acceptance boundary

This repository does not invent human-owned acceptance fixtures, governed rule-type names, or Informatica evaluation semantics. REQ-R12/12A truth-table verification remains unclaimed until the reviewed evaluation-semantics specification, vectors and required reference snapshots are supplied. The internal mechanics tests under `tests/test_internal_mechanics.py` are engineering checks only; they are not substitutes for the URS acceptance fixtures.
