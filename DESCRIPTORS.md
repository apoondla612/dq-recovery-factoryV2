# Rule-type descriptor contract

Descriptors are human-owned JSON data under an external directory passed with `--descriptors`. Adding a descriptor requires no code change.

Each descriptor requires:

```json
{
  "name": "governed_rule_type_name",
  "version": "1",
  "shape": ["... shape emitted by V2 ..."],
  "parameters": [
    {"name": "field", "slot": 1},
    {"name": "limit", "slot": 2}
  ],
  "outcomes": ["VALID", "INVALID", "NOT_EVALUATED"],
  "example": "human-authored example"
}
```

The shape is recursively validated against the V2 REQ-R05A representation. Concrete leaves are replaced by typed positional placeholders (`FIELD`, `STR`, `NUM`, `NULL`, `BOOL`, `EMPTY`, `OUTCOME`, `REF`). Operators, function names, arity and order remain structural.

Matching evaluates **every** descriptor with exactly the same declared shape. Parameter `slot` values bind to the corresponding concrete leaf. Zero complete matches is unmatched; one is matched; more than one is a hard descriptor conflict. A non-complete parse/bind state cannot be promoted to matched.

This file defines the implementation contract only. It does not name any governed customer rule type and is not a substitute for the human-owned descriptor set.
