---
name: import-practice-questions
description: 'Turn a pasted third-party practice exam (quiz export, screenshot transcript, PDF dump) into original, gate-verified questions for this bank. Use when the user pastes/attaches third-party exam questions and asks to add, import, or load them into the question bank, add questions from a practice test, or "do the same" with a new batch of pasted questions. Covers copyright/verification triage, domain remapping, independent re-grounding against docs.getdbt.com, batch authoring, item_gate/balance_keys/authored_ingest, and the commit+push workflow.'
---

# Importing a pasted practice exam as original questions

Third-party dbt practice material is **untrusted** (see
`.github/copilot-instructions.md` source-of-truth hierarchy) and is frequently wrong about
current dbt behavior. This skill turns a pasted dump of such material into **original**
items that teach the same concepts, independently verified against cached
`docs.getdbt.com` pages, through the normal [`/author`](../../prompts/author.prompt.md)
quality gate. It does not scrape, paraphrase-to-evade, or admit the source's claimed
answers uncritically.

Read [docs/item-authoring-spec.md](../../../docs/item-authoring-spec.md) and
`.github/prompts/author.prompt.md` first — this skill assumes that spec and adds the
pasted-source-specific procedure on top of it.

## 1. Triage before writing anything

1. **Confirm rights.** A pasted quiz export is presumptively a third-party copyrighted
   work. Ask the user (`ask_user`) whether they have rights to reproduce it verbatim, or
   whether you should create **original** questions on the same concepts instead. Default
   recommendation: original. Never reproduce stems/options verbatim without explicit
   confirmed rights.
2. **Confirm scope.** Ask whether to cover every source question (1:1) or only concepts
   not already in the bank. If the user has already answered this in an earlier turn of
   the same kind of request (e.g. "do the same with these new questions"), reuse that
   answer — do not re-ask.
3. **Parse the dump.** Extract question count, per-question stem text, and the source's
   own domain label, e.g.:
   ```python
   import re
   parts = re.split(r'Question (\d+)', raw_text)[1:]
   # parts[i] = question number, parts[i+1] = body text
   ```
   Classify qtype heuristically (`fill the blank` → fill_in_blank, `Choose N`/`TWO` →
   multiple_response, else multiple_choice) to plan batch sizes.
4. **Never trust the source's claimed answer or domain label.** Re-derive the answer from
   cached docs independently. Re-map every question to the real blueprint domain/task
   using `exam_facts()` — practice-exam domain headings are often wrong or coarser than
   the official study guide.

## 2. Ground every concept before drafting

Batch-fetch every doc a question will need **before** writing stems, exactly as
`/author` requires:

```
cache_check(url) → cache_fetch_batch([...])  # never fetch during drafting, only before it
```

If a source question hinges on something with no citable `docs.getdbt.com` page (a
third-party package macro like `dbt_expectations`, raw cron syntax, an undocumented
behavior), **do not invent a citation** — substitute a different, well-documented dbt
concept from the same domain/task instead. Note the substitution to the user if asked.

While reading the cached pages, independently verify the source's claimed answer. It is
common to find the pasted material is simply wrong (seen in practice: a unit-test
`given`/`expect` block reversed, a `delete+insert`-vs-`merge` claim contradicted by the
adapter docs). Grounding in the cache catches this before it propagates into the bank.

## 3. Draft in batches of 6–13 items per domain cluster

Map each source question to its real domain/task (per `exam_facts()`), group into
per-file batches by domain cluster (not strictly by source order), and write each item
per [docs/item-authoring-spec.md](../../../docs/item-authoring-spec.md) §2–§9. Stage
drafts as JSON arrays under `question-bank/authored/<descriptive-name>.json` (new
filenames — never edit the repo's pre-existing authored batch files).

Read [references/gate-fix-patterns.md](./references/gate-fix-patterns.md) before
drafting — it is a cheat-sheet of the specific `item_gate` fatal failures that recur with
this workflow and exactly how to pre-empt or fix each one. Following it cuts
gate-iteration rounds roughly in half.

## 4. Gate, fix, repeat — per batch file

```
item_gate(path="question-bank/authored/<file>.json")
```

Fix every **fatal failure** (apply [references/gate-fix-patterns.md](./references/gate-fix-patterns.md)),
re-run, repeat until every item in the file `ACCEPT`s. Do not move to the next batch with
unresolved fatals — fixes compound faster per-file than at the end.

## 5. Balance, ingest, verify

Once every batch file accepts:

```
balance_keys(write=True)          # rebalances across the WHOLE authored/ directory
authored_ingest(write=False)      # dry run — confirm admitted count == new item count,
                                   # rejected == 0, skipped_as_duplicates == prior bank size
authored_ingest(write=True)
bank_audit()                      # sanity check — failures here should be non-blocking
verify_seal(question_id, deep=True)   # spot-check 2-3 newly admitted ids
```

`balance_keys` touches every file in `question-bank/authored/`, including old ones
already ingested — that's expected and harmless (ingestion is stem-deduplicated), not a
sign something broke.

## 6. Commit and push

Stage **only** the files this task touched — `question-bank/authored/`,
`question-bank/index.json`, and `sources/cache/_index.json` — never a blanket `git add -A`,
since unrelated pre-existing working-tree changes (e.g. editor settings) must stay
untouched:

```bash
git add question-bank/authored/ question-bank/index.json sources/cache/_index.json
git commit -F <message-file>   # avoid inline -m with backticks/special chars; use -F
git push origin main
```

Write the commit message body to a temp file and commit with `-F`, not `-m`, when the
message contains backticks or other shell-sensitive characters.

## Forbidden

- ❌ Reproducing pasted third-party stems/options verbatim without confirmed rights
- ❌ Trusting the source's claimed answer or domain label without independent verification
- ❌ Inventing a citation for a concept that has no real `docs.getdbt.com` page
- ❌ Editing `question-bank/index.json` directly instead of going through the gate
- ❌ `git add -A` / staging unrelated working-tree files
- ❌ Moving to the next batch file while the current one still has fatal failures
