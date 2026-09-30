# DAG failure points and selection

**Domain:** ae-04 — Task 4.1
**Verified:** 2026-09-29
**Concepts:** graph operators, plus operator, n-plus, at operator, @, --exclude, skipping, on_error, run_results.json, dbt retry

Official topic: *"Troubleshooting and managing failure points in the DAG"*
(AE study guide, Topic 04).

[source: [Graph operators — dbt Docs](https://docs.getdbt.com/reference/node-selection/graph-operators) — accessed 2026-09-29]
[source: [About dbt build command — dbt Docs](https://docs.getdbt.com/reference/commands/build) — accessed 2026-09-29]
[source: [About dbt retry command — dbt Docs](https://docs.getdbt.com/reference/commands/retry) — accessed 2026-09-29]

## What a failure does to the rest of the DAG

- By default, if a **model** fails, all downstream models are **skipped**.
- Under `dbt build`, **tests on upstream resources block downstream resources**, and a
  test failure causes those downstream resources to skip entirely.
- To stop a test causing skips, adjust its **severity or thresholds** to `warn` rather
  than `error`.
- For a test with multiple parents where one parent depends on the other, the test blocks
  and skips children of the **most-downstream parent only**. For independent parents, dbt
  skips a downstream node only if it depends on **all** of those parents.

## Re-running just the broken part

| Operator | Selects |
|---|---|
| `my_model+` | the model and **all descendants** (downstream) |
| `+my_model` | the model and **all ancestors** (upstream) |
| `+my_model+` | the model, all ancestors, and all descendants |
| `my_model+1` | the model and its **first-degree** descendants |
| `2+my_model` | the model, its parents, and its grandparents |
| `3+my_model+4` | ancestors up to 3 degrees, descendants down to 4 |
| `@my_model` | like `+`, but **also all ancestors of all descendants** |

The `@` operator exists for CI environments where you want to build a model and all of
its descendants, but the **ancestors of those descendants might not exist in the schema
yet**. That is the fact that separates `@` from `+`.

Combine any of these with `--exclude` for finer control.

## `dbt retry`

`dbt retry` re-executes the **last invocation from the point of failure**.

- **Trap:** if **no nodes executed** before the failure — for example a warehouse
  connection or permission error that killed the run early — retry **won't run anything**,
  because there are no recorded nodes to retry from. The documented advice is to check
  `run_results.json` and manually re-run the full job.
- Once some nodes have run, retry re-executes from any new point of failure.
- If the previous command completed successfully, **retry finishes as a no-op**.

## Traps

- **Trap:** `+` and `@` are not interchangeable. `@` additionally pulls in the ancestors
  of the descendants — the thing you need when the downstream models' other parents are
  missing.
- **Trap:** the number in `my_model+1` counts **edges**, not nodes.
- **Trap:** a skipped model is not a failed model. Chasing the skip instead of the
  original failure is the classic misdiagnosis.
- **Trap:** `dbt retry` after a connection failure appears to "do nothing". That is
  documented behaviour, not a broken retry.
- **Trap:** `dbt retry` resumes; `--full-refresh` rebuilds; `dbt clone` copies. Three
  different recovery stories.

## Why this is likely on the exam

Topic 04 has only two sub-topics, and this is one of them, so the DAG-failure material is
concentrated. The `@` operator's rationale and the retry-with-no-recorded-nodes case are
the two most discriminating facts.

## Related

- `dbt-clone.md` — Task 4.2
- `../07-dbt-state/README.md` — `dbt retry` in depth (Task 7.2)
- `../01-developing-and-optimizing-models/dbt-commands.md` — `dbt build` skipping rules
