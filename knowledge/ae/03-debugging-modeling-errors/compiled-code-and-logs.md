# Debugging with compiled code

**Domain:** ae-03 — Tasks 3.1, 3.2
**Verified:** 2026-09-29
**Concepts:** dbt compile, target/compiled, target/run, dbt parse, dbt debug, --inline, execute, compiled SQL, logs/dbt.log

Official topics: *"Understanding logged error messages"* and *"Troubleshooting using
compiled code"* (AE study guide, Topic 03).

[source: [About dbt compile command — dbt Docs](https://docs.getdbt.com/reference/commands/compile) — accessed 2026-09-29]
[source: [About dbt debug command — dbt Docs](https://docs.getdbt.com/reference/commands/debug) — accessed 2026-09-29]
[source: [Logs — dbt Docs](https://docs.getdbt.com/reference/global-configs/logs) — accessed 2026-09-29]

## What `dbt compile` is for

- **Visually inspecting** the compiled output of resource files — useful for validating
  complex Jinja logic or macro usage.
- **Manually running compiled SQL.** While debugging a model or a data test, it is often
  useful to execute the underlying `select` statement to find the source of the bug.
- Compiling **analysis** files.

Compiled SQL files land in the `target/` directory of the project.

Since dbt v1.5, `compile` can be **interactive**, displaying compiled code in the CLI:

```bash
dbt compile --select "stg_orders"
dbt compile --inline "select * from {{ ref('raw_orders') }}"
```

`--inline` logs the compiled SQL to the terminal **in addition to** writing to `target/`.

## Three commands people confuse

| Command | Connects to the warehouse? | Use when |
|---|---|---|
| `dbt parse` | **No** | You just want dbt to read and validate the project code |
| `dbt compile` | **Yes** — it runs queries and `execute` is `True` | You want to see or hand-run the SQL dbt would submit |
| `dbt debug` | **Yes** | You suspect the connection, profile, project file, or environment is broken |

`dbt compile` is similar to `dbt run` except that it does not materialize the compiled
SQL into a table. Up to the point of materialization they both require a data platform
connection, run queries, and set the `execute` variable to `True`.

## What `dbt debug` validates

By default: the **database connection** for configured profiles, **dbt project setup**
(such as `dbt_project.yml` validity), the **system environment** (OS, Python version,
installed dbt version), **required dependencies** (such as `git` for `dbt deps`), and
**adapter details**.

**Trap:** `dbt debug` is not to be confused with **debug-level logging** via the
`--debug` option, which simply increases verbosity.

## Logs

- dbt writes logs to `logs/` and all other artifacts to `target/`, both relative to
  `dbt_project.yml` of the active project.
- `--debug` (shorthand `-d`) redirects debug logs to standard output, showing
  debug-level information in the terminal **in addition to** the `logs/dbt.log` file.
- `QUIET` shows only error logs in stdout, though logs still include anything passed to
  the `print()` macro — handy for isolating a Jinja error.
- Override locations with `--target-path` / `--log-path` or `DBT_ENGINE_TARGET_PATH` /
  `DBT_ENGINE_LOG_PATH`.

## Traps

- **Trap:** `dbt compile` is **not** a prerequisite of `dbt run` or the other building
  commands. They handle compilation themselves. Adding `dbt compile` before `dbt run` in
  a job is a classic over-engineering distractor.
- **Trap:** if you do **not** want to connect to the warehouse, `dbt compile` is the
  wrong command — use `dbt parse`.
- **Trap:** compiled SQL for resources that use **introspective queries** may depend on
  warehouse metadata, so compilation can be incomplete or differ depending on the state
  of that metadata. "The compiled file looks wrong" is not automatically a Jinja bug.
- **Trap:** `--debug` increases verbosity; `dbt debug` tests the connection. Different
  things with confusingly similar names.
- **Trap:** you can compile **tests** too, as long as the selector matches a test node —
  for example `dbt compile --select "resource_type:test"`.

## Why this is likely on the exam

Two of the five Topic 03 sub-topics are about reading errors and compiled code, and the
`parse` / `compile` / `debug` / `--debug` cluster is a four-way confusable set with a
crisp documented separator: does it touch the warehouse, and does it materialize?

## Related

- `behaviour-flags.md` — `--warn-error`, `--fail-fast`, log verbosity (Task 3.5)
- `../01-developing-and-optimizing-models/dbt-commands.md` — the wider command set
