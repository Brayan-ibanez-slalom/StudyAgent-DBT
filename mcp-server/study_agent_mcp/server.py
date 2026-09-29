"""study-agent MCP server — FastMCP over stdio (dbt certifications).

Covers both current dbt Labs exams via the `track` filter:
  ae    — dbt Analytics Engineering Certification (the "dbt Certified Developer" path)
  arch  — dbt Architect Certification

Tool groups:
  drill:      drill_pick, drill_grade, drill_grade_reasoned, drill_why, drill_hint,
              drill_explain, drill_help
  topics:     topic_search, topic_read, concept_lookup, domain_briefing
  cache:      cache_check, cache_fetch, cache_fetch_batch, cache_stats
  verify:     verify_seal, verify_all
  authoring:  item_gate, bank_audit, authored_ingest, coverage_report, balance_keys,
              difficulty_observed, defect_scan, retire_superseded
  progress:   progress_summary, asked_stats, session_save, session_clear, session_summary
  questions:  question_full, exam_facts
  ingestion:  ingest_help, ingest_scan, ingest_seal, ingest_dispute
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

from . import briefing, exam_config, grading, pipeline, repo

mcp = FastMCP("study-agent")

# Product, command, and object names. They anchor a rationale, but saying one is not
# evidence that the learner understood anything, so they are excluded from the
# reasoning score. (On AIP-C01 the most-"missed concept" turned out to be the word
# "bedrock", which made a perfect-reasoning verdict unreachable.)
DBT_ANCHORS = {
    "dbt", "model", "models", "modeling", "project", "projects", "warehouse",
    "snowflake", "databricks", "bigquery", "redshift", "postgres", "duckdb",
    "table", "tables", "view", "views", "schema", "schemas", "database",
    "column", "columns", "select", "query", "queries", "sql", "yaml", "yml",
    "command", "commands", "config", "configs", "configuration", "file", "files",
    "folder", "directory", "environment", "environments", "job", "jobs",
    "run", "runs", "build", "builds", "target", "targets", "cloud", "core",
    "platform", "account", "user", "users", "team", "teams",
}

# Share of non-anchor concepts a learner must express to count as sound reasoning.
RIGHT_REASONING_BAR = 0.6


# ---------------------------------------------------------------- PROTOCOL GUARDRAILS

# Server-side enforcement of the interactive drill protocol. The ONLY escape is
# `user_override=True`, which the agent must not set on its own — it exists so a
# user can explicitly request a deviation.

_PROTOCOL_STATE: dict = {"drill_help_seen": False}
_INTERACTIVE_MIN_REASONING_CHARS = 15

# Sealers we trust structurally (a vendor asserted the answer) but have NOT
# cross-verified against dbt docs.
VENDOR_SEALERS = {"vendor_ingestor", "community_ingestor"}

_OVERRIDE_HINT = (
    "This guardrail can be bypassed with user_override=True, but ONLY when the user "
    "explicitly asked for this deviation. The agent must not set it on its own."
)


def _guard(condition: bool, error_msg: str, code: str, user_override: bool) -> Optional[dict]:
    if condition or user_override:
        return None
    return {"error": error_msg, "guardrail": code, "hint": _OVERRIDE_HINT}


# ---------------------------------------------------------------- EXAM FACTS

@mcp.tool()
def exam_facts(track: Optional[str] = None) -> dict:
    """Published facts about the dbt exams, plus what is explicitly NOT published.

    Domains and tasks come from the official dbt Labs study guides. Question count
    (65) and passing score (65%) are published. Per-topic weighting is NOT — so
    `subtopic_share_pct` and `estimated_questions` are clearly-labelled proxies derived
    from how many sub-topics each topic lists, never presented as exam facts.
    """
    tracks = [track] if track in exam_config.EXAM_FACTS else list(exam_config.EXAM_FACTS)
    out: dict[str, Any] = {"tracks": {}}
    for t in tracks:
        facts = dict(exam_config.EXAM_FACTS[t])
        domains = exam_config.domains_for(t)
        share = exam_config.subtopic_share(t)
        est = exam_config.estimated_questions(t)
        facts["domains"] = {
            d: {"title": v["title"],
                "official_weight": v["weight"],
                "subtopic_count": len(v["tasks"]),
                "subtopic_share_pct": share[d],
                "estimated_questions_proxy": est[d],
                "tasks": {k: title for k, (title, _) in v["tasks"].items()},
                "provenance": v["provenance"]}
            for d, v in domains.items()
        }
        facts["domain_count"] = len(domains)
        facts["subtopic_count"] = sum(len(v["tasks"]) for v in domains.values())
        facts["unscored_questions"] = exam_config.UNSCORED_QUESTIONS_NOTE
        out["tracks"][t] = facts
    out["not_published_by_dbt_labs"] = [
        "per-topic weighting — both guides say only that all questions are weighted equally",
        "how many of the 65 questions fall in each topic",
        "how many of the 65 questions are unscored research items",
    ]
    out["proxy_warning"] = (
        "subtopic_share_pct and estimated_questions_proxy are DERIVED from sub-topic "
        "counts in the official outline. They are a study-time heuristic, not a "
        "statement about the exam. Never present them as official weights."
    )
    out["question_formats"] = exam_config.QUESTION_TYPES
    return out


# ---------------------------------------------------------------- DRILL

def _matches_difficulty(q: dict, difficulty: str) -> bool:
    order = exam_config.DIFFICULTY_LADDER
    wanted = difficulty.rstrip("+").upper()
    if wanted not in order:
        return False
    allowed = set(order[order.index(wanted):]) if difficulty.endswith("+") else {wanted}
    return q.get("difficulty_estimate") in allowed


@mcp.tool()
def drill_pick(
    count: int = 1,
    track: Optional[str] = None,
    domain: Optional[str] = None,
    mode: str = "random",
    exclude_seen: bool = False,
    difficulty: Optional[str] = None,
    task: Optional[str] = None,
    qtype: Optional[str] = None,
    user_override: bool = False,
) -> list[dict] | dict:
    """Pick sealed (drill-ready) questions.

    Returns the rendered question and the answer instruction for its format — never
    the sealed key.

    ENFORCED GUARDRAILS (bypass only with user_override=True on explicit user request):
      - drill_help must have been called at least once in this process.
      - count must be 1 in interactive mode. Batches require user_override.

    Args:
        count: how many questions to return
        track: 'ae' | 'arch' — which certification
        domain: e.g. 'ae-02' or 'arch-03'
        mode: 'random' | 'missed' | 'weakest' | 'unseen' | 'least-seen' | 'hard'
        exclude_seen: drop anything already in progress/asked-log.json
        difficulty: 'L4' or 'L4+' for L4 and above
        task: within-domain task id, e.g. '2.2' (use with `domain`)
        qtype: restrict to one format, e.g. 'build_list' or 'fill_in_blank'
        user_override: reserved for USER-initiated bypass. Agent must not set.
    """
    err = _guard(_PROTOCOL_STATE["drill_help_seen"],
                 "drill_help() has not been called this session; protocol not primed.",
                 "PROTOCOL_NOT_PRIMED", user_override)
    if err:
        return err
    err = _guard(count == 1,
                 f"count={count} violates interactive protocol (one question per turn).",
                 "BATCH_NOT_ALLOWED", user_override)
    if err:
        return err

    # Retired items stay in the bank for provenance but are never served: each one has
    # been replaced by the rewrite named in its `superseded_by` field. `drill_exclude`
    # covers the other case — an item answerable without dbt knowledge.
    pool = [q for q in repo.load_index()["questions"]
            if q.get("verified") and not q.get("retired") and not q.get("drill_exclude")]
    if track:
        pool = [q for q in pool if exam_config.track_of(q.get("domain")) == track]
    if domain:
        pool = [q for q in pool if q.get("domain") == domain]
    if task:
        pool = [q for q in pool if q.get("blueprint_task") == task]
    if qtype:
        pool = [q for q in pool if grading.qtype_of(q) == qtype]
    if difficulty:
        pool = [q for q in pool if _matches_difficulty(q, difficulty)]
    if not pool:
        return {"error": "NO_MATCHES",
                "message": "No sealed questions match those filters.",
                "filters": {"track": track, "domain": domain, "task": task,
                            "difficulty": difficulty, "qtype": qtype}}

    asked = repo.load_asked_log()
    seen_ids = set(asked) | repo.load_attempted_ids()

    if mode == "missed":
        missed = repo.load_missed_ids()
        pool = [q for q in pool if q["id"] in missed]
    elif mode == "weakest":
        acc = repo.load_scorecard_accuracy()
        pool.sort(key=lambda q: acc.get(q.get("domain"), 101))
    elif mode == "unseen":
        pool = [q for q in pool if q["id"] not in seen_ids]
    elif mode == "least-seen":
        pool.sort(key=lambda q: asked.get(q["id"], {}).get("count", 0))
    elif mode == "hard":
        rank = {d: i for i, d in enumerate(reversed(exam_config.DIFFICULTY_LADDER))}
        pool.sort(key=lambda q: (rank.get(q.get("difficulty_estimate"), 9),
                                 -len(q.get("stem") or "")))

    if exclude_seen and mode != "unseen":
        pool = [q for q in pool if q["id"] not in seen_ids]
    if not pool:
        return {"error": "NO_MATCHES", "message": f"mode={mode} left an empty pool."}

    if mode == "random":
        random.shuffle(pool)

    now_iso = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": q["id"],
            "track": exam_config.track_of(q.get("domain")),
            "domain": q.get("domain"),
            "blueprint_task": q.get("blueprint_task"),
            "qtype": grading.qtype_of(q),
            "difficulty": q.get("difficulty_estimate"),
            "status": q["status"],
            "times_asked": asked.get(q["id"], {}).get("count", 0),
            "question": repo.entry_stem_only(q["id"]),
            "answer_instruction": grading.answer_instruction(q),
            # Pass back to drill_grade_reasoned(served_at=...) to record time-to-answer.
            "served_at": now_iso,
        }
        for q in pool[:count]
    ]


def _record_attempt(e: dict, result: dict, user_answer: Any, extra: dict) -> None:
    correct = result["correct"]
    if not correct:
        repo.log_miss(e["id"], e.get("domain", "?"), result.get("given"),
                      result.get("expected"), e.get("topics", []))
    repo.bump_scorecard(e.get("domain", ""), correct)
    repo.log_asked(e["id"], correct)
    repo.append_attempt({
        "ts": datetime.now(timezone.utc).isoformat(),
        "qid": e["id"],
        "track": exam_config.track_of(e.get("domain")),
        "domain": e.get("domain"),
        "qtype": grading.qtype_of(e),
        "user_answer": user_answer if isinstance(user_answer, (str, int)) else json.dumps(user_answer),
        "expected": result.get("expected") if isinstance(result.get("expected"), str)
        else json.dumps(result.get("expected")),
        "correct": correct,
        "score": result.get("score"),
        **extra,
    })


def _blocked(e: Optional[dict], qid: str) -> Optional[dict]:
    if not e:
        return {"error": f"question {qid} not found"}
    if not e.get("verified"):
        return {"error": f"{qid} is not sealed (status={e.get('status')}); drill blocked",
                "hint": "run ingest_seal, or pick a sealed question"}
    return None


@mcp.tool()
def drill_grade(question_id: str, user_answer: Any, user_override: bool = False) -> dict:
    """Grade an answer against the sealed key, without validating reasoning.

    DEPRECATED for interactive use — call drill_grade_reasoned so both the answer and
    the reasoning are checked. This entry point errors unless user_override=True, which
    the USER may pass to opt into answer-only grading.

    `user_answer` shape depends on the question's format; see `answer_instruction`
    from drill_pick, or grading rules in docs/question-formats.md.
    """
    err = _guard(False,
                 "drill_grade skips reasoning; interactive protocol requires "
                 "drill_grade_reasoned.", "REASONING_REQUIRED", user_override)
    if err:
        return err
    e = repo.find_question(question_id)
    if blocked := _blocked(e, question_id):
        return blocked
    try:
        result = grading.grade(e, user_answer)
    except grading.AnswerFormatError as ex:
        return {"error": "ANSWER_FORMAT", "message": str(ex),
                "qtype": grading.qtype_of(e),
                "answer_instruction": grading.answer_instruction(e)}
    _record_attempt(e, result, user_answer, {"verdict": "ungraded_reasoning"})
    return {**result, "id": question_id, "qtype": grading.qtype_of(e),
            "rationale": e.get("drill_answer_short"),
            "topics": e.get("topics", []), "status": e["status"]}


@mcp.tool()
def drill_grade_reasoned(
    question_id: str,
    user_answer: Any,
    user_reasoning: str,
    served_at: Optional[str] = None,
    user_override: bool = False,
) -> dict:
    """Grade the answer AND validate the reasoning against the sealed rationale.

    One call per question replaces drill_grade + drill_why. Emits the same side effects
    (log_miss, bump_scorecard, log_asked) plus a per-attempt record in
    progress/attempts.jsonl.

    ENFORCED GUARDRAIL: user_reasoning must be at least
    _INTERACTIVE_MIN_REASONING_CHARS characters — a one-word "because" is not engagement.
    """
    err = _guard(
        len((user_reasoning or "").strip()) >= _INTERACTIVE_MIN_REASONING_CHARS,
        f"user_reasoning too short (<{_INTERACTIVE_MIN_REASONING_CHARS} chars); "
        "interactive protocol requires a substantive rationale.",
        "REASONING_TOO_SHORT", user_override)
    if err:
        return err
    e = repo.find_question(question_id)
    if blocked := _blocked(e, question_id):
        return blocked
    try:
        result = grading.grade(e, user_answer)
    except grading.AnswerFormatError as ex:
        return {"error": "ANSWER_FORMAT", "message": str(ex),
                "qtype": grading.qtype_of(e),
                "answer_instruction": grading.answer_instruction(e)}

    sealed_rationale = e.get("drill_answer_short") or ""
    keywords = _keywords_from_rationale(sealed_rationale)
    score = score_reasoning(keywords, user_reasoning)
    covered, missed = score["covered"], score["missed"]

    if result["correct"] and score["concept_coverage"] >= RIGHT_REASONING_BAR:
        verdict = "right_answer_right_reasoning"
    elif result["correct"] and not covered:
        verdict = "right_answer_unengaged_reasoning"
    elif result["correct"]:
        verdict = "right_answer_partial_reasoning"
    elif covered:
        verdict = "wrong_answer_partial_reasoning"
    else:
        verdict = "wrong_answer_unengaged_reasoning"

    answered_ms: Optional[int] = None
    if served_at:
        try:
            served_dt = datetime.fromisoformat(served_at.replace("Z", "+00:00"))
            answered_ms = int(
                (datetime.now(timezone.utc) - served_dt).total_seconds() * 1000)
        except ValueError:
            answered_ms = None

    _record_attempt(e, result, user_answer, {
        "verdict": verdict,
        "user_reasoning": user_reasoning,
        "reasoning_keywords_covered": covered,
        "reasoning_keywords_missed": missed,
        "answered_ms": answered_ms,
    })

    return {
        **result,
        "id": question_id,
        "qtype": grading.qtype_of(e),
        "verdict": verdict,
        "sealed_rationale": sealed_rationale,
        "reasoning_keywords_all": keywords,
        "reasoning_keywords_covered": covered,
        "reasoning_keywords_missed": missed,
        "answered_ms": answered_ms,
        "topics": e.get("topics", []),
        "sources": e.get("sources", []),
        "status": e["status"],
        "domain": e.get("domain"),
        "track": exam_config.track_of(e.get("domain")),
    }


@mcp.tool()
def drill_why(question_id: str, verbose: bool = False, user_override: bool = False) -> dict:
    """Return sealed reasoning + sources + per-distractor traps.

    ENFORCED GUARDRAIL: refuses until the question has actually been attempted. A
    docstring saying "use after grading" is not enforcement — one premature call hands
    the learner the key. Review of an unattempted question is still possible via
    `question_full(include_answer=True)`, which is explicitly a review tool, or with
    user_override=True on an explicit user request.

    Pass `verbose=true` for the full synthesized entry text.
    """
    e = repo.find_question(question_id)
    if not e:
        return {"error": "not found"}
    err = _guard(
        question_id in repo.load_attempted_ids(),
        f"{question_id} has not been answered yet; revealing the rationale now would "
        "leak the key.",
        "NOT_YET_ATTEMPTED", user_override)
    if err:
        return err
    out = {
        "id": question_id,
        "qtype": grading.qtype_of(e),
        "drill_answer": e.get("drill_answer"),
        "rationale": e.get("drill_answer_short"),
        "drill_rationale": e.get("drill_rationale"),
        "distractor_traps": e.get("distractor_traps") or {},
        "options_analysis": e.get("options_analysis"),
        "sources": e.get("sources", []),
        "sealed_at": e.get("sealed_at"),
        "topics": e.get("topics", []),
    }
    if verbose:
        out["full_entry"] = repo.entry_full(question_id)
    return out


def _hint_terms(text: str) -> set[str]:
    """Words a hint could carry. Hyphens and underscores split, so a slug yields parts."""
    return set(re.findall(r"[a-z][a-z0-9]{3,}", (text or "").lower()))


def _key_only_terms(e: dict) -> set[str]:
    """Words in the key that appear in neither the stem nor any distractor.

    The learner can already see the stem and every option, so a term unique to the key
    is a giveaway. For non-letter formats the key IS the answer text, so everything in
    it is treated as leaky.
    """
    stem_terms = _hint_terms(e.get("stem"))
    if not grading.is_letter_type(e):
        return _hint_terms(str(e.get("drill_answer"))) - stem_terms
    opts = e.get("option_texts") or {}
    keyed = grading.letters(e.get("drill_answer"))
    key_terms: set[str] = set()
    distractor_terms: set[str] = set()
    for letter, text in opts.items():
        target = key_terms if letter in keyed else distractor_terms
        target |= _hint_terms(text)
    return key_terms - distractor_terms - stem_terms


@mcp.tool()
def drill_hint(question_id: str) -> dict:
    """Return a SUBTLE hint for a sealed question.

    Never reveals the key, quotes the sealed rationale, or names the dbt feature that IS
    the answer. Hints point at a general skill area; anything carrying a word unique to
    the key is suppressed and reported in `suppressed_as_leaky`.

    Opt-in only: the user asks for a hint, the agent calls this tool.
    """
    e = repo.find_question(question_id)
    if not e or not e.get("verified"):
        return {"error": "not found or not sealed", "id": question_id}

    leak_terms = _key_only_terms(e)
    suppressed: list[str] = []

    def _safe(candidate: str) -> bool:
        if _hint_terms(candidate) & leak_terms:
            suppressed.append(candidate)
            return False
        return True

    # General skill area first — the blueprint task, not the feature that answers it.
    concept_areas: list[str] = []
    task = e.get("blueprint_task")
    title = exam_config.task_title(e.get("domain", ""), task or "")
    if title and _safe(title):
        concept_areas.append(f"{task} {title}" if task else title)

    # Topic slugs are far more specific, so they are admitted only if they don't leak.
    for t in e.get("topics") or []:
        m = re.search(r"/([a-z][a-z0-9\-]+?)(?:\.md)?$", t)
        if m and _safe(m.group(1)):
            concept_areas.append(m.group(1))

    if not concept_areas:
        # Every label for this item names the answer. A bare identifier has no content
        # words at all, so it is the last thing that is still safe.
        concept_areas.append(task or f"domain {e.get('domain')}")

    visible = repo.entry_stem_only(question_id).lower()
    all_kw = _keywords_from_rationale(e.get("drill_answer_short") or "")
    cues = [k for k in all_kw if k not in visible and _safe(k)][:3]

    traps = e.get("distractor_traps") or {}
    if len(traps) >= 3:
        watch_out = ("Several options look workable; at least one is the right idea "
                     "applied at the wrong layer or the wrong lifecycle stage.")
    elif traps:
        watch_out = "One option is a superficial workaround for what needs a root-cause fix."
    else:
        watch_out = None

    return {
        "id": question_id,
        "qtype": grading.qtype_of(e),
        "concept_areas": concept_areas,
        "concept_cues": cues,
        "watch_out_for": watch_out,
        "suppressed_as_leaky": suppressed,
        "note": "Hint names a skill area only; it never reveals the key, the sealed "
                "rationale, or a term unique to the correct answer.",
    }


# Plain-English glossary for common dbt jargon. Only entries whose key phrase appears
# in the sealed content are surfaced, so the calling model is not handed a wall of
# irrelevant definitions.
_PLAIN_GLOSSARY: dict[str, str] = {
    # Core objects
    "model": "A SELECT statement in a .sql file. dbt wraps it in CREATE TABLE/VIEW and runs it for you.",
    "ref(": "How one model points at another. dbt reads these to build the DAG and to work out run order.",
    "source(": "How a model points at raw data dbt did NOT create — tables loaded by something else.",
    "seed": "A small CSV committed to the repo that dbt loads into the warehouse as a table. For lookup lists, not for loading real data.",
    "snapshot": "dbt's built-in slowly-changing-dimension recorder: it captures what a mutable source row looked like at each point in time.",
    "exposure": "A declared downstream consumer of your models (a dashboard, an ML job). It appears in the DAG so you can see what breaks.",
    "analysis": "A .sql file dbt compiles but never runs against the warehouse — for one-off queries you want version-controlled.",
    # Materializations
    "materialization": "How dbt physically builds a model: as a view, a table, an incremental table, or inlined as a CTE (ephemeral).",
    "ephemeral": "Not built in the warehouse at all — the SQL is pasted into downstream models as a CTE.",
    "incremental": "Build the table once, then on later runs only process and merge new or changed rows instead of rebuilding.",
    "is_incremental": "The Jinja check that is true only on a normal incremental run, so you can add a 'only new rows' filter there.",
    "full refresh": "Throw the existing table away and rebuild an incremental model from scratch.",
    "microbatch": "An incremental strategy that splits a backfill into time-bounded batches dbt runs independently.",
    "on_schema_change": "What dbt does when an incremental model's columns change: ignore, fail, append new ones, or sync them.",
    # Jinja / macros
    "jinja": "The templating language embedded in dbt SQL. `{{ }}` prints a value, `{% %}` runs logic like loops and ifs.",
    "macro": "A reusable Jinja function. Write the logic once, call it from many models.",
    "package": "Someone else's dbt project installed into yours (via packages.yml), bringing their macros and models.",
    "dispatch": "The mechanism that lets a macro have a different implementation per data platform.",
    "this": "Jinja shorthand for the relation the current model will be written to.",
    # Testing
    "generic test": "A reusable test you attach to a column in YAML, like unique or not_null.",
    "singular test": "A one-off test written as a SQL file. It passes when the query returns zero rows.",
    "unit test": "A test that runs a model against fixed, made-up input rows and checks the exact output — it tests the logic, not the data.",
    "severity": "Whether a failing test errors the run or only warns.",
    "store_failures": "Write failing test rows into a table so you can inspect what actually broke.",
    "contract": "A promise about a model's columns and types, enforced by the warehouse at build time.",
    # State / selection
    "state:modified": "A selector meaning 'only the nodes that changed since a saved manifest' — the basis of Slim CI.",
    "defer": "Use production's versions of models you did not build yourself, instead of rebuilding your own upstream copies.",
    "manifest.json": "The artifact describing every node in a project after compilation. Comparing two of them is what makes state selection possible.",
    "dbt retry": "Re-run only what failed (and what was skipped because of it) in the previous invocation.",
    "dbt clone": "Create cheap warehouse-native copies of an existing set of relations instead of rebuilding them.",
    # Governance / Mesh
    "dbt mesh": "Splitting one giant project into several that reference each other through explicitly public models.",
    "access:": "Whether a model may be referenced from outside its group or project: private, protected, or public.",
    "group": "A labelled set of models with an owner; used with access to control who may reference what.",
    "dependencies.yml": "Where a project declares the other dbt projects it references (as opposed to packages it installs).",
    # dbt platform / Architect
    "environment": "A named configuration binding a dbt version, a branch, and warehouse credentials — typically development vs deployment.",
    "deploy job": "A scheduled or triggered run of dbt commands in a deployment environment.",
    "ci job": "A job that runs on a pull request to build and test only what changed before it is merged.",
    "slim ci": "Running CI with state comparison and deferral so only changed models (and their children) get built.",
    "service token": "A non-human credential for machine access to the dbt APIs, scoped by permission set.",
    "rbac": "Role-based access control — permissions attach to roles and groups, not to individuals.",
    "permission set": "A named bundle of permissions assigned to a group, optionally scoped to specific projects.",
    "discovery api": "The API for querying metadata about your projects, runs, and lineage.",
    "webhook": "An outbound HTTP call dbt makes when a run event happens, so another system can react.",
    "threads": "How many models dbt builds in parallel against the warehouse in a single run.",
}


@mcp.tool()
def drill_explain(question_id: str, include_sealed: bool = True) -> dict:
    """Explain a sealed question in plain English.

    Returns the sealed content plus a glossary filtered to the dbt jargon actually
    present in this question, plus rendering instructions the calling model can follow
    for a consistent style.

    Set `include_sealed=false` for glossary + instructions only, when the caller already
    has the sealed content in context.
    """
    e = repo.find_question(question_id)
    if not e or not e.get("verified"):
        return {"error": "not found or not sealed", "id": question_id}

    haystack = " ".join([
        str(e.get("drill_answer_short") or ""),
        str(e.get("drill_rationale") or ""),
        str(e.get("options_analysis") or ""),
        str(e.get("stem") or ""),
        *(str(v) for v in (e.get("distractor_traps") or {}).values()),
    ]).lower()

    hits = {term: d for term, d in _PLAIN_GLOSSARY.items() if term in haystack}

    result: dict = {
        "id": question_id,
        "domain": e.get("domain"),
        "qtype": grading.qtype_of(e),
        "glossary": hits,
        "glossary_hits_count": len(hits),
        "rendering_instructions": (
            "Render the plain-English explanation in this order:\n"
            "1) One sentence: what the question is really asking, in plain wording.\n"
            "2) 'Why the right answer works' — 2-3 sentences, substituting glossary "
            "definitions where jargon appears.\n"
            "3) 'Why each wrong answer fails' — one sentence per distractor, naming the "
            "specific trap.\n"
            "4) A one-line rule the reader can apply to the next similar question.\n"
            "Define jargon on first mention. Do not invent facts beyond the sealed content."
        ),
    }
    if include_sealed:
        result.update({
            "drill_answer": e.get("drill_answer"),
            "drill_answer_short": e.get("drill_answer_short"),
            "drill_rationale": e.get("drill_rationale"),
            "options_analysis": e.get("options_analysis"),
            "distractor_traps": e.get("distractor_traps") or {},
        })
    return result


_DRILL_INTERACTIVE_FLOW = [
    "1. Agent: drill_pick(count=1, track=..., mode='hard'|'missed'|'weakest'|...) — ONE question",
    "2. Agent: presents `question` VERBATIM including `answer_instruction`, then STOPS",
    "3. Agent's message MUST ask the user to reply with their answer AND their reasoning",
    "4. User (next turn): sends the answer in the question's format + short reasoning",
    "5. Agent: drill_grade_reasoned(qid, user_answer, user_reasoning, served_at=...) — one call",
    "6. Agent: 2-3 sentence verdict using the returned `verdict` + covered/missed keywords",
    "7. Agent: asks 'next?' — do NOT auto-continue without user consent",
]

_DRILL_FORBIDDEN = [
    "Fabricating 'your answer was X' when the user has not answered",
    "Calling a grade tool in the same turn as drill_pick",
    "Presenting more than ONE question per turn in interactive mode",
    "Generating your own rationale instead of using sealed_rationale from the tool",
    "Reformatting a question into multiple choice because its real format is harder to serve",
    "Continuing to the next question without the user asking",
]


@mcp.tool()
def drill_help() -> dict:
    """Return the canonical INTERACTIVE drill workflow. Call this first in a session."""
    _PROTOCOL_STATE["drill_help_seen"] = True
    return {
        "purpose": "Interactive one-question-at-a-time drill with reasoning validation.",
        "tracks": {t: f["name"] for t, f in exam_config.EXAM_FACTS.items()},
        "workflow": _DRILL_INTERACTIVE_FLOW,
        "forbidden": _DRILL_FORBIDDEN,
        "question_formats": {
            qt: {"answer_shape": meta["answer_shape"],
                 "partial_credit_reported": meta["partial_credit"]}
            for qt, meta in exam_config.QUESTION_TYPES.items()
        },
        "format_note": (
            "dbt exams use six formats. drill_pick returns `answer_instruction` per "
            "question — relay it verbatim. `score` is reported for coaching only; dbt "
            "awards one point for a correct answer and zero otherwise, so `correct` is "
            "always the binary outcome."
        ),
        "enforced_guardrails": {
            "PROTOCOL_NOT_PRIMED": "drill_pick refuses until drill_help has been called.",
            "BATCH_NOT_ALLOWED": "drill_pick refuses count > 1 (bypass: user_override=True).",
            "REASONING_REQUIRED": "drill_grade refuses (bypass: user_override=True).",
            "REASONING_TOO_SHORT": (
                f"drill_grade_reasoned refuses user_reasoning shorter than "
                f"{_INTERACTIVE_MIN_REASONING_CHARS} chars (bypass: user_override=True)."),
            "NOT_YET_ATTEMPTED": "drill_why refuses until the question has been "
                                 "answered (bypass: user_override=True).",
            "ANSWER_FORMAT": "The answer could not be read in the question's format; "
                             "the error carries the correct shape.",
        },
        "recommended_pick_modes": {
            "hard": "highest labelled difficulty first",
            "weakest": "sort by domain accuracy ascending — targets weak spots",
            "missed": "only previously missed questions — spaced repetition",
            "least-seen": "fewest drills so far",
            "unseen": "never drilled",
        },
        "verdict_labels": {
            "right_answer_right_reasoning": "answer correct AND sealed concepts covered — solid",
            "right_answer_partial_reasoning": "correct but only some concepts engaged",
            "right_answer_unengaged_reasoning": "correct but reasoning missed every concept — likely a guess",
            "wrong_answer_partial_reasoning": "wrong but reasoning touched correct concepts — near miss",
            "wrong_answer_unengaged_reasoning": "wrong and reasoning missed every concept — needs re-teach",
        },
        "coaching_template": (
            "Given the tool response, respond in <=3 sentences: 1) correct/wrong + the key, "
            "2) name the decisive sealed concept (from reasoning_keywords_missed if wrong, "
            "covered if right), 3) point to a source only if the user asked or the verdict "
            "is *_unengaged_*. Do NOT paste the whole sealed_rationale unless asked 'why'."
        ),
    }


# ---------------------------------------------------------------- TOPICS

@mcp.tool()
def topic_search(keyword: str, limit: int = 5, track: Optional[str] = None) -> list[dict]:
    """Reverse-index lookup on knowledge/_tags.json: keyword -> topic IDs."""
    tags = repo.load_tags()
    topics = repo.load_topics()
    key = keyword.lower()
    unique: dict[str, dict] = {}
    for tag, topic_ids in tags.items():
        if key not in tag.lower():
            continue
        for tid in topic_ids:
            if tid in unique:
                continue
            t = topics.get(tid, {})
            if track and t.get("track") != track:
                continue
            unique[tid] = {"topic_id": tid, "matched_tag": tag, "title": t.get("title"),
                           "path": t.get("path"), "domain": t.get("domain"),
                           "track": t.get("track")}
    return list(unique.values())[:limit]


@mcp.tool()
def topic_read(topic_id: str, section: Optional[str] = None) -> dict:
    """Read a topic note. If `section` is provided, return only that H2 section."""
    t = repo.load_topics().get(topic_id)
    if not t:
        return {"error": f"topic {topic_id} not found"}
    p = repo.REPO_ROOT / t["path"]
    if not p.exists():
        return {"error": f"file missing: {t['path']}"}
    content = p.read_text()
    if section:
        content = repo.extract_section(content, section) or content
    return {"topic_id": topic_id, "title": t.get("title"), "path": t["path"],
            "domain": t.get("domain"), "content": content}


@mcp.tool()
def domain_briefing(domain: str, topic_id: Optional[str] = None, full: bool = False) -> dict:
    """Pre-drill study material for one domain, built only from knowledge/*.md.

    Returns, per topic note: the tasks it covers, the exam angle it states, its decision
    rules, its traps, and a heading-level digest. Every string is lifted verbatim from a
    note, so a briefing cannot invent content.

    `needs_full_read` and each topic's `thin` list name the notes that state no traps or
    decision rules — read those with `full=True` rather than briefing a gap.
    """
    return briefing.build(domain, topic_id=topic_id, full=full)


@mcp.tool()
def concept_lookup(name: str) -> dict:
    """Tier-3 index: dbt concept, command, or config name -> canonical knowledge/ note.

    Substring, case-insensitive, against knowledge/_concepts.json.
    """
    concepts = repo.load_concepts()
    key = name.lower()
    hits = [{"concept": n, "path": p} for n, p in concepts.items() if key in n.lower()]
    return {"query": name, "hits": hits[:10], "indexed_concepts": len(concepts)}


# ---------------------------------------------------------------- CACHE

@mcp.tool()
def cache_check(url: str) -> dict:
    """Is URL cached in sources/cache/_index.json? Returns freshness age in days."""
    for e in repo.load_cache_index()["entries"]:
        if e["url"] == url:
            return {"cached": True, "path": e["path"],
                    "age_days": repo.days_since(e["fetched_at"]),
                    "sha256": e.get("sha256"), "title": e.get("title")}
    return {"cached": False, "url": url}


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    return "\n".join(line.strip() for line in main.get_text(separator="\n").splitlines()
                     if line.strip())


def _extract_title(html: str) -> str:
    t = BeautifulSoup(html, "html.parser").find("title")
    return t.get_text(strip=True) if t else ""


def _fetch_one(url: str, force: bool) -> dict:
    hit = next((e for e in repo.load_cache_index()["entries"] if e["url"] == url), None)
    if hit and not force and repo.days_since(hit["fetched_at"]) < repo.CACHE_STALE_DAYS:
        return {"status": "cached-fresh", "url": url, "path": hit["path"],
                "age_days": repo.days_since(hit["fetched_at"]), "title": hit.get("title")}
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30.0,
                         headers={"User-Agent": "study-agent-dbt/0.1 (personal exam prep)"})
        resp.raise_for_status()
    except Exception as ex:  # noqa: BLE001
        return {"status": "fetch-error", "url": url, "error": str(ex)}

    text = _html_to_text(resp.text)
    u = urlparse(url)
    rel = f"{u.netloc}{u.path}".rstrip("/") + ".txt"
    raw_path = repo.CACHE_RAW / rel
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text)
    return {"status": "fetched", "url": url,
            "path": str(raw_path.relative_to(repo.REPO_ROOT)),
            "title": _extract_title(resp.text),
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "bytes": len(text), "fetched_at": repo.today_iso()}


def _persist_fetches(results: list[dict]) -> None:
    fresh = [r for r in results if r.get("status") == "fetched"]
    if not fresh:
        return
    idx = repo.load_cache_index()
    by_url = {e["url"]: e for e in idx["entries"]}
    for r in fresh:
        by_url[r["url"]] = {"url": r["url"], "path": r["path"], "title": r["title"],
                            "fetched_at": r["fetched_at"], "sha256": r["sha256"],
                            "source": "mcp-cache_fetch"}
    idx["entries"] = list(by_url.values())
    repo.save_cache_index(idx)


@mcp.tool()
def cache_fetch(url: str, force: bool = False) -> dict:
    """Fetch a URL, extract main text, cache under sources/cache/_raw/.

    Skips the network if the URL is cached and less than 90 days old, unless force=True.
    docs.getdbt.com is the intended target but any https:// page works.
    """
    if not url.startswith("https://"):
        return {"status": "invalid-url", "error": "cache_fetch requires an https:// URL",
                "url": url}
    result = _fetch_one(url, force)
    _persist_fetches([result])
    return result


@mcp.tool()
def cache_fetch_batch(urls: list[str], force: bool = False, max_concurrency: int = 5) -> dict:
    """Fetch many URLs in parallel. Same caching rules as cache_fetch.

    max_concurrency is capped at 8 to stay polite to docs.getdbt.com.
    """
    unique = list(dict.fromkeys(u for u in urls if u.startswith("https://")))
    invalid = [u for u in urls if not u.startswith("https://")]
    workers = max(1, min(max_concurrency, 8))

    results: list[dict] = []
    if unique:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_fetch_one, u, force) for u in unique]
            results = [f.result() for f in as_completed(futures)]
    _persist_fetches(results)

    counts: Counter = Counter(r.get("status", "fetch-error") for r in results)
    return {"requested": len(urls), "unique_https": len(unique), "invalid_urls": invalid,
            "concurrency": workers, "summary": dict(counts), "results": results}


@mcp.tool()
def cache_stats() -> dict:
    """Cache health: total / fresh (< 90d) / stale / missing files on disk."""
    idx = repo.load_cache_index()
    fresh = stale = missing = 0
    hosts: Counter = Counter()
    for e in idx["entries"]:
        hosts[urlparse(e["url"]).netloc] += 1
        if not (repo.REPO_ROOT / e["path"]).exists():
            missing += 1
        elif repo.days_since(e["fetched_at"]) < repo.CACHE_STALE_DAYS:
            fresh += 1
        else:
            stale += 1
    return {"total_entries": len(idx["entries"]), "fresh_lt_90d": fresh,
            "stale_gte_90d": stale, "missing_files_on_disk": missing,
            "by_host": dict(hosts.most_common(10))}


# ---------------------------------------------------------------- VERIFY

@mcp.tool()
def verify_seal(question_id: str, deep: bool = False) -> dict:
    """Verify one sealed question against its cited source.

    Shallow: sources exist (topic-note file exists OR URL is well-formed).
    Deep: for URL sources, ensure they are cached; for note sources, check the note's
          `**Verified:**` header freshness and keyword-match any cited dbt docs URLs
          against the cached text.

    Validity semantic: structural checks (existence, cache, freshness) must ALL pass.
    Keyword checks are collective — at least ONE cited source must contain the answer's
    core keywords, because a synthesis note may cite complementary pages.

    Vendor-declared seals short-circuit to seal_valid=True with an explicit
    `vendor_declared` check, reflecting that a vendor asserted the answer but we have
    NOT cross-verified it against dbt docs.
    """
    e = repo.find_question(question_id)
    if not e:
        return {"error": "not found"}
    if not e.get("verified"):
        return {"error": f"{question_id} not sealed", "status": e.get("status")}

    checks: list[dict] = []
    result = {"id": question_id, "drill_answer": e.get("drill_answer"),
              "drill_answer_short": e.get("drill_answer_short"),
              "sources": e.get("sources", []), "sealed_by": e.get("sealed_by"),
              "checks": checks}

    if (e.get("sealed_by") or "").lower() in VENDOR_SEALERS:
        checks.append({"check": f"vendor_declared:{e.get('sealed_by')}", "pass": True,
                       "detail": "vendor-sealed; not cross-verified against dbt docs. "
                                 "Ranks below knowledge/*.md-backed seals."})
        result["seal_valid"] = True
        result["seal_source"] = "vendor_declared"
        return result

    sources = e.get("sources") or []
    if not sources:
        checks.append({"check": "has_sources", "pass": False, "detail": "empty sources list"})
        result["seal_valid"] = False
        return result

    keywords = _keywords_from_rationale(" ".join(
        str(e.get(k) or "") for k in
        ("drill_answer_short", "options_analysis", "drill_rationale", "decision_hinge")))
    result["keywords"] = keywords

    for src in sources:
        if src.startswith("knowledge/"):
            note_path = repo.REPO_ROOT / src
            checks.append({"check": f"note_exists:{src}", "pass": note_path.exists()})
            if not note_path.exists() or not deep:
                continue
            content = note_path.read_text()
            if m := re.search(r"\*\*Verified:\*\*\s+(\d{4}-\d{2}-\d{2})", content):
                age = repo.days_since(m.group(1))
                checks.append({"check": f"note_freshness:{src}", "pass": age <= 180,
                               "detail": f"note Verified {age} days ago"})
            cited = [u.rstrip(").,;") for u in re.findall(r"https?://[^\s\)\]]+", content)
                     if any(h in u for h in exam_config.AUTHORITATIVE_HOSTS)]
            for url in list(dict.fromkeys(cited))[:6]:
                _kw_check(url, keywords, checks)
        elif src.startswith("http"):
            checks.append({"check": f"source_is_url:{src[:70]}", "pass": True})
            if deep:
                _kw_check(src, keywords, checks)
        else:
            checks.append({"check": f"source_unknown_shape:{src[:70]}", "pass": False})

    result["seal_valid"] = _compute_seal_valid(checks)
    return result


def _compute_seal_valid(checks: list[dict]) -> bool:
    if not checks:
        return False
    structural = [c for c in checks if not c["check"].startswith("keywords_in:")]
    keyword = [c for c in checks if c["check"].startswith("keywords_in:")]
    if not all(c["pass"] for c in structural):
        return False
    return not (keyword and not any(c["pass"] for c in keyword))


def _kw_check(url: str, keywords: list[str], checks: list[dict]) -> None:
    ch = cache_check(url)
    if not ch.get("cached"):
        checks.append({"check": f"cache_miss:{url[:70]}", "pass": False,
                       "detail": "URL not in sources/cache/_index.json — run "
                                 "cache_fetch on it, then re-verify."})
        return
    p = repo.REPO_ROOT / ch["path"]
    if not p.exists():
        checks.append({"check": f"cache_file_missing:{url[:70]}", "pass": False})
        return
    text = p.read_text().lower()
    matched = [k for k in keywords if k.lower() in text]
    checks.append({"check": f"keywords_in:{url[:70]}",
                   "pass": len(matched) >= max(2, len(keywords) // 3),
                   "matched": matched,
                   "unmatched": [k for k in keywords if k not in matched],
                   "cache_age_days": ch.get("age_days")})


# Editorial filler and exam-prose words that rarely appear verbatim in dbt docs.
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "into", "onto", "upon", "when",
    "then", "than", "need", "must", "only", "also", "which", "what", "where", "have",
    "been", "being", "more", "less", "most", "best", "some", "such", "just", "like",
    "over", "under", "after", "before", "without", "during", "across", "between",
    "your", "yours", "their", "them", "they", "these", "those", "would", "could",
    "should", "about", "above", "again", "against", "because", "below", "does",
    "each", "further", "here", "itself", "other", "same", "there", "through",
    "very", "while", "doing", "having",
    "wrong", "right", "valid", "invalid", "scope", "quality", "fully", "really",
    "actually", "solves", "addresses", "provides", "requires", "supports", "enables",
    "native", "managed", "fresh", "stale", "proper", "reuse", "reusable", "distinct",
    "direct", "directly", "clearly", "explicit", "implicit", "typical", "common",
    "various", "additional", "aligned", "specifically", "primarily", "essentially",
    "options", "option", "stem", "answer", "correct", "incorrect", "dropdown",
    "large", "small", "medium", "minimum", "maximum", "first", "second", "third",
    "final", "level", "layer", "stage", "phase", "group", "piece", "part",
    "similar", "related", "different", "multiple", "single", "appropriate",
    "individual", "seamless", "comprehensive", "configurable", "detailed",
}


def _keywords_from_rationale(rationale: str) -> list[str]:
    """Rank the decisive terms in a sealed rationale, product anchors last."""
    text = re.sub(r"\\u[0-9a-fA-F]{4}", " ", rationale or "")
    tokens = re.findall(r"\b[a-z][a-z0-9_\-]{4,}\b", text.lower())
    counts = Counter(t for t in tokens if t not in _STOP)
    ranked = sorted(counts.items(),
                    key=lambda kv: (kv[0] in DBT_ANCHORS, -kv[1], -len(kv[0])))
    return [t for t, _ in ranked[:8]]


def _covers(keyword: str, reasoning: str, reasoning_words: set[str]) -> bool:
    """Did the learner express this idea, allowing for ordinary word endings?"""
    if keyword in reasoning:
        return True
    root = keyword[:6]
    return len(root) >= 6 and any(w.startswith(root) for w in reasoning_words)


def score_reasoning(keywords: list[str], user_reasoning: str) -> dict:
    """Split keywords into scored concepts and unscored product-name anchors.

    Naming the feature is not evidence of understanding, so anchors are excluded from
    the coverage ratio that decides `right_answer_right_reasoning`.
    """
    lowered = (user_reasoning or "").lower()
    words = set(re.findall(r"[a-z][a-z0-9_\-]+", lowered))
    covered = [k for k in keywords if _covers(k, lowered, words)]
    missed = [k for k in keywords if k not in covered]
    concepts = [k for k in keywords if k not in DBT_ANCHORS]
    hit = [k for k in concepts if k in covered]
    ratio = len(hit) / len(concepts) if concepts else float(bool(covered))
    return {"covered": covered, "missed": missed, "concepts": concepts,
            "concept_coverage": round(ratio, 2)}


@mcp.tool()
def verify_all(deep: bool = False, track: Optional[str] = None,
               domain: Optional[str] = None, summary_only: bool = True) -> dict:
    """Sweep every sealed question; report seal integrity."""
    pool = [q for q in repo.load_index()["questions"] if q.get("verified")]
    if track:
        pool = [q for q in pool if exam_config.track_of(q.get("domain")) == track]
    if domain:
        pool = [q for q in pool if q.get("domain") == domain]

    valid, problems, failing_ids = 0, [], []
    for q in pool:
        r = verify_seal(q["id"], deep=deep)
        if r.get("seal_valid"):
            valid += 1
            continue
        failing_ids.append(q["id"])
        if not summary_only:
            problems.append({"id": q["id"], "domain": q.get("domain"),
                             "checks_failed": [c for c in r.get("checks", [])
                                               if not c.get("pass")]})
    out = {"total_sealed": len(pool), "seal_valid": valid,
           "seal_invalid": len(failing_ids), "mode": "deep" if deep else "shallow"}
    if summary_only:
        out["failing_ids"] = failing_ids[:20]
        out["truncated"] = len(failing_ids) > 20
    else:
        out["problems"] = problems
    return out


# ---------------------------------------------------------------- AUTHORING PIPELINE

@mcp.tool()
def item_gate(path: Optional[str] = None, item: Optional[dict] = None) -> dict:
    """Run the anti-hallucination authoring gate over candidate items.

    Pass `path` to a JSON file (repo-relative, absolute, or a bare filename inside
    question-bank/authored/) or an inline `item`. Returns each item's verdict with fatal
    failures and warnings, plus the batch's key-position balance.

    This is the only admission standard for the bank — `authored_ingest` re-runs it.
    """
    return pipeline.gate(path=path, item=item)


@mcp.tool()
def bank_audit() -> dict:
    """Run the reusable quality checks over every sealed item already in the bank."""
    return pipeline.bank_audit()


@mcp.tool()
def authored_ingest(write: bool = False, force: bool = False) -> dict:
    """Admit gate-passing authored items from question-bank/authored/ into the bank.

    Dry run by default. `force` re-admits an item whose stem already exists.
    """
    return pipeline.authored_ingest(write=write, force=force)


@mcp.tool()
def coverage_report(track: Optional[str] = None, domain: Optional[str] = None) -> dict:
    """Blueprint coverage: how many items sit under each task versus target.

    Targets are derived from task count, not from a percentage weight — dbt does not
    publish section weights. `author_here` lists tasks at least 2 items short.
    """
    return pipeline.coverage(track=track, domain=domain)


@mcp.tool()
def balance_keys(write: bool = False) -> dict:
    """Spread the correct answer across option letters in the authored drafts.

    Dry run by default. Moves every letter-keyed field with the key, so evidence stays
    attached to the option it was written for. Skips non-letter formats.
    """
    return pipeline.balance_keys(write=write)


@mcp.tool()
def difficulty_observed(write: bool = False) -> dict:
    """Score difficulty from real attempt results instead of the structural proxy.

    Dry run by default, and deliberately starved: a question needs at least 2 attempts
    before its result counts as a measurement rather than a coin flip.
    """
    return pipeline.difficulty_observed(write=write)


@mcp.tool()
def defect_scan(defect: Optional[str] = None, provenance: Optional[str] = None,
                include_retired: bool = False, limit: int = 25) -> dict:
    """Rank servable bank items by authoring defect, worst first — the rewrite queue.

    `defect` one of: key_longest, long_key, lexical_giveaway, odd_one_out, unverifiable
    (default: all). `provenance` one of: authored, official, community, practice.

    Prefer `key_longest`: "pick the longest option and read nothing" is the single most
    reliable exploit of a badly authored multiple-choice item.
    """
    return pipeline.defect_scan(defect=defect, provenance=provenance,
                                include_retired=include_retired, limit=limit)


@mcp.tool()
def retire_superseded(mapping: dict, reason: str, write: bool = False) -> dict:
    """Retire rewritten originals and point each at its replacement. Dry run by default.

    `mapping` is {original_id: replacement_id}. Retired items stay in the bank for
    provenance and are filtered out of drill_pick. Refuses to write if any replacement
    is missing, unsealed, or itself retired.
    """
    return pipeline.retire_superseded(mapping=mapping, reason=reason, write=write)


# ---------------------------------------------------------------- PROGRESS

@mcp.tool()
def progress_summary(include_markdown: bool = False) -> dict:
    """Compact scorecard + coverage. Pass `include_markdown=true` for raw scorecard.md."""
    asked = repo.load_asked_log()
    questions = repo.load_index()["questions"]
    sealed = [q for q in questions if q.get("verified") and not q.get("retired")]
    seen = [q for q in sealed if q["id"] in asked]
    by_track: Counter = Counter(exam_config.track_of(q.get("domain")) for q in sealed)
    by_type: Counter = Counter(grading.qtype_of(q) for q in sealed)
    out = {
        "scorecard_by_domain_accuracy": repo.load_scorecard_accuracy(),
        "recent_missed_ids": repo.load_missed_recent(10),
        "sealed_total": len(sealed),
        "sealed_seen": len(seen),
        "sealed_unseen": len(sealed) - len(seen),
        "sealed_by_track": dict(by_track),
        "sealed_by_qtype": dict(by_type),
        "unsealed_total": sum(1 for q in questions if not q.get("verified")),
    }
    if include_markdown:
        out["scorecard_markdown"] = repo.load_scorecard_raw()
    return out


@mcp.tool()
def asked_stats(limit: int = 20) -> dict:
    """Per-question ask-count / accuracy from progress/asked-log.json."""
    items = [{"id": qid, "count": v.get("count", 0), "correct": v.get("correct", 0),
              "last_asked": v.get("last_asked"), "last_correct": v.get("last_correct")}
             for qid, v in repo.load_asked_log().items()]
    items.sort(key=lambda x: (-x["count"], x["id"]))
    total_asks = sum(i["count"] for i in items)
    total_correct = sum(i["correct"] for i in items)
    return {"unique_questions_asked": len(items), "total_ask_events": total_asks,
            "total_correct": total_correct,
            "overall_accuracy_pct": (100 * total_correct // total_asks) if total_asks else 0,
            "top": items[:limit]}


_SESSION_ARTIFACTS = ("asked-log.json", "missed-questions.md", "scorecard.md",
                      "attempts.jsonl")


@mcp.tool()
def session_save(name: str, overwrite: bool = False) -> dict:
    """Snapshot progress/ artifacts into progress/sessions/<name>/<date>/.

    Fails without `overwrite=true` if a snapshot with the same name+date exists.
    """
    if not re.match(r"^[A-Za-z0-9_\-]{1,64}$", name):
        return {"error": "invalid_name",
                "message": "name must be 1-64 chars: letters, digits, '-', '_'."}
    dest = repo.PROGRESS_DIR / "sessions" / name / repo.today_iso()
    if dest.exists() and not overwrite:
        return {"error": "exists", "path": str(dest.relative_to(repo.REPO_ROOT)),
                "fix": "pass overwrite=true to replace, or pick a different name"}
    dest.mkdir(parents=True, exist_ok=True)
    saved: dict[str, int] = {}
    for fname in _SESSION_ARTIFACTS:
        src = repo.PROGRESS_DIR / fname
        if src.exists():
            content = src.read_bytes()
            (dest / fname).write_bytes(content)
            saved[fname] = len(content)
    return {"name": name, "path": str(dest.relative_to(repo.REPO_ROOT)),
            "saved": saved, "total_bytes": sum(saved.values())}


@mcp.tool()
def session_clear(scope: str = "asked", confirm: bool = False) -> dict:
    """Reset progress artifacts. Preview by default; set confirm=true to write.

    scope: 'asked' | 'missed' | 'scorecard' | 'attempts' | 'all'
    """
    paths = {"asked": repo.ASKED_LOG, "missed": repo.MISSED_MD,
             "scorecard": repo.SCORECARD_MD, "attempts": repo.ATTEMPTS_JSONL}
    if scope not in set(paths) | {"all"}:
        return {"error": "invalid_scope", "valid_scopes": sorted(set(paths) | {"all"})}
    targets = list(paths) if scope == "all" else [scope]

    preview = []
    for t in targets:
        p = paths[t]
        preview.append({"scope": t,
                        "path": str(p.relative_to(repo.REPO_ROOT)) if p.exists() else None,
                        "exists": p.exists(),
                        "size_bytes": p.stat().st_size if p.exists() else 0})
    if confirm is not True:
        return {"dry_run": True, "scope": scope, "would_clear": preview,
                "fix": "call again with confirm=true to actually clear"}

    cleared = []
    for t in targets:
        if t == "asked":
            repo.ASKED_LOG.write_text("{}\n")
            cleared.append(t)
        elif t == "missed" and repo.MISSED_MD.exists():
            head, _, _ = repo.MISSED_MD.read_text().partition("## Current queue")
            repo.MISSED_MD.write_text(
                (head or "# Missed questions queue\n\n")
                + "## Current queue\n\n| Question ID | Domain | Date | Detail | Status |\n"
                  "|---|---|---|---|---|\n")
            cleared.append(t)
        elif t == "scorecard" and repo.SCORECARD_MD.exists():
            repo.SCORECARD_MD.write_text(re.sub(
                r"(\|\s*(?:ae|arch)-\d{2}\s*\|[^|]*\|)\s*\d+\s*\|\s*\d+\s*\|[^|]*\|",
                r"\1 0 | 0 | — |", repo.SCORECARD_MD.read_text()))
            cleared.append(t)
        elif t == "attempts" and repo.ATTEMPTS_JSONL.exists():
            repo.ATTEMPTS_JSONL.unlink()
            cleared.append(t)
    return {"cleared": cleared, "scope": scope, "confirmed": True}


@mcp.tool()
def session_summary(range: str = "all") -> dict:
    """On-demand digest of drill activity. range: 'today' | 'week' | 'all'.

    Reads progress/attempts.jsonl (rich) if present, falls back to asked-log.json.
    """
    if range not in ("today", "week", "all"):
        return {"error": "invalid_range", "valid": ["today", "week", "all"]}
    now = datetime.now(timezone.utc)
    cutoff = (now.replace(hour=0, minute=0, second=0, microsecond=0) if range == "today"
              else now - timedelta(days=7) if range == "week" else None)

    attempts = []
    for rec in repo.load_attempts():
        if cutoff:
            try:
                if datetime.fromisoformat(str(rec.get("ts", "")).replace("Z", "+00:00")) < cutoff:
                    continue
            except ValueError:
                continue
        attempts.append(rec)

    if not attempts:
        stats = asked_stats(limit=200)
        return {"range": range, "source": "asked_log (attempts.jsonl empty or missing)",
                "total_attempts": stats["total_ask_events"],
                "total_correct": stats["total_correct"],
                "accuracy_pct": stats["overall_accuracy_pct"],
                "unique_questions": stats["unique_questions_asked"]}

    total = len(attempts)
    correct = sum(1 for a in attempts if a.get("correct"))
    per_domain: dict[str, list[int]] = {}
    per_qtype: dict[str, list[int]] = {}
    for a in attempts:
        for bucket, key in ((per_domain, a.get("domain") or "?"),
                            (per_qtype, a.get("qtype") or "?")):
            bucket.setdefault(key, [0, 0])
            bucket[key][0] += 1
            bucket[key][1] += 1 if a.get("correct") else 0

    def _rollup(b: dict[str, list[int]]) -> dict:
        return {k: {"attempts": n, "correct": c, "accuracy_pct": (100 * c // n) if n else 0}
                for k, (n, c) in b.items()}

    times = [a["answered_ms"] for a in attempts if isinstance(a.get("answered_ms"), int)]
    streak = 0
    for a in reversed(attempts):
        if not a.get("correct"):
            break
        streak += 1

    return {
        "range": range, "source": "attempts.jsonl",
        "total_attempts": total, "total_correct": correct,
        "accuracy_pct": (100 * correct // total) if total else 0,
        "per_domain": _rollup(per_domain),
        "per_qtype": _rollup(per_qtype),
        "verdict_distribution": dict(Counter(a.get("verdict") for a in attempts
                                             if a.get("verdict"))),
        "avg_answered_ms": int(sum(times) / len(times)) if times else None,
        "current_streak_correct": streak,
        "recent_missed": [a["qid"] for a in reversed(attempts) if not a.get("correct")][:5],
    }


# ---------------------------------------------------------------- QUESTION LOOKUP

@mcp.tool()
def question_full(question_id: str, include_answer: bool = False) -> dict:
    """Fetch a question's rendered body.

    By default returns the drillable rendering (no key). Pass `include_answer=true` for
    the sealed answer + rationale + traps (review mode).
    """
    e = repo.find_question(question_id)
    if not e:
        return {"error": f"question {question_id} not found"}
    return {
        "id": question_id, "domain": e.get("domain"),
        "track": exam_config.track_of(e.get("domain")),
        "blueprint_task": e.get("blueprint_task"),
        "qtype": grading.qtype_of(e), "status": e["status"],
        "verified": e.get("verified", False),
        "body": repo.entry_full(question_id) if include_answer
        else repo.entry_stem_only(question_id),
    }


# ---------------------------------------------------------------- INGESTION

_INGEST_WORKFLOW = [
    "1. ingest_scan(track=..., domain=...) — list unsealed questions awaiting a verdict",
    "2. For each pending question, in order:",
    "   a. question_full(question_id) — read the verbatim stem, options, and format",
    "   b. cache_check(url) BEFORE any fetch; cache_fetch only on a miss or stale entry",
    "   c. topic_search(concept) OR concept_lookup(name) — find the backing "
    "knowledge/*.md note; if none exists, write it first",
    "   d. ingest_seal(question_id, drill_answer, drill_answer_short, topics, "
    "verified_source, ...)",
    "3. After the batch: run scripts/build_topic_index.py to refresh _topics.json / _tags.json.",
]

_INGEST_RULES = [
    "Never accept a claimed answer without independently reasoning it through against "
    "docs.getdbt.com. Third-party dbt practice material is frequently wrong.",
    "drill_answer format depends on qtype. Letters ('B', 'A,C') for multiple_choice / "
    "multiple_response / domc. For fill_in_blank pass the canonical string and list "
    "variants in accepted_answers. For matching pass 'left -> right' pairs. For "
    "build_list pass the ordered item ids. For hotspot pass the target ids.",
    "drill_answer_short is the ONE-LINE rationale shown after a wrong answer — name the "
    "decisive dbt behaviour, not the option letter.",
    "drill_rationale (optional, multi-paragraph) is the FULL sealed explanation.",
    "distractor_traps (optional, {letter: why-wrong}) is what makes pattern learning work.",
    "topics: at least one entry linking into knowledge/. Either a known topic ID, an "
    "existing 'knowledge/...md' path, or a planned id matching "
    "'<track>/<NN>-<slug>/<note-slug>'.",
    "verified_source: an existing 'knowledge/...md' file OR a full https:// URL "
    "(docs.getdbt.com preferred).",
    "status: 'verified' (backed by dbt docs) | 'concept-only' (right principle, no "
    "direct doc match yet) | 'disputed' (the source's claimed answer looks wrong).",
    f"seal_confidence: 0-100. >= {exam_config.SEAL_CONFIDENCE_FLOOR} recommended for "
    "drill-pool inclusion.",
]


@mcp.tool()
def ingest_help() -> dict:
    """Return the canonical sealing workflow + rules. Call this FIRST when sealing."""
    return {
        "purpose": "Seal dbt certification questions into drill-ready form.",
        "tracks": {t: f["name"] for t, f in exam_config.EXAM_FACTS.items()},
        "workflow": _INGEST_WORKFLOW,
        "rules_ingest_seal_enforces": _INGEST_RULES,
        "question_formats": exam_config.QUESTION_TYPES,
        "refusal_codes": {
            "not_found": "question_id doesn't exist in index.json.",
            "invalid_status": "status must be 'verified' | 'concept-only' | 'disputed'.",
            "invalid_drill_answer": "the answer does not parse in this question's format.",
            "empty_rationale": "drill_answer_short cannot be empty.",
            "empty_topics": "every sealed question must cite at least one concept note.",
            "invalid_topic": "topic must be an id in _topics.json, an existing "
                             "knowledge/*.md path, or a valid planned id.",
            "invalid_verified_source": "verified_source must be an existing "
                                       "knowledge/*.md file OR an https:// URL.",
        },
        "invariants": [
            "Dumps in question-bank/raw/ are read-only. Never edit them.",
            "index.json is written only by the ingest scripts and this tool.",
            "A sealed entry with status != 'disputed' AND verified=True enters the "
            "drill_pick pool.",
            "Disputed entries are excluded from drill_pick automatically.",
        ],
        "next_step": "Call ingest_scan() to list pending questions.",
    }


@mcp.tool()
def ingest_scan(track: Optional[str] = None, domain: Optional[str] = None,
                limit: int = 30) -> dict:
    """List pending (unsealed) questions from question-bank/index.json. Read-only."""
    questions = repo.load_index()["questions"]
    pending = []
    for q in questions:
        if q.get("verified"):
            continue
        if track and exam_config.track_of(q.get("domain")) != track:
            continue
        if domain and q.get("domain") != domain:
            continue
        pending.append({
            "id": q["id"],
            "track": exam_config.track_of(q.get("domain")),
            "domain": q.get("domain"),
            "domain_confidence": q.get("domain_confidence"),
            "blueprint_task": q.get("blueprint_task"),
            "qtype": grading.qtype_of(q),
            "status": q.get("status"),
            "first_line": (str(q.get("stem") or "").strip().splitlines() or [""])[0][:180],
        })
    pending.sort(key=lambda p: (p["domain"] or "zz",
                                -(p.get("domain_confidence") or 0), p["id"]))
    return {
        "total_in_index": len(questions),
        "sealed_count": sum(1 for q in questions if q.get("verified")),
        "pending_count": sum(1 for q in questions if not q.get("verified")),
        "filters": {"track": track, "domain": domain},
        "pending": pending[:limit],
        "truncated": len(pending) > limit,
        "next_step": "For each pending qid: question_full(qid) -> research docs.getdbt.com "
                     "-> ingest_seal(...). If unsure, call ingest_help().",
    }


_TOPIC_PLANNED_RE = re.compile(
    r"^(ae|arch)/\d{2}-[a-z][a-z0-9\-]+/[a-z][a-z0-9\-]+$")


def _resolve_topic(t: str) -> tuple[Optional[str], Optional[str]]:
    """Return (resolved_path, error). Accepts topic ID, knowledge/*.md path, planned id."""
    known = repo.load_topics()
    if t in known:
        return known[t].get("path"), None
    if t.startswith("knowledge/") and (repo.REPO_ROOT / t).exists():
        return t, None
    if _TOPIC_PLANNED_RE.match(t):
        return f"knowledge/{t}.md", None
    return None, (f"unknown topic: {t!r} (not an id in _topics.json, not an existing "
                  "knowledge/*.md, not a valid planned id like "
                  "'ae/04-testing-and-debugging/unit-tests')")


@mcp.tool()
def ingest_seal(
    question_id: str,
    drill_answer: Any,
    drill_answer_short: str,
    topics: list[str],
    verified_source: str,
    drill_rationale: str = "",
    distractor_traps: Optional[dict] = None,
    options_analysis: str = "",
    accepted_answers: Optional[list[str]] = None,
    seal_confidence: Optional[int] = None,
    status: str = "verified",
    notes: str = "",
    domain: Optional[str] = None,
    blueprint_task: Optional[str] = None,
) -> dict:
    """Promote an unsealed stub to a drill-ready sealed question.

    Refuses unless:
      - status is 'verified' | 'concept-only' | 'disputed'
      - drill_answer parses in the question's own format (letters for choice formats,
        pairs for matching, ordered items for build_list, and so on)
      - drill_answer_short is non-empty
      - topics is non-empty and each entry resolves to a real or planned note
      - verified_source is an existing 'knowledge/*.md' OR an https:// URL
    """
    e = repo.find_question(question_id)
    if not e:
        return {"error": "not_found", "message": f"question {question_id} not found",
                "fix": "Run ingest_scan to list valid IDs."}
    if status not in repo.VALID_STATUS - {"unsealed"}:
        return {"error": "invalid_status", "message": f"invalid status: {status}",
                "fix": "Use 'verified', 'concept-only', or 'disputed'."}
    if not (drill_answer_short or "").strip():
        return {"error": "empty_rationale",
                "message": "drill_answer_short cannot be empty",
                "fix": "One line naming the decisive dbt behaviour, e.g. 'An ephemeral "
                       "model is inlined as a CTE, so it is never built in the warehouse "
                       "and cannot be selected directly.'"}
    if not topics:
        return {"error": "empty_topics", "message": "topics cannot be empty",
                "fix": "Pass at least one topic id, knowledge/*.md path, or planned id."}

    resolved_topics = []
    for t in topics:
        path, err = _resolve_topic(t)
        if err:
            return {"error": "invalid_topic", "message": err,
                    "fix": "Call topic_search or concept_lookup, or write the note first."}
        resolved_topics.append(path)

    src_ok = verified_source.startswith("https://") or (
        verified_source.startswith("knowledge/")
        and (repo.REPO_ROOT / verified_source).exists())
    if not src_ok:
        return {"error": "invalid_verified_source",
                "message": f"verified_source must be an existing 'knowledge/*.md' or an "
                           f"https:// URL, got: {verified_source}",
                "fix": "Point at an existing note or cite a docs.getdbt.com URL."}

    # Validate the key by grading it against itself in the question's own format.
    candidate = {**e, "drill_answer": drill_answer}
    if accepted_answers:
        candidate["accepted_answers"] = accepted_answers
    try:
        check = grading.grade(candidate, drill_answer)
        if not check["correct"]:
            raise grading.AnswerFormatError(
                f"the sealed key does not grade as correct against itself: {check['detail']}")
    except grading.AnswerFormatError as ex:
        return {"error": "invalid_drill_answer", "message": str(ex),
                "qtype": grading.qtype_of(e),
                "fix": exam_config.QUESTION_TYPES[grading.qtype_of(e)]["answer_shape"]}

    if domain and domain in repo.VALID_DOMAINS:
        e["domain"] = domain
    if blueprint_task:
        e["blueprint_task"] = blueprint_task

    e.update({
        "status": status,
        "verified": status != "disputed",
        "topics": resolved_topics,
        "drill_answer": drill_answer,
        "drill_answer_short": drill_answer_short.strip(),
        "drill_rationale": drill_rationale.strip() or e.get("drill_rationale"),
        "distractor_traps": distractor_traps if distractor_traps is not None
        else e.get("distractor_traps"),
        "options_analysis": options_analysis.strip() or e.get("options_analysis"),
        "accepted_answers": accepted_answers or e.get("accepted_answers"),
        "sources": [verified_source],
        "sealed_at": repo.today_iso(),
        "sealed_by": e.get("sealed_by") or "agent",
        "seal_confidence": seal_confidence if seal_confidence is not None
        else e.get("seal_confidence"),
        "notes": (notes or e.get("notes") or "").strip(),
    })
    repo.upsert_question(e)

    low_confidence = (e.get("seal_confidence") or 0) < exam_config.SEAL_CONFIDENCE_FLOOR
    return {
        "sealed": question_id, "status": status, "verified": e["verified"],
        "qtype": grading.qtype_of(e), "drill_answer": e["drill_answer"],
        "sources": e["sources"], "topics": resolved_topics,
        "seal_confidence": e.get("seal_confidence"),
        "warning": (f"seal_confidence below {exam_config.SEAL_CONFIDENCE_FLOOR} — append "
                    "this id to progress/needs-review.md") if low_confidence else None,
        "next_step": "ingest_scan for the next pending qid, or drill_pick to try it live.",
    }


@mcp.tool()
def ingest_dispute(question_id: str, reason: str) -> dict:
    """Mark a question disputed (our research contradicts the source's claimed answer).

    Sets status='disputed', verified=false; drill_pick will skip it.
    """
    e = repo.find_question(question_id)
    if not e:
        return {"error": "not_found", "message": f"question {question_id} not found"}
    if not (reason or "").strip():
        return {"error": "empty_reason", "message": "reason cannot be empty"}
    e.update({"status": "disputed", "verified": False,
              "notes": ((e.get("notes") or "") + " | DISPUTED: " + reason).strip(" |")})
    repo.upsert_question(e)
    return {"disputed": question_id, "reason": reason}
