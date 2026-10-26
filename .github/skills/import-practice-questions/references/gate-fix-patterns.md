# item_gate fatal-failure cheat-sheet

Empirically, these are the fatal failures that recur most when authoring items this way,
and the fastest fix for each. All examples assume the letter-option (multiple_choice /
multiple_response) formats; fill_in_blank items skip almost all of these automatically.

## "no term leaks from stem to key alone"

**Cause:** a distinctive word (≥5–6 chars) appears in the stem and in the correct
option(s), but in **no distractor**. The checker flags this as a free giveaway.

**Fix:** add the same word into at least one distractor's text — even a semantically odd
placement is fine, since it's a wrong option anyway. Do **not** just delete the word from
the key; it's usually load-bearing for correctness. Watch for hyphenated compounds: `"T-1"`
and `"T1"` are different tokens, so `"already-compiled"` does **not** satisfy a leak on
the bare word `"already"` — spell the shared word out standalone in the distractor.

## "every distractor has a quoted verdict" / "plausible options cite a stem clause"

**Cause:** a `plausible_options` or `eliminated_by` quote is not an **exact** substring of
the final stem (missing/extra punctuation, backticks, or the quote drifted after a later
stem edit), or the quote is the lead-in question itself (contains `?`), or is under 20
characters.

**Fix:** copy-paste the quote directly from the final stem text, including backticks.
Re-check every quote any time you edit the stem afterward — this is the single most
common regression when fixing a different failure on the same item.

## "plausible options are not T1/T4 traps"

**Cause:** an option listed in `plausible_options` is tagged `T1` (fabricated) or `T4`
(breaks a stated requirement) in `distractor_traps`. A genuinely plausible rival cannot
be definitionally fabricated or requirement-breaking.

**Fix:** retag the plausible option's trap family to `T2`, `T3`, `T5`, `T6`, `T7`, or
`T8` — whichever is closest to the real reasoning. `T3` (confusable sibling) is the
safest default when unsure.

## "not solvable by elimination alone" / "elimination signals are not one sweep"

**Cause:** every distractor is eliminated by a bare stem-signal quote (no `requires_fact`,
no `plausible_options` entry) — the item is answerable by reading comprehension alone,
with no dbt knowledge required. This is most common on simple "which of these is NOT X"
recall items with 3 cheaply-wrong distractors.

**Fix:** mark **one** distractor as `plausible_options` instead of `eliminated_by` (it
needs no elimination verdict at all once it's plausible), or convert one `eliminated_by`
entry to the `{"signal": ..., "requires_fact": ...}` dict form with a real documented
fact. Either one creates a genuine "survives without the tested fact" rival.

## "no lexical giveaway in the key" / "key is not the odd one out"

**Cause:** the key echoes far more distinctive stem vocabulary than any distractor
(lexical giveaway), or every distractor opens with the same word/shape while the key
opens differently (structural giveaway).

**Fix:** paraphrase the key to use less of the stem's exact phrasing, and/or spread the
stem's named entities across distractors too. For structural giveaways, rewrite option
openings to share a part-of-speech pattern (e.g. make every option a noun phrase, or make
every option start with the same subject).

## Multiple-response count / option-count mismatches

`multiple_choice`/`domc` use the official option counts (4–5 for single-answer);
`multiple_response` needs 4–6 options total regardless of how many are correct. Don't
default to exactly 4 options with 2 correct and only 2 distractors if the concept
naturally supports a 5th or 6th plausible-but-wrong option — more real distractors make
`check_not_pure_elimination` easier to satisfy.

## General workflow tip

Fix an entire batch file's fatals in one `python3` patch script per round (read JSON,
mutate by `id`, write back), then re-run `item_gate` once per round, rather than editing
and re-gating one item at a time. Two to three rounds normally clears an 8–13 item batch.
