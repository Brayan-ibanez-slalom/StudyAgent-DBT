# Snapshots

**Domain:** ae-01 — Task 1.10
**Verified:** 2026-09-29
**Concepts:** snapshot, strategy, timestamp, check, check_cols, updated_at, unique_key, hard_deletes, dbt_valid_from, dbt_valid_to, dbt_valid_to_current, snapshot_meta_column_names, SCD Type 2

Snapshots record changes to a mutable table over time, implementing **Type 2 slowly
changing dimension** history. They are the only dbt resource that captures history — no
incremental strategy does.

Official topic: *"Creating snapshots in YAML"* (AE study guide, Topic 01).

[source: [Add snapshots to your DAG — dbt Docs](https://docs.getdbt.com/docs/build/snapshots) — accessed 2026-09-29]
[source: [About dbt snapshot command — dbt Docs](https://docs.getdbt.com/reference/commands/snapshot) — accessed 2026-09-29]

## Defining a snapshot in YAML

From **dbt v1.9 and later**, snapshots are configured in YAML files placed in the
`snapshots` directory or alongside models in `models`.

```yaml
snapshots:
  - name: orders_snapshot
    relation: source('jaffle_shop', 'orders')   # or ref('my_model')
    config:
      schema: snapshots
      strategy: timestamp
      unique_key: id
      updated_at: updated_at
      hard_deletes: invalidate
```

| Config | Required? | Notes |
|---|---|---|
| `strategy` | **Yes** | `timestamp` or `check` |
| `unique_key` | **Yes** | Column, array of columns, or expression |
| `updated_at` | Only with `timestamp` | Column marking when the record last changed |
| `check_cols` | Only with `check` | List of columns, or `all` |
| `hard_deletes` | No | `ignore` (default), `invalidate`, `new_record` |
| `dbt_valid_to_current` | No | Value used instead of `NULL` for current records |
| `snapshot_meta_column_names` | No | Dictionary renaming the meta fields |
| `database` / `schema` / `alias` | No | Custom build location |

## Choosing a strategy

| Situation | Strategy |
|---|---|
| The source has a reliable "last updated" column | `timestamp` — **the recommended default** |
| No reliable timestamp; changes must be detected by comparing values | `check` |
| Source schema evolves, columns added and removed over time | `timestamp` — it tracks one column and handles schema change automatically |

The docs recommend `timestamp` because it relies on a single `updated_at` field, handles
new or removed columns automatically, and avoids having to keep `check_cols` in sync as
the source evolves.

## Meta columns

dbt adds `dbt_valid_from` and `dbt_valid_to` to the snapshot table. Current records have
`dbt_valid_to = null`, or the value set in `dbt_valid_to_current` (dbt 1.9+) if
configured — which makes date-range filtering straightforward.

## Traps

- **Trap (version drift):** `hard_deletes: invalidate` **replaces the legacy
  `invalidate_hard_deletes=true`**. Both appear in older material; only `hard_deletes` is
  the current key.
- **Trap:** `hard_deletes` defaults to `ignore`, so a row deleted at the source is
  silently left marked current unless you configure it.
- **Trap:** `hard_deletes: new_record` is a third option, not a synonym for `invalidate`
  — it adds a new record marking the deletion rather than closing the existing one.
- **Trap (version drift):** in v1.9 `target_schema` became **optional**. Without
  `target_schema` or `target_database`, snapshots use `generate_schema_name` /
  `generate_database_name`, which is what makes them environment-aware. Older material
  presents `target_schema` as required.
- **Trap:** snapshots **can't be rebuilt**. That is why the docs advise a separate schema
  and tighter privileges — and why `--full-refresh` is not the recovery story it is for
  incremental models.
- **Trap:** the `unique_key` must really be unique. dbt uses it to match rows; a
  non-unique key corrupts the history rather than erroring loudly.
- **Trap:** to clean or transform data before snapshotting, reference an ephemeral or
  staging model from the snapshot — do not bury transformations in the snapshot itself.

## Traps about what a snapshot is not

- A **seed** is a CSV in the repo loaded into the warehouse.
- A **source** is a table dbt did not build.
- An **incremental model** updates a table with new/changed rows but keeps **no history**.
- Only a **snapshot** produces SCD2 validity ranges.

## Why this is likely on the exam

"Creating snapshots in YAML" is a named sub-topic whose correct shape changed in v1.9,
making it the single richest version-drift target in Topic 01. Expect items that pair a
strategy choice with a schema-evolution or deleted-rows constraint.

## Related

- `incremental-models.md` — the strategies that explicitly do not do SCD2 (Task 1.11)
- `materializations.md` — where snapshots sit relative to models (Task 1.2)
