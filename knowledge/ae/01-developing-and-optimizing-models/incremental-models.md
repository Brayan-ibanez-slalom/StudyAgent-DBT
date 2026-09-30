# Incremental models and incremental strategies

**Domain:** ae-01 — Task 1.11
**Verified:** 2026-09-29
**Concepts:** incremental, incremental_strategy, append, merge, delete+insert, insert_overwrite, unique_key, is_incremental, custom incremental strategy

An incremental model is a table that dbt updates by transforming and loading only new or
changed data since the last run, instead of reprocessing the whole dataset.

Official topic: *"Selecting the optimal incremental strategy based on a dataset's
characteristics"* (AE study guide, Topic 01).

[source: [About incremental strategy — dbt Docs](https://docs.getdbt.com/docs/build/incremental-strategy) — accessed 2026-09-29]
[source: [Incremental models — dbt Docs](https://docs.getdbt.com/docs/build/incremental-models) — accessed 2026-09-29]

## The five built-in strategies

| `incremental_strategy` | What it does to the target table | Needs `unique_key`? |
|---|---|---|
| `append` | Inserts selected records **without updating or deleting** existing data | No |
| `merge` | Inserts rows whose `unique_key` is absent; **updates** rows whose key exists | Yes, in practice |
| `delete+insert` | **Deletes** the rows for the `unique_key`, then inserts them again | Yes |
| `insert_overwrite` | Replaces **entire partitions** wholesale, not individual rows | No — uses partitions |
| `microbatch` | Splits a time-series load into independent time-bounded batches | No — uses `event_time` |

Each built-in strategy is implemented by a macro, and the naming is regular:

| Strategy | Macro |
|---|---|
| `append` | `get_incremental_append_sql` |
| `delete+insert` | `get_incremental_delete_insert_sql` |
| `merge` | `get_incremental_merge_sql` |
| `insert_overwrite` | `get_incremental_insert_overwrite_sql` |
| `microbatch` | `get_incremental_microbatch_sql` |

## Choosing a strategy

| Dataset characteristic | Strategy |
|---|---|
| Immutable event log, duplicates acceptable or impossible | `append` |
| Rows get updated after they land, warehouse supports MERGE | `merge` |
| Rows get updated, but `unique_key` is **not truly unique**, or MERGE is unsupported | `delete+insert` |
| Table is partitioned by date and whole partitions get corrected/refreshed | `insert_overwrite` |
| Very large time-series table with a reliable time column | `microbatch` |
| Full SCD Type 2 history is needed | **None of these** — use a snapshot |

## Traps

- **Trap:** `merge` **without** a `unique_key` behaves like the `append` strategy. It
  silently stops de-duplicating rather than erroring.
- **Trap:** `append` does not check for duplicates or verify whether a record already
  exists. The same source record arriving twice is inserted twice.
- **Trap:** `merge` and `delete+insert` are the classic confusable pair. `merge` updates
  matching records in place; `delete+insert` removes the matching records first and then
  re-inserts them.
- **Trap:** `merge` scans the entire destination table to decide what to update or
  insert, so it can be expensive on very large tables — "it updates rows" is not on its
  own a reason to pick it.
- **Trap:** none of these strategies capture history. `append` superficially resembles
  SCD2 because it adds rows, but it tracks no versioning. For SCD2 use `snapshots.md`,
  not `delete+insert`.
- **Trap:** `insert_overwrite` operates at partition grain. Using it on an unpartitioned
  table is a scope error.

## Custom strategies

Available from dbt v1.2 onward, as an easier alternative to writing a whole new
materialization:

1. Define a macro named `get_incremental_STRATEGY_sql`, replacing `STRATEGY` with your
   strategy name.
2. Set `incremental_strategy: STRATEGY` on the incremental model.

**Trap:** dbt does **not** validate user-defined strategy names. It just looks for the
macro and raises an error if it cannot find one — so a typo surfaces as a missing-macro
error, not as "unknown strategy".

**Trap:** custom strategies are **not currently supported** on the BigQuery and Spark
adapters.

## Why this is likely on the exam

This is an explicitly named sub-topic, and the strategies form a tight family of
confusable siblings — exactly the shape of a good distractor set. The highest-value items
give you a dataset characteristic (late-arriving updates, a non-unique key, partitioned
data, an unsupported MERGE) and make the characteristic decide the strategy.

## Related

- `microbatch.md` — the time-series strategy in depth (Task 1.14)
- `materializations.md` — where `incremental` sits among the five materializations (Task 1.2)
- `snapshots.md` — the SCD2 answer that incremental strategies are not (Task 1.10)
