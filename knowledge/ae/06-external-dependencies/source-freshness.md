# Source freshness

**Domain:** ae-06 — Task 6.2
**Verified:** 2026-09-29
**Concepts:** freshness, warn_after, error_after, loaded_at_field, loaded_at_query, filter, count, period, dbt source freshness, sources.json

Official topic: *"Implementing source freshness"* (AE study guide, Topic 06).

[source: [freshness — dbt Docs](https://docs.getdbt.com/reference/resource-properties/freshness) — accessed 2026-09-29]
[source: [About dbt source command — dbt Docs](https://docs.getdbt.com/reference/commands/source) — accessed 2026-09-29]
[source: [Add sources to your DAG — dbt Docs](https://docs.getdbt.com/docs/build/sources) — accessed 2026-09-29]

## The config

Use the `freshness` config to declare how fresh source (or model) data should be.

```yaml
sources:
  - name: jaffle_shop
    database: raw
    config:
      freshness:            # changed to config in v1.9
        warn_after: {count: 12, period: hour}
        error_after: {count: 24, period: hour}
      loaded_at_field: _etl_loaded_at
```

| Field | Meaning |
|---|---|
| `warn_after` | How old the most recent data can be before the check reports a **warning** |
| `error_after` | Same format, but reports an **error** |
| `loaded_at_field` | The column dbt queries for the most recent loaded timestamp. **Required when adapter metadata is unavailable** |
| `loaded_at_query` | A SQL expression returning the most recent loaded timestamp. An **alternative** to `loaded_at_field`. Available in **dbt v1.10 and later** |
| `filter` | Adds a `WHERE` clause to the freshness query to limit data scanned |

`period` is one of `minute`, `hour`, or `day`, and `count` is a positive integer.

## The rules that decide questions

- **One or both** of `warn_after` and `error_after` can be provided. **If neither is set,
  dbt will not check freshness for that resource** — silently, no error.
- Each of `warn_after` and `error_after` **requires both `count` and `period`**. Setting
  only one issues a **parse warning** but causes an **error when the freshness check
  runs**.
- Setting **both `loaded_at_query` and `loaded_at_field`** on the same resource is a
  **parse error**.
- `filter` is useful for BigQuery partitioned tables or large Snowflake/Databricks/Spark
  tables. It **does not affect other uses** of the source or model, and it **does not
  apply to `loaded_at_query`**.
- If a table is stale, dbt reports a warning or error accordingly and **exits with a
  nonzero exit code**.

## Running the check

| Command | Scope | Version |
|---|---|---|
| **`dbt source freshness`** | **Sources only.** Produces `sources.json` | The long-standing command; still supported for backward compatibility |
| `dbt freshness` | Sources **and models** in one command | dbt **v2.0 and later** |

## Traps

- **Trap:** a source with no `warn_after` and no `error_after` is **not checked at all**.
  "Freshness is configured but nothing is reported" usually means exactly this.
- **Trap:** `count` without `period` parses with only a warning, so the failure surfaces
  later, at check time — a classic "why did this only break in production" item.
- **Trap:** `loaded_at_field` and `loaded_at_query` are mutually exclusive on one
  resource. Setting both is a **parse error**, not a precedence rule.
- **Trap:** `filter` reduces the data scanned by the **freshness query only**. It does not
  filter the source for models that `ref` it.
- **Trap:** freshness is about **staleness of arriving data**. It is not a data test and
  it does not check row values.
- **Trap (version drift):** `freshness` moved under `config` in **v1.9**, and `dbt source
  freshness` is joined by `dbt freshness` in **v2.0**. Older material shows `freshness`
  as a bare top-level property.

## Why this is likely on the exam

It is one of two Topic 06 sub-topics, the config has several exact keys, and the
"neither threshold set means no check" behaviour is a silent failure — ideal L4 material.

## Related

- `exposures.md` — Task 6.1
- `../01-developing-and-optimizing-models/dbt-commands.md` — where `dbt source` sits
