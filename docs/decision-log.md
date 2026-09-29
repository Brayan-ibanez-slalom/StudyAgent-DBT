# Decision log

Append-only. Newest last. Record *why*, not *what* — the code already says what.

---

## 2026-09-29 — Repo created as a port of StudyAgent-AIP-C01

Ported the topic-first, cache-first, MCP-first study architecture from the AWS AIP-C01
sibling. Reusable as-is: the drill protocol and its guardrails, the seal/verify pipeline,
the cache layer, the knowledge-note contract and index builder, the authoring gate's
evidence model, and the defect-scan/retire workflow.

## 2026-09-29 — Both certifications in one repo, split by `track`

dbt Labs currently offers two certifications: Analytics Engineering (whose learning path
and study guide call it "dbt Certified Developer") and Architect. They share a question
format set, a scoring model, a documentation source, and most of the tooling.

Two repos would duplicate the entire MCP server to change a constant. Instead every
domain id is prefixed with its track (`ae-*`, `arch-*`) and `drill_pick`, `verify_all`,
`coverage_report`, and `ingest_scan` all take an optional `track` filter. Progress is
tracked per domain, so the two tracks never contaminate each other's scorecard.

## 2026-09-29 — All exam metadata centralised in `exam_config.py`

The predecessor scattered `DOMAIN_WEIGHTS`, `DOMAIN_KEYWORDS`, `TASKS`, `VALID_DOMAINS`,
and ID prefixes across ten files, so retargeting the repo meant hunting constants and
hoping none were missed.

`exam_config.py` is now the only place any of that lives. `repo.py` imports
`VALID_DOMAINS` from it, `build_topic_index.py` derives the folders to scan from it,
`bootstrap_repo.py` generates the scorecard rows from it, and
`test_exam_config.py` asserts the invariants (domain id matches folder number, task
major number matches domain number, ID prefixes are unique).

Adding a domain is now a single edit plus `python3 scripts/bootstrap_repo.py`.

## 2026-09-29 — Weights are `None`, and a test enforces it

dbt Labs publishes no section weights, no question count, and no passing score. It states
only that all questions are weighted equally and that the result is a percentage.

A plausible-looking weight table would be the single most damaging thing this repo could
contain, because every downstream study decision would inherit it. So:

- `DOMAINS[*]["weight"]` is `None` and `EXAM_FACTS[*]["weights_published"]` is `False`.
- `progress/scorecard.md` has **no weighted column**.
- `coverage_report` uses a flat `TARGET_PER_TASK`, not a share of an exam.
- `exam_facts()` returns an explicit `not_published_by_dbt_labs` list.
- `test_weights_are_all_none` fails the build if anyone adds one.

Domains themselves are derived from the public learn.getdbt.com learning paths and are
labelled with their `provenance` so the derivation is auditable.

## 2026-09-29 — New module: `grading.py`, because dbt uses six question formats

The predecessor graded letter sets only, which is correct for AWS exams. dbt exams also
use fill-in-the-blank, matching, hotspot, build list, and Discrete Option Multiple Choice.

Serving all of those as multiple choice would train recognition instead of recall, so the
grading engine was written first and the drill tools were built on top of it. Every
format has a normalizer (accept what a human would plausibly type), a grader, a rendering
branch, and a unit-test class.

Two design points worth keeping:

- **`score` never flips `correct`.** dbt awards one point or zero. Fractional scores
  exist for coaching feedback only.
- **A malformed answer is an `ANSWER_FORMAT` error, not a wrong answer.** Typing
  `line-9` on a hotspot with three regions should not be recorded as a knowledge failure.

`coverage_report` reports a `format_gaps` floor so the bank cannot quietly drift back to
being all multiple choice.

## 2026-09-29 — Two grading bugs caught by unit tests before first use

1. `letters()` matched any `[A-Z]`, so a user replying `"Answer: B"` was parsed as
   `{A, B, E, N, R, S, W}` and rejected. Now matches `\b([A-F])\b` — standalone option
   tokens only.
2. `qtype_of` silently coerced an unknown `qtype` to `multiple_choice`, meaning a typo in
   a seal would quietly downgrade a `build_list` item. `grade()` now rejects a declared
   but unknown qtype outright.

Both were found by tests written before the code ran. Keep writing them that way.

## 2026-09-29 — The bank starts empty, and authoring gets the expensive model

There is no dbt equivalent of the ExamTopics dump that seeded the predecessor, and the
third-party dbt material that exists is frequently describing older dbt versions.

So the bank is authored from `docs.getdbt.com` through the `item_gate`, `/author` is
pinned to Opus, and `check_source_is_authoritative` requires at least one source on an
official dbt Labs host. A blog post restating dbt behaviour is not a source.

This also makes **T6 (stale behaviour)** the highest-value distractor family for this
exam — version drift is where an experienced practitioner's instincts actively mislead
them.

