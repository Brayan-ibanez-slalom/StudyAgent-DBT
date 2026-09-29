#!/usr/bin/env python3
"""Map question-bank items to blueprint tasks and report coverage gaps.

dbt Labs does not publish section weights, so the target-per-task is a flat number
rather than a share of an exam. Treat the output as an authoring queue, not a
certified mapping.

Usage:
    python3 scripts/blueprint_coverage.py [--json] [--track ae] [--domain ae-02]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "mcp-server"))

from study_agent_mcp import exam_config  # noqa: E402

INDEX_JSON = REPO_ROOT / "question-bank" / "index.json"

# How many sealed items each task should carry before it stops being a gap. Flat,
# because every dbt exam question is worth the same point.
TARGET_PER_TASK = 6

# Formats that must appear somewhere in a track's bank, or drilling trains the wrong
# muscle: the real exam is not all multiple choice.
FORMAT_FLOOR = {"fill_in_blank": 3, "build_list": 2, "matching": 2, "domc": 2}


def _servable(q: dict) -> bool:
    return (q.get("verified") and not q.get("retired")
            and q.get("status") != "disputed")


def _load_items() -> list[dict]:
    if not INDEX_JSON.exists():
        return []
    return json.loads(INDEX_JSON.read_text()).get("questions", [])


def _task_of(q: dict) -> str | None:
    """Stored task if present, else a keyword guess within the question's own domain."""
    if q.get("blueprint_task"):
        return q["blueprint_task"]
    domain = q.get("domain")
    if not domain:
        return None
    blob = " ".join([str(q.get("stem") or "")]
                    + [str(v) for v in (q.get("option_texts") or {}).values()])
    task, hits = exam_config.classify_task(blob, domain)
    return task if hits else None


def build_report(track: str | None = None) -> dict:
    items = [q for q in _load_items() if _servable(q)]
    if track:
        items = [q for q in items
                 if exam_config.track_of(q.get("domain")) == track]

    domains: dict[str, dict] = {}
    scope = exam_config.domains_for(track) if track else exam_config.DOMAINS

    for domain_id, meta in scope.items():
        in_domain = [q for q in items if q.get("domain") == domain_id]
        per_task: Counter = Counter(t for q in in_domain if (t := _task_of(q)))
        rows = []
        for task_id, (title, _) in sorted(meta["tasks"].items()):
            have = per_task.get(task_id, 0)
            rows.append({"task": task_id, "title": title, "have": have,
                         "target": TARGET_PER_TASK,
                         "gap": max(0, TARGET_PER_TASK - have)})
        domains[domain_id] = {
            "title": meta["title"],
            "track": meta["track"],
            "weight": meta["weight"],
            "subtopic_share_pct": exam_config.subtopic_share(meta["track"])[domain_id],
            "items": len(in_domain),
            "unclassified": sum(1 for q in in_domain if not _task_of(q)),
            "tasks": rows,
        }

    formats: Counter = Counter(
        q.get("qtype") or ("multiple_response"
                           if "," in str(q.get("drill_answer") or "")
                           else "multiple_choice")
        for q in items)
    format_gaps = {fmt: floor - formats.get(fmt, 0)
                   for fmt, floor in FORMAT_FLOOR.items()
                   if formats.get(fmt, 0) < floor}

    return {
        "track_filter": track,
        "target_per_task": TARGET_PER_TASK,
        "weight_note": (
            "dbt Labs publishes the topic outline and the 65-question length, but NOT "
            "per-topic weighting. Targets are flat per sub-topic, so a topic with more "
            "sub-topics naturally earns a larger share — the same proxy reported by "
            "exam_facts() as subtopic_share_pct."),
        "servable_items": len(items),
        "domains": domains,
        "by_format": dict(formats),
        "format_gaps": format_gaps,
        "total_gap": sum(row["gap"] for d in domains.values() for row in d["tasks"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--track", choices=list(exam_config.VALID_TRACKS))
    ap.add_argument("--domain")
    args = ap.parse_args()

    report = build_report(track=args.track)
    if args.domain:
        report["domains"] = {d: v for d, v in report["domains"].items() if d == args.domain}

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"servable items: {report['servable_items']}   "
          f"target per task: {report['target_per_task']}\n")
    for domain_id, data in report["domains"].items():
        print(f"{domain_id}  {data['title']}   ({data['items']} items, "
              f"{data['unclassified']} unclassified)")
        for row in data["tasks"]:
            flag = "  <-- author here" if row["gap"] >= 2 else ""
            print(f"    {row['task']:<5}{row['title'][:52]:<54}"
                  f"{row['have']:>3}/{row['target']}{flag}")
        print()
    print(f"by format: {report['by_format']}")
    if report["format_gaps"]:
        print(f"format gaps (bank is too multiple-choice-heavy): {report['format_gaps']}")
    print(f"total gap: {report['total_gap']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
