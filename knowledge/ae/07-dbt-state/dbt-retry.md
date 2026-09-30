# `dbt retry`

**Domain:** ae-07 — Task 7.2
**Verified:** 2026-09-29
**Concepts:** dbt retry, run_results.json, point of failure, no operation, --threads, --vars

Official topic: *"Using dbt retry"* (AE study guide, Topic 07).

[source: [About dbt retry command — dbt Docs](https://docs.getdbt.com/reference/commands/retry) — accessed 2026-09-29)]
[source: [About dbt retry command — dbt Docs](https://docs.getdbt.com/reference/commands/retry) — accessed 2026-09-29]

## What it does

`dbt retry` **re-executes the last invocation from the point of failure**. It reads the
previous run's results rather than re-deciding what to build.

## The three cases you can be tested on

| Situation | What `dbt retry` does |
|---|---|
| Some nodes ran, then one failed | Re-executes **from the point of failure** |
| **No nodes executed** before the failure — e.g. a warehouse connection or permission error | **Runs nothing**, because there are no recorded nodes to retry from |
| The previous command **completed successfully** | Finishes as a **no operation** |

In the no-recorded-nodes case the documented advice is to **check `run_results.json` and
manually re-run the full job** so the nodes build. Once some nodes have run, you can use
retry to re-execute from any new point of failure.

## Flags

`dbt retry` flags apply to a self-hosted dbt installation or the Studio IDE. Against a
cloud environment the dbt platform CLI accepts only a small subset of overrides —
typically `--threads`, `--vars`, and related options; `dbt retry --help` lists what a
given build supports.

Supported overrides include `-t, --target`, `--project-dir`, `--profile`,
`--profiles-dir`, `--packages-install-path`, `--target-path`, and `--vars`.

## Traps

- **Trap:** retry after an early connection or permission failure looks broken. It is
  documented behaviour — no recorded nodes means nothing to resume.
- **Trap:** retry does **not** re-select. It resumes the previous invocation, so a
  changed selector will not be honoured — re-run the command instead.
- **Trap:** retry is not `--full-refresh`. It resumes; `--full-refresh` rebuilds
  incremental models as tables.
- **Trap:** retry is not `dbt clone`. It re-executes work; clone copies existing objects.
- **Trap:** a successful previous run makes retry a no-op, not an error.

## Decision rule

| Goal | Command |
|---|---|
| Resume a partially completed run where it stopped | `dbt retry` |
| Rebuild an incremental model from scratch | `dbt run --full-refresh` |
| Build only what changed since production | `--select "state:modified" --state ...` |
| Avoid building unselected parents | `--defer --state ...` |
| Copy existing production objects | `dbt clone --state ...` |

## Why this is likely on the exam

It is one of only two Topic 07 sub-topics, so it is disproportionately likely to appear,
and the "retry did nothing" case is the single most testable fact about it.

## Related

- `state-selection.md` — Task 7.1
- `../04-troubleshooting-pipelines/dag-failure-points.md` — Task 4.1
- `../04-troubleshooting-pipelines/dbt-clone.md` — Task 4.2
