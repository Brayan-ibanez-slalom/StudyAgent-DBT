---
applyTo: "question-bank/**"
---

# Question bank rules

- Never modify `question-bank/raw/` — any third-party dump is immutable evidence.
- Never hand-edit `index.json`. It is written by `ingest_seal`, `authored_ingest`,
  `retire_superseded`, and `difficulty_observed`.
- Question records are lean pointers: identity, `domain`, `blueprint_task`, `qtype`, the
  question payload, the sealed key and rationale, `topics[]`, `sources[]`, and seal
  metadata. Detailed teaching belongs in `knowledge/`, not inflated into the record.

## Sealing standard

A question is `verified: true` only when the Sealer has:

1. Reasoned through every option independently, without reading any claimed answer first
2. Cited the deciding fact to a note (which itself cites `docs.getdbt.com`) or directly
   to a cached dbt Labs URL
3. Checked that the behaviour is **current**, not from an older dbt version
4. Written a self-critique it could not poke a hole in
5. Assigned `seal_confidence >= 70`

If `seal_confidence < 70` → keep `verified: false` and append to
`progress/needs-review.md`.

If independent reasoning disagrees with a source's claimed answer → `ingest_dispute`.
Disputed questions are excluded from `drill_pick` until reconciled.

## Format rules

`qtype` must be one of the seven in `exam_config.QUESTION_TYPES`. `drill_answer`'s shape
follows from it, and `ingest_seal` validates the key by grading it against itself — a key
that does not grade as correct is rejected.

Format-specific payload is **required**, not optional:

- `fill_in_blank` → `accepted_answers`, and `____` in the stem
- `matching` → `match_left`, `match_right` (right must be longer than left)
- `hotspot` → `hotspot_targets` (3+)
- `build_list` → `build_items` (3+), and the ordered key must only use those items

## Authoring flow

Drafts go in `question-bank/authored/` as JSON. Then:

```
item_gate(path="...")      # verdicts; fatal failures block admission
balance_keys()             # dry run — spread the key across letters
authored_ingest()          # dry run; write=True to admit
```

The gate is the **only** admission standard. There is no side door. See
[docs/item-authoring-spec.md](../docs/item-authoring-spec.md).

## Retiring, never deleting

A rewritten item is retired via `retire_superseded({old: new}, reason=...)`. It stays in
the bank for provenance with `retired: true` and `superseded_by`, and `drill_pick`
filters it out. Never delete an entry or silently overwrite one.

## Bank health

- `defect_scan` ranks servable items by authoring defect, worst first — the rewrite queue.
- `bank_audit` runs the reusable checks over everything sealed.
- `coverage_report` shows task gaps **and** `format_gaps`. A bank that drifts back to all
  multiple choice is a defect, not a convenience.
