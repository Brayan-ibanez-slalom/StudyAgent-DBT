#!/usr/bin/env python3
"""Spread the correct answer across option letters in the authored drafts.

A learner who notices the key is usually C scores without reading. Only letter-option
formats can be rebalanced; fill-in-the-blank, matching, hotspot, and build-list have no
letter to move and are left alone.

Every letter-keyed field moves with the key (option_texts, plausible_options,
eliminated_by, distractor_traps), so evidence stays attached to the option it was
written for.

Usage:
    python3 scripts/balance_keys.py            # dry run
    python3 scripts/balance_keys.py --write
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from item_qa import LETTER_FORMATS, key_letters, qtype_of  # noqa: E402

AUTHORED_DIR = REPO_ROOT / "question-bank" / "authored"

LETTER_KEYED_FIELDS = ("option_texts", "plausible_options", "eliminated_by",
                       "distractor_traps", "options_analysis")


def _swap_letters(item: dict, a: str, b: str) -> None:
    """Move every letter-keyed field's entry for `a` to `b` and vice versa.

    Rebuilt rather than swapped in place: a field may hold only one of the two letters
    (distractor_traps never has an entry for the key), and an in-place swap has to
    create a None and delete it again to handle that.
    """
    for field in LETTER_KEYED_FIELDS:
        block = item.get(field)
        if not isinstance(block, dict) or not (a in block or b in block):
            continue
        rebuilt = {}
        for letter, value in block.items():
            rebuilt[b if letter == a else a if letter == b else letter] = value
        item[field] = {k: rebuilt[k] for k in sorted(rebuilt)}
    item["drill_answer"] = ",".join(
        sorted({b if x == a else a if x == b else x for x in key_letters(item)}))


def run(write: bool = False) -> dict:
    files = sorted(AUTHORED_DIR.glob("*.json"))
    items: list[tuple[Path, int, dict]] = []
    # Recorded at load time: deciding list-vs-object by re-reading the file after
    # mutating it in memory would be reading a shape we are about to overwrite.
    is_list: dict[Path, bool] = {}
    for path in files:
        payload = json.loads(path.read_text())
        is_list[path] = isinstance(payload, list)
        rows = payload if is_list[path] else [payload]
        for i, item in enumerate(rows):
            items.append((path, i, item))

    singles = [(p, i, it) for p, i, it in items
               if qtype_of(it) in LETTER_FORMATS and len(key_letters(it)) == 1]
    before = Counter(next(iter(key_letters(it))) for _, _, it in singles)
    if not singles:
        return {"rebalanced": [], "before": {}, "after": {}, "dry_run": not write,
                "note": "no single-answer letter-format drafts to balance"}

    letters = sorted({L for _, _, it in singles for L in (it.get("option_texts") or {})})
    target = len(singles) / max(1, len(letters))

    moves = []
    counts = Counter(before)
    for path, idx, item in singles:
        current = next(iter(key_letters(item)))
        if counts[current] <= target:
            continue
        options = [L for L in (item.get("option_texts") or {}) if L != current]
        if not options:
            continue
        dest = min(options, key=lambda L: counts[L])
        if counts[dest] + 1 > target + 1:
            continue
        _swap_letters(item, current, dest)
        counts[current] -= 1
        counts[dest] += 1
        moves.append({"file": path.name, "index": idx,
                      "id": item.get("id", "?"), "from": current, "to": dest})

    if write and moves:
        by_file: dict[Path, list] = {}
        for path, _, item in items:
            by_file.setdefault(path, []).append(item)
        for path in {AUTHORED_DIR / m["file"] for m in moves}:
            rows = by_file[path]
            payload = rows if is_list[path] else rows[0]
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    return {"files_scanned": len(files), "single_answer_items": len(singles),
            "before": dict(sorted(before.items())), "after": dict(sorted(counts.items())),
            "target_per_letter": round(target, 1),
            "rebalanced": moves, "written": bool(write and moves), "dry_run": not write}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    result = run(write=args.write)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
