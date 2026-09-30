# Model contracts

**Domain:** ae-02 — Task 2.1
**Verified:** 2026-09-29
**Concepts:** contract, enforced, data_type, preflight check, model governance

A contract is a set of upfront guarantees about the shape of a model's returned dataset.
While building the model, dbt verifies that the transformation produces a dataset
matching the contract, **or it fails to build**.

Official topic: *"Adding contracts to models to ensure the shape of models"*
(AE study guide, Topic 02).

[source: [Model contracts — dbt Docs](https://docs.getdbt.com/docs/collaborate/govern/model-contracts) — accessed 2026-09-29]
[source: [contract — dbt Docs](https://docs.getdbt.com/reference/resource-configs/contract) — accessed 2026-09-29]

## Declaring one

```yaml
models:
  - name: dim_customers
    config:
      contract:
        enforced: true
    columns:
      - name: customer_id
        data_type: int
        constraints:
          - type: not_null
      - name: customer_name
        data_type: string
```

When enforced, the contract **must include every column's `name` and `data_type`**, and
the `data_type` must be one the data platform understands.

## What dbt does differently

1. A **"preflight" check** that the model's query returns a set of columns with names and
   data types matching those defined. The check is **agnostic to the order of columns**
   in the SQL or the YAML spec.
2. dbt includes the column names, data types, and constraints in the **DDL statements**
   it submits to the platform, and **orders the columns per the contract** rather than
   per the model.

## Where contracts are and are not supported

| Supported | Not supported |
|---|---|
| SQL models | **Python models** |
| `table` | **`ephemeral`** |
| `view` — names and data types, **but not constraints** | **`materialized_view`** |
| `incremental` — with `on_schema_change: append_new_columns` or `fail` | Custom materializations, unless the author added support |
| Declared in `dbt_project.yml` or `properties.yml` | Models with recursive CTEs in BigQuery |
| | Other resource types: sources, seeds, **snapshots** |

## Traps

- **Trap:** governance features — access, contracts, versions — are **model-specific**.
  They do **not** apply to snapshots, seeds, or sources, because those objects change
  structure over time and are not suited to such guarantees.
- **Trap:** `ephemeral` cannot carry a contract. There is no relation in the warehouse to
  enforce anything against.
- **Trap:** a `view` can carry a contract for **names and data types only** — constraints
  need `table` or `incremental`.
- **Trap:** an `incremental` model needs `on_schema_change` set to `append_new_columns`
  or `fail`. Leaving it at `ignore` is the quiet disqualifier.
- **Trap:** the preflight check does not care about **column order** in your SQL, but the
  DDL dbt submits **does** order columns per the contract. "Reorder the select list" is
  therefore not a fix for a contract failure.
- **Trap:** contracts add structure, so they make rollbacks harder and increase
  maintenance if adopted too early. The docs explicitly say to consider whether the
  project is ready.

## Why this is likely on the exam

It is the first named sub-topic of Topic 02, and the support matrix is full of crisp
disqualifiers (Python, ephemeral, materialized view, snapshots) that make excellent
single-fact hinges.

## Related

- `constraints.md` — what you can add on top of a contract (Task 2.3)
- `model-versions.md` — what you do when a contract must break (Task 2.2)
- `../01-developing-and-optimizing-models/materializations.md` — why ephemeral is excluded
