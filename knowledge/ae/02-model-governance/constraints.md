# Constraints

**Domain:** ae-02 — Task 2.3
**Verified:** 2026-09-29
**Concepts:** constraints, not_null, primary_key, foreign_key, unique, check, custom, warn_unenforced, warn_unsupported, to, to_columns, expression

Constraints are a feature of the **data platform**. When specified, the platform performs
additional validation as data is populated. If validation fails, the table creation or
update fails, the operation is **rolled back**, and you see a clear error message.

Official topic: *"Defining constraints in YAML to enforce data integrity at the platform
level"* (AE study guide, Topic 02).

[source: [constraints — dbt Docs](https://docs.getdbt.com/reference/resource-properties/constraints) — accessed 2026-09-29]
[source: [Model contracts — dbt Docs](https://docs.getdbt.com/docs/collaborate/govern/model-contracts) — accessed 2026-09-29]

## Prerequisites

- **Supported materializations only.** Constraints work on `table` and `incremental`
  models. They are **never** applied on `ephemeral` models or those materialized as
  `view`.
- **An enforced contract.** To use constraints, the model must declare and enforce a
  `contract`, which means explicitly defining the `data_type` for **every** column.

## Structure of a constraint

| Field | Meaning |
|---|---|
| `type` | **Required.** One of `not_null`, `unique`, `primary_key`, `foreign_key`, `check`, `custom` |
| `expression` | Free text qualifying the constraint. Required for some types, optional for others |
| `name` | Optional human-friendly name, supported by some platforms |
| `columns` | **Model level only.** List of columns the constraint applies over |

Foreign keys take two more inputs (dbt v1.9 and later):

| Field | Meaning |
|---|---|
| `to` | A relation input — likely `ref()` or `source()` — naming the referenced table |
| `to_columns` | The column(s) in that table holding the corresponding primary or unique key |

Because this syntax uses `ref`, it **captures dependencies and works across environments**
— unlike a hard-coded relation name.

## Column level vs model level

Constraints may be defined **for a single column** or **at the model level for one or
more columns**. The docs recommend defining single-column constraints directly on the
column.

**Trap:** if you define **multiple `primary_key` constraints** for a single model, they
**must** be defined at the model level. Multiple column-level `primary_key` constraints
are **not supported**.

## Three categories of platform support

| Category | Meaning |
|---|---|
| **Definable and enforced** | The model won't build if it violates the constraint |
| **Definable and not enforced** | The platform accepts the constraint, but the model still builds when violated — metadata only. More typical in cloud warehouses |
| **Not definable and not enforced** | You can't specify that constraint type at all |

Two optional fields suppress the resulting warnings:

- `warn_unenforced: False` — skip warnings for constraints the platform supports but does
  not enforce (the docs' example: `primary_key` in Snowflake).
- `warn_unsupported: False` — skip warnings for constraints the platform does not support
  at all (the docs' example: `check` in Redshift).

## Traps

- **Trap:** a **constraint** is a platform-level guarantee checked at build/insert time;
  a **data test** is a dbt query run against rows after they land. A stem asking to stop
  bad data from ever being written points at a constraint; a stem asking to detect and
  report bad data points at a test.
- **Trap:** "definable" is not "enforced". On many cloud warehouses a `primary_key`
  constraint is metadata only — the model still builds with duplicates.
- **Trap:** `warn_unenforced` and `warn_unsupported` **silence warnings**. They do not
  make an unenforced constraint enforced.
- **Trap:** constraints on a `view` are a non-starter. So is `ephemeral`.
- **Trap:** the `columns` field is model-level only. Putting it inside a column's own
  constraint block is a scope error.

## Why this is likely on the exam

It is a named sub-topic, it depends on a second fact (the contract prerequisite), and the
definable-versus-enforced distinction is genuinely surprising — ideal L4 material.

## Related

- `model-contracts.md` — the prerequisite (Task 2.1)
- `../05-implementing-tests/README.md` — the tests that constraints are not
