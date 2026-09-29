"""Bridge from the MCP tool surface to the authoring pipeline in scripts/.

The quality gate must be reachable from the same interface as everything else, or it
stops being the single admission standard. Imports are lazy and reloaded on every call
so a broken script can never stop the server starting, and edits to scripts/ take
effect without restarting a long-lived server.
"""
from __future__ import annotations

import importlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from .repo import AUTHORED_DIR, REPO_ROOT, load_index, save_index

SCRIPTS = REPO_ROOT / "scripts"


def _load(module: str):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    return importlib.reload(__import__(module))


def _resolve(path: str) -> Path:
    for candidate in (Path(path), REPO_ROOT / path, AUTHORED_DIR / path):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"no such candidates file: {path} (looked in repo root and {AUTHORED_DIR})")


def gate(path: Optional[str] = None, item: Optional[dict] = None) -> dict:
    item_qa = _load("item_qa")
    if item is not None:
        items, source = [item], "inline item"
    else:
        if not path:
            return {"error": "provide either `path` to a candidates file or an inline `item`"}
        resolved = _resolve(path)
        data = json.loads(resolved.read_text())
        items = data if isinstance(data, list) else [data]
        source = resolved.relative_to(REPO_ROOT).as_posix()
    report = item_qa.gate_report(items)
    report["source"] = source
    return report


def bank_audit() -> dict:
    return _load("item_qa").audit_report()


def authored_ingest(write: bool = False, force: bool = False) -> dict:
    return _load("ingest_authored").run(write=write, force=force)


def coverage(track: Optional[str] = None, domain: Optional[str] = None) -> dict:
    report = _load("blueprint_coverage").build_report(track=track)
    if domain:
        report["domains"] = {d: v for d, v in report["domains"].items() if d == domain}
    thin = [{"domain": d, **row}
            for d, data in report["domains"].items()
            for row in data["tasks"] if row["gap"] >= 2]
    report["author_here"] = sorted(thin, key=lambda r: -r["gap"])
    return report


def balance_keys(write: bool = False) -> dict:
    return _load("balance_keys").run(write=write)


def difficulty_observed(write: bool = False) -> dict:
    return _load("observed_difficulty").run(write=write)


# Each entry: name -> (item_qa check, what the defect lets a candidate do without
# knowing any dbt fact).
DEFECTS = {
    "long_key": ("check_key_not_longest", "answerable by picking the longest option"),
    "lexical_giveaway": ("check_no_lexical_giveaway",
                         "key echoes stem wording more than any distractor"),
    "odd_one_out": ("check_key_not_odd_one_out", "key is findable by its opening verb"),
    "key_longest": ("check_key_not_the_longest_option",
                    "key ranks as the single longest option"),
    "unverifiable": ("check_source_verifiable",
                     "answer cannot be re-checked against a cached dbt docs page"),
}


def _provenance_of(qid: str) -> str:
    for marker, name in (("-AU-", "authored"), ("-OF-", "official"),
                         ("-CO-", "community"), ("-PA-", "practice")):
        if marker in qid:
            return name
    return "unknown"


def _is_servable(q: dict) -> bool:
    """Sealed, not retired, not disputed — what `drill_pick` can actually hand out."""
    return (q.get("status") not in ("unsealed", "disputed")
            and not q.get("retired")
            and q.get("verified") is not False)


def defect_scan(defect: Optional[str] = None, provenance: Optional[str] = None,
                include_retired: bool = False, limit: int = 25) -> dict:
    """Rank servable bank items by authoring defect, worst first — the rewrite queue."""
    item_qa = _load("item_qa")
    if defect and defect not in DEFECTS:
        return {"error": f"unknown defect {defect!r}", "known": sorted(DEFECTS)}
    wanted = [defect] if defect else list(DEFECTS)

    items = [q for q in load_index().get("questions", [])
             if _is_servable(q) or (include_retired and q.get("retired"))]
    if provenance:
        items = [q for q in items if _provenance_of(q["id"]) == provenance]

    rows, totals = [], {name: {} for name in wanted}
    for q in items:
        hits = []
        for name in wanted:
            ok, detail = getattr(item_qa, DEFECTS[name][0])(q)
            if ok:
                continue
            hits.append({"defect": name, "detail": detail})
            bucket = totals[name]
            key = _provenance_of(q["id"])
            bucket[key] = bucket.get(key, 0) + 1
        if hits:
            rows.append({"id": q["id"], "provenance": _provenance_of(q["id"]),
                         "domain": q.get("domain"),
                         "blueprint_task": q.get("blueprint_task"),
                         "qtype": q.get("qtype"),
                         "difficulty_estimate": q.get("difficulty_estimate"),
                         "key_length_margin": _key_margin(q),
                         "defects": hits})
    rows.sort(key=lambda r: (-len(r["defects"]), -(r["key_length_margin"] or 0)))
    return {"scanned": len(items), "defective": len(rows),
            "by_defect_and_provenance": totals,
            "worst_first": rows[:limit],
            "truncated": max(0, len(rows) - limit)}


def _key_margin(q: dict) -> Optional[int]:
    opts = q.get("option_texts") or {}
    answer = [a.strip() for a in str(q.get("drill_answer") or "").split(",") if a.strip()]
    if not opts or not answer or any(a not in opts for a in answer):
        return None
    distractors = [t for letter, t in opts.items() if letter not in answer]
    if not distractors:
        return None
    return (max(len(opts[a].split()) for a in answer)
            - max(len(t.split()) for t in distractors))


def retire_superseded(mapping: dict[str, str], reason: str, write: bool = False) -> dict:
    """Mark originals retired and point each at the item that replaced it.

    Refuses to retire anything whose replacement is missing, unsealed, or itself
    retired, so a rewrite can never leave the bank with a dangling pointer.
    """
    data = load_index()
    by_id = {q["id"]: q for q in data.get("questions", [])}
    planned, problems = [], []
    for original, replacement in mapping.items():
        if original not in by_id:
            problems.append(f"{original}: not in the bank")
        elif replacement not in by_id:
            problems.append(f"{original}: replacement {replacement} is not in the bank")
        elif by_id[replacement].get("retired"):
            problems.append(f"{original}: replacement {replacement} is itself retired")
        elif by_id[replacement].get("status") == "unsealed":
            problems.append(f"{original}: replacement {replacement} is not sealed")
        else:
            planned.append({"retire": original, "superseded_by": replacement,
                            "already_retired": bool(by_id[original].get("retired"))})
    if problems:
        return {"error": "refusing to write", "problems": problems, "written": False}
    if write:
        for row in planned:
            entry = by_id[row["retire"]]
            entry.update({"retired": True, "retired_at": date.today().isoformat(),
                          "retired_reason": reason,
                          "superseded_by": row["superseded_by"]})
        save_index(data)
    questions = data.get("questions", [])
    return {"planned": planned, "written": write, "dry_run": not write,
            "bank_total": len(questions),
            "retired_total": sum(1 for q in questions if q.get("retired")),
            "servable": sum(1 for q in questions if _is_servable(q))}
