# Knowledge base

Verified topic notes. This is the source of truth for the repo — question records are
lean pointers into these files.

## Layout

```
knowledge/
  _topics.json      generated — per-note metadata (path, title, domain, keywords, sources)
  _tags.json        generated — reverse index: keyword -> topic ids
  _concepts.json    generated — dbt concept/command name -> canonical note path
  ae/               dbt Analytics Engineering track (7 official topics)
    01-developing-and-optimizing-models/
    02-model-governance/
    03-debugging-modeling-errors/
    04-troubleshooting-pipelines/
    05-implementing-tests/
    06-external-dependencies/
    07-dbt-state/
  arch/             dbt Architect track (8 official topics)
    01-warehouse-connections/
    02-git-connections/
    03-environments/
    04-job-definitions/
    05-security-and-licenses/
    06-monitoring-and-alerting/
    07-mesh-and-cross-project/
    08-dbt-catalog/
```

Folder names mirror the official topic outlines in the dbt Labs study guides, via
`mcp-server/study_agent_mcp/exam_config.py`. Create them with
`python3 scripts/bootstrap_repo.py` rather than by hand, so the folder name always
matches the domain id — `test_docs_consistency.py` fails if they drift apart.

## Lookup order — indexes before files

Never grep this directory cold. It costs tokens and misses cross-links.

1. `topic_search(keyword)` → `_tags.json` → candidate topic ids
2. `concept_lookup(name)` → `_concepts.json` → the canonical note for a dbt concept
3. `topic_read(topic_id, section="...")` → just the section you need
4. `domain_briefing(domain)` → study material for a whole domain, assembled from notes

## Note contract

```markdown
# Incremental models

**Domain:** ae-02 — Task 2.2
**Verified:** 2026-09-29
**Concepts:** incremental, is_incremental, incremental_strategy, on_schema_change

## What it is
...

## When to use which strategy
| Strategy | Use when | Requires |
|---|---|---|

## Traps
- **Trap:** ...

## Why this is likely on the exam
...
```

`briefing.py` reads those headings by pattern. A note with no traps and no decision rules
is reported as `thin` and shows up in `needs_full_read` — that is a gap, not a note.

Full rules: [.github/instructions/knowledge-base.instructions.md](../.github/instructions/knowledge-base.instructions.md)

## After editing

```bash
python3 scripts/build_topic_index.py
```

Commit the regenerated `_topics.json`, `_tags.json`, and `_concepts.json` alongside the
note. Lookups are stale until you do.

## Shared concepts

dbt Mesh, deferral, and environments appear on both exams. Write the note **once**, in
the track whose depth it belongs to, and cross-link with `` `other-note.md` ``. The index
builder resolves those references across tracks, so one note can back questions in both.
