# StudyAgent-DBT

An agentic study workbench for the two **dbt Labs certifications**, built as a local MCP
server plus a verified knowledge base.

| Track | Exam |
|---|---|
| `ae` | **dbt Analytics Engineering Certification** — the learning path and study guide call it the *dbt Certified Developer* exam |
| `arch` | **dbt Architect Certification** |

Ported from [`StudyAgent-AIP-C01`](../StudyAgent-AIP-C01) (AWS). Same topic-first,
cache-first, MCP-first architecture; different source of truth and a multi-format grading
engine.

---

## What makes this different from a flashcard app

- **Nothing is asserted without a citation.** Every question's answer is sealed against a
  cached `docs.getdbt.com` page, and the authoring gate rejects any item whose deciding
  fact cannot be found in that cached text.
- **All six dbt question formats are drilled in their real form** — including Discrete
  Option Multiple Choice, where options are shown one at a time and you cannot revise.
  Practising only multiple choice trains recognition instead of recall.
- **Reasoning is graded, not just the answer.** `drill_grade_reasoned` compares your
  stated reason against the sealed rationale, so "right for the wrong reason" is caught.
- **No invented exam facts.** Domains are the official topic outlines from the dbt Labs
  study guides. Per-topic weighting is *not* published, so this repo has none — and a
  unit test fails the build if anyone adds one.

---

## Getting started

```bash
git clone <this repo> && cd StudyAgent-DBT
./scripts/setup.sh
```

That creates the venv, installs deps, generates the directory skeleton and progress
artifacts from `exam_config.py`, builds the knowledge indexes, and runs the smoke test.

Then reload your editor window so the MCP client picks up `.vscode/mcp.json`, and confirm
the `study-agent` server is listed and started.

### Slash commands

| Command | Model | Purpose |
|---|---|---|
| `/study` | Sonnet | Brief a domain from the notes, then drill it |
| `/drill` | Sonnet | Interactive quiz, one question per turn, reasoning validated |
| `/author` | Opus | Write new items from dbt docs through the quality gate |
| `/seal` | Opus | Independently derive and verify an unsealed answer |
| `/verify` | Sonnet | Sweep for broken seals, stale sources, and version drift |

### Other MCP clients

The server is plain stdio, so any MCP client works. Point it at:

```
command: <repo>/mcp-server/.venv/bin/python
args:    [<repo>/mcp-server/run.py]
```

For Copilot CLI, choose "Yes, and remember this folder" on first run — without folder
trust the MCP config is silently ignored.

---

## The bank starts empty. That is deliberate.

There is no dbt equivalent of the large public question dumps that exist for cloud exams,
and the third-party dbt material that does exist frequently describes older dbt versions.
Seeding from it would poison the bank.

So the first real session is authoring, not drilling:

```
/author
```

It will pull `coverage_report`, pick the emptiest task, fetch the relevant
`docs.getdbt.com` pages into the cache, and write items through `item_gate`.

Expect to build the bank up over several sessions. `coverage_report(track="ae")` shows
both task gaps and **format gaps** — it will tell you when the bank has drifted into
being all multiple choice.

---

## Repo map

| Path | What it is |
|---|---|
| `mcp-server/study_agent_mcp/exam_config.py` | **Single source of truth**: official topic outlines, tasks, formats, ID prefixes. Adding a domain is one edit here plus `bootstrap_repo.py`. |
| `mcp-server/study_agent_mcp/grading.py` | Multi-format answer engine (all six dbt formats) |
| `mcp-server/study_agent_mcp/server.py` | The MCP tool surface |
| `mcp-server/tests/` | 55 unit tests + a 40-check integration smoke test |
| `knowledge/<track>/<domain>/` | Verified topic notes — the knowledge base |
| `question-bank/` | `index.json` (sealed bank) and `authored/` (drafts awaiting the gate) |
| `progress/` | Scorecard, missed queue, per-attempt log, session snapshots |
| `sources/cache/` | Cached dbt docs; 90-day freshness window |
| `docs/` | Blueprints, question formats, authoring spec, domain rubric, model routing, decision log |
| `scripts/` | Index builder, quality gate, ingest, coverage, bootstrap |

---

## Exam facts (published)

Both exams: **65 questions**, **65% to pass**, **2 hours**, **$200**, online proctored via
Talview, not open book, valid 2 years. AE targets **dbt Core 1.11** and is offered in
English and Japanese; Architect adds French and assumes Enterprise account administration
experience.

Scoring: one point per correct answer, all questions weighted equally, plus an undisclosed
number of unscored research questions mixed in.

Domains in this repo are the **official topic outlines** transcribed from the dbt Labs
study guides — 7 topics for AE, 8 for Architect, with sub-topic titles quoted verbatim.

**Still not published:** per-topic weighting. `exam_facts()` returns a `subtopic_share_pct`
proxy derived from sub-topic counts (AE Topic 1 has 14 sub-topics, Topic 4 has 2), clearly
labelled as a proxy. Never quote it as a weight.

[source: getdbt.com official study guides — accessed 2026-09-29]

---

## Question formats

| Format | Answer |
|---|---|
| Multiple choice | one letter |
| Multiple response | exact set of letters |
| Fill in the blank | typed term, matched against accepted variants |
| Matching | `left -> right` pairs |
| Hotspot | region id(s) |
| Build list | ordered items — **order is graded** |
| DOMC | `Y`/`N` per option, presented **one at a time** |

See [docs/question-formats.md](docs/question-formats.md).

---

## Common tasks

```bash
# rebuild knowledge indexes after editing notes
./mcp-server/.venv/bin/python scripts/build_topic_index.py

# run a candidate batch through the quality gate
./mcp-server/.venv/bin/python scripts/item_qa.py question-bank/authored/batch.json --verbose

# what to author next
./mcp-server/.venv/bin/python scripts/blueprint_coverage.py --track ae

# tests
./mcp-server/.venv/bin/python -m unittest discover -s mcp-server/tests -p 'test_*.py'
./mcp-server/.venv/bin/python mcp-server/tests/smoke.py
```

Prefer the MCP tools over the scripts in normal use — the scripts are the implementation,
the tool surface is the product.

---

## Adding a domain or a question format

**Domain:** edit `exam_config.DOMAINS`, run `python3 scripts/bootstrap_repo.py`, then
`python3 scripts/build_topic_index.py`. `test_exam_config.py` will catch an id that
disagrees with its folder or a task with the wrong major number.

**Format:** see the checklist at the end of
[docs/question-formats.md](docs/question-formats.md). A test fails if you skip the
rendering step.

---

## License

MIT — see [LICENSE](LICENSE).
