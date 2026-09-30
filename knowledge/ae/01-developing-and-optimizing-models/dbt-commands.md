# Core dbt commands

**Domain:** ae-01 — Task 1.4
**Verified:** 2026-09-29
**Concepts:** dbt build, dbt run, dbt test, dbt seed, dbt snapshot, dbt show, dbt compile, dbt docs generate, indirect selection, --limit, --inline

Official topic: *"Using commands such as build, run, test, docs, show, snapshot, and
seed"* (AE study guide, Topic 01).

[source: [About dbt build command — dbt Docs](https://docs.getdbt.com/reference/commands/build) — accessed 2026-09-29]
[source: [About dbt run command — dbt Docs](https://docs.getdbt.com/reference/commands/run) — accessed 2026-09-29]
[source: [About dbt show command — dbt Docs](https://docs.getdbt.com/reference/commands/show) — accessed 2026-09-29]
[source: [About dbt seed command — dbt Docs](https://docs.getdbt.com/reference/commands/seed) — accessed 2026-09-29]
[source: [dbt Command reference — dbt Docs](https://docs.getdbt.com/reference/dbt-commands) — accessed 2026-09-29]

## What each command actually covers

| Command | Resource types it acts on |
|---|---|
| `dbt run` | **Models only.** Not tests, snapshots, or seeds |
| `dbt test` | Tests |
| `dbt seed` | Seeds — loads CSVs from `seed-paths` into the warehouse as tables |
| `dbt snapshot` | Snapshots |
| `dbt build` | Models, tests, snapshots, and seeds — **in DAG order** |
| `dbt show` | Compiles and runs **one** node and previews rows in the terminal |
| `dbt compile` | Compiles without running |

From dbt v1.11 and up, `dbt build` also builds **user-defined functions**.

## `dbt build` is not "run then test"

`dbt build` interleaves in DAG order, which is why it behaves differently from running
the commands in sequence:

- **Skipping on failures:** tests on upstream resources **block** downstream resources.
  If `model_b` depends on `model_a` and a `unique` test on `model_a` fails, `model_b` is
  **skipped**, not built-then-tested.
- To stop a test from causing skipping, adjust its **severity or thresholds** to `warn`
  instead of `error`.
- For a test with multiple parents where one depends on the other (for example a
  `relationships` test between `model_a` and `model_b`), the test blocks and skips
  children of the **most-downstream parent only**.
- **Artifacts:** `build` writes a single `manifest` and a single run results artifact
  covering everything selected, combined into one file.
- `build` supports `--select` / `--exclude` plus a `--resource-type` final filter.

**Indirect selection:** `dbt build -s model_a` will both run *and* test `model_a`. Tests
that directly depend on `model_a` are included, so long as they do not also depend on
other unselected parents.

## `dbt show`

- Previews the first **5** rows by default; change with `--limit`.
- **Always compiles and runs the query from source.** It does **not** select from the
  already-materialized relation, even if you just ran the model.
- `--limit n` modifies the underlying SQL — dbt wraps the query and applies a SQL
  `limit n`, so the warehouse only processes and returns that many rows.
- Only a **single** node can be selected. Selector methods and graph operators that
  select multiple nodes are not used.
- Results are only in logs and the terminal; nothing is materialized.
- `--inline` runs ad-hoc dbt-SQL. Because dbt cannot guarantee the query is read-only,
  use a read-only profile or role.
- **`dbt show` does not support Python (dbt-py) models.**

## Traps

- **Trap:** `dbt run` does **not** run tests, snapshots, or seeds. Reaching for
  `dbt run` when the stem also needs seeds or snapshots is the standard scope error.
- **Trap:** `dbt show` previewing stale-looking data is expected — it recompiles from
  source rather than reading the built table. Blaming the materialization is the wrong
  diagnosis.
- **Trap:** `--limit` is not a display setting. It changes the SQL sent to the warehouse.
- **Trap (version drift):** before `dbt build` existed, the pattern was
  `dbt seed && dbt run && dbt snapshot && dbt test`. That sequence still works but loses
  the DAG-order skipping behaviour, so it is a `T7`/`T6` distractor rather than the best
  answer.
- **Trap:** a failing test blocks downstream models under `build`. Switching the test to
  `severity: warn` is the documented way to unblock — not removing the test or splitting
  the command.

## Why this is likely on the exam

The commands are named verbatim in the study guide, and the interesting distinctions —
`run` vs `build`, `show`'s compile-from-source behaviour, indirect test selection — are
exactly where practitioners carry stale habits.

## Related

- `dry-runs-and-sampling.md` — `--empty` and `--sample` (Tasks 1.12, 1.13)
- `project-config-and-flags.md` — flag precedence (Task 1.6)
