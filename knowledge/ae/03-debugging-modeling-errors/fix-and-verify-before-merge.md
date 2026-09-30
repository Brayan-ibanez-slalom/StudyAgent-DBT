# Fixing and verifying before merge

**Domain:** ae-03 — Task 3.4
**Verified:** 2026-09-29
**Concepts:** CI job, continuous integration, Slim CI, --defer, --state, --favor-state, --defer-state, state:modified, temporary schema

Official topic: *"Developing and implementing a fix and testing it prior to merging"*
(AE study guide, Topic 03).

[source: [Continuous integration in dbt — dbt Docs](https://docs.getdbt.com/docs/deploy/continuous-integration) — accessed 2026-09-29]
[source: [Defer — dbt Docs](https://docs.getdbt.com/reference/node-selection/defer) — accessed 2026-09-29]

## What a CI job does

dbt tracks the state of what is running in the production environment. When a CI job
runs, **only the modified data assets in the pull request and their downstream
dependencies** are built and tested, in a **staging schema**.

- dbt listens for a notification from the Git provider that a PR has been opened or
  updated with new commits, then enqueues a run of the CI job.
- It builds and tests the affected models, semantic models, metrics, and saved queries
  in a **temporary schema unique to the PR**, named
  **`dbt_cloud_pr_<job_id>_<pr_id>`** (for example `dbt_cloud_pr_1862_1704`).
- The status is posted back to GitHub, GitLab, or Azure DevOps, and the Git provider can
  be configured so only PRs with successful CI checks are approvable.
- dbt **deletes the temporary schema** when the PR is closed or merged.

**Trap:** if the project customises schemas with `generate_schema_name`, dbt **might not
drop** the temporary schema. That is a documented caveat, not a bug in your code.

## Defer — building a subset without building its parents

Defer makes it possible to run a subset of models, tests, or functions in a sandbox
environment **without first building their upstream parents**. Use it to modify
end-of-pipeline models by pointing at production models instead of running everything
upstream.

Defer **requires a manifest from a previous dbt invocation**, supplied with `--state`
(or `DBT_ENGINE_STATE`). Together with the `state:` selection method, this is **Slim CI**.

```bash
dbt run --select [...] --defer --state path/to/artifacts
dbt test --select [...] --defer --state path/to/artifacts
```

### When a `ref` actually gets deferred

With `--defer` enabled, dbt resolves `ref` (and `function`) calls using the **state
manifest** instead, but **only if**:

1. the node **is not among the selected nodes**, **and**
2. it **does not exist in the database** — *or* `--favor-state` is used.

**Trap:** **ephemeral models are never deferred**, because they are pass-throughs for
other `ref` calls.

### `--favor-state`

When `--favor-state` is passed, dbt **prioritises node definitions from the `--state`
directory**. However, this does **not** apply if the node is also part of the selected
nodes.

So the difference in one line: `--defer` falls back to prod only when the object is
missing locally; `--favor-state` prefers prod even when a local object exists.

### Separate state for comparison and deferral

`--state` / `DBT_ENGINE_STATE` and `--defer-state` / `DBT_ENGINE_DEFER_STATE` can point
at different manifests, letting you compare logical state against one environment while
deferring to applied state from another. **If `--defer-state` is not specified, deferral
uses the manifest supplied to `--state`.**

## Traps

- **Trap:** `--defer` without `--state` does nothing useful — deferral requires a
  manifest from a previous invocation.
- **Trap:** a selected node is never deferred, even with `--favor-state`. Selection wins.
- **Trap:** `dbt clone` can achieve similar outcomes for some use cases, but it copies
  objects into your schema rather than redirecting `ref`s.
- **Trap:** CI builds **modified assets and their downstream dependencies** — not the
  whole project, and not only the changed file.

## Why this is likely on the exam

"Test it prior to merging" is the named sub-topic, and the defer/favor-state condition is
a two-part rule with an explicit exception — textbook L4/L5 material.

## Related

- `../07-dbt-state/README.md` — `state:modified` and `dbt retry` (Topic 07)
- `../01-developing-and-optimizing-models/dbt-commands.md` — `dbt build` in CI
