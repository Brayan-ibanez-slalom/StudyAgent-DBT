#!/usr/bin/env python3
"""Create the directory skeleton and progress artifacts from exam_config.

Idempotent and non-destructive: existing files are left alone unless --force. Run this
after adding or renaming a domain in exam_config.py.

`--force` rewrites the regenerable skeleton (domain READMEs, scorecard, queues). It
deliberately CANNOT touch `question-bank/index.json` or `sources/cache/_index.json` —
those accumulate real work and are marked protected.

Creates:
  knowledge/<track>/<NN>-<slug>/README.md   for every configured domain
  progress/scorecard.md                     one row per domain
  progress/missed-questions.md              empty queue table
  progress/asked-log.json                   {}
  progress/needs-review.md                  low-confidence seal queue
  question-bank/index.json                  empty bank
  sources/cache/_index.json                 empty cache index

Usage:
    python3 scripts/bootstrap_repo.py
    python3 scripts/bootstrap_repo.py --force   # rewrite scorecard rows too
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "mcp-server"))

from study_agent_mcp import exam_config  # noqa: E402


def _write(path: Path, content: str, force: bool, created: list, skipped: list,
           protected: bool = False) -> None:
    """Create `path` if missing. `force` rewrites it unless it is protected.

    Protected files accumulate real data (the question bank, the doc-cache index).
    Losing them to a --force meant to reset a scorecard would be a silent, expensive
    mistake, so --force deliberately cannot reach them.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and (protected or not force):
        skipped.append(str(path.relative_to(REPO_ROOT)))
        return
    path.write_text(content)
    created.append(str(path.relative_to(REPO_ROOT)))


def domain_readme(domain_id: str, meta: dict) -> str:
    facts = exam_config.EXAM_FACTS[meta["track"]]
    task_rows = "\n".join(
        f"| {tid} | {title} |" for tid, (title, _) in sorted(meta["tasks"].items()))
    return f"""# {domain_id} — {meta['title']}

**Exam:** {facts['name']}
**Weight:** not published by dbt Labs. Every question scores one point.
**Provenance of this domain:** {meta['provenance']}

## Tasks

| Task | Title |
|---|---|
{task_rows}

## Notes in this folder

One `.md` per concept, kebab-case. Every note must carry:

```
# <Title>

**Domain:** {domain_id} — Task {sorted(meta['tasks'])[0]}
**Verified:** YYYY-MM-DD
**Concepts:** comma, separated, lookup, keys
```

Then rebuild the index: `python3 scripts/build_topic_index.py`

See [knowledge/README.md](../../README.md) for the full note contract.
"""


SCORECARD_HEADER = """# Scorecard

Accuracy per domain, updated automatically by `drill_grade_reasoned`.

There is no weighted column. dbt Labs does not publish section weights and states that
all questions are weighted equally, so a weighted total would be invented arithmetic.
Use the raw accuracy and the attempt count.

Reset with `session_clear(scope="scorecard", confirm=true)`.

"""


def scorecard(track: str) -> str:
    facts = exam_config.EXAM_FACTS[track]
    rows = "\n".join(
        f"| {d} | {meta['title']} | 0 | 0 | — |"
        for d, meta in sorted(exam_config.domains_for(track).items()))
    return (f"## {facts['name']}\n\n"
            "| Domain | Title | Attempted | Correct | Accuracy |\n"
            "|---|---|---|---|---|\n"
            f"{rows}\n\n")


MISSED_MD = """# Missed questions queue

Appended automatically on every wrong answer. Drill these again with
`drill_pick(mode="missed")`.

## Current queue

| Question ID | Domain | Date | Detail | Status |
|---|---|---|---|---|
"""


def needs_review_md() -> str:
    return f"""# Needs review

Seals the Sealer was not confident about. A question lands here when
`seal_confidence < {exam_config.SEAL_CONFIDENCE_FLOOR}`, or when independent reasoning
disagreed with a source's claimed answer.

Resolve each one by re-reading docs.getdbt.com, then either re-seal with a higher
confidence or call `ingest_dispute`.

| Question ID | Domain | Confidence | Why it is here | Resolution |
|---|---|---|---|---|
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="rewrite the regenerable skeleton (READMEs, scorecard, queues). "
                         "Never touches the question bank or the cache index.")
    args = ap.parse_args()

    created: list[str] = []
    skipped: list[str] = []

    for domain_id, meta in exam_config.DOMAINS.items():
        path = REPO_ROOT / "knowledge" / meta["track"] / meta["dir"] / "README.md"
        _write(path, domain_readme(domain_id, meta), args.force, created, skipped)

    scorecard_body = SCORECARD_HEADER + "".join(
        scorecard(t) for t in exam_config.VALID_TRACKS)
    _write(REPO_ROOT / "progress" / "scorecard.md", scorecard_body,
           args.force, created, skipped)
    _write(REPO_ROOT / "progress" / "missed-questions.md", MISSED_MD,
           args.force, created, skipped)
    _write(REPO_ROOT / "progress" / "needs-review.md", needs_review_md(),
           args.force, created, skipped)
    _write(REPO_ROOT / "progress" / "asked-log.json", "{}\n", args.force, created, skipped)

    _write(REPO_ROOT / "question-bank" / "index.json",
           json.dumps({"questions": [], "total": 0,
                       "last_updated_at": date.today().isoformat()}, indent=2) + "\n",
           args.force, created, skipped, protected=True)
    _write(REPO_ROOT / "sources" / "cache" / "_index.json",
           json.dumps({"version": 1, "count": 0,
                       "updated_at": date.today().isoformat(), "entries": []},
                      indent=2) + "\n",
           args.force, created, skipped, protected=True)

    for keep in ("question-bank/authored/.gitkeep", "question-bank/raw/.gitkeep",
                 "progress/sessions/.gitkeep", "sources/cache/_raw/.gitkeep"):
        _write(REPO_ROOT / keep, "", args.force, created, skipped)

    print(f"created {len(created)} file(s)")
    for c in created:
        print(f"   + {c}")
    if skipped:
        print(f"\nleft alone {len(skipped)} existing file(s) (use --force to rewrite)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
