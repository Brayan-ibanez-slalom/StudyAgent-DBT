# Item authoring spec

This repo's question bank is **authored**, not scraped. There is no large public dump of
dbt certification questions the way there is for cloud exams, and the third-party dbt
material that does exist is frequently wrong about current behaviour.

That makes the authoring gate the most important component here. It is implemented in
[scripts/item_qa.py](../scripts/item_qa.py) and reachable as the `item_gate` MCP tool.
`authored_ingest` re-runs it, so there is no side door into the bank.

---

## 1. The anti-hallucination rule

The dangerous part of a generated item is never the prose. It is the **single documented
fact that decides the answer.**

Every candidate item must declare:

```jsonc
{
  "decision_hinge": "An ephemeral model is not built in the warehouse; it is interpolated into downstream models as a common table expression.",
  "sources": ["https://docs.getdbt.com/docs/build/materializations"]
}
```

The gate then checks that **at least 60% of the hinge's content terms appear in the
cached text of a cited URL on disk.** No cached page, no pass. Terms not found, no pass.

So the authoring order is always:

1. `cache_check(url)` → `cache_fetch(url)` if it is a miss
2. Read the cached text
3. Write the hinge **from** that text
4. Write the stem and options **around** the hinge

Never the reverse. Writing the item first and hunting for a citation afterwards is how
plausible-but-false items get in.

`check_source_is_authoritative` additionally requires at least one source on
`docs.getdbt.com`, `getdbt.com`, or `learn.getdbt.com`. A blog post restating dbt
behaviour is not a source.

---

## 2. Stem anatomy

```
[Actor + context]      A data team maintains a model that processes 400M rows daily.
[Requirement 1]        The model must only process rows loaded since the last run.
[Requirement 2]        Late-arriving records must update rows already written.
[Hard limit]           The warehouse does not support MERGE on this table type.
[Lead-in question]     Which configuration meets these requirements?
```

Rules:

- Stem at or under **95 words** (warning above).
- At least **one** requirement clause (`must` / `needs to` / `requires` / `should`).
- State hard limits explicitly. They are what make a distractor die.
- **Do not forbid an approach outright.** Prefer a comparative qualifier so every option
  is workable and the trade-off decides. A prohibition lets the candidate answer by
  spotting the banned option.

---

## 3. The qualifier decides the answer, not the stem

When the stem contains a CAPS qualifier (`LEAST`, `MOST`, `BEST`, `FEWEST`, `ONLY`,
`FIRST`), **at least two options must be functionally correct**, and the qualifier is
what separates them. This is enforced by `check_qualifier_has_rivals`.

If only one option actually works, drop the qualifier — it is decorative, and decorative
qualifiers teach the learner to ignore them.

| Qualifier | What it should select for on a dbt exam |
|---|---|
| **LEAST operational overhead** | The built-in dbt feature over a hand-rolled macro |
| **MOST efficient / FEWEST rebuilds** | Incremental + state selection over full refresh |
| **BEST practice** | The pattern the dbt docs actually recommend, not merely one that runs |
| **FIRST** | Ordering questions — usually a `build_list` in disguise; consider that format |
| **ONLY** | Access modifiers, permissions, licence scopes — exclusivity is the point |

---

## 4. Proving the distractors are real

Two independently written evidence fields, both checked against the stem verbatim.

### `plausible_options` — options that genuinely satisfy every stated requirement

```jsonc
"plausible_options": {
  "B": "Late-arriving records must update rows already written",
  "D": "Late-arriving records must update rows already written"
}
```

Each value must be a **verbatim quote from the stem**, at least 20 characters, and not
the lead-in question. Otherwise plausibility is just the author's word.

### `eliminated_by` — every remaining distractor needs a verdict

```jsonc
"eliminated_by": {
  "A": "The model must only process rows loaded since the last run",
  "C": {
    "signal": "The warehouse does not support MERGE on this table type",
    "requires_fact": "The delete+insert incremental strategy removes matching rows and re-inserts them rather than issuing a MERGE statement."
  }
}
```

- A **bare string** means the option dies to a stem signal alone — any reader can drop it
  without knowing dbt.
- A **dict with `requires_fact`** means it only dies once you know a documented fact.
  That fact is verified against the cached sources at the same 60% bar as the hinge, and
  the option then counts as a genuine surviving rival.

### The check that matters most

`check_not_pure_elimination`: **at least one distractor must survive for a reader who
does not know the tested fact.** If every distractor dies to a stem signal, the item
tests reading comprehension, not dbt.

`check_elimination_signals_distinct`: one sentence must not kill the whole board.

---

## 5. Distractor taxonomy

