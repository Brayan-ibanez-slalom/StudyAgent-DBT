---
mode: agent
model: Claude Sonnet 5 (copilot)
description: Sweep sealed questions for broken seals, stale sources, and version drift.
tools: ["verify_seal", "verify_all", "cache_check", "cache_fetch", "cache_fetch_batch", "cache_stats", "bank_audit", "defect_scan", "topic_read", "topic_search", "question_full", "progress_summary"]
---

# Verify — seal integrity sweep (Sonnet, fast tier)

Mechanical work: does each sealed answer still hold, and is its evidence still on disk?
No re-derivation — that is `/seal`.

## Model routing

Pinned to **Claude Sonnet 5**. Checking whether a cited page still contains the claim is
a lookup, not a judgement call. Anything that turns out to need judgement gets handed to
`/seal`.

## Sweep

```
verify_all(deep=True, track="ae", summary_only=False)
```

`seal_valid` is computed as: **all** structural checks pass (note exists, URL cached,
note `**Verified:**` within 180 days), **and** at least one cited source contains the
answer's core keywords. The keyword check is collective on purpose — a synthesis note may
cite several complementary pages where each covers only part of the rationale.

## Triage by failure mode

| Failure | What it means | Fix |
|---|---|---|
| `cache_miss:<url>` | Source was never fetched, or the cache was cleared | `cache_fetch(url)`, re-verify |
| `cache_file_missing` | Index entry exists, file does not | `cache_fetch(url, force=True)` |
| `note_exists: false` | The seal points at a note nobody wrote | Write the note, or re-seal against a URL |
| `note_freshness` | Note `**Verified:**` older than 180 days | Re-read the cited docs, update the date — **or find that dbt changed** |
| `keywords_in: false` on every source | The cited page does not support the claim | **Hand to `/seal`.** Do not patch the keywords. |
| `has_sources: false` | Sealed with no citation at all | Hand to `/seal` |

**The only one you must not fix yourself is the last keyword case.** A seal whose source
does not support it is a correctness problem, not a plumbing problem.

## Staleness sweep — the dbt-specific part

```
cache_stats()
```

dbt ships fast enough that a 90-day-old cached page is a real risk, not a formality.
For anything in `stale_gte_90d`:

```
cache_fetch_batch([...stale urls...], force=True)
```

Then re-run `verify_all(deep=True)`. **A seal that was valid against an old page and is
now invalid against the fresh one is the single most valuable finding in this repo** — it
means dbt changed and the bank is teaching something false. Flag it loudly and hand it to
`/seal`.

## Structural sweep

```
bank_audit()
defect_scan()
```

These do not check correctness — they check whether an item is answerable without
knowing any dbt. Report the queue; rewriting is `/author`'s job.

## Report format

Lead with what is broken, not with what passed:

1. Count: sealed / valid / invalid
2. Invalid items grouped by failure mode, with the fix for each
3. Anything that went from valid → invalid after a cache refresh, called out separately
   as **suspected dbt behaviour change**
4. Cache health: fresh / stale / missing
5. The handoff list for `/seal` and `/author`

## Forbidden

- ❌ Re-deriving a sealed answer — hand it to `/seal`
- ❌ Editing `drill_answer_short` to make a keyword check pass
- ❌ Marking something valid because it "looks right"
- ❌ Bulk-refreshing the whole cache without reporting what changed
