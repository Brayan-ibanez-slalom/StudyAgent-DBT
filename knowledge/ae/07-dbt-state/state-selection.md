# State and state selection

**Domain:** ae-07 — Task 7.1
**Verified:** 2026-09-29
**Concepts:** state, --state, state:new, state:modified, state:old, state:unmodified, state:modified.body, state:modified.configs, state:modified.contract, manifest, Slim CI

Official topic: *"Understanding state and state selection"* (AE study guide, Topic 07).

[source: [Node selector methods — dbt Docs](https://docs.getdbt.com/reference/node-selection/methods) — accessed 2026-09-29]
[source: [Caveats to state comparison — dbt Docs](https://docs.getdbt.com/reference/node-selection/state-comparison-caveats) — accessed 2026-09-29]
[source: [Defer — dbt Docs](https://docs.getdbt.com/reference/node-selection/defer) — accessed 2026-09-29]

## The four state selectors

| Selector | Selects |
|---|---|
| `state:new` | Nodes with no matching `unique_id` in the comparison manifest |
| `state:modified` | **All new nodes, plus any changes to existing nodes** |
| `state:old` | Nodes whose `unique_id` **does** exist in the comparison manifest |
| `state:unmodified` | All existing nodes with **no** changes |

`state:old` and `state:unmodified` are the inverses of the first two and exist to shorten
run times by excluding unchanged nodes. **They currently have no subselectors.**

```bash
dbt run --select "state:modified" --state path/to/artifacts
dbt ls  --select "state:modified" --state path/to/artifacts
```

## `state:modified` subselectors

Because state comparison is complex, dbt supports subselectors covering a subset of the
full `modified` criteria:

| Subselector | Detects |
|---|---|
| `state:modified.body` | Changes to node body — model SQL, seed values |
| `state:modified.configs` | Changes to node configs, **excluding** `database` / `schema` / `alias` / `tags` / `meta` |
| `state:modified.relation` | Changes to `database` / `schema` / `alias`, irrespective of `target` values or `generate_x_name` macros |
| `state:modified.persisted_descriptions` | Relation- or column-level `description` changes, **if and only if** `persist_docs` is enabled at each level |
| `state:modified.macros` | Changes to upstream macros, called directly or indirectly |
| `state:modified.contract` | Changes to a model's contract — currently the `name` and `data_type` of columns |

Plain `state:modified` includes **all** of the above, plus resource-specific criteria such
as a source's `freshness` or `quoting` rules, or an exposure's `maturity`. It also picks
up changes to `access` permissions, `deprecation_date`, and `latest_version`.

**Trap:** for `state:modified.contract`, **removing or changing the type of an existing
column is a breaking change and raises an error** — it does not merely flag the node.

## What does *not* count as modified

- **`tags` and `meta`** — at the resource level **or** on individual columns — are treated
  as **metadata only** and do **not** trigger `state:modified`. This is intentional,
  because they do not affect how a resource is materialized.
- **`description`** is different: it **does** count, but **only when `persist_docs` is
  enabled**.
- Any other config change counts, because a config could affect materialization.

## Caveats that decide exam questions

- **Seeds:** dbt stores a file hash for seeds **under 1 MiB**. For a seed **over 1 MiB**
  dbt cannot compare contents, raises a warning, and falls back to comparing the **file
  path only** — so editing a large seed's rows without renaming the file leaves it
  **unmodified**.
- **Macros:** dbt marks modified any resource depending on a changed macro, or on a macro
  that depends on a changed macro.
- **Vars:** if a model uses a `var` or `env_var`, dbt **cannot** trace that lineage well
  enough to include the model in `state:modified` just because the value changed. It will
  only be flagged if the change results in a different configuration.
- **Tests:** `dbt test -s state:modified` includes both tests that select from a new or
  modified resource **and** tests that are themselves new or modified.
- Adding a test without modifying its model can mean testing a model you have not run —
  which is what **deferral** is for.

## `state:modified` vs `--defer` vs `--favor-state`

| | Answers |
|---|---|
| `state:modified` | **What should I build?** |
| `--defer` | **Where do unbuilt parents come from?** |
| `--favor-state` | **Which side wins when both exist?** |

## Traps

- **Trap:** state selection needs `--state` pointing at a manifest from a previous
  invocation. Without it there is nothing to compare against.
- **Trap:** renaming a tag does not rebuild anything. Renaming a **group** does, because
  `group` is a config.
- **Trap:** `state:modified.configs` deliberately excludes `database`/`schema`/`alias` —
  those belong to `state:modified.relation`.

## Why this is likely on the exam

It is one of two Topic 07 sub-topics, the subselector list is exact-spelling recall, and
the "tags and meta do not count" rule is counter-intuitive enough to make a strong key.

## Related

- `dbt-retry.md` — Task 7.2
- `../03-debugging-modeling-errors/fix-and-verify-before-merge.md` — defer and Slim CI