| Family | Name | Definition | dbt example |
|---|---|---|---|
| **T1** | Fabricated | A config, command, or feature that does not exist | `materialized='cached'` |
| **T2** | Wrong layer | Real feature, wrong place in the stack | Fixing a data-quality issue with a warehouse grant |
| **T3** | Confusable sibling | Real feature from the right family, wrong member | `packages.yml` vs `dependencies.yml`; data test vs unit test |
| **T4** | Breaks a stated requirement | Works in general, violates a clause in the stem | Full refresh when the stem forbids reprocessing |
| **T5** | Right diagnosis, wrong symptom | Explains a different failure than the one described | Blaming `on_schema_change` when the error is a dependency cycle |
| **T6** | Stale behaviour | True in an older dbt version, not current | `tests:` vs `data_tests:`; pre-`dbt build` workflows |
| **T7** | Over-engineering | A custom macro where a built-in exists | Hand-rolled SCD logic instead of a snapshot |
| **T8** | Scope error | Right idea at the wrong grain | Project-level config where the stem needs model-level |

Rules:

- Tag each distractor: `"distractor_traps": {"A": "T3: dependencies.yml installs packages — it declares cross-project refs"}`
- **T1 and T4 cannot coexist with `plausible_options`** — a fabricated or
  requirement-breaking option is not a surviving rival. Enforced by
  `check_trap_consistency`.
- At least **2 distinct trap families** per item (warning).
- **T6 is the highest-value family for dbt.** Version drift is the single most common way
  third-party dbt material is wrong, and it is where an experienced practitioner's
  instincts actively mislead them.

---

## 6. Structural giveaways the gate rejects

These are the ways an item can be answered **without any dbt knowledge**:

| Check | Exploit it closes |
|---|---|
| `check_key_not_the_longest_option` | "Pick the longest option and read nothing." Rank, not margin, is the exploit. A tie is fine. |
| `check_no_lexical_giveaway` | The key echoes distinctive stem wording more than any distractor. |
| `check_no_leaked_term` | One loud word appears in the stem and the key and nowhere else. Aggregate overlap can look balanced while this still points at the key. |
| `check_key_not_odd_one_out` | Every distractor opens with the same verb and the key does not — findable by shape. |
| `check_option_not_checklist` | An option over 55 words is a checklist restating the stem; requirement-counting then beats knowing the answer. |
| `check_option_parity` | Length spread over 45% from the median. |
| `check_key_balance` | A **batch** property: the key sitting on the same letter too often. Tested with a Bonferroni-corrected binomial tail, so it fires on real skew, not noise. Fix with `balance_keys`. |

---

## 7. Difficulty ladder

| Level | What makes it that level |
|---|---|
| **L1** | Single-fact recall. What does `dbt seed` do? |
| **L2** | Recall plus one distinction. Seed vs source. |
| **L3** | Apply a config to a described situation. Which incremental strategy fits? |
| **L4** | Two interacting facts, or a diagnosis from symptoms. Why did this model silently drop a column? |
| **L5** | Multi-step reasoning with a non-obvious hinge, or a version-drift trap. |

`difficulty_estimate` starts as an authoring guess (`difficulty_source: "authored"`).
Once a question has 2+ recorded attempts, `difficulty_observed` overwrites it from
measured accuracy and sets `difficulty_source: "observed"`. Measurement beats assertion.

---

## 8. Format-specific rules

Multiple choice is the easiest format to author and the least representative of the real
exam. `coverage_report` reports a `format_gaps` floor per track for exactly this reason.

See [question-formats.md](question-formats.md) for each format's required payload. The
gate's `check_format_payload` rejects an item missing the fields its renderer needs, and
`check_distractor_plausible_for_format` enforces that non-letter formats still have
decoys (more right-hand options than left in `matching`, 3+ regions in `hotspot`, 3+
steps in `build_list`).

---

## 9. Required record fields

Minimum for the gate to run:

```jsonc
{
  "id": "draft-001",
  "domain": "ae-02",
  "blueprint_task": "2.2",
  "qtype": "multiple_choice",
  "difficulty_estimate": "L3",
  "stem": "...",
  "option_texts": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "drill_answer": "B",
  "decision_hinge": "...",
  "sources": ["https://docs.getdbt.com/..."],
  "plausible_options": {"D": "<verbatim stem quote>"},
  "eliminated_by": {"A": "<verbatim stem quote>", "C": {"signal": "...", "requires_fact": "..."}},
  "distractor_traps": {"A": "T4: ...", "C": "T3: ...", "D": "T8: ..."},
  "topics": ["knowledge/ae/01-developing-and-optimizing-models/incremental-models.md"]
}
```

Drop the file in `question-bank/authored/`, then:

```bash
item_gate(path="my-batch.json")     # verdicts + warnings
balance_keys()                       # dry run; --write to apply
authored_ingest()                    # dry run; write=True to admit
```

---

## 10. Known gaps

- The gate cannot detect a hinge that is **true but irrelevant** to the stem. A human
  still has to read the item.
- `check_requires_fact_addresses_its_option` catches the worst case — a `requires_fact`
  that merely restates the key and never mentions the option it supposedly eliminates —
  but it is a **warning**, not a reject, because a fact supporting the key genuinely can
  be the fact that kills a rival.
- No check yet detects version drift in the **stem** (an item that describes pre-1.x
  behaviour as current). Cache freshness is the only guard, which is why
  `cache_stats()` staleness matters.
