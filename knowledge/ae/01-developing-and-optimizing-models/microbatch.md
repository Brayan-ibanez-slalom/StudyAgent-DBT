# Microbatch incremental models

**Domain:** ae-01 — Task 1.14
**Verified:** 2026-09-29
**Concepts:** microbatch, event_time, begin, batch_size, lookback, concurrent_batches, backfill, batch

`microbatch` is an incremental strategy designed for **large time-series datasets**. It
relies solely on a time column (`event_time`) to define time-based ranges for filtering,
and splits the work into multiple bounded queries called batches.

Available from dbt v1.9 and higher.

Official topic: *"Understanding advanced dbt materializations such as microbatch"*
(AE study guide, Topic 01).

[source: [About microbatch incremental models — dbt Docs](https://docs.getdbt.com/docs/build/incremental-microbatch) — accessed 2026-09-29]
[source: [event_time — dbt Docs](https://docs.getdbt.com/reference/resource-configs/event-time) — accessed 2026-09-29]

## Relevant configs

| Config | Meaning | Default | Required |
|---|---|---|---|
| `event_time` | The column indicating "at what time did the row occur" | none | **Required** |
| `begin` | The "beginning of time" for the model — the starting point for initial and full-refresh builds | none | **Required** |
| `batch_size` | Batch granularity: `hour`, `day`, `month`, or `year` | none | **Required** |
| `lookback` | Process X batches prior to the latest bookmark, to capture late-arriving records | `1` | Optional |
| `concurrent_batches` | Overrides dbt's auto-detection: `true` runs batches in parallel, `false` sequentially | `None` (auto) | Optional |

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='microbatch',
    event_time='session_start',
    begin='2020-01-01',
    batch_size='day'
) }}
```

## How it works

Each batch corresponds to a single bounded time period and is an **atomic, idempotent**
unit that can be built or replaced on its own. That is what makes it possible for dbt to
run batches separately, concurrently, and **retry them independently**.

Where other incremental strategies only distinguish "old" from "new" data, microbatch
treats every batch the same way — so given the same input data, reprocessing a batch any
number of times produces the same table.

dbt uses the most efficient "full batch" replacement mechanism each adapter offers, so
the underlying operation differs by platform (for example `merge` on dbt-postgres,
`delete+insert` on dbt-snowflake and dbt-redshift, `insert_overwrite` on dbt-bigquery and
dbt-spark, `replace_where` on dbt-databricks).

## Upstream `event_time` is the thing people get wrong

Set `event_time` on the microbatch model **and on its direct parents** that should be
filtered.

**Trap:** if an upstream model does not have `event_time` configured, dbt **cannot**
auto-filter it and will perform a **full table scan on every batch run**. It does not
fail — it just gets expensive. In the docs' own example, a `sessions` model filters
`page_views` (which sets `event_time`) to each batch, while `customers` (which does not)
is fully scanned for every batch.

## Traps

- **Trap:** `event_time` is not `partition_by`. `event_time` defines time-based ranges
  for filtering; `partition_by` groups rows into partitions.
- **Trap:** microbatch **complements** the other incremental strategies rather than
  replacing them. Without a reliable `event_time` column, or when you want more control
  over the incremental logic, another strategy is the better answer.
- **Trap:** the custom-macro behaviour flag is only needed if you use a **custom**
  microbatch macro. With no custom macro, dbt microbatches automatically for any model
  using the `microbatch` strategy — so "you must set a behaviour flag" is a distractor
  in the plain case.
- **Trap:** `lookback` defaults to `1`, not `0`. Late-arriving data within one batch
  period is already handled without extra config.
- **Trap:** `begin` matters most on the **first** build and on `--full-refresh`. A daily
  model run on 2024-10-01 with `begin = '2023-10-01'` processes 366 batches plus today's.

## Why this is likely on the exam

It is the named example of an "advanced materialization", it is recent enough to be a
version-drift trap, and its three required configs (`event_time`, `begin`, `batch_size`)
are exactly the kind of exact-spelling recall dbt tests. The most discriminating fact is
the upstream-`event_time` full-scan behaviour, because it is a silent cost problem rather
than an error.

## Related

- `incremental-models.md` — the other four strategies (Task 1.11)
- `dbt-state-and-retry.md` — retrying failed batches (Task 7.2)
