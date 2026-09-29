---
mode: agent
model: Claude Sonnet 5 (copilot)
description: Study a domain from the knowledge notes, then drill it — briefing first, questions second.
tools: ["domain_briefing", "topic_read", "topic_search", "concept_lookup", "drill_help", "drill_pick", "drill_grade_reasoned", "drill_why", "drill_explain", "progress_summary", "session_summary", "coverage_report", "exam_facts"]
---

# Study — briefing then drill (Sonnet, fast tier)

A full study cycle for one domain: read what the notes actually say, then test it.

## 1. Pick a domain

If the user has not named one, call `progress_summary()` and offer their **weakest**
domain by accuracy. If they have no history, ask which track (`ae` or `arch`) and start
at the first domain.

## 2. Brief

```
domain_briefing(domain="ae-02")
```

Everything returned is lifted **verbatim** from `knowledge/` notes, so a briefing cannot
invent content. Present it in this order:

1. **Exam angle** — what each note says about why this shows up
2. **Decision rules** — the "when to pick what" tables. These are the highest-value
   content in a briefing.
3. **Traps** — what the notes flag as commonly confused
4. **Section digest** — heading-level map so the user knows what exists

Then report the gaps honestly:

- `tasks_with_no_note` — blueprint tasks with no note at all
- `needs_full_read` — notes that state no traps and no decision rules

**Do not fill a gap from memory.** Say the note does not cover it, and offer to either
read the note in full (`domain_briefing(domain=..., topic_id=..., full=True)`) or hand
off to `/author` to write the missing note.

## 3. Drill what you just briefed

```
drill_help()
drill_pick(count=1, domain="ae-02", mode="unseen")
```

Then follow the standard drill protocol — **one question per turn**, present the
`answer_instruction` verbatim, stop and wait, grade with `drill_grade_reasoned`, coach in
2–3 sentences. See `.github/prompts/drill.prompt.md`; every rule there applies here.

## 4. Close the loop

After 5–8 questions, or when the user stops:

```
session_summary(range="today")
```

Tie the result back to the briefing:

- Which **decision rule** from the briefing did the misses cluster around?
- Which **trap** actually caught them?
- Is any **format** much worse than the rest? That is a format-practice gap, not a
  knowledge gap — say so and offer `drill_pick(qtype=...)` next time.

Then offer one of:

- Re-drill the missed concepts (`mode="missed"`)
- Move to the next domain
- Read one note in full, if a specific concept kept costing points

## Discipline

- ❌ Do not teach from memory. Everything you assert in a briefing must come from
  `domain_briefing` or `topic_read`.
- ❌ Do not state a domain weight or a passing score — dbt publishes none. Call
  `exam_facts()` if the user asks.
- ❌ Do not `cache_fetch` here. If a note is missing, that is an authoring task, not a
  study task.
- ❌ Do not answer the drill questions yourself.
