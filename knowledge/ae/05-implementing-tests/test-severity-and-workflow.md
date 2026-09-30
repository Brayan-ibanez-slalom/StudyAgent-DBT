# Test severity and the testing workflow

**Domain:** ae-05 — Task 5.3
**Verified:** 2026-09-29
**Concepts:** severity, error_if, warn_if, store_failures, store_failures_as, --warn-error, indirect selection, test_type selector, arguments

Official topic: *"Implementing various testing steps in the workflow"*
(AE study guide, Topic 05).

[source: [severity, error_if, and warn_if — dbt Docs](https://docs.getdbt.com/reference/resource-configs/severity) — accessed 2026-09-29]
[source: [store_failures — dbt Docs](https://docs.getdbt.com/reference/resource-configs/store_failures) — accessed 2026-09-29]
[source: [About data tests property — dbt Docs](https://docs.getdbt.com/reference/resource-properties/data-tests) — accessed 2026-09-29]

## How a test decides pass / warn / error

Tests return a **number of failures** — usually the count of rows returned by the test
query, because test queries are written to return all the rows you *don't* want.

| Config | Values | Default |
|---|---|---|
| `severity` | `error` or `warn` | `error` |
| `error_if` | conditional expression | `!=0` |
| `warn_if` | conditional expression | `!=0` |

Conditional expressions can be any comparison your SQL supports against an integer
failure count: `> 5`, `= 0`, `between 5 and 10`.

The evaluation order matters:

- **`severity: error`** — dbt checks **`error_if` first**. If met, the test errors. If
  not, dbt checks `warn_if`; if that is met (or unspecified) the test **warns**, otherwise
  it passes.
- **`severity: warn`** — dbt **skips `error_if` entirely** and jumps straight to
  `warn_if`. If met the test warns, otherwise it passes.

By default a test with `severity: warn` will **only ever warn**, never error. You can
promote warnings to errors with `--warn-error` (all warnings) or `--warn-error-options`
(named warnings only).

## `store_failures`

- The configured tests store their failures when `dbt test --store-failures` is invoked.
- Set as `true` or `false`, the **`store_failures` config takes precedence over the
  presence or absence of the `--store-failures` flag**. If the config is `none` or
  omitted, the resource uses the flag's value.
- When true, it saves all failing records (up to `limit`) in a **new table named after
  the test**.
- A test's results **always replace previous failures for the same test**, even when the
  test returns no failures.
- By default the failures land in a schema named `{{ profile.schema }}_dbt_test__audit`;
  this is configurable.
- **Trap:** if `store_failures` is `false` but **`store_failures_as` is configured, it
  will be overridden.**

## Where tests fit in the workflow

| Step | Command |
|---|---|
| Run models then tests in DAG order, skipping downstream on failure | `dbt build` |
| Run only the tests | `dbt test` |
| Run only unit tests | `dbt test --select "test_type:unit"` |
| Run a model and its own tests | `dbt build -s model_a` (indirect selection) |

**Indirect selection:** `dbt build -s model_a` both runs **and** tests `model_a`. Tests
that directly depend on `model_a` are included, so long as they do not also depend on
other unselected parents.

## Traps

- **Trap (version drift):** arguments passed to a generic data test should be nested
  below the **`arguments`** property. That form is available in **v1.10.5 and higher**;
  older versions set the argument name as a top-level property. Older material therefore
  shows `values:` directly under the test name.
- **Trap:** `severity: warn` does not make a test optional — it still runs and still
  reports.
- **Trap:** `error_if` is ignored entirely when `severity: warn`. Setting both and
  expecting the error branch is a common misreading.
- **Trap:** `store_failures` is about **inspection**, not about blocking. It does not
  stop a failing test from skipping downstream models.
- **Trap:** the `store_failures` **config beats the flag**, not the other way round.

## Why this is likely on the exam

"Various testing steps in the workflow" is deliberately broad, and the severity
evaluation order plus the config-beats-flag rule are precise, checkable, and easy to get
backwards.

## Related

- `test-types.md` — the five test flavours (Tasks 5.1, 5.2)
- `../01-developing-and-optimizing-models/dbt-commands.md` — `dbt build` skipping
- `../03-debugging-modeling-errors/behaviour-flags.md` — `--warn-error`
