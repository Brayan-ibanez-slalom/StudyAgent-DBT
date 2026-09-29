# dbt Analytics Engineering Certification — Official Blueprint

Transcribed from the **official dbt Labs study guide**, "dbt Analytics Engineering
Certification Exam Study Guide", updated for **dbt Core 1.11**.

- Exam guide: <https://www.getdbt.com/certifications/analytics-engineer-certification-exam>
- Study guide PDF: <https://www.getdbt.com/dbt-assets/certifications/dbt-certificate-study-guide-version-1-11>

[accessed 2026-09-29]

---

## Logistics (published)

| Item | Value |
|---|---|
| Duration | 2 hours |
| Format | Online proctored |
| **Length** | **65 questions** |
| **Passing score** | **65% or higher** — reported immediately |
| Version | dbt Core 1.11 |
| Price | $200 (each retake also $200) |
| Language | English, Japanese |
| Expiration | 2 years after award |
| Open book | No |
| Browsers | Caveon Web browsers |
| Recommended | SQL proficiency, 6+ months dbt experience |

### Scoring

> "The exam is scored on a point basis, with 1 point for each correct answer, and 0
> points for incorrect answers. All questions are weighted equally."

> "An undisclosed number of unscored questions will be included on each exam. These are
> unmarked and indistinguishable from scored questions."

### Still NOT published

- **Per-topic weighting.** "All questions are weighted equally" is a *per-question*
  statement. How many of the 65 land in each topic is not disclosed.
- How many of the 65 are unscored research items.

`exam_config.DOMAINS[*]["weight"]` therefore remains `None`, and
`test_weights_are_not_fabricated` fails the build if anyone adds one.

---

## Question formats

All six, per the guide:

Multiple-choice · Fill-in-the-blank · Matching · Hotspot · Build list ·
Discrete Option Multiple Choice (DOMC)

See [question-formats.md](question-formats.md). Note the official sample questions use
**four or five** options for single-answer items, which is why the authoring gate
accepts both.

---

## Topics Outline (official)

> "The dbt Analytics Engineering Certification Exam has been designed to assess the
> following topics and sub-topics."

Repo domain ids map one-to-one onto these topics.

### Topic 01 — Developing and optimizing dbt models → `ae-01`

| Task | Sub-topic (verbatim) |
|---|---|
| 1.1 | Identifying and verifying any raw object dependencies |
| 1.2 | Understanding core dbt materializations |
| 1.3 | Conceptualizing modularity and how to incorporate DRY principles |
| 1.4 | Using commands such as build, run, test, docs, show, snapshot, and seed |
| 1.5 | Creating a logical flow of models and building clean DAGs |
| 1.6 | Defining configurations in `dbt_project.yml` |
| 1.7 | Using dbt Packages |
| 1.8 | Creating Python Models |
| 1.9 | Providing access to users to models with the `grants` config |
| 1.10 | Creating snapshots in YAML |
| 1.11 | Selecting the optimal incremental strategy based on a dataset's characteristics |
| 1.12 | Validating model logic and schema definitions in dry-runs using the `--empty` flag |
| 1.13 | Running models in sample mode using the `--sample` flag |
| 1.14 | Understanding advanced dbt materializations such as microbatch |

### Topic 02 — Managing dbt models governance → `ae-02`

| Task | Sub-topic |
|---|---|
| 2.1 | Adding contracts to models to ensure the shape of models |
| 2.2 | Creating different versions of our models and deprecating the old ones |
| 2.3 | Defining constraints in YAML to enforce data integrity at the platform level |

### Topic 03 — Debugging data modeling errors → `ae-03`

| Task | Sub-topic |
|---|---|
| 3.1 | Understanding logged error messages |
| 3.2 | Troubleshooting using compiled code |
| 3.3 | Troubleshooting `.yml` compilation errors |
| 3.4 | Developing and implementing a fix and testing it prior to merging |
| 3.5 | Managing dbt behavior with flags |

### Topic 04 — Troubleshooting and optimizing dbt pipelines → `ae-04`

| Task | Sub-topic |
|---|---|
| 4.1 | Troubleshooting and managing failure points in the DAG |
| 4.2 | Using `dbt clone` |

### Topic 05 — Implementing dbt tests → `ae-05`

| Task | Sub-topic |
|---|---|
| 5.1 | Using generic, singular, custom, custom generic, and unit tests on a wide variety of models and sources |
| 5.2 | Testing assumptions for dbt models and sources |
| 5.3 | Implementing various testing steps in the workflow |

### Topic 06 — Implementing and maintaining external dependencies → `ae-06`

| Task | Sub-topic |
|---|---|
| 6.1 | Implementing dbt exposures |
| 6.2 | Implementing source freshness |

### Topic 07 — Leveraging the dbt state → `ae-07`

| Task | Sub-topic |
|---|---|
| 7.1 | Understanding state and state selection |
| 7.2 | Using `dbt retry` |

---

## Sub-topic share — a proxy, not a weight

dbt Labs publishes no per-topic weighting. The only defensible signal is how many
sub-topics each topic enumerates:

| Domain | Sub-topics | Share | ~Questions of 65 |
|---|---|---|---|
| `ae-01` Developing and optimizing dbt models | 14 | 45.2% | ~29 |
| `ae-03` Debugging data modeling errors | 5 | 16.1% | ~10 |
| `ae-02` Managing dbt models governance | 3 | 9.7% | ~6 |
| `ae-05` Implementing dbt tests | 3 | 9.7% | ~6 |
| `ae-04` Troubleshooting and optimizing dbt pipelines | 2 | 6.5% | ~4 |
| `ae-06` Implementing and maintaining external dependencies | 2 | 6.5% | ~4 |
| `ae-07` Leveraging the dbt state | 2 | 6.5% | ~4 |

> **This is a derived proxy for allocating study time.** It is not what dbt Labs says the
> exam contains. `exam_facts()` returns it as `subtopic_share_pct` with an explicit
> `proxy_warning`. Do not quote it as an official weight.

The one solid conclusion: **Topic 01 is nearly half the enumerated surface area.**
Everything in it — materializations, incremental strategy, snapshots, packages, Python
models, `grants`, `--empty`, `--sample`, microbatch — deserves disproportionate attention.

---

## Notable scope signals

Things the outline makes explicit that a general dbt practitioner might not expect:

- **`--empty` and `--sample` are named sub-topics** (1.12, 1.13). These are recent flags
  and easy to have never used. One of the ten official sample questions is about `--empty`.
- **Microbatch is called out by name** (1.14).
- **Git workflow is in scope** (3.4) — one sample question is about `git pull` vs
  `git fetch`.
- **`dbt clone` gets its own sub-topic** (4.2) despite the topic having only two.
- **Behaviour-change flags** (3.5) — the version-drift surface, explicitly examinable.
- **Unit tests sit alongside data tests** in a single sub-topic (5.1), so the distinction
  between them is fair game.

---

## Official sample questions

The guide ships 10 sample questions with explanations. They are the best available
calibration for item authoring — see [item-authoring-spec.md](item-authoring-spec.md).
Observed characteristics:

- Four or five options for single-answer items
- Stems are short; several are 1–2 sentences plus a code block
- Explanations name why each distractor fails — the same structure the `item_gate`
  requires via `distractor_traps` and `eliminated_by`
- At least one item is a log-reading diagnosis (`FAIL` → `SKIP` sequencing)

---

## Refresh policy

The guide is versioned against dbt Core. Re-check this file when:

- the study-guide version changes (currently dbt Core 1.11),
- a note's `**Verified:**` date passes 180 days,
- `cache_stats()` reports stale entries.
