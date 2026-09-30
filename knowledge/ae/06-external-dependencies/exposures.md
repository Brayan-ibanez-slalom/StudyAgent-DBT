# Exposures

**Domain:** ae-06 — Task 6.1
**Verified:** 2026-09-29
**Concepts:** exposure, exposures, type, owner, depends_on, maturity, label, url, exposure: selection method

An exposure defines and describes a **downstream use** of your dbt project — a dashboard,
application, or data science pipeline.

Official topic: *"Implementing dbt exposures"* (AE study guide, Topic 06).

[source: [Add Exposures to your DAG — dbt Docs](https://docs.getdbt.com/docs/build/exposures) — accessed 2026-09-29]
[source: [Exposure properties — dbt Docs](https://docs.getdbt.com/reference/exposure-properties) — accessed 2026-09-29]

## What defining one buys you

- You can **run, test, and list** the resources that feed into the exposure.
- It **populates a dedicated page** in the auto-generated documentation site with context
  for data consumers.

```bash
dbt run  -s +exposure:weekly_jaffle_report
dbt test -s +exposure:weekly_jaffle_report
```

## Declaring one

Exposures live in `.yml` files under an **`exposures:`** key, typically alongside models.

```yaml
exposures:
  - name: weekly_jaffle_metrics
    label: Jaffles by the Week
    type: dashboard
    maturity: high
    url: https://bi.tool/dashboards/1
    description: >
      Did someone say "exponential growth"?
    depends_on:
      - ref('fct_orders')
      - ref('dim_customers')
      - source('gsheets', 'goals')
      - metric('count_orders')
    owner:
      name: Callum McData
      email: data@jaffleshop.com
```

| Property | Status | Notes |
|---|---|---|
| `name` | **Required** | Unique, **snake case** |
| `type` | **Required** | One of `dashboard`, `notebook`, `analysis`, `ml`, `application` |
| `owner` | **Required** | `name` **or** `email` required; extra properties allowed |
| `depends_on` | Expected | Refable nodes — `metric`, `ref`, and `source` |
| `label` | Optional | May contain spaces, capitals, special characters |
| `url` | Optional | Activates the "View this exposure" link in the docs site |
| `maturity` | Optional | `high`, `medium`, or `low` — confidence/stability |
| `description`, `tags`, `meta`, `enabled` | Optional | `enabled` may also be set project-wide in `dbt_project.yml` |

## Manual vs automatic

- **Manual** — declared explicitly in the project's YAML.
- **Automatic** — dbt creates and visualises downstream exposures automatically for
  supported integrations. These are stored in dbt's metadata system, appear in Catalog,
  and **behave like manual exposures — but they do not exist in YAML files.**

## Traps

- **Trap:** `name` must be **snake case**. Spaces and capitals belong in `label`, which
  is exactly what `label` exists for.
- **Trap:** `owner` is **required**, and it is satisfied by `name` *or* `email` — not
  necessarily both.
- **Trap:** the `depends_on` **YAML property** is not the `-- depends_on` **SQL comment
  directive** at the top of a model file. The latter explicitly adds DAG dependencies so
  referenced resources are built first.
- **Trap:** it is highly unlikely an exposure needs to depend on a `source` directly, even
  though it is possible.
- **Trap:** `maturity` is documentation metadata. It does not change build order or
  gating.
- **Trap:** an **exposure** is a declared downstream consumer; a **model version** is a
  parallel shape of a model; a **`deprecation_date`** is a lifecycle signal. Three
  different answers to three different questions.

## Why this is likely on the exam

Topic 06 has only two sub-topics and this is one of them. The required-vs-optional
property split and the `name`/`label` distinction are exactly the sort of exact-spelling
recall dbt tests.

## Related

- `source-freshness.md` — Task 6.2
- `../02-model-governance/model-versions.md` — the other "downstream consumers" idea
