# `dbt_project.yml` and flag precedence

**Domain:** ae-01 — Task 1.6
**Verified:** 2026-09-29
**Concepts:** dbt_project.yml, config-version, model-paths, require-dbt-version, flags, global configs, config precedence, configs vs properties, --project-dir

Official topic: *"Defining configurations in dbt_project.yml"* (AE study guide, Topic 01).

[source: [dbt_project.yml — dbt Docs](https://docs.getdbt.com/reference/dbt_project.yml) — accessed 2026-09-29]
[source: [About flags (global configs) — dbt Docs](https://docs.getdbt.com/reference/global-configs/about-global-configs) — accessed 2026-09-29]
[source: [Command line options — dbt Docs](https://docs.getdbt.com/reference/global-configs/command-line-options) — accessed 2026-09-29]

## The file itself

`dbt_project.yml` is **required for all dbt projects** — its presence is how dbt knows a
directory is a dbt project. By default dbt looks for it in the current working directory
and its parents; override with `--project-dir` (or `DBT_ENGINE_PROJECT_DIR` from dbt
v1.11 and later).

Top-level keys include `name`, `config-version: 2`, `version`, `profile`, the various
`*-paths` keys (`model-paths`, `seed-paths`, `test-paths`, `analysis-paths`,
`macro-paths`, `snapshot-paths`, `docs-paths`, `asset-paths`), `packages-install-path`,
`clean-targets`, `query-comment`, `require-dbt-version`, and a `flags:` dictionary.

**Trap:** you **cannot** set a *property* in `dbt_project.yml` if it is not a *config*.
`macros` is the docs' own example. This applies to all resource types — see
[Configs and properties](https://docs.getdbt.com/reference/configs-and-properties).

## Flag precedence — "the most specific setting wins"

In order, highest precedence first:

| Rank | Where | Scope |
|---|---|---|
| 1 | **CLI options** | This invocation only |
| 2 | **Environment variables** | This runtime environment / this user |
| 3 | **`dbt_project.yml`** (`flags:`) | Version-controlled default for everyone on the project |
| 4 | **`~/.dbt/user_settings.yml`** | Personal preference across all projects on the machine |

If set nowhere, dbt uses the built-in default.

```yaml
# dbt_project.yml
flags:
  fail_fast: true
```

From dbt v1.11 the environment-variable prefix is **`DBT_ENGINE_`** (for example
`DBT_ENGINE_FAIL_FAST`). v1.10 and earlier use the `DBT_` prefix.

## Flags that break the pattern

- **Flags setting file paths** (for example `--log-path`, `--state`) **cannot** be set in
  `dbt_project.yml`. Use CLI options or environment variables.
- **Opt-in behaviour-change flags** can **only** be defined in `dbt_project.yml`, because
  they are meant to be version-controlled and migrated via pull request.
- Path keys that tell dbt where project resources live (for example `model-paths`) go in
  `dbt_project.yml` as **top-level keys, outside the `flags:` dictionary**.

## Traps

- **Trap (version drift):** `DBT_ENGINE_*` replaced `DBT_*` as the environment-variable
  prefix in v1.11. Older material uses `DBT_`.
- **Trap:** CLI flags belong **after** the subcommand — `dbt run --no-populate-cache`,
  not `dbt --no-populate-cache run`. Passing global flags before the subcommand is legacy
  functionality dbt Labs can remove at any time, and the same flag must not be used on
  both sides.
- **Trap:** flags are *global configs*, not *resource configs*. `materialized` and
  `grants` are resource configs; `fail_fast` and `warn_error` are flags. A stem asking
  "where do I set X for everyone on the project" depends on which kind X is.
- **Trap:** `full_refresh` and `store_failures` appear in the flag table **and** as
  resource configs. That dual nature is a natural distractor.
- **Trap:** strongly avoid using `flags` as an input to configs or to `ref`/`source`
  dependencies — dbt resolves those during parsing and flag values differ across
  invocations.

## Why this is likely on the exam

It is a named sub-topic, and precedence questions are easy to write and hard to guess.
The two exceptions (path flags cannot be in the project file; behaviour-change flags can
*only* be there) are the sharpest discriminators.

## Related

- `dry-runs-and-sampling.md` — two flags that cannot live in `dbt_project.yml` (Tasks 1.12, 1.13)
- `grants.md` — a resource config with its own inheritance rule (Task 1.9)
