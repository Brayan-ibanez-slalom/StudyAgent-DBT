---
mode: agent
model: Claude Opus 4.7 (copilot)
description: Author new exam items from docs.getdbt.com through the quality gate — the primary way this bank grows.
tools: ["item_gate", "balance_keys", "authored_ingest", "coverage_report", "cache_check", "cache_fetch", "cache_fetch_batch", "topic_search", "topic_read", "concept_lookup", "defect_scan", "bank_audit", "exam_facts", "question_full"]
---

# Author — write new items (Opus, heavy tier)

This bank is **authored**, not scraped. There is no dbt equivalent of the large public
question dumps that exist for cloud exams, and the third-party dbt material that does
exist frequently describes older dbt versions.

So authoring is the primary growth path, and the [item gate](../../docs/item-authoring-spec.md)
is the only admission standard.

## Model routing

Pinned to **Claude Opus 4.7**. Writing a distractor that is wrong in an *instructive* way
is the hardest generation task in this repo — a lazy distractor teaches nothing and a
careless one teaches something false.

## 1. Pick a target

```
coverage_report(track="ae")
```

Use `author_here` (tasks 2+ items short), worst gap first. Also check `format_gaps`: if
the bank is short on `fill_in_blank`, `build_list`, `matching`, or `domc`, **author those
formats**. A bank that drifts back to all multiple choice trains recognition instead of
recall.

## 2. Cache first, write second — never the reverse

This is the anti-hallucination rule and it is not negotiable.

```
cache_check("https://docs.getdbt.com/docs/build/incremental-strategy")
cache_fetch(...)   # only on a miss
```

Read the cached text. Write the `decision_hinge` **from** that text. Then build the
question around the hinge.

Writing the item first and hunting for a citation afterwards is exactly how a
plausible-but-false item gets in. The gate checks that 60% of the hinge's terms appear in
the cached page, so this order is also the only one that passes.

## 3. Write the item

```jsonc
{
  "id": "draft-001",
  "domain": "ae-02",
  "blueprint_task": "2.2",
  "qtype": "multiple_choice",
  "difficulty_estimate": "L3",

  "stem": "[actor + context] [requirement] [requirement] [hard limit] [lead-in?]",
  "option_texts": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "drill_answer": "B",

  "decision_hinge": "The single documented fact that decides this, in dbt's own words.",
  "sources": ["https://docs.getdbt.com/..."],

  "plausible_options": {"D": "<verbatim quote from the stem>"},
  "eliminated_by": {
    "A": "<verbatim quote from the stem>",
    "C": {"signal": "<verbatim stem quote>", "requires_fact": "<documented dbt fact>"}
  },
  "distractor_traps": {"A": "T4: ...", "C": "T3: ...", "D": "T8: ..."},
  "topics": ["knowledge/ae/01-developing-and-optimizing-models/incremental-models.md"]
}
```

### The check that decides whether the item is worth anything

`check_not_pure_elimination`: **at least one distractor must survive for a reader who
does not know the tested fact.** If every distractor dies to a stem signal, the item
tests reading comprehension, not dbt.

That is what `requires_fact` is for — it marks a distractor that only dies once you know
something documented.

### Distractor families — reach for T6 first

`T1` fabricated · `T2` wrong layer · `T3` confusable sibling · `T4` breaks a stated
requirement · `T5` right diagnosis wrong symptom · **`T6` stale behaviour** · `T7`
over-engineering · `T8` scope error

**T6 is the highest-value family for a dbt exam.** Version drift is where an experienced
practitioner's instincts actively mislead them: `tests:` vs `data_tests:`, pre-`dbt build`
workflows, hand-rolled SCD logic instead of snapshots, `packages.yml` where
`dependencies.yml` belongs.

Use the confusion-pair table in `.github/copilot-instructions.md` as a distractor source —
every row is a ready-made T3.

### Non-multiple-choice formats

See [docs/question-formats.md](../../docs/question-formats.md) for required payload. Quick
guidance on what makes each one *hard* rather than merely different:

- **`build_list`** — put distractor steps in `build_items` that are not in the answer.
  Ordering alone is too easy.
- **`matching`** — `match_right` must be longer than `match_left` (the gate enforces it),
  and the extras should be plausible, not filler.
- **`hotspot`** — the wrong line should be *syntactically valid*. A syntax error is
  findable without dbt knowledge.
- **`fill_in_blank`** — if you need more than ~4 `accepted_answers`, the blank is
  ambiguous. Rewrite it.
- **`domc`** — write distractors that each look individually reasonable. DOMC defeats
  elimination, so an option that is only wrong *relative to another option* does not work.

## 4. Gate it

```
item_gate(path="my-batch.json")
```

Fix every **fatal failure**. Read every **warning** and decide — `key is not the longest
option` and `option length parity` are prompts to look, not verdicts.

Structural giveaways the gate will catch: the key being the single longest option, the
key echoing stem wording, a term appearing only in the stem and the key, and the key
being the odd one out by opening verb.

## 5. Balance and admit

```
balance_keys()             # dry run
balance_keys(write=True)   # if the batch is skewed
authored_ingest()          # dry run
authored_ingest(write=True)
```

`check_key_balance` is a **batch** property — no single item can fail it. It uses a
Bonferroni-corrected binomial tail, so it fires on real skew, not noise.

## 6. Verify the bank is still healthy

```
bank_audit()
defect_scan(defect="key_longest")
```

## Rewriting existing items

`defect_scan` is the rewrite queue, worst first. When you replace an item:

```
retire_superseded({"Q-AU-DBTAE-004": "Q-AU-DBTAE-031"}, reason="key was the longest option", write=True)
```

Never delete. Retired items stay for provenance and are filtered out of `drill_pick`.

## Forbidden

- ❌ Writing the item before reading the cached source
- ❌ Citing a blog or course instead of an official dbt Labs host
- ❌ Inventing a config key, flag, or YAML property to make a distractor
- ❌ Authoring only multiple choice because it is easier
- ❌ Bypassing `item_gate` by editing `index.json` directly
- ❌ Asserting a domain weight, question count, or passing score — dbt publishes none
