# Materializations

**Domain:** ae-01 — Task 1.2
**Verified:** 2026-09-29
**Concepts:** materialization, materialized, view, table, incremental, ephemeral, materialized_view, custom materialization

Materializations are strategies for persisting dbt models in a warehouse. There are
**five** built into dbt: `table`, `view`, `incremental`, `ephemeral`, and
`materialized_view`. You can also write custom materializations.

Official topic: *"Understanding core dbt materializations"* (AE study guide, Topic 01).

[source: [Materializations — dbt Docs](https://docs.getdbt.com/docs/build/materializations) — accessed 2026-09-29]

## Configuring

The default is **`view`**. Set `materialized` in any of three places, in increasing
order of specificity:

```yaml
# dbt_project.yml — applies to a folder
models:
  my_project:
    events:
      +materialized: table
```

```sql
-- models/events/stg_event_log.sql — applies to one model
{{ config(materialized='table', sort='timestamp', dist='user_id') }}
select ...
```

It can also be set in the model's `properties.yml`.

## When to use which

| Materialization | Built in the warehouse as | Use when | Main cost |
|---|---|---|---|
| `view` | `create view as` | Light transformation — renaming, recasting. **Start here.** | Slow to query if the transformation is significant or views are stacked |
| `table` | `create table as`, rebuilt every run | Queried by BI tools; slow transformations feeding many downstream models | Long rebuilds; new source records do not appear until the next run |
| `incremental` | A table, inserted/updated since the last run | Event-style data, once `dbt run` is becoming too slow | Extra configuration; an advanced usage — **do not start here** |
| `ephemeral` | **Nothing** — interpolated into dependents as a CTE | Very light transformation early in the DAG, used by one or two models, never queried directly | Cannot be selected from; harder to debug |
| `materialized_view` | A materialized view in the target database | Similar cases to incremental, when the database can refresh on a cadence without a dbt batch run | Database support varies |

**Advice from the docs:** generally start with `view` and only change when you notice
performance problems.

## Ephemeral is the special case

`ephemeral` models are **not directly built into the database**. dbt interpolates the
code from an ephemeral model into its dependent models using a common table expression.
You can control the CTE's identifier with a model alias, but dbt always prefixes the
model identifier with `__dbt__cte__`.

That one fact drives every ephemeral restriction:

- **Trap:** you **cannot select directly** from an ephemeral model. There is no object in
  the warehouse to select from.
- **Trap:** operations (for example macros called via `dbt run-operation`) **cannot**
  `ref()` an ephemeral node.
- **Trap:** ephemeral materialization **does not support model contracts**. A contract
  enforces column names and types on a built relation, and there is no relation.
- **Trap:** overusing ephemeral makes queries harder to debug, because the logic
  disappears into the compiled SQL of its consumers.

## Traps

- **Trap:** the default is `view`, not `table`. Setting `+materialized: view` explicitly
  is redundant.
- **Trap:** `table` does **not** pick up new source records on its own — it only refreshes
  on the next `dbt run`. "Stale data" questions often hinge on this, not on incremental
  logic.
- **Trap:** `materialized_view` and `incremental` serve similar use cases, so they make
  natural confusable siblings. The difference is *who* refreshes: the database on a
  cadence versus a dbt batch run.
- **Trap:** "reduce clutter in the warehouse" points at `ephemeral`, but so does "light
  transformation". Read on to whether the model must be **queryable** — that is what
  actually decides it.

## Why this is likely on the exam

Materialization choice is the single most common design decision in a dbt project, and
the five options have crisp, documented trade-offs. It is also an explicit sub-topic of
the largest topic on the exam. The highest-value items combine a materialization with a
second constraint (a contract, a direct query, an operation, a BI consumer) so the answer
turns on a restriction rather than on the happy path.

## Related

- `incremental-models.md` — strategies, `is_incremental()`, `on_schema_change` (Task 1.11)
- `snapshots.md` — Task 1.10
