# Test types: generic, singular, custom generic, unit

**Domain:** ae-05 — Tasks 5.1, 5.2
**Verified:** 2026-09-29
**Concepts:** data test, generic test, singular test, custom generic test, unit test, not_null, unique, relationships, accepted_values, test block, tests/generic, test_type

Official topics: *"Using generic, singular, custom, custom generic, and unit tests on a
wide variety of models and sources"* and *"Testing assumptions for dbt models and
sources"* (AE study guide, Topic 05).

[source: [Add data tests to your DAG — dbt Docs](https://docs.getdbt.com/docs/build/data-tests) — accessed 2026-09-29]
[source: [Writing custom generic data tests — dbt Docs](https://docs.getdbt.com/best-practices/writing-custom-generic-tests) — accessed 2026-09-29]
[source: [Unit tests — dbt Docs](https://docs.getdbt.com/docs/build/unit-tests) — accessed 2026-09-29]

## The families

| Type | What it is | Where it lives |
|---|---|---|
| **Generic data test** | A reusable, parameterised assertion referenced by name in YAML | Built in, or a `test` block |
| **Singular data test** | A one-off `select` returning the failing rows | A `.sql` file in `tests/` |
| **Custom generic data test** | Your own `test` block, usable like a built-in | `tests/generic/` or `macros/` |
| **Unit test** | Validates SQL modelling logic against **static inputs**, before materializing | A `.yml` file under `model-paths` |

dbt ships with **four** built-in generic data tests: `not_null`, `unique`,
`relationships`, and `accepted_values`. These used to be called "schema tests", a name
you will still see in places. Under the hood they are defined as `test` blocks, like
macros.

**Trap:** many more generic tests exist in packages such as `dbt-utils` and
`dbt-expectations`. Writing your own when a package already has it is the `T7`
over-engineering distractor.

## Custom generic tests

Define a `test` block called `<test_name>`. The files can live in **two** places:

- **`tests/generic/`** — a subfolder named `generic` inside your test paths
- **`macros/`** — because generic tests work a lot like macros, and historically this was
  the only place they could be defined. Convenient when the test depends on complex macro
  logic.

All generic tests should accept one or both standard arguments:

- **`model`** — the resource the test is defined on, templated to its relation name.
  **The argument is always named `model`, even when the resource is a source, seed, or
  snapshot.**
- **`column_name`** — the column the test is defined on, for column-level tests.

## Unit tests

Available from dbt **v1.8**. Data tests could only be executed **after** building a
model; unit tests validate SQL modelling logic on a **small set of static inputs
before** you materialize the full model.

### Prerequisites and unsupported cases

- **SQL models only**, and only models in the **current** project.
- **Not supported:** `materialized_view` materialization, recursive SQL, introspective
  queries.
- Must be defined in a **`.yml` file in the `models/` directory** — unit tests are
  discovered from `model-paths`. **Do not** put unit test YAML in `tests/`, which is
  reserved for data tests.
- **Table names must be aliased** in order to unit test `join` logic.
- Include **all** `ref` or `source` references as `input`s, or compilation raises
  "node not found".
- If a model has multiple versions, by default the unit test runs on **all** versions.

### Where unit tests run

dbt Labs **strongly recommends running unit tests only in development or CI**. Since the
inputs are static, there is no need to spend compute on them in production. Exclude them
from production builds with `--exclude-resource-type` (or
`DBT_ENGINE_EXCLUDE_RESOURCE_TYPES` from dbt v1.11). To run only unit tests on demand,
use the **`test_type`** selector.

Under `dbt build`, in lineage order dbt will: **run the unit tests on the model,
materialize the model, then run the data tests on the model.**

**Trap:** incremental models must **exist in the database** before unit tests or a
`dbt build`. Use `--empty` to build an empty version cheaply.

## Traps

- **Trap:** a **unit test** checks logic against fixtures; a **data test** checks real
  rows after a build. A stem about catching a logic bug before any data lands is a unit
  test; a stem about detecting bad values in production is a data test.
- **Trap:** unit tests in `tests/` will not be discovered. That directory is for data
  tests.
- **Trap:** the generic-test argument is `model` even for a **source**. `source_name` is
  a fabrication.
- **Trap:** a singular test is just SQL returning failing rows — it needs no `test` block
  and cannot take arguments.
- **Trap:** running unit tests in production is not an error, just waste — the docs call
  it out explicitly, which makes it a good LEAST-cost qualifier.

## Why this is likely on the exam

Topic 05 names five test flavours in one sub-topic, which guarantees confusable-sibling
items. The unit-test prerequisite list is a dense source of single-fact disqualifiers.

## Related

- `test-severity-and-workflow.md` — `severity`, `error_if`, `warn_if` (Task 5.3)
- `../02-model-governance/constraints.md` — platform guarantees, not tests
