#!/usr/bin/env python3
"""Ingest gate-approved authored items from question-bank/authored/ into index.json.

Only items that currently PASS scripts/item_qa.py are admitted, so the gate is the
single admission criterion for the bank — there is no side door.

Idempotent: an item whose stem already exists is skipped unless --force.

Usage:
    python3 scripts/ingest_authored.py            # dry run
    python3 scripts/ingest_authored.py --write
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "mcp-server"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from study_agent_mcp import exam_config  # noqa: E402
from item_qa import CHECKS, qtype_of  # noqa: E402

INDEX_JSON = REPO_ROOT / "question-bank" / "index.json"
AUTHORED_DIR = REPO_ROOT / "question-bank" / "authored"

# Same shapes `ingest_seal` accepts, so a topic reference means the same thing whichever
# door an item comes through.
TOPIC_PLANNED_RE = re.compile(r"^(ae|arch)/\d{2}-[a-z][a-z0-9\-]+/[a-z][a-z0-9\-]+$")


def resolve_topic(t: str) -> str | None:
    """Normalize a topic reference to a repo-relative knowledge/ path, or None."""
    if t.startswith("knowledge/"):
        return t
    if TOPIC_PLANNED_RE.match(t):
        return f"knowledge/{t}.md"
    return None


def passes_gate(item: dict) -> tuple[bool, list[str]]:
    failures = [name for name, fn, fatal in CHECKS if fatal and not fn(item)[0]]
    return not failures, failures


def _load_index() -> dict:
    if not INDEX_JSON.exists():
        return {"questions": [], "total": 0}
    return json.loads(INDEX_JSON.read_text())


def next_counter(index: dict, prefix: str) -> int:
    pat = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    used = [int(m.group(1)) for q in index["questions"]
            if (m := pat.match(q.get("id", "")))]
    return max(used, default=0) + 1


def to_entry(item: dict, qid: str, src_file: Path) -> dict:
    domain = item["domain"]
    task = item.get("blueprint_task")
    entry = {
        "id": qid,
        "source": "authored",
        "source_url": None,
        "raw_path": src_file.relative_to(REPO_ROOT).as_posix(),
        "stem": item["stem"],
        "option_texts": item.get("option_texts") or {},
        "domain": domain,
        "track": exam_config.track_of(domain),
        "blueprint_task": task,
        "blueprint_task_title": exam_config.task_title(domain, task or ""),
        "qtype": qtype_of(item),
        "difficulty_estimate": item.get("difficulty_estimate"),
        "difficulty_source": "authored",
        "drill_answer": item["drill_answer"],
        "drill_answer_short": item.get("drill_answer_short")
        or f"{item['decision_hinge']}",
        "drill_rationale": item.get("drill_rationale") or item["decision_hinge"],
        "decision_hinge": item["decision_hinge"],
        "plausible_options": item.get("plausible_options", {}),
        "eliminated_by": item.get("eliminated_by", {}),
        "distractor_traps": item.get("distractor_traps", {}),
        "options_analysis": item.get("options_analysis", ""),
        "sources": item["sources"],
        "citation_status": "resolved",
        "topics": [p for t in item.get("topics", []) if (p := resolve_topic(t))],
        "verified": True,
        "status": "verified",
        "sealed_by": "authored_via_item_qa",
        "sealed_at": date.today().isoformat(),
        "seal_confidence": item.get("seal_confidence", 90),
        "needs_review": False,
    }
    # Format-specific payload travels with the item or the renderer breaks.
    for field in ("accepted_answers", "match_left", "match_right", "hotspot_targets",
                  "build_items", "code_block", "code_language"):
        if item.get(field):
            entry[field] = item[field]
    return entry


def run(write: bool = False, force: bool = False) -> dict:
    index = _load_index()
    existing_stems = {q.get("stem") for q in index["questions"] if q.get("stem")}
    counters: dict[str, int] = {}

    admitted, rejected, duplicates, malformed = [], [], [], []
    for path in sorted(AUTHORED_DIR.glob("*.json")):
        payload = json.loads(path.read_text())
        for item in (payload if isinstance(payload, list) else [payload]):
            domain = item.get("domain")
            if domain not in exam_config.VALID_DOMAINS:
                malformed.append({"id": item.get("id", "?"),
                                  "problem": f"domain {domain!r} is not in exam_config",
                                  "valid": sorted(exam_config.VALID_DOMAINS)})
                continue
            bad_topics = [t for t in item.get("topics", []) if resolve_topic(t) is None]
            if bad_topics:
                malformed.append({"id": item.get("id", "?"),
                                  "problem": f"unresolvable topic(s) {bad_topics}",
                                  "valid": "'knowledge/<track>/<NN>-<slug>/<note>.md' or "
                                           "'<track>/<NN>-<slug>/<note>'"})
                continue
            ok, failures = passes_gate(item)
            if not ok:
                rejected.append({"id": item.get("id", "?"), "failed_checks": failures})
                continue
            if item["stem"] in existing_stems and not force:
                duplicates.append(item.get("id", "?"))
                continue
            track = exam_config.track_of(domain)
            prefix = exam_config.id_prefix("authored", track)
            if prefix not in counters:
                counters[prefix] = next_counter(index, prefix)
            qid = f"{prefix}-{counters[prefix]:03d}"
            counters[prefix] += 1
            admitted.append(to_entry(item, qid, path))
            existing_stems.add(item["stem"])

    wrote = False
    if write and admitted:
        index["questions"].extend(admitted)
        index["total"] = len(index["questions"])
        index["last_updated_at"] = date.today().isoformat()
        INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
        INDEX_JSON.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
        wrote = True

    return {
        "admitted": [{"id": e["id"], "domain": e["domain"],
                      "blueprint_task": e["blueprint_task"], "qtype": e["qtype"],
                      "difficulty_estimate": e["difficulty_estimate"],
                      "stem": e["stem"][:80]} for e in admitted],
        "rejected": rejected,
        "malformed": malformed,
        "skipped_as_duplicates": duplicates,
        "written": wrote,
        "bank_total": index.get("total", len(index["questions"])),
        "dry_run": not write,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    result = run(write=args.write, force=args.force)
    print(f"admitted  {len(result['admitted'])}")
    for e in result["admitted"]:
        print(f"   {e['id']}  {e['domain']} task {e['blueprint_task']}  "
              f"{e['qtype']:<18}{e['stem'][:48]}...")
    if result["skipped_as_duplicates"]:
        print(f"skipped as duplicates: {result['skipped_as_duplicates']}")
    if result["malformed"]:
        print(f"\nMALFORMED ({len(result['malformed'])}):")
        for m in result["malformed"]:
            print(f"   {m['id']}: {m['problem']}")
    if result["rejected"]:
        print(f"\nREJECTED by the gate ({len(result['rejected'])}):")
        for r in result["rejected"]:
            print(f"   {r['id']}: {r['failed_checks']}")
    if result["written"]:
        print(f"\nwrote {len(result['admitted'])} entries -> {INDEX_JSON} "
              f"(total {result['bank_total']})")
    elif result["dry_run"]:
        print("\nDRY RUN — nothing saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
