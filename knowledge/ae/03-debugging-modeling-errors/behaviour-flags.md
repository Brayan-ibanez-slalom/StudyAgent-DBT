# Managing dbt behaviour with flags

**Domain:** ae-03 — Task 3.5
**Verified:** 2026-09-29
**Concepts:** --warn-error, --warn-error-options, WARN_ERROR, WARN_ERROR_OPTIONS, --fail-fast, -x, --quiet, --debug, partial_parse, behaviour flags

Official topic: *"Managing dbt behavior with flags"* (AE study guide, Topic 03).

[source: [Warnings — dbt Docs](https://docs.getdbt.com/reference/global-configs/warnings) — accessed 2026-09-29]
[source: [Failing fast — dbt Docs](https://docs.getdbt.com/reference/global-configs/failing-fast) — accessed 2026-09-29]
[source: [Parsing — dbt Docs](https://docs.getdbt.com/reference/global-configs/parsing) — accessed 2026-09-29]

## `--warn-error` vs `--warn-error-options`

| Flag | Effect |
|---|---|
| `--warn-error` | Converts **all** dbt warnings into errors. Any time dbt would warn, it raises an error instead |
| `--warn-error-options` | Granular control over **exactly which types** of warnings are treated as errors |

Examples of things that normally warn: `--select` criteria that selects no resources,
deprecations, configurations with no associated models, invalid test configurations, and
tests or freshness checks configured to return warnings.

**`WARN_ERROR` and `WARN_ERROR_OPTIONS` are mutually exclusive.** You can only specify
one, even across different places (env var and flag), or you get a usage error.

Warnings to promote are named through the `error` parameter. Warning names come from the
`types.py` file in `dbt-labs/dbt`, where each class inheriting from `WarnLevel` is a
warning name — for example `AdapterDeprecationWarning`, `NoNodesForSelectionCriteria`.

**Trap:** the docs explicitly warn against `--warn-error` (or
`--warn-error-options '{"error": "all"}'`) in production, because it treats **all current
and future** warnings as errors — a new warning in a future dbt version can start failing
a production job unexpectedly. The recommended production pattern is to **list explicitly**
only the warnings you want as errors.

## `--fail-fast` / `-x`

Supply `-x` or `--fail-fast` to `dbt run`, `dbt build`, or `dbt test` to make dbt exit
immediately on the first failure.

- `fail_fast` is a **global** flag, so it stops on **both run errors and test errors** —
  not just run errors.
- If other models are in progress when the first failure happens, dbt **terminates the
  connections** for those still-running models.
- The error you see is `FailFast Error in model ... Failing early due to test failure or
  runtime error`.

## Decision rule

| Goal | Flag |
|---|---|
| Stop the run the moment anything fails | `--fail-fast` / `-x` |
| Make one specific warning break CI | `--warn-error-options` with that warning in `error` |
| Make every warning break a dev run | `--warn-error` |
| See what dbt is really doing, verbosely | `--debug` / `-d` |
| Show only error logs in stdout | `QUIET` |

## Traps

- **Trap:** `--fail-fast` and `--warn-error` solve different problems. `--fail-fast` is
  about **when to stop**; `--warn-error` is about **what counts as a failure**.
- **Trap:** setting both `WARN_ERROR` and `WARN_ERROR_OPTIONS` is a usage error, not a
  merge.
- **Trap:** a test configured with `severity: warn` still warns under normal runs; it
  only becomes a failure under `--warn-error` or a matching `--warn-error-options`.
- **Trap:** flags are not resource configs. Setting `fail_fast` on a model is a scope
  error.
- **Trap:** CLI options beat environment variables beat `dbt_project.yml` beat
  `user_settings.yml` — see `../01-developing-and-optimizing-models/project-config-and-flags.md`.

## Why this is likely on the exam

It is a named sub-topic, and the `--warn-error` / `--warn-error-options` mutual exclusion
plus the production caveat give a clean BEST-practice qualifier with two genuinely
workable options.

## Related

- `compiled-code-and-logs.md` — `--debug` and log locations (Tasks 3.1, 3.2)
- `../01-developing-and-optimizing-models/project-config-and-flags.md` — precedence (Task 1.6)
