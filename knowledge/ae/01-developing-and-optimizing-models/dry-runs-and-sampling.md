# Dry runs (`--empty`) and sample mode (`--sample`)

**Domain:** ae-01 — Tasks 1.12, 1.13
**Verified:** 2026-09-29
**Concepts:** --empty, empty flag, dry run, --sample, sample mode, DBT_ENGINE_EMPTY, DBT_ENGINE_SAMPLE

Two flags that let you execute a project cheaply against the real warehouse. They are
confusable siblings and both are named sub-topics, so keep the distinction crisp.

Official topics: *"Validating model logic and schema definitions in dry-runs using the
`--empty` flag"* and *"Running models in sample mode using the `--sample` flag"*
(AE study guide, Topic 01).

[source: [About dbt run command — dbt Docs](https://docs.getdbt.com/reference/commands/run) — accessed 2026-09-29]
[source: [Upgrading to v1.10 — dbt Docs](https://docs.getdbt.com/docs/dbt-versions/core-upgrade/upgrading-to-v1.10) — accessed 2026-09-29]
[source: [About flags (global configs) — dbt Docs](https://docs.getdbt.com/reference/global-configs/about-global-configs) — accessed 2026-09-29]

## `--empty` — schema-only dry run

The `run` command supports the `--empty` flag for building **schema-only dry runs**.

- It **limits the refs and sources to zero rows.**
- dbt **still executes the model SQL against the target data warehouse**, but avoids
  expensive reads of input data.
- This **validates dependencies and ensures your models will build properly.**

It is a boolean flag: `--empty` / `--no-empty`, default `False`, env var
`DBT_ENGINE_EMPTY`. It is a CLI flag and **cannot** be set in `dbt_project.yml`.

```bash
dbt run --empty --select my_model+
```

## `--sample` — time-based sample mode

Large data sets slow down build times, making it harder to test new code efficiently.
The `--sample` flag, available for the **`run` and `build`** commands, reduces build
times and warehouse costs by running dbt in **sample mode**. It generates **filtered refs
and sources using time-based sampling**, so developers can validate outputs without
building entire models.

It is a **string**-valued flag (default `None`), env var `DBT_ENGINE_SAMPLE`, and also
cannot be set in `dbt_project.yml`.

## Decision rule

| Goal | Flag |
|---|---|
| Prove the SQL compiles, the DAG resolves, and the output schema is right — no rows needed | `--empty` |
| Actually look at plausible output values, cheaply, over a recent time window | `--sample` |
| Check the SQL without touching the warehouse at all | Neither — use `dbt compile` |

## Traps

- **Trap:** `--empty` is **not** a no-op. dbt still executes the model SQL against the
  warehouse; it is the *input reads* that go to zero rows. "It does not connect to the
  warehouse" is false — that describes `dbt compile`.
- **Trap:** `--empty` gives you **zero rows**, so it validates schema and dependencies,
  not data. Any stem asking to eyeball values needs `--sample`.
- **Trap:** `--sample` filters by **time**. It is not a random-row sample and not a
  `--limit`.
- **Trap:** `--limit` belongs to `dbt show` and previews a single node. It is not a
  project-wide development mode.
- **Trap:** neither flag is settable in `dbt_project.yml`. Both are per-invocation.
- **Trap (version drift):** `--sample` arrived in dbt v1.10. Material written earlier
  offers hand-rolled `{% if target.name == 'dev' %} limit 1000 {% endif %}` macros — that
  is the `T7` over-engineering distractor this flag replaced.

## Why this is likely on the exam

Both flags are named sub-topics in their own right, they are recent, and they are easy to
confuse with each other and with `dbt compile` / `dbt show --limit`. Expect a stem that
states whether **rows** are needed — that is always what decides it.

## Related

- `dbt-commands.md` — `dbt show --limit`, `dbt compile` (Task 1.4)
- `project-config-and-flags.md` — where flags can and cannot be set (Task 1.6)
