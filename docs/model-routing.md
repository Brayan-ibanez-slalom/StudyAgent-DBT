# Model routing

> **Sonnet for drilling. Opus for sealing and authoring.**

A wrong seal is worse than a slow one: it cascades into every future drill of that
question and actively teaches something false. A slow drill turn just costs a few
seconds.

| Workflow | Model | Why |
|---|---|---|
| Ambient chat | Claude Sonnet 5 | Repo questions, navigation, quick lookups |
| `/drill` | Claude Sonnet 5 | High turn count, low work per turn — serve, grade, coach in 3 sentences. The seal already paid the reasoning cost. |
| `/verify` | Claude Sonnet 5 | Mechanical: does the cited page still support the claim? |
| `/seal` | Claude Opus 4.7 | One-time deep pass per question. Reason through every option independently, self-critique, cite. |
| `/author` | Claude Opus 4.7 | Writing a new item means inventing distractors that are wrong in *instructive* ways. This is the hardest generation task in the repo. |

Slash-command workflows pin the model in `.github/prompts/*.prompt.md` frontmatter.
Ambient chat inherits the picker — keep it on Sonnet.

---

## Why authoring gets the expensive tier here

The AIP-C01 predecessor could seed its bank from a 97-question ExamTopics dump, so most
Opus time went to *verifying* existing items.

This repo has no equivalent dump: third-party dbt certification material is thin and
frequently describes behaviour from older dbt versions. The bank is authored from
`docs.getdbt.com` instead. That moves the expensive, error-prone work from sealing to
authoring, so `/author` is pinned to Opus and the `item_gate` runs on every candidate.

---

## Cost discipline

- **Cache-first, always.** `cache_check` before `cache_fetch`. The 90-day freshness
  window is deliberate — dbt ships fast enough that older cached pages should be
  re-fetched rather than trusted.
- **Indexes before files.** `topic_search` (indexed) beats reading whole notes.
  `topic_read(topic_id, section=...)` beats a full-note read.
- **Do not re-derive sealed answers.** Serve them. That is what sealing bought.
- **Never `cache_fetch` during a drill turn.** Sealed content is sufficient. If it is
  not, the seal is the defect — fix it with `/seal`, not inline.
- **Batch doc fetches.** `cache_fetch_batch` on a list of URLs beats N sequential calls.