## 2026-09-29 — `_services.json` became `_concepts.json`

AWS has services; dbt has commands, configs, and objects. A note declares its lookup keys
with a `**Concepts:**` header line and `build_topic_index.py` harvests them, so the index
is generated rather than hand-maintained — the predecessor's `_services.json` was an
empty stub for months because nothing generated it.

## 2026-09-29 (later) — Official study guides found; derived domains replaced

The user located `getdbt.com/certifications/analytics-engineer-certification-exam`, which
links a **public, non-gated study guide PDF**. The Architect equivalent exists at
`/certifications/dbt-architect-certification-exam` with its own guide (V.6.4).

Earlier in the day I concluded, and the repo encoded, that no official blueprint existed
and derived domains from the learn.getdbt.com learning paths. That was **wrong** — I had
searched `learn.getdbt.com` and `docs.getdbt.com` but not the `/certifications/` path on
the marketing site. Lesson: for certification metadata, check the vendor's *marketing*
site alongside its docs and LMS.

What the guides actually publish, which the repo previously claimed was unavailable:

- **65 questions** and a **65% passing score**, for both exams
- AE targets **dbt Core 1.11**; the Architect guide is **V.6.4**
- An **official numbered topic outline** with sub-topic bullets — 7 topics for AE, 8 for
  Architect
- 10 sample questions with explanations, per exam

All AE and Architect domains were rewritten to match the official topics one-to-one, with
task titles quoted verbatim and `provenance` citing the guide. The derived 5-domain AE
structure and 4-domain Architect structure are gone.

Knock-on changes: `check_option_count` now accepts 4 **or** 5 options for single-answer
items, because the official samples use both.

## 2026-09-29 (later) — Weights are still unpublished, so the proxy is explicit

The guides publish the topic outline and the exam length, but still **not** how many of
the 65 questions fall in each topic. Both say only "All questions are weighted equally",
which is a per-question statement, not a per-topic one.

So `weight` stays `None`, and the renamed `test_weights_are_not_fabricated` now asserts
both things at once: no domain may carry a weight, and `question_count` / `passing_score_pct`
**must** be populated (they are published now, and silently leaving them `None` would be
its own inaccuracy).

The defensible proxy is sub-topic count: AE Topic 1 enumerates 14 sub-topics, Topic 4
enumerates 2. `subtopic_share()` and `estimated_questions()` expose that, and
`exam_facts()` ships it with a `proxy_warning` telling the caller not to present it as an
official weight. Because coverage targets are flat per task, the same proxy already falls
out of `coverage_report` without extra machinery.

Most actionable consequence: **AE Topic 1 is ~45% of the enumerated surface**, and on the
Architect exam **deferral appears in four separate sub-topics** (3.8, 4.1, 4.10, 4.11).

## 2026-09-29 (later) — Review pass: `drill_why` could leak the key before grading

Two independent review agents audited the code and the docs. The one finding that
mattered: `drill_why` returned `drill_answer` for any sealed question, gated only by a
docstring saying "use after grading". A docstring is not enforcement — a single
premature call during a drill hands the learner the answer.

It now refuses unless the question appears in `attempts.jsonl`, using the same
`_guard` / `user_override` pattern as the other drill guardrails. Review of an
unattempted question is still possible through `question_full(include_answer=True)`,
which is explicitly named as a review tool, so nothing legitimate is blocked.

Smaller fixes from the same pass: unresolvable topic references were being stored as
`None` in a question's `topics` list; `observed_difficulty` raised `KeyError` on a record
missing `id`; `balance_keys` decided list-vs-object file shape by re-reading a file it
had already mutated in memory, and its letter swap created `None` values to delete them
again. `item_qa` now imports `qtype_of` and letter parsing from `grading` instead of
reimplementing them, so the gate and the drill engine cannot disagree about what format
an item is.

## 2026-09-29 (later) — Stale docs became a test, not a chore

The domain rewrite left eight markdown files naming knowledge folders that no longer
existed. Prose does not fail a build, so it rotted silently — and the docs-audit agent
itself missed two of the eight (both in `seal.prompt.md`).

`mcp-server/tests/test_docs_consistency.py` now parses every markdown file for
`knowledge/<track>/<dir>` paths, bare `<track>/<dir>/<note>` planned-topic ids, and
`ae-NN` / `arch-NN` domain ids, and fails if any names something absent from
`exam_config.DOMAINS`. It also asserts the folders on disk match the config, and that
authored drafts use real domains and tasks.

It found all eight immediately, including the two the agent missed. Any future domain
rename now breaks the build instead of quietly misleading a reader.

`docs/domain-rubric.md` was rewritten from scratch — every row of its tie-breaker table
had described the old derived domains and would have actively misfiled questions.


