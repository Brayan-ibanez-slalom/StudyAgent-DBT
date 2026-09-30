# Model versions and deprecation

**Domain:** ae-02 — Task 2.2
**Verified:** 2026-09-29
**Concepts:** versions, latest_version, prerelease, deprecation_date, ref with version, include, exclude, model versions

Versions let a model owner change a model's structure in a way that would break its
contract, without breaking consumers on day one.

Official topic: *"Creating different versions of our models and deprecating the old
ones"* (AE study guide, Topic 02).

[source: [Model versions — dbt Docs](https://docs.getdbt.com/docs/collaborate/govern/model-versions) — accessed 2026-09-29]
[source: [deprecation_date — dbt Docs](https://docs.getdbt.com/reference/resource-properties/deprecation_date) — accessed 2026-09-29]

## Why version rather than edit in place

If a model defines a contract, changing its structure can break the guarantees — obvious
cases like removing or renaming a column, subtler ones like changing a data type or
nullability. Versions let the owner:

- test **"prerelease"** changes in production and in downstream systems
- bump the **latest** version to be the canonical source of truth
- offer a **migration window** off the old version

## The three states and the naming convention

With `latest_version: 2`, `v3` is prerelease and `v1` is an old version still inside its
deprecation window:

| Version | State | `ref` syntax | File name | Database relation |
|---|---|---|---|---|
| 3 | prerelease | `ref('dim_customers', v=3)` | `dim_customers_v3.sql` | `analytics.dim_customers_v3` |
| 2 | **latest** | `ref('dim_customers', v=2)` **and** `ref('dim_customers')` | `dim_customers_v2.sql` **or** `dim_customers.sql` | `analytics.dim_customers_v2` |
| 1 | old | `ref('dim_customers', v=1)` | `dim_customers_v1.sql` | `analytics.dim_customers_v1` |

Key points:

- **All versions preserve the model's original name.** Versioning is a suffix on the
  relation, not a rename.
- The **latest** version gets special treatment: it may live in a file **without** a
  suffix, and an unpinned `ref('dim_customers')` resolves to it.
- You can **select** models to build based on whether they are a `latest`, `prerelease`,
  or `old` version.
- dbt notifies consumers when new versions become available or when a version is slated
  for deprecation.

**Trap:** `latest_version` is what makes a version "latest" — not the highest number.
A prerelease `v3` exists but an unpinned `ref` still resolves to `v2` until the
maintainer bumps `latest_version`. dbt even logs that a prerelease is available and has
not yet been marked `'latest'` by its maintainer.

## `deprecation_date`

dbt **1.6** introduced first-class support for deprecating models via `deprecation_date`.

```yaml
models:
  - name: my_model
    description: deprecating in the future
    deprecation_date: 2999-01-01 00:00:00.00+00:00
```

- Formatted as a date, optionally with a timezone offset. Supported RFC 3339 forms:
  `YYYY-MM-DD hh:mm:ss.sss±hh:mm`, `YYYY-MM-DD hh:mm:ss.sss`, `YYYY-MM-DD`.
- **Trap:** without an offset from UTC it is interpreted in the **system time zone of the
  dbt execution environment** — not UTC.
- It works well **alongside** model versions but can be used **independently** of them.

## Traps

- **Trap:** version vs deprecation vs exposure are three different things. A **version**
  is a parallel shape of the same model; a **`deprecation_date`** is a lifecycle signal;
  an **exposure** is a downstream consumer declared in the DAG.
- **Trap:** bumping a version does not remove the old one. The old version keeps building
  through its migration window, which is the entire point.
- **Trap:** a model with an **enforced contract** cannot simply be deleted before its
  deprecation date passes.
- **Trap:** `ref('model')` with no `v=` is not "whatever exists" — it is `latest_version`.

## Why this is likely on the exam

It is a named sub-topic, and the `latest_version`-versus-highest-number distinction plus
the unsuffixed-file convention are exactly the kind of detail that separates people who
have read the docs from people who have only used dbt.

## Related

- `model-contracts.md` — the guarantee that versioning exists to break safely (Task 2.1)
- `../06-external-dependencies/README.md` — exposures, the other "downstream consumer" idea
