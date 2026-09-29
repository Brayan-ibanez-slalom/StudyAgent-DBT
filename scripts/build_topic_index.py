#!/usr/bin/env python3
"""Build knowledge/_topics.json, knowledge/_tags.json, and knowledge/_concepts.json.

Agents should NOT open every topic note to find where a concept is covered. Instead:

  1. knowledge/_tags.json     — reverse index: keyword -> [topic ids]
  2. knowledge/_topics.json   — per topic: path, title, domain, keywords, sources, related
  3. knowledge/_concepts.json — dbt concept/command name -> canonical note path
  4. Only then open the specific .md file(s) that matter

Domain directories are derived from mcp-server/study_agent_mcp/exam_config.py, so adding
a domain there is the only edit needed to index a new folder.

Run:  python3 scripts/build_topic_index.py
"""
from __future__ import annotations

import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcp-server"))

from study_agent_mcp import exam_config  # noqa: E402

KDIR = ROOT / "knowledge"
OUT_TOPICS = KDIR / "_topics.json"
OUT_TAGS = KDIR / "_tags.json"
OUT_CONCEPTS = KDIR / "_concepts.json"

# Curated tags. A note earns a tag by containing the phrase; H2/H3 headings are also
# harvested so notes can introduce their own vocabulary without editing this list.
KEYWORD_TAGS = [
    # core objects
    "model", "source", "seed", "snapshot", "exposure", "analysis", "macro",
    "package", "test", "unit test", "singular test", "generic test",
    "contract", "model version", "group", "access",
    # materializations
    "materialization", "view", "table", "ephemeral", "incremental",
    "materialized view", "is_incremental", "full refresh", "microbatch",
    "incremental_strategy", "on_schema_change", "merge", "insert_overwrite",
    "delete+insert", "append",
    # jinja
    "jinja", "macro", "dispatch", "run_query", "adapter", "whitespace control",
    "generate_schema_name", "generate_alias_name", "custom materialization",
    # selection / state
    "node selection", "state:modified", "defer", "manifest", "run_results",
    "selector", "graph operator", "dbt retry", "dbt clone", "slim ci",
    # project / config
    "dbt_project.yml", "profiles.yml", "target", "vars", "hook", "pre-hook",
    "post-hook", "on-run-start", "on-run-end", "grants", "persist_docs",
    # platform / architect
    "environment", "deploy job", "ci job", "continuous integration", "threads",
    "service token", "permission set", "rbac", "sso", "webhook", "notification",
    "discovery api", "dbt catalog", "dbt explorer", "dbt mesh", "cross-project",
    "dependencies.yml", "project dependency", "branching strategy", "ip restriction",
    # cross-cutting
    "trap", "terminology", "troubleshooting", "error",
]

AUTHORITATIVE_HOSTS = exam_config.AUTHORITATIVE_HOSTS

# A note declares its canonical concepts with a `**Concepts:**` header line, e.g.
#   **Concepts:** incremental, is_incremental, on_schema_change
CONCEPTS_RE = re.compile(r"^\*\*Concepts:\*\*\s*(.+)$", re.M)


def extract_meta(text: str):
    title = None
    verified = None
    sources: list[dict] = []

    for line in text.splitlines()[:40]:
        if line.startswith("# ") and title is None:
            title = line[2:].strip()
        if m := re.match(r"\*\*Verified:\*\*\s*(\S+)", line):
            verified = m.group(1)

    for m in re.finditer(r"\[([^\]]+)\]\((https?://[^\)]+)\)", text):
        url = m.group(2)
        if any(h in url for h in AUTHORITATIVE_HOSTS) and \
                not any(s["url"] == url for s in sources):
            sources.append({"title": m.group(1), "url": url})

    related = re.findall(r"`([a-z0-9\-]+)\.md`", text)
    related += re.findall(r"\]\(\./([a-z0-9\-]+)\.md\)", text)

    concepts: list[str] = []
    for m in CONCEPTS_RE.finditer(text):
        concepts += [c.strip() for c in m.group(1).split(",") if c.strip()]

    return title, verified, sources, sorted(set(related)), concepts


def extract_keywords(text: str) -> list[str]:
    low = text.lower()
    hits = [k for k in KEYWORD_TAGS if k.lower() in low]
    for line in text.splitlines():
        if m := re.match(r"#{2,3}\s+(.+)", line):
            h = m.group(1).strip().lower()
            if 3 <= len(h) <= 60:
                hits.append(h)
    return sorted(set(hits))


def main() -> int:
    topics: list[dict] = []
    concepts: dict[str, str] = {}
    missing_dirs: list[str] = []

    for domain_id, meta in exam_config.DOMAINS.items():
        domain_dir = KDIR / meta["track"] / meta["dir"]
        if not domain_dir.is_dir():
            missing_dirs.append(str(domain_dir.relative_to(ROOT)))
            continue
        for md in sorted(domain_dir.glob("*.md")):
            if md.name == "README.md":
                continue
            text = md.read_text()
            title, verified, sources, related, note_concepts = extract_meta(text)
            topic_id = f"{meta['track']}/{meta['dir']}/{md.stem}"
            rel_path = str(md.relative_to(ROOT))

            related_ids = []
            for r in related:
                for other_id, other in exam_config.DOMAINS.items():
                    cand = KDIR / other["track"] / other["dir"] / f"{r}.md"
                    if cand.exists():
                        related_ids.append(f"{other['track']}/{other['dir']}/{r}")
                        break

            for c in note_concepts:
                concepts.setdefault(c, rel_path)

            topics.append({
                "id": topic_id,
                "path": rel_path,
                "title": title or md.stem,
                "track": meta["track"],
                "domain": domain_id,
                "domain_title": meta["title"],
                "domain_weight": meta["weight"],
                "verified": verified,
                "keywords": extract_keywords(text),
                "concepts": note_concepts,
                "sources": sources,
                "related": sorted(set(related_ids)),
            })

    tag_map: dict[str, list[str]] = {}
    for t in topics:
        for kw in t["keywords"]:
            tag_map.setdefault(kw, []).append(t["id"])
    tag_map = {k: sorted(set(v)) for k, v in sorted(tag_map.items())}

    today = datetime.date.today().isoformat()
    KDIR.mkdir(parents=True, exist_ok=True)
    OUT_TOPICS.write_text(json.dumps({
        "version": 1, "generated_at": today,
        "description": "Machine-readable index of knowledge/ topic notes. "
                       "Regenerate with scripts/build_topic_index.py.",
        "weight_note": "dbt Labs does not publish section weights; domain_weight is "
                       "null by design.",
        "topic_count": len(topics), "topics": topics,
    }, indent=2) + "\n")

    OUT_TAGS.write_text(json.dumps({
        "version": 1, "generated_at": today,
        "description": "Reverse index: keyword/tag -> topic IDs. Look here before "
                       "reading any note file.",
        "tag_count": len(tag_map), "tags": tag_map,
    }, indent=2) + "\n")

    OUT_CONCEPTS.write_text(json.dumps({
        "version": 1, "generated_at": today,
        "description": "dbt concept/command/config name -> canonical note path. "
                       "Declared by a '**Concepts:**' line in each note.",
        "concept_count": len(concepts),
        "concepts": dict(sorted(concepts.items())),
    }, indent=2) + "\n")

    print(f"topics: {len(topics)}   tags: {len(tag_map)}   concepts: {len(concepts)}")
    if missing_dirs:
        print(f"note: {len(missing_dirs)} domain folder(s) not created yet:")
        for d in missing_dirs:
            print(f"   {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
