# Packages and project dependencies

**Domain:** ae-01 — Task 1.7
**Verified:** 2026-09-29
**Concepts:** packages.yml, dependencies.yml, dbt deps, package dependencies, project dependencies, dbt Hub, private packages

Official topic: *"Using dbt Packages"* (AE study guide, Topic 01).

[source: [Packages — dbt Docs](https://docs.getdbt.com/docs/build/packages) — accessed 2026-09-29]

## `packages.yml` vs `dependencies.yml`

`dependencies.yml` can contain **both** kinds of dependency:

| Kind | What it does |
|---|---|
| **Package dependencies** | Add source code from someone else's dbt project into your own, like a library |
| **Project dependencies** | Build on top of someone else's dbt project via cross-project `ref` — the dbt Mesh workflow |

Either file lives at the same level as `dbt_project.yml`. `dbt deps` installs what they
declare.

## Decision rule

| Situation | File |
|---|---|
| You only use hub/Git/local packages as libraries | `packages.yml` (or `dependencies.yml`) |
| You need cross-project references between dbt projects (dbt Mesh) | `dependencies.yml` |
| You want projects **and** non-private packages in one place | `dependencies.yml` |
| Your package specs use **Jinja** — e.g. an env var or a Git token method for a **private** package | **`packages.yml`** — keep the filename |

If your project does not need Jinja in the package specifications, you can simply rename
`packages.yml` to `dependencies.yml`.

## Traps

- **Trap:** **private packages are not supported in `dependencies.yml`.** That file
  intentionally does **not** support Jinja rendering or conditional configuration, to
  keep the configuration static and predictable and compatible with other dbt services.
  So "just rename the file" is wrong precisely when a private Git package with a token is
  involved.
- **Trap:** `dependencies.yml` is **not** simply "the new name for `packages.yml`". A
  project can legitimately keep both.
- **Trap:** `packages.yml` installs code **into** your project; project dependencies let
  you `ref` across project boundaries without vendoring the code. Conflating the two is
  the classic `T3` confusable-sibling error.
- **Trap:** adding a package is not enough — `dbt deps` must run before the package's
  models and macros resolve.

## Why this is likely on the exam

"Using dbt Packages" is a named sub-topic, and the `packages.yml` / `dependencies.yml`
split is both recent and widely misunderstood. The private-package/Jinja restriction is
the highest-value single fact because it makes the obvious answer wrong.

## Related

- `../../arch/07-mesh-and-cross-project/README.md` — cross-project refs on the Architect track
- `dbt-commands.md` — `dbt deps` in the command set (Task 1.4)
