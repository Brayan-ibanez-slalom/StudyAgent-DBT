# The `grants` config

**Domain:** ae-01 — Task 1.9
**Verified:** 2026-09-29
**Concepts:** grants, privilege, grantee, +select, clobber, merge and clobber, hooks, apply grants

Official topic: *"Providing access to users to models with the 'grants' config"*
(AE study guide, Topic 01).

[source: [grants — dbt Docs](https://docs.getdbt.com/reference/resource-configs/grants) — accessed 2026-09-29]

## What it does

Define `grants` as resource configs on each **model, seed, or snapshot**. When the
resource finishes building, dbt ensures that the grants on its view or table **match
exactly** the grants you configured, by running `grant` and/or `revoke` statements.

Two components:

- **Privilege** — a right to perform an action on a database object, such as selecting
  data from a table.
- **Grantees** — the recipients. Some platforms call these "principals": a user, a group,
  a Snowflake role, a BigQuery service account.

Set project-wide defaults in `dbt_project.yml`, and resource-specific grants in the
model's `config:` block in YAML or in the `.sql` file.

```yaml
# dbt_project.yml — the + is required here for a dictionary-valued config
models:
  +grants:
    select: ['user_a', 'user_b']
```

```sql
-- models/specific_model.sql
{{ config(grants = {'select': ['user_c']}) }}
```

## Inheritance: "merge and clobber"

When `grants` is set for the same model in more than one place, dbt's **default behaviour
replaces** the less-specific set of grantees with the more-specific set. This "merge and
clobber" behaviour updates **each privilege** when dbt parses the project.

In the example above, `specific_model` grants `select` to **`user_c` only**.

To **add** instead of replace, prefix the **privilege name** with `+`:

```sql
{{ config(grants = {'+select': ['user_c']}) }}
```

Now the model grants `select` to `user_a`, `user_b`, **and** `user_c`.

## Traps

- **Trap:** the `+` goes on the **privilege name inside the dictionary** (`'+select'`),
  and that is a *different* use of `+` from the `+grants:` prefix in `dbt_project.yml`,
  which merely marks a config with a dictionary value.
- **Trap:** the add-vs-clobber behaviour is **per privilege**. If you grant `select` with
  `+` and `insert` without it, `insert` still clobbers.
- **Trap:** the default is clobber, not merge. A model-level grant silently removes the
  project-level grantees from the database — which is a permissions incident, not an
  error message.
- **Trap:** grants apply to the resource's **view or table** at build time. For grants on
  other database objects, row- or column-level access, masking policies, or future
  grants, you need **hooks**, not the `grants` config.
- **Trap:** `grants` covers models, seeds, and snapshots — not sources, which dbt does
  not build.

## When to use hooks instead

Per the docs, define grants as resource configs whenever possible; reach for hooks when
you need to:

- apply grants on database objects other than views and tables
- create row-/column-level access, masking policies, or future grants
- use advanced platform permission capabilities dbt does not configure out of the box
- apply grants in a more complex or custom manner

## Why this is likely on the exam

It is a named sub-topic with one genuinely surprising documented behaviour (clobber by
default) and one exact-spelling detail (`'+select'`). That combination is ideal item
material, and the "grants vs hooks" boundary gives a clean LEAST-overhead qualifier.

## Related

- `project-config-and-flags.md` — config inheritance generally (Task 1.6)
- `../../arch/05-security-and-licenses/README.md` — account-level access on the Architect track
