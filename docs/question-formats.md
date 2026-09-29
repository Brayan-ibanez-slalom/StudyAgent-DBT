# Question formats — record shapes and grading semantics

dbt exams use six question formats. Every one is supported by
`mcp-server/study_agent_mcp/grading.py`, and every one has unit tests in
`mcp-server/tests/test_grading.py`.

[source: getdbt.com/dbt-certification FAQ — accessed 2026-09-29]

**Never reformat a question into multiple choice because another format is harder to
serve.** Practising only multiple choice trains the wrong muscle: recognition instead of
recall. `coverage_report` enforces a floor per format for exactly this reason.

---

## Shared fields

Every question record carries these regardless of format:

```jsonc
{
  "id": "Q-AU-DBTAE-001",
  "domain": "ae-02",              // must exist in exam_config.DOMAINS
  "blueprint_task": "2.2",
  "qtype": "...",                 // one of the six below
  "stem": "...",
  "drill_answer": ...,            // shape depends on qtype
  "drill_answer_short": "One line naming the decisive dbt behaviour.",
  "decision_hinge": "The single documented fact that decides the answer.",
  "sources": ["https://docs.getdbt.com/..."],
  "topics": ["knowledge/ae/01-developing-and-optimizing-models/incremental-models.md"],
  "difficulty_estimate": "L3",
  "verified": true,
  "status": "verified",
  "seal_confidence": 85
}
```

Optional on any format:

```jsonc
{
  "code_block": "{{ config(materialized='incremental') }}\nselect ...",
  "code_language": "sql"
}
```

---

## 1. `multiple_choice`

```jsonc
{
  "qtype": "multiple_choice",
  "option_texts": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "drill_answer": "B"
}
```

- Exactly 4 options (gate check).
- Answer is one letter. `"b."`, `"Answer: B"`, and `"B"` all parse.
- Two letters is a format error, not a wrong answer.

## 2. `multiple_response`

```jsonc
{
  "qtype": "multiple_response",
  "option_texts": {"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."},
  "drill_answer": "A,C"
}
```

- 4–6 options.
- **Exact-set match.** A partial selection is wrong even though `score` reports 0.5 —
  `score` is for coaching only.

## 3. `fill_in_blank`

```jsonc
{
  "qtype": "fill_in_blank",
  "stem": "The ____ macro returns true only on an incremental run.",
  "drill_answer": "is_incremental()",
  "accepted_answers": ["is_incremental()", "is_incremental"]
}
```

- Stem **must** contain `____` (gate check).
- `accepted_answers` is required and must list every reasonable spelling. Normalization
  already handles case, surrounding backticks/quotes, accents, and whitespace — so list
  genuine variants (with/without parentheses, with/without a `dbt ` prefix), not casing.
- Authoring rule: if more than ~4 variants are needed, the blank is ambiguous. Rewrite it.

## 4. `matching`

```jsonc
{
  "qtype": "matching",
  "match_left": ["snapshot", "seed", "ephemeral"],
  "match_right": ["SCD Type 2 history", "CSV loaded into the warehouse",
                  "Inlined as a CTE", "Rebuilt on every run"],
  "drill_answer": {"snapshot": "SCD Type 2 history",
                   "seed": "CSV loaded into the warehouse",
                   "ephemeral": "Inlined as a CTE"}
}
```

- **`match_right` must be longer than `match_left`** (gate check). With equal lengths the
  last pair is free by elimination.
- Accepts `{"a": "b"}` or `"a -> b, c -> d"`.
- All pairs must be right for `correct: true`; `score` reports the fraction.

## 5. `hotspot`

```jsonc
{
  "qtype": "hotspot",
  "code_block": "1  {{ config(materialized='incremental') }}\n2  select * from {{ source('raw','orders') }}\n3  {% if is_incremental() %}\n4    where updated_at > (select max(updated_at) from this)\n5  {% endif %}",
  "hotspot_targets": ["line-1", "line-2", "line-3", "line-4", "line-5"],
  "drill_answer": "line-4"
}
```

- At least 3 targets (gate check) or it is a coin flip.
- Selecting a target not in `hotspot_targets` is a **format error**, so a typo does not
  get scored as a wrong answer.
- Extra selections make the answer wrong.

## 6. `build_list`

```jsonc
{
  "qtype": "build_list",
  "stem": "Order the commands a CI job runs for a Slim CI check.",
  "build_items": ["dbt deps", "dbt seed", "dbt build --select state:modified+",
                  "dbt compile"],
  "drill_answer": ["dbt deps", "dbt compile", "dbt build --select state:modified+"]
}
```

- **Order is graded.** Right items in the wrong order is wrong, and the detail says so.
- `build_items` may contain distractor steps that do not appear in `drill_answer` — this
  is the format's main source of difficulty, so use it.
- At least 3 items (gate check).
- Accepts `"a, b, c"` or a numbered list.

## 7. `domc` — Discrete Option Multiple Choice

```jsonc
{
  "qtype": "domc",
  "option_texts": {"A": "...", "B": "...", "C": "..."},
  "drill_answer": "B"
}
```

DOMC shows options **one at a time** and the candidate accepts or rejects each without
being able to revise. It defeats elimination strategies, which is precisely why dbt uses
it — and why it must be drilled in its real form.

- 3–8 options.
- Answer is `{"A": "N", "B": "Y", "C": "N"}` or `"A:N, B:Y, C:N"`.
- **Every** option needs a verdict. Accepting a distractor is as wrong as rejecting the
  key. A missing verdict is incorrect, not ignored.

**Serving protocol for the drill agent:** present option A alone, take the Y/N, present
option B, and so on. Do not show the remaining options early — that turns it into
multiple choice.

---

## Adding a seventh format

1. Add it to `exam_config.QUESTION_TYPES` with its `answer_shape`.
2. Add `_grade_<name>` plus a branch in `grading.grade`.
3. Add a rendering branch in `grading.render_question` and a line in
   `grading.answer_instruction`.
4. Add payload validation to `item_qa.check_format_payload`.
5. Add a `Test<Name>` class to `mcp-server/tests/test_grading.py`.

`test_every_format_has_an_instruction` fails if step 3 is skipped.
