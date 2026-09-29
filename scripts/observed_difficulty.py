#!/usr/bin/env python3
"""Score difficulty from real attempt results instead of the structural proxy.

`difficulty_estimate` starts life as an authoring guess. Once a question has actually
been drilled, the attempt record is better evidence. This script rewrites
`difficulty_estimate` from observed accuracy and sets `difficulty_source: "observed"`.

Deliberately starved: a question needs MIN_ATTEMPTS results before its outcome counts
as a measurement rather than a coin flip.

Usage:
    python3 scripts/observed_difficulty.py            # dry run
    python3 scripts/observed_difficulty.py --write
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_JSON = REPO_ROOT / "question-bank" / "index.json"
ATTEMPTS = REPO_ROOT / "progress" / "attempts.jsonl"

MIN_ATTEMPTS = 2

# Accuracy band -> difficulty. Lower accuracy means a harder item.
BANDS = [(0.90, "L1"), (0.75, "L2"), (0.55, "L3"), (0.35, "L4"), (0.0, "L5")]


def _band(accuracy: float) -> str:
    for floor, label in BANDS:
        if accuracy >= floor:
            return label
    return "L5"


def run(write: bool = False) -> dict:
    if not ATTEMPTS.exists():
        return {"error": "no progress/attempts.jsonl yet", "updated": [], "dry_run": True}
    if not INDEX_JSON.exists():
        return {"error": "no question-bank/index.json yet", "updated": [], "dry_run": True}

    tally: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for line in ATTEMPTS.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        qid = rec.get("qid")
        if not qid:
            continue
        tally[qid][0] += 1
        tally[qid][1] += 1 if rec.get("correct") else 0

    index = json.loads(INDEX_JSON.read_text())
    updated, skipped_thin, malformed = [], 0, []
    for q in index.get("questions", []):
        qid = q.get("id")
        if not qid:
            malformed.append(str(q)[:80])
            continue
        attempts, correct = tally.get(qid, [0, 0])
        if attempts < MIN_ATTEMPTS:
            if attempts:
                skipped_thin += 1
            continue
        accuracy = correct / attempts
        new = _band(accuracy)
        old = q.get("difficulty_estimate")
        if new == old and q.get("difficulty_source") == "observed":
            continue
        q["difficulty_estimate"] = new
        q["difficulty_source"] = "observed"
        q["difficulty_reasons"] = [
            f"{correct}/{attempts} correct ({accuracy:.0%}) across recorded attempts"]
        updated.append({"id": qid, "from": old, "to": new,
                        "attempts": attempts, "accuracy_pct": round(100 * accuracy)})

    if write and updated:
        INDEX_JSON.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")

    return {"questions_with_attempts": len(tally),
            "skipped_below_min_attempts": skipped_thin,
            "malformed_records_skipped": malformed,
            "min_attempts": MIN_ATTEMPTS,
            "updated": updated, "written": bool(write and updated), "dry_run": not write}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    print(json.dumps(run(write=args.write), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
