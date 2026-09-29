"""Integration smoke test: exercise every tool without going through MCP transport.

Snapshots and restores question-bank/index.json and progress/ so a run leaves no trace.
Read-only tools are always called; mutating tools run against a temporary fixture
question that is removed afterwards.

Run:  python3 mcp-server/tests/smoke.py
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from study_agent_mcp import repo, server  # noqa: E402

PASS, FAIL = [], []

FIXTURE_ID = "Q-AU-DBTAE-999"
FIXTURE = {
    "id": FIXTURE_ID,
    "source": "smoke-test",
    "stem": "A team needs the transformation inlined into its consumers rather than "
            "built as an object in the warehouse. Which materialization does this?",
    "option_texts": {"A": "table", "B": "view", "C": "ephemeral", "D": "incremental"},
    "drill_answer": "C",
    "drill_answer_short": "An ephemeral model is inlined as a CTE, so nothing is built.",
    "drill_rationale": "Ephemeral models are interpolated into downstream models.",
    "distractor_traps": {"A": "T2: builds an object", "B": "T2: builds an object",
                         "D": "T3: right family, still builds an object"},
    "qtype": "multiple_choice",
    "domain": "ae-02",
    "blueprint_task": "2.1",
    "difficulty_estimate": "L2",
    "topics": ["knowledge/ae/02-materializations-and-performance/materializations.md"],
    "sources": ["https://docs.getdbt.com/docs/build/materializations"],
    "verified": True,
    "status": "verified",
    "sealed_by": "smoke_test",
    "sealed_at": repo.today_iso(),
    "seal_confidence": 90,
}


def check(name, fn, predicate=lambda r: r is not None):
    try:
        result = fn()
        if predicate(result):
            PASS.append(name)
        else:
            FAIL.append((name, f"predicate failed on {str(result)[:160]}"))
        return result
    except Exception:  # noqa: BLE001
        FAIL.append((name, traceback.format_exc(limit=2).strip().splitlines()[-1]))
        return None


def no_error(r):
    return isinstance(r, dict) and "error" not in r


def main() -> int:
    backup = tempfile.mkdtemp(prefix="studyagent-smoke-")
    originals = {}
    for path in (repo.INDEX_JSON, repo.ASKED_LOG, repo.SCORECARD_MD,
                 repo.MISSED_MD, repo.ATTEMPTS_JSONL):
        if path.exists():
            dest = pathlib.Path(backup) / path.name
            shutil.copy2(path, dest)
            originals[path] = dest

    try:
        # ---- read-only, no fixture needed -------------------------------------
        check("exam_facts", lambda: server.exam_facts(),
              lambda r: "tracks" in r and "ae" in r["tracks"])
        check("exam_facts names unpublished items",
              lambda: server.exam_facts(),
              lambda r: len(r["not_published_by_dbt_labs"]) >= 3)
        check("drill_help", lambda: server.drill_help(),
              lambda r: "workflow" in r and len(r["question_formats"]) == 7)
        check("ingest_help", lambda: server.ingest_help(), no_error)
        check("ingest_scan", lambda: server.ingest_scan(), no_error)
        check("cache_check (miss)", lambda: server.cache_check("https://example.invalid/x"),
              lambda r: r["cached"] is False)
        check("cache_stats", lambda: server.cache_stats(),
              lambda r: "total_entries" in r)
        check("topic_search", lambda: server.topic_search("incremental"),
              lambda r: isinstance(r, list))
        check("concept_lookup", lambda: server.concept_lookup("snapshot"),
              lambda r: "hits" in r)
        check("progress_summary", lambda: server.progress_summary(), no_error)
        check("asked_stats", lambda: server.asked_stats(), no_error)
        check("session_summary", lambda: server.session_summary(range="all"), no_error)
        check("coverage_report", lambda: server.coverage_report(track="ae"),
              lambda r: "domains" in r)
        check("bank_audit", lambda: server.bank_audit(), lambda r: "audited" in r)
        check("defect_scan", lambda: server.defect_scan(), lambda r: "scanned" in r)
        check("verify_all", lambda: server.verify_all(), lambda r: "total_sealed" in r)
        check("domain_briefing (ae-02)", lambda: server.domain_briefing("ae-02"),
              lambda r: "topics" in r or "error" in r)
        check("domain_briefing rejects junk domain",
              lambda: server.domain_briefing("nope-99"), lambda r: "error" in r)
        check("session_clear dry run",
              lambda: server.session_clear(scope="asked"), lambda r: r.get("dry_run"))

        # ---- guardrails --------------------------------------------------------
        server._PROTOCOL_STATE["drill_help_seen"] = False
        check("drill_pick blocked before drill_help",
              lambda: server.drill_pick(count=1),
              lambda r: isinstance(r, dict) and r.get("guardrail") == "PROTOCOL_NOT_PRIMED")
        server.drill_help()
        check("drill_pick blocks batches",
              lambda: server.drill_pick(count=5),
              lambda r: isinstance(r, dict) and r.get("guardrail") == "BATCH_NOT_ALLOWED")

        # ---- mutating, against the fixture -------------------------------------
        idx = repo.load_index()
        idx["questions"] = [q for q in idx["questions"] if q["id"] != FIXTURE_ID]
        idx["questions"].append(dict(FIXTURE))
        repo.save_index(idx)

        picked = check("drill_pick returns the fixture",
                       lambda: server.drill_pick(count=1, domain="ae-02", mode="random"),
                       lambda r: isinstance(r, list) and len(r) == 1)
        if picked:
            body = picked[0]["question"]
            if "ephemeral" in body and "C." in body:
                PASS.append("drill_pick renders options")
            else:
                FAIL.append(("drill_pick renders options", body[:120]))
            if "Answer:" in body or picked[0].get("drill_answer"):
                FAIL.append(("drill_pick hides the key", "key leaked into the payload"))
            else:
                PASS.append("drill_pick hides the key")

        check("drill_grade refuses without override",
              lambda: server.drill_grade(FIXTURE_ID, "C"),
              lambda r: r.get("guardrail") == "REASONING_REQUIRED")
        check("drill_why blocked before the question is attempted",
              lambda: server.drill_why(FIXTURE_ID),
              lambda r: r.get("guardrail") == "NOT_YET_ATTEMPTED"
              and "drill_answer" not in r)
        check("drill_grade_reasoned rejects thin reasoning",
              lambda: server.drill_grade_reasoned(FIXTURE_ID, "C", "yes"),
              lambda r: r.get("guardrail") == "REASONING_TOO_SHORT")
        check("drill_grade_reasoned grades a correct answer",
              lambda: server.drill_grade_reasoned(
                  FIXTURE_ID, "C",
                  "ephemeral models are inlined as a CTE so nothing is built"),
              lambda r: r.get("correct") is True
              and r.get("verdict", "").startswith("right_answer"))
        check("drill_grade_reasoned grades a wrong answer",
              lambda: server.drill_grade_reasoned(
                  FIXTURE_ID, "A", "I think it creates a physical table in the warehouse"),
              lambda r: r.get("correct") is False)
        check("drill_grade_reasoned reports a format error",
              lambda: server.drill_grade_reasoned(
                  FIXTURE_ID, "C,D", "both of these avoid building anything at all"),
              lambda r: r.get("error") == "ANSWER_FORMAT")
        check("drill_why", lambda: server.drill_why(FIXTURE_ID),
              lambda r: r.get("drill_answer") == "C")
        check("drill_hint does not leak the key",
              lambda: server.drill_hint(FIXTURE_ID),
              lambda r: "ephemeral" not in json.dumps(r).lower())
        check("drill_explain returns a glossary",
              lambda: server.drill_explain(FIXTURE_ID),
              lambda r: r.get("glossary_hits_count", 0) > 0)
        check("question_full hides the key by default",
              lambda: server.question_full(FIXTURE_ID),
              lambda r: "Answer:" not in r.get("body", ""))
        check("question_full reveals with include_answer",
              lambda: server.question_full(FIXTURE_ID, include_answer=True),
              lambda r: "**Answer:** C" in r.get("body", ""))
        check("verify_seal (shallow)", lambda: server.verify_seal(FIXTURE_ID),
              lambda r: "seal_valid" in r)
        check("ingest_seal rejects an empty rationale",
              lambda: server.ingest_seal(FIXTURE_ID, "C", "", ["ae/02-x/y"],
                                         "https://docs.getdbt.com/x"),
              lambda r: r.get("error") == "empty_rationale")
        check("ingest_seal rejects an unknown topic",
              lambda: server.ingest_seal(FIXTURE_ID, "C", "ok", ["not-a-topic"],
                                         "https://docs.getdbt.com/x"),
              lambda r: r.get("error") == "invalid_topic")
        check("ingest_seal rejects a non-official-shaped source",
              lambda: server.ingest_seal(
                  FIXTURE_ID, "C", "ok",
                  ["ae/02-materializations-and-performance/materializations"], "see the docs"),
              lambda r: r.get("error") == "invalid_verified_source")
        check("ingest_seal accepts a well-formed seal",
              lambda: server.ingest_seal(
                  FIXTURE_ID, "C", "Ephemeral is inlined as a CTE.",
                  ["ae/02-materializations-and-performance/materializations"],
                  "https://docs.getdbt.com/docs/build/materializations",
                  seal_confidence=85),
              lambda r: r.get("sealed") == FIXTURE_ID)
        check("ingest_dispute", lambda: server.ingest_dispute(FIXTURE_ID, "smoke test"),
              lambda r: r.get("disputed") == FIXTURE_ID)

    finally:
        for path, saved in originals.items():
            shutil.copy2(saved, path)
        for path in (repo.INDEX_JSON, repo.ASKED_LOG, repo.SCORECARD_MD,
                     repo.MISSED_MD, repo.ATTEMPTS_JSONL):
            if path not in originals and path.exists():
                path.unlink()
        shutil.rmtree(backup, ignore_errors=True)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed\n")
    for name in PASS:
        print(f"  ok    {name}")
    for name, why in FAIL:
        print(f"  FAIL  {name}: {why}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
