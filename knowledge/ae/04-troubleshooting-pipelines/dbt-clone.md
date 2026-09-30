# `dbt clone`

**Domain:** ae-04 — Task 4.2
**Verified:** 2026-09-29
**Concepts:** dbt clone, clone materialization, zero-copy clone, pointer view, --state, --full-refresh, threads, blue/green

Official topic: *"Using dbt clone"* (AE study guide, Topic 04).

[source: [About dbt clone command — dbt Docs](https://docs.getdbt.com/reference/commands/clone) — accessed 2026-09-29]
[source: [Defer — dbt Docs](https://docs.getdbt.com/reference/node-selection/defer) — accessed 2026-09-29]

## What it does

`dbt clone` clones selected nodes **from the specified state** to the target schema(s),
using the `clone` materialization:

- If the platform supports **zero-copy cloning** of tables (**Snowflake, Databricks, or
  BigQuery**) **and** the model exists as a **table** in the source environment, dbt
  creates it in the target environment as a clone.
- **Otherwise dbt creates a simple pointer view** — `select * from` the source object.

```bash
dbt clone --state path/to/artifacts
dbt clone --select "one_specific_model" --state path/to/artifacts
dbt clone --state path/to/artifacts --full-refresh
dbt clone --state path/to/artifacts --threads 50
```

- By default `dbt clone` **will not recreate pre-existing relations** in the current
  target. Use **`--full-refresh`** to override that.
- Individual clone statements are independent of one another, so a **higher `--threads`**
  value decreases execution time.

## What it is useful for

- **Blue/green continuous deployment**, on warehouses that support zero-copy cloning
- Cloning current **production state into development schemas**
- Handling **incremental models in CI jobs**, on warehouses that support zero-copy cloning
- Testing code changes on **downstream dependencies in a BI tool**

## `dbt clone` vs deferral

Unlike deferral, `dbt clone` **requires some compute and the creation of additional
objects** in the warehouse. In many cases **deferral is a cheaper and simpler
alternative**. But `dbt clone` covers cases deferral cannot: by creating real warehouse
objects, it lets you test code changes against downstream dependencies — for example a
BI tool that can only point at a real relation.

## Decision rule

| Requirement | Reach for |
|---|---|
| Avoid rebuilding unselected parents, cheapest option | `--defer` |
| A real object a BI tool or external consumer can query | `dbt clone` |
| Swap a whole environment atomically | `dbt clone` (blue/green) |
| Rebuild an incremental model from scratch | `--full-refresh` |
| Resume a failed run where it stopped | `dbt retry` |

## Traps

- **Trap:** clone is **not always zero-copy**. On a platform without support, or for a
  node that is not a table in the source environment, you get a **pointer view** instead.
  A stem that says "the platform does not support zero-copy cloning" does not make
  `dbt clone` fail — it changes what you get.
- **Trap:** clone does **not** overwrite existing relations by default. If the clone
  "didn't work", the pre-existing relation is the usual reason, and `--full-refresh` is
  the fix.
- **Trap:** clone requires `--state`. It clones **from a state manifest**, not from
  whatever happens to be in production right now.
- **Trap:** deferral is cheaper. Reaching for `dbt clone` when nothing external needs a
  real object is over-engineering.

## Why this is likely on the exam

It is one of only two sub-topics in Topic 04, and the clone-vs-defer trade-off is
precisely the kind of LEAST-cost / BEST-fit comparison dbt likes, with the zero-copy
fallback as the hidden second fact.

## Related

- `dag-failure-points.md` — Task 4.1
- `../03-debugging-modeling-errors/fix-and-verify-before-merge.md` — `--defer` in depth
