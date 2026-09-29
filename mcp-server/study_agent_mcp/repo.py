"""Repo paths, JSON loaders, and file-mutation helpers.

The MCP server never touches paths directly — everything routes through here, and
everything exam-specific routes through `exam_config`. There are no domain names,
weights, or ID prefixes in this file.

Schema notes
------------
  - `question-bank/index.json` has top-level key `"questions"` (a list).
  - A question's `domain` is a global id from exam_config.DOMAINS ('ae-02', 'arch-03').
  - `blueprint_task` is the within-domain task id ('2.2'); combine with `domain`
    for a globally unique task key.
  - Status vocabulary: unsealed | verified | concept-only | disputed.
  - `qtype` is one of exam_config.QUESTION_TYPES; grading lives in grading.py.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import exam_config, grading

REPO_ROOT = Path(__file__).resolve().parents[2]

QUESTION_BANK = REPO_ROOT / "question-bank"
INDEX_JSON = QUESTION_BANK / "index.json"
AUTHORED_DIR = QUESTION_BANK / "authored"
RAW_DIR = QUESTION_BANK / "raw"

KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
TAGS_JSON = KNOWLEDGE_DIR / "_tags.json"
TOPICS_JSON = KNOWLEDGE_DIR / "_topics.json"
CONCEPTS_JSON = KNOWLEDGE_DIR / "_concepts.json"

CACHE_ROOT = REPO_ROOT / "sources" / "cache"
CACHE_INDEX = CACHE_ROOT / "_index.json"
CACHE_RAW = CACHE_ROOT / "_raw"

PROGRESS_DIR = REPO_ROOT / "progress"
MISSED_MD = PROGRESS_DIR / "missed-questions.md"
SCORECARD_MD = PROGRESS_DIR / "scorecard.md"
ASKED_LOG = PROGRESS_DIR / "asked-log.json"
ATTEMPTS_JSONL = PROGRESS_DIR / "attempts.jsonl"

DOCS_DIR = REPO_ROOT / "docs"

VALID_DOMAINS = exam_config.VALID_DOMAINS
VALID_STATUS = exam_config.VALID_STATUS
CACHE_STALE_DAYS = 90


# ---------- dates ----------

def today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def days_since(iso: str) -> int:
    d = datetime.strptime(iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - d).days


# ---------- json envelopes ----------

def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text() or "null") or default
    except json.JSONDecodeError:
        return default


def load_index() -> dict:
    data = _read_json(INDEX_JSON, {"questions": [], "total": 0})
    data.setdefault("questions", [])
    return data


def save_index(data: dict) -> None:
    data["total"] = len(data.get("questions", []))
    data["last_updated_at"] = today_iso()
    INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
    INDEX_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_tags() -> dict:
    raw = _read_json(TAGS_JSON, {})
    return raw.get("tags", raw) if isinstance(raw, dict) else {}


def load_topics() -> dict:
    raw = _read_json(TOPICS_JSON, {})
    items = raw.get("topics", raw) if isinstance(raw, dict) else raw
    if isinstance(items, list):
        return {t["id"]: t for t in items}
    return items or {}


def load_concepts() -> dict:
    """dbt concept/command name -> canonical note path (the Tier-3 index)."""
    raw = _read_json(CONCEPTS_JSON, {})
    return raw.get("concepts", raw) if isinstance(raw, dict) else {}


def load_cache_index() -> dict:
    raw = _read_json(CACHE_INDEX, {})
    if not isinstance(raw, dict) or "entries" not in raw:
        return {"version": 1, "count": 0, "entries": []}
    return raw


def save_cache_index(data: dict) -> None:
    data.setdefault("version", 1)
    data["count"] = len(data.get("entries", []))
    data["updated_at"] = today_iso()
    CACHE_INDEX.parent.mkdir(parents=True, exist_ok=True)
    CACHE_INDEX.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# ---------- asked-log / attempts ----------

def load_asked_log() -> dict:
    raw = _read_json(ASKED_LOG, {})
    return raw if isinstance(raw, dict) else {}


def save_asked_log(data: dict) -> None:
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    ASKED_LOG.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def load_attempts() -> list[dict]:
    if not ATTEMPTS_JSONL.exists():
        return []
    out = []
    for line in ATTEMPTS_JSONL.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def load_attempted_ids() -> set[str]:
    return {r["qid"] for r in load_attempts() if isinstance(r.get("qid"), str)}


def append_attempt(record: dict) -> None:
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    with ATTEMPTS_JSONL.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_asked(qid: str, correct: bool) -> None:
    log = load_asked_log()
    entry = log.get(qid, {"count": 0, "correct": 0, "last_asked": None, "last_correct": None})
    entry["count"] += 1
    entry["correct"] += 1 if correct else 0
    entry["last_asked"] = today_iso()
    entry["last_correct"] = bool(correct)
    log[qid] = entry
    save_asked_log(log)


# ---------- question lookup ----------

def find_question(qid: str) -> Optional[dict]:
    for q in load_index()["questions"]:
        if q["id"] == qid:
            return q
    return None


def _sort_key(q: dict) -> tuple:
    return (q.get("domain") or "zz", q.get("blueprint_task") or "9.9", q.get("id") or "")


def upsert_question(entry: dict) -> None:
    idx = load_index()
    idx["questions"] = [q for q in idx["questions"] if q["id"] != entry["id"]] + [entry]
    idx["questions"].sort(key=_sort_key)
    save_index(idx)


def next_question_id(provenance: str, track: str) -> str:
    prefix = exam_config.id_prefix(provenance, track)
    pat = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    used = [int(m.group(1)) for q in load_index()["questions"]
            if (m := pat.match(q.get("id", "")))]
    return f"{prefix}-{max(used, default=0) + 1:03d}"


# ---------- rendering ----------

def entry_stem_only(qid: str) -> str:
    """Stem + options + answer instruction. Safe to show during a drill."""
    e = find_question(qid)
    return grading.render_question(e, reveal_answer=False) if e else ""


def entry_full(qid: str) -> str:
    """Full synthesized review body: question, sealed key, rationale, traps, sources."""
    e = find_question(qid)
    if not e:
        return ""
    parts = [grading.render_question(e, reveal_answer=bool(e.get("verified"))), ""]
    if not e.get("verified"):
        return "\n".join(parts + [f"_(not yet sealed — status={e.get('status')})_"]).rstrip()

    if e.get("drill_rationale"):
        parts += ["", "**Rationale:**", str(e["drill_rationale"]).strip()]
    traps = e.get("distractor_traps")
    if traps:
        parts += ["", "**Distractor traps:**"]
        if isinstance(traps, dict):
            parts += [f"- **{k}:** {v}" for k, v in traps.items()]
        else:
            parts += [f"- {t}" for t in traps] if isinstance(traps, list) else [str(traps)]
    if e.get("topics"):
        parts += ["", "**Topics:** " + ", ".join(e["topics"])]
    if e.get("sources"):
        parts.append("**Sources:** " + ", ".join(e["sources"]))
    parts.append(
        f"<!-- sealed_at={e.get('sealed_at')} status={e.get('status')} "
        f"seal_confidence={e.get('seal_confidence')} -->")
    return "\n".join(parts).rstrip()


# ---------- topic notes ----------

def extract_section(md: str, h2_name: str) -> Optional[str]:
    pat = rf"^## {re.escape(h2_name)}\s*\n(.+?)(?=^## |\Z)"
    m = re.search(pat, md, flags=re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else None


def topic_id_to_path(topic_id: str) -> Optional[str]:
    t = load_topics().get(topic_id)
    return t.get("path") if t else None


# ---------- scorecard / missed ----------

def log_miss(qid: str, domain: str, given, correct, topics: list[str]) -> None:
    if not MISSED_MD.exists():
        return
    content = MISSED_MD.read_text()
    topic_str = ", ".join(topics[:2]) if topics else ""
    reason = f"Yours: {given} · Key: {correct}"
    if topic_str:
        reason += f" — review {topic_str}"
    row = f"| {qid} | {domain} | {today_iso()} | {reason} | open |"
    sep = "|---|---|---|---|---|"
    if sep in content and qid not in content:
        MISSED_MD.write_text(content.replace(sep, f"{sep}\n{row}", 1))


_SCORE_ROW_RE = re.compile(
    r"^\|\s*(?P<domain>(?:ae|arch)-\d{2})\s*\|(?P<title>[^|]*)\|"
    r"\s*(?P<attempted>\d+)\s*\|\s*(?P<correct>\d+)\s*\|(?P<acc>[^|]*)\|",
    re.MULTILINE,
)


def bump_scorecard(domain: str, correct: bool) -> None:
    """Increment attempted/correct/accuracy for `domain` in progress/scorecard.md.

    The scorecard has no weighted column: dbt does not publish section weights and
    scores every question equally, so a weighted total would be invented arithmetic.
    """
    if not SCORECARD_MD.exists() or domain not in VALID_DOMAINS:
        return
    text = SCORECARD_MD.read_text()

    def _sub(m: re.Match) -> str:
        if m.group("domain") != domain:
            return m.group(0)
        attempted = int(m.group("attempted")) + 1
        correct_ct = int(m.group("correct")) + (1 if correct else 0)
        pct = 100 * correct_ct // attempted
        return (f"| {domain} |{m.group('title')}| {attempted} | {correct_ct} | {pct}% |")

    new_text = _SCORE_ROW_RE.sub(_sub, text)
    if new_text != text:
        SCORECARD_MD.write_text(new_text)


def load_scorecard_raw() -> str:
    return SCORECARD_MD.read_text() if SCORECARD_MD.exists() else ""


def load_scorecard_accuracy() -> dict[str, int]:
    """{domain: accuracy_pct} for the `weakest` drill mode. Skips untouched rows."""
    if not SCORECARD_MD.exists():
        return {}
    out: dict[str, int] = {}
    for m in _SCORE_ROW_RE.finditer(SCORECARD_MD.read_text()):
        attempted = int(m.group("attempted"))
        if attempted == 0:
            continue
        pct = re.search(r"(\d+)", m.group("acc"))
        out[m.group("domain")] = int(pct.group(1)) if pct else 0
    return out


def load_missed_ids() -> set[str]:
    if not MISSED_MD.exists():
        return set()
    return set(re.findall(r"Q-[A-Z]{2}-[A-Z0-9]+-\d+", MISSED_MD.read_text()))


def load_missed_recent(n: int = 10) -> list[str]:
    if not MISSED_MD.exists():
        return []
    return re.findall(r"(Q-[A-Z]{2}-[A-Z0-9]+-\d+)", MISSED_MD.read_text())[-n:]
