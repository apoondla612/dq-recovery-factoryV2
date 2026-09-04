# DQ-RCV-URS-001 implementation reconciliation

`Implemented` below means the implementation-owned mechanism exists and has been exercised; it does **not** replace a human-owned fixture/specification gate required by the URS.

| Requirement | Status | Current evidence / remaining boundary |
|---|---|---|
| R00 — rule identity | **Blocked on ratification** | Mechanical evidence: 106 single-primary invocations + 2 emitted readings for one ambiguous invocation = 108 primary-endpoint candidates; 21 helpers/non-outcomes. Architecture must ratify the governed denominator. |
| R01 — nothing dropped | **Implemented; acceptance fixture pending** | Three reconciling XML denominators with mapped/evidence-only/marked-unknown/ignored classes; unknowns retained and reported. |
| R02 — normalisation specification | **Normative input** | Approved operator decisions are treated as authority; implementation applies no operand sorting or unapproved reorder. |
| R02A — record-kind classification | **Implemented** | Expression/lookup/filter parsed; join/SQL/dynamic-cache classified outside the expression grammar. |
| R02B — parser | **Implemented; acceptance fixture/fuzz gate pending** | 2,324/2,324 pilot records complete; comments are lexer trivia; malformed input is total/fail-closed. |
| R02C — binding | **Partial** | Native field ID, datatype, precision/scale and I/O role are bound within owning transformation; unresolved cross-instance evidence remains partial rather than guessed. |
| R03 — normalisation | **Implemented; human collision fixtures pending** | Canonical bytes/hash and conservative transformations implemented. |
| R04 — repeatability | **Implemented on pilot** | 117 files under `output/` are byte-identical across two runs. |
| R05 — descriptor format/load validation | **Implemented** | JSON descriptors are versioned data, recursively shape-validated, hashed as a set and require no code change to add. Governed descriptors themselves remain human input. |
| R05A — shape specification | **Normative input** | Typed positional placeholders retain operator/function structure. |
| R05B — shape derivation | **Partial-to-implemented for current closure** | Primary expression and recovered supporting/companion structure are retained; unresolved cross-instance operations remain blockers. |
| R06 — clustering | **Implemented** | Grouping uses shape signature only, with count/example and descriptor-coverage flag. |
| R07 — matching | **Implemented** | Every shape-matching descriptor is evaluated deterministically; parameters bind by typed slot; parse status caps match; duplicate complete matches are a hard `descriptor_conflict`. |
| R08 — ambiguity | **Implemented for discovered primary ambiguity; generic construct ambiguity still extensible** | Both Standard Lead Time readings are emitted as candidates sharing one ambiguity ID; neither is chosen. |
| R09 — canonical rules | **Implemented for recovered graph; external blockers explicit** | Stable semantics/bindings/evidence; source-neutral semantics; supporting expressions, companions, operations and native provenance separated. |
| R10 — render | **Implemented for expression graph** | Canonical normalised expressions render back to native expression form; external operations remain non-renderable blockers. |
| R11 — round-trip | **Implemented for verifiable expression closure** | Primary + supporting + companion expressions compare canonical bytes; 11 passed, 97 blocked, 0 failed. |
| R12 — truth table | **Blocked by normative inputs** | Not run or claimed. |
| R12A — interpreter | **Blocked by normative input** | Reviewed Informatica evaluation-semantics specification is explicitly missing and recorded as such. |
| R13 — construct matrix | **Implemented** | Counts/support/example for required construct classes; prior-output comparison can flag newly unsupported constructs. |
| R14 — coverage | **Implemented mechanically; R00 denominator ratification pending** | Separate discovery, parse, recovery, verification and truth-table metrics with named denominators; prior matched-percentage regression fails non-zero. |
| R15 — open questions | **Implemented** | 107 domain-addressed, code-free consolidated questions in the pilot. |
| R16 — run record | **Implemented with missing normative inputs declared** | Deterministic manifest pins source/member hashes, code SHA when resolvable, authority hashes/status, descriptor hash/version, config/counts; operational event separate. |
| R17 — one command / manifest input | **Partial** | `dq source register` and manifest-first `dq recover` implemented; one end-to-end command implemented. Fine-grained restartable subcommand per every internal stage remains. |
| R18 — run budget | **Mechanism implemented; production ceiling pending** | Wall/RSS measured operationally; optional external ceiling enforced non-zero. No ceiling invented by implementation. |

## Current pilot summary

- Source/record reconciliation: **pass**
- Parser completeness: **2,324 / 2,324**
- Mechanical primary-endpoint denominator: **108**, pending R00 ratification
- Recovery status: **106 unmatched / 2 semantic_ambiguity**
- Verification: **11 passed / 97 blocked_external / 0 failed**
- Deterministic output diff: **pass**
- Vendor-neutral semantics: **pass**
- Descriptor conflict gate: **implemented and exercised**
- Coverage regression gate: **implemented and exercised**
- Independent truth-table oracle: **not run / not claimed**
