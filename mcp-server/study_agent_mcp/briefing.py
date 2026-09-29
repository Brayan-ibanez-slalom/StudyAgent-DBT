"""Domain briefing: turn knowledge/<track>/<domain>/*.md into pre-drill study material.

The notes are the only source. Nothing here invents content — every string returned is
lifted verbatim from a note, so a briefing cannot drift from what was verified.

Notes are uneven: some mark traps inline (`**Trap:** ...`), some collect them under a
`## Traps` heading, some state neither. `extract_note` handles all three shapes and
reports what it could not find in `thin`, so the caller knows where a note needs a full
read rather than silently briefing a gap.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from . import exam_config, repo

# H2 headings whose bullets are decision rules rather than background.
DECISION_HEADING_RE = re.compile(
    r"when to|decision|cheat.?sheet|matrix|choosing|\bvs\.?\b|pick by|which\b",
    re.I,
)
TRAP_HEADING_RE = re.compile(r"\btraps?\b|gotcha|what .* is not|common mistake", re.I)
EXAM_ANGLE_HEADING_RE = re.compile(r"why this is likely on the exam|exam angle|recurring exam", re.I)

TRAP_LINE_RE = re.compile(r"^\s*(?:[-*]\s*)?\*\*Traps?:?\*\*\s*(.+)$", re.M)
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$")
BOLD_LEAD_RE = re.compile(r"^\*\*(.+?)\*\*")

MAX_TRAPS = 10
MAX_RULES = 14
MAX_LEADS_PER_SECTION = 5


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_sections(body: str) -> list[tuple[str, str]]:
    parts = re.split(r"^## +(.+)$", body, flags=re.M)
    return [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts), 2)]


def _bullets(section_body: str) -> list[str]:
    out: list[str] = []
    current: list[str] = []
    for line in section_body.splitlines():
        m = BULLET_RE.match(line)
        if m:
            if current:
                out.append(" ".join(current))
            current = [m.group(1)]
        elif current and line.startswith(("  ", "\t")) and line.strip():
            current.append(line.strip())
        elif current:
            out.append(" ".join(current))
            current = []
    if current:
        out.append(" ".join(current))
    return [_clean(b) for b in out if _clean(b)]


def _table_rows(section_body: str) -> list[str]:
    rows = []
    for line in section_body.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|") and not re.fullmatch(r"[|\s:-]+", s):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if any(cells):
                rows.append(" | ".join(cells))
    return rows[1:] if len(rows) > 1 else rows  # drop the header row


def _lead_ins(bullets: list[str]) -> list[str]:
    leads = []
    for b in bullets:
        m = BOLD_LEAD_RE.match(b)
        leads.append(_clean(m.group(1)) if m else b)
    return leads


def _dedup(xs: list[str]) -> list[str]:
    seen, out = set(), []
    for x in xs:
        k = x.lower()[:80]
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def extract_note(path: Path) -> dict:
    text = path.read_text()

    title_m = re.search(r"^# +(.+)$", text, re.M)
    domain_m = re.search(r"^\*\*Domain:\*\*\s*(.+)$", text, re.M)
    verified_m = re.search(r"^\*\*Verified:\*\*\s*(.+)$", text, re.M)

    domain_line = _clean(domain_m.group(1)) if domain_m else ""
    tasks = re.findall(r"\b(\d\.\d)\b", domain_line)

    traps: list[str] = []
    exam_angle = ""
    decision_rules: list[str] = []
    section_digest: list[dict] = []

    for heading, body in _split_sections(text):
        bullets = _bullets(body)
        rows = _table_rows(body)
        if EXAM_ANGLE_HEADING_RE.search(heading) and not exam_angle:
            exam_angle = _clean(re.sub(r"^\s*[-*]", "", body))[:600]
        if TRAP_HEADING_RE.search(heading):
            traps.extend(bullets)
        if DECISION_HEADING_RE.search(heading):
            decision_rules.extend(rows or bullets)
        section_digest.append({
            "heading": _clean(heading),
            "key_points": _lead_ins(bullets)[:MAX_LEADS_PER_SECTION],
            "has_table": bool(rows),
        })

    for m in TRAP_LINE_RE.finditer(text):
        traps.append(_clean(m.group(1)))

    traps = _dedup(traps)[:MAX_TRAPS]
    decision_rules = _dedup(decision_rules)[:MAX_RULES]

    thin = []
    if not traps:
        thin.append("no_traps")
    if not decision_rules:
        thin.append("no_decision_rules")
    if not exam_angle:
        thin.append("no_exam_angle")
    if not tasks:
        thin.append("no_specific_task")

    return {
        "title": _clean(title_m.group(1)) if title_m else path.stem,
        "path": str(path.relative_to(repo.REPO_ROOT)),
        "tasks": sorted(set(tasks)),
        "domain_line": domain_line,
        "verified": _clean(verified_m.group(1)) if verified_m else None,
        "exam_angle": exam_angle,
        "decision_rules": decision_rules,
        "traps": traps,
        "sections": section_digest,
        "thin": thin,
        "lines": text.count("\n") + 1,
    }


def _domain_dir(domain: str) -> Optional[Path]:
    frag = exam_config.domain_dir(domain)
    if not frag:
        return None
    d = repo.KNOWLEDGE_DIR / frag
    return d if d.is_dir() else None


def build(domain: str, topic_id: Optional[str] = None, full: bool = False) -> dict:
    """Digest every topic note in a domain, or read one note in full.

    `full=True` returns whole note bodies instead of the digest — use it for a single
    topic, not a whole domain.
    """
    if topic_id:
        t = repo.load_topics().get(topic_id)
        if not t:
            return {"error": f"topic {topic_id} not found"}
        p = repo.REPO_ROOT / t["path"]
        if not p.exists():
            return {"error": f"file missing: {t['path']}"}
        note = extract_note(p)
        note["topic_id"] = topic_id
        if full:
            note["content"] = p.read_text()
        return {"domain": t.get("domain"), "topic_count": 1, "topics": [note]}

    d = _domain_dir(domain)
    if d is None:
        return {"error": f"no knowledge folder for domain {domain!r}",
                "available": sorted(exam_config.VALID_DOMAINS)}

    meta = exam_config.DOMAINS[domain]
    notes = []
    for p in sorted(d.glob("*.md")):
        if p.stem.upper() == "README":
            continue
        note = extract_note(p)
        note["topic_id"] = f"{meta['track']}/{meta['dir']}/{p.stem}"
        if full:
            note["content"] = p.read_text()
        notes.append(note)

    covered: set[str] = set()
    for n in notes:
        covered.update(n["tasks"])

    return {
        "domain": domain,
        "domain_title": meta["title"],
        "track": meta["track"],
        "weight": meta["weight"],
        "weight_note": "dbt Labs does not publish section weights; all questions score equally.",
        "topic_count": len(notes),
        "tasks_in_blueprint": sorted(meta["tasks"]),
        "tasks_covered_by_notes": sorted(covered),
        "tasks_with_no_note": sorted(set(meta["tasks"]) - covered),
        "topics_without_specific_task": [
            n["topic_id"] for n in notes if "no_specific_task" in n["thin"]],
        "trap_count": sum(len(n["traps"]) for n in notes),
        "decision_rule_count": sum(len(n["decision_rules"]) for n in notes),
        "needs_full_read": [
            n["topic_id"] for n in notes if not n["traps"] and not n["decision_rules"]],
        "topics": notes,
    }
