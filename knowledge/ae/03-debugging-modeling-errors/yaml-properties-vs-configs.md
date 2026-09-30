# YAML properties vs configs

**Domain:** ae-03 — Task 3.3
**Verified:** 2026-09-29
**Concepts:** properties, configs, properties.yml, config(), dbt_project.yml, config: selection method, inherit, override

Official topic: *"Troubleshooting .yml compilation errors"* (AE study guide, Topic 03).

[source: [Configurations and properties — dbt Docs](https://docs.getdbt.com/reference/configs-and-properties) — accessed 2026-09-29]
[source: [Model properties — dbt Docs](https://docs.getdbt.com/reference/model-properties) — accessed 2026-09-29]

## The distinction that causes most YAML errors

**Properties describe resources. Configurations control how dbt builds them.**

Configs are a **special kind of property** that bring extra abilities. The rule of thumb
from the docs: *properties declare things **about** your project resources; configs go
the extra step of telling dbt **how** to build those resources in your warehouse.* The
docs add that this is generally true but not always, so check.

| | Where it can be set |
|---|---|
| **Property** | Declared for resources one-by-one in `properties.yml` files |
| **Config** | In `properties.yml` nested under a `config` property; via the `config()` macro right in `.sql` files; or for many resources at once in `dbt_project.yml` |

Because configs can be set in multiple places, they are applied **hierarchically** — an
individual resource may **inherit** or **override** configs set elsewhere. Properties
have no such hierarchy.

## Consequences you can be tested on

- You can **select resources by config value** using the `config:` selection method — but
  **not** by the values of non-config properties.
- A **property** cannot be set in `dbt_project.yml` if it is not a config. `macros` is
  the docs' own example of a property that cannot live there.
- Examples of properties: descriptions of models/snapshots/seeds and their columns, data
  tests asserting truths about a model, and exposures declaring official downstream uses.

## Traps

- **Trap:** putting a non-config property in `dbt_project.yml` is one of the most common
  `.yml` compilation errors, and the error names the property rather than explaining the
  rule.
- **Trap:** nesting matters. A config in a properties file must sit under the `config:`
  key; putting it at the same level as `name:` is a parse error, not a silent no-op.
- **Trap (version drift):** the current YAML key for tests is **`data_tests:`**. The
  older key **`tests:` is still supported as an alias** — so "`tests:` is invalid" is
  wrong, and so is "the two keys mean different things".
  [source: [Add data tests to your DAG — dbt Docs](https://docs.getdbt.com/docs/build/data-tests)]
- **Trap:** `config:` selection works on configs only. "Select every model whose
  description mentions X" is not a thing.
- **Trap:** YAML is whitespace-significant and dbt parses **all** `.yml` files in the
  configured paths. A broken file that no model references still breaks the parse.

## Fix-and-verify loop for a YAML error

| Step | Command |
|---|---|
| Validate the project code without touching the warehouse | `dbt parse` |
| See what the YAML actually produced for one node | `dbt compile --select my_model` |
| Confirm the connection is not the real problem | `dbt debug` |

## Why this is likely on the exam

It is a named sub-topic, and the property/config boundary explains a whole family of
error messages. The `config:` selection asymmetry is a crisp, checkable fact.

## Related

- `compiled-code-and-logs.md` — `dbt parse` vs `dbt compile` (Tasks 3.1, 3.2)
- `../01-developing-and-optimizing-models/project-config-and-flags.md` — Task 1.6
- `fix-and-verify-before-merge.md` — Task 3.4
