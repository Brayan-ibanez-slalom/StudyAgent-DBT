# Question bank

```
question-bank/
  index.json     the sealed bank — written only by MCP tools
  authored/      drafts awaiting the quality gate
  raw/           immutable third-party dumps, if any are ever added
```

## Why this starts empty

There is no dbt equivalent of the large public question dumps that seeded this repo's AWS
predecessor. The third-party dbt certification material that exists is thin and frequently
describes behaviour from older dbt versions, so seeding from it would poison the bank.

Items are authored from `docs.getdbt.com` through the gate instead. Run `/author`.

Have a third-party practice exam to draw inspiration from instead? See the
[import-practice-questions skill](../.github/skills/import-practice-questions/SKILL.md) —
it turns a pasted quiz dump into original, independently-verified items through the same
gate, rather than reproducing it.

## Record shape

```jsonc
{
  "id": "Q-AU-DBTAE-001",
  "source": "authored",
  "domain": "ae-02",                    // from exam_config.DOMAINS
  "track": "ae",
  "blueprint_task": "2.2",
  "qtype": "multiple_choice",           // one of seven; decides the answer shape
  "difficulty_estimate": "L3",
  "difficulty_source": "authored",      // becomes "observed" after 2+ attempts

  "stem": "...",
  "option_texts": {"A": "...", "B": "...", "C": "...", "D": "..."},
  // plus format payload where relevant:
  //   accepted_answers | match_left + match_right | hotspot_targets | build_items
  //   code_block + code_language

  "drill_answer": "B",
  "drill_answer_short": "One line naming the decisive dbt behaviour.",
  "drill_rationale": "...",
  "decision_hinge": "The single documented fact that decides the answer.",
  "options_analysis": "...",
  "distractor_traps": {"A": "T3: ...", "C": "T6: ...", "D": "T4: ..."},
  "plausible_options": {"D": "<verbatim stem quote>"},
  "eliminated_by": {"A": "<verbatim stem quote>"},

  "topics": ["knowledge/ae/01-developing-and-optimizing-models/incremental-models.md"],
  "sources": ["https://docs.getdbt.com/docs/build/incremental-models"],
  "verified": true,
  "status": "verified",                 // unsealed | verified | concept-only | disputed
  "sealed_by": "authored_via_item_qa",
  "sealed_at": "2026-09-29",
  "seal_confidence": 90
}
```

## ID scheme

`Q-<provenance>-<exam code>-<NNN>`

| Provenance | Prefix (AE / Architect) |
|---|---|
| Authored here | `Q-AU-DBTAE-` / `Q-AU-DBTARCH-` |
| Official practice material | `Q-OF-DBTAE-` / `Q-OF-DBTARCH-` |
| Community-sourced | `Q-CO-DBTAE-` / `Q-CO-DBTARCH-` |
| Third-party practice test | `Q-PA-DBTAE-` / `Q-PA-DBTARCH-` |

Always reference a question by id. Never paraphrase when you can quote by id.

## Status vocabulary

| Status | Meaning | Drillable |
|---|---|---|
| `unsealed` | Stubbed, no verified answer yet | No |
| `verified` | Answer derived and cited to dbt docs, confidence >= 70 | Yes |
| `concept-only` | Right principle, no single doc sentence states it | Yes, flagged |
| `disputed` | Our reasoning contradicts the source's claimed answer | No |

Plus `retired: true` — rewritten and superseded, kept for provenance, never served.

## Workflow

```
item_gate(path="batch.json")   # fatal failures block admission
balance_keys()                 # spread the key across letters
authored_ingest(write=True)    # admit
verify_seal(qid, deep=True)    # confirm the citation still holds
```

Rules: [.github/instructions/question-bank.instructions.md](../.github/instructions/question-bank.instructions.md)
Spec: [docs/item-authoring-spec.md](../docs/item-authoring-spec.md)
Formats: [docs/question-formats.md](../docs/question-formats.md)
