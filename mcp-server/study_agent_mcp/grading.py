"""Answer normalization and grading for all six dbt exam question formats.

The AIP-C01 predecessor only ever graded letter sets, because AWS exams are
multiple-choice and multiple-response. dbt exams also use fill-in-the-blank,
matching, hotspot, build-list, and Discrete Option Multiple Choice.
  [source: getdbt.com/dbt-certification FAQ — accessed 2026-09-29]

Each format has a `normalize` (accept what a human would plausibly type) and a
`grade` (compare against the sealed answer). Grading returns a uniform dict so
the drill tools never branch on qtype themselves:

    {"correct": bool, "score": 0.0-1.0, "detail": str, "expected": ..., "given": ...}

`score` is fractional only for formats that dbt itself can award partial credit
on in principle (matching, hotspot, build_list). It is used for coaching
feedback, never to flip `correct` — the bank records a binary outcome because
dbt scores one point for a correct answer and zero otherwise.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from .exam_config import NON_LETTER_TYPES, QUESTION_TYPES

# A standalone option token, not any capital letter in the sentence. Without the word
# boundaries, "Answer: B" parses as A, B, E, N, R, S, W and a correct reply is rejected.
LETTER_RE = re.compile(r"\b([A-F])\b")


class AnswerFormatError(ValueError):
    """The submitted answer cannot be read as the question's format."""


# --------------------------------------------------------------------------- #
# Shared normalization
# --------------------------------------------------------------------------- #

def letters(raw: Any) -> set[str]:
    """Option letters A-F in a string or iterable. 'a, c', ['A','C'] and 'Answer: B' work."""
    if isinstance(raw, (list, tuple, set)):
        raw = ",".join(str(x) for x in raw)
    return set(LETTER_RE.findall(str(raw or "").upper()))


def normalize_text(raw: Any) -> str:
    """Casefold, strip accents and punctuation noise, collapse whitespace.

    Fill-in-the-blank answers on a dbt exam are things like `is_incremental()`,
    `dbt run --select`, or `ephemeral`. Candidates type them inconsistently, so
    trailing parentheses, surrounding backticks/quotes, and a leading `dbt ` are
    all tolerated by the accepted-answer list rather than by guessing here.
    """
    s = unicodedata.normalize("NFKD", str(raw or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.strip().strip("`'\"").casefold()
    s = re.sub(r"\s+", " ", s)
    return s


def _seq(raw: Any) -> list[str]:
    """Read an ordered answer as a list of normalized item ids."""
    if isinstance(raw, (list, tuple)):
        return [normalize_text(x) for x in raw if str(x).strip()]
    parts = re.split(r"\s*(?:,|->|→|;|\n|\d+\.\s)\s*", str(raw or ""))
    return [normalize_text(p) for p in parts if p.strip()]


def _pairs(raw: Any) -> dict[str, str]:
    """Read a matching answer as {left: right}. Accepts a dict or 'a -> b, c -> d'."""
    if isinstance(raw, dict):
        return {normalize_text(k): normalize_text(v) for k, v in raw.items()}
    out: dict[str, str] = {}
    for chunk in re.split(r"\s*(?:,|;|\n)\s*", str(raw or "")):
        if not chunk.strip():
            continue
        m = re.split(r"\s*(?:->|=>|→|:|=)\s*", chunk, maxsplit=1)
        if len(m) != 2:
            raise AnswerFormatError(
                f"cannot read {chunk!r} as a pair; use 'left -> right' or a JSON object")
        out[normalize_text(m[0])] = normalize_text(m[1])
    return out


def _yes_no(raw: Any) -> dict[str, str]:
    """Read a DOMC answer as {LETTER: 'Y'|'N'}. Accepts 'A:Y, B:N' or a dict."""
    src = raw if isinstance(raw, dict) else None
    if src is None:
        src = {}
        for chunk in re.split(r"\s*(?:,|;|\n)\s*", str(raw or "")):
            if not chunk.strip():
                continue
            m = re.split(r"\s*(?::|=|->)\s*", chunk, maxsplit=1)
            if len(m) != 2:
                raise AnswerFormatError(
                    f"cannot read {chunk!r} as a DOMC verdict; use 'A:Y, B:N'")
            src[m[0]] = m[1]
    out: dict[str, str] = {}
    for k, v in src.items():
        key = str(k).strip().upper()[:1]
        val = str(v).strip().upper()[:1]
        if key and val in ("Y", "N"):
            out[key] = val
        elif key:
            raise AnswerFormatError(f"DOMC verdict for {key} must be Y or N, got {v!r}")
    return out


# --------------------------------------------------------------------------- #
# Per-format graders
# --------------------------------------------------------------------------- #

def _grade_letters(expected: Any, given: Any, exact_set: bool) -> dict:
    exp, got = letters(expected), letters(given)
    if not got:
        raise AnswerFormatError("no answer letter found; reply with a letter such as 'B'")
    if not exact_set and len(got) > 1:
        raise AnswerFormatError(
            f"this is a single-answer question but {sorted(got)} were given")
    correct = exp == got
    hit, extra, missed = exp & got, got - exp, exp - got
    score = len(hit) / len(exp | got) if (exp | got) else 0.0
    detail = "exact match" if correct else (
        f"missed {sorted(missed) or '—'}, extra {sorted(extra) or '—'}")
    return {"correct": correct, "score": round(score, 2), "detail": detail,
            "expected": ",".join(sorted(exp)), "given": ",".join(sorted(got))}


def _grade_fill_in_blank(question: dict, given: Any) -> dict:
    accepted = question.get("accepted_answers") or []
    if not accepted:
        accepted = [question.get("drill_answer", "")]
    norm_accepted = [normalize_text(a) for a in accepted if str(a).strip()]
    got = normalize_text(given)
    if not got:
        raise AnswerFormatError("empty answer")
    correct = got in norm_accepted
    detail = ("matches an accepted answer" if correct
              else f"not in accepted set ({len(norm_accepted)} variant(s) allowed)")
    return {"correct": correct, "score": 1.0 if correct else 0.0, "detail": detail,
            "expected": accepted[0], "given": str(given).strip()}


def _grade_matching(question: dict, given: Any) -> dict:
    exp = _pairs(question.get("drill_answer"))
    got = _pairs(given)
    if not exp:
        raise AnswerFormatError("question has no matching key sealed")
    hits = [k for k, v in exp.items() if got.get(k) == v]
    wrong = {k: got.get(k) for k in exp if got.get(k) != exp[k]}
    unmatched = [k for k in exp if k not in got]
    score = len(hits) / len(exp)
    return {
        "correct": len(hits) == len(exp) and len(got) == len(exp),
        "score": round(score, 2),
        "detail": f"{len(hits)}/{len(exp)} pairs correct"
                  + (f"; unpaired {unmatched}" if unmatched else ""),
        "expected": exp, "given": got, "wrong_pairs": wrong,
    }


def _grade_hotspot(question: dict, given: Any) -> dict:
    targets = [normalize_text(t) for t in (question.get("hotspot_targets") or [])]
    exp = set(_seq(question.get("drill_answer")))
    got = set(_seq(given))
    unknown = sorted(got - set(targets)) if targets else []
    if unknown:
        raise AnswerFormatError(
            f"selected target(s) {unknown} are not on this question "
            f"(valid: {targets})")
    hit, extra, missed = exp & got, got - exp, exp - got
    score = len(hit) / len(exp | got) if (exp | got) else 0.0
    return {"correct": exp == got, "score": round(score, 2),
            "detail": f"{len(hit)}/{len(exp)} correct region(s)"
                      + (f", {len(extra)} spurious" if extra else ""),
            "expected": sorted(exp), "given": sorted(got)}


def _grade_build_list(question: dict, given: Any) -> dict:
    exp = _seq(question.get("drill_answer"))
    got = _seq(given)
    if not exp:
        raise AnswerFormatError("question has no ordered key sealed")
    in_place = sum(1 for i, item in enumerate(got) if i < len(exp) and exp[i] == item)
    score = in_place / len(exp)
    detail = f"{in_place}/{len(exp)} items in the right position"
    if set(got) == set(exp) and got != exp:
        detail += " — right items, wrong order"
    elif set(got) != set(exp):
        detail += f" — item set differs (missing {sorted(set(exp) - set(got))})"
    return {"correct": got == exp, "score": round(score, 2), "detail": detail,
            "expected": exp, "given": got}


def _grade_domc(question: dict, given: Any) -> dict:
    """Discrete Option MC: the candidate accepts or rejects each option in turn.

    A DOMC item is correct only when every presented option received the right
    verdict — accepting a distractor is as wrong as rejecting the key.
    """
    key = letters(question.get("drill_answer"))
    got = _yes_no(given)
    presented = [L for L in (question.get("option_texts") or {})] or sorted(got)
    if not got:
        raise AnswerFormatError("no DOMC verdicts found; reply like 'A:N, B:Y'")
    unanswered = [L for L in presented if L not in got]
    wrong = [L for L in presented
             if L in got and got[L] != ("Y" if L in key else "N")]
    judged = [L for L in presented if L in got]
    score = (len(judged) - len(wrong)) / len(presented) if presented else 0.0
    return {
        "correct": not wrong and not unanswered,
        "score": round(max(score, 0.0), 2),
        "detail": (f"{len(wrong)} wrong verdict(s) {wrong}" if wrong else "all verdicts correct")
                  + (f"; no verdict for {unanswered}" if unanswered else ""),
        "expected": {L: ("Y" if L in key else "N") for L in presented},
        "given": got,
    }


# --------------------------------------------------------------------------- #
# Public surface
# --------------------------------------------------------------------------- #

def qtype_of(question: dict) -> str:
    """Resolve a question's format, defaulting by answer shape for legacy records.

    An unknown declared qtype is NOT silently coerced — `grade` rejects it, so a typo
    in a seal cannot quietly downgrade a build_list item to multiple choice.
    """
    qt = (question.get("qtype") or "").strip()
    if qt in QUESTION_TYPES:
        return qt
    return "multiple_response" if len(letters(question.get("drill_answer"))) > 1 \
        else "multiple_choice"


def grade(question: dict, user_answer: Any) -> dict:
    """Grade `user_answer` against the sealed key. Raises AnswerFormatError on junk."""
    declared = (question.get("qtype") or "").strip()
    if declared and declared not in QUESTION_TYPES:
        raise AnswerFormatError(
            f"unknown qtype {declared!r}; known: {sorted(QUESTION_TYPES)}")
    qt = qtype_of(question)
    if qt == "multiple_choice":
        return _grade_letters(question.get("drill_answer"), user_answer, exact_set=False)
    if qt == "multiple_response":
        return _grade_letters(question.get("drill_answer"), user_answer, exact_set=True)
    if qt == "fill_in_blank":
        return _grade_fill_in_blank(question, user_answer)
    if qt == "matching":
        return _grade_matching(question, user_answer)
    if qt == "hotspot":
        return _grade_hotspot(question, user_answer)
    if qt == "build_list":
        return _grade_build_list(question, user_answer)
    if qt == "domc":
        return _grade_domc(question, user_answer)
    raise AnswerFormatError(f"unknown qtype {qt!r}; known: {sorted(QUESTION_TYPES)}")


def answer_instruction(question: dict) -> str:
    """How the learner should phrase their answer — shown with every served question."""
    qt = qtype_of(question)
    return {
        "multiple_choice": "Reply with one letter, e.g. `B`.",
        "multiple_response": "Reply with every correct letter, e.g. `A,C`. "
                             "Partial selections are marked wrong.",
        "fill_in_blank": "Reply with the exact term or command that fills the blank.",
        "matching": "Reply with one pair per line, e.g. `snapshot -> SCD Type 2`.",
        "hotspot": "Reply with the id(s) of the region you would click, e.g. `line-4`.",
        "build_list": "Reply with the steps in order, comma-separated, e.g. `b, a, d`.",
        "domc": "You will see one option at a time. For each, answer `Y` (this is "
                "correct) or `N` (this is not). You cannot revise an earlier verdict.",
    }[qt]


def render_question(question: dict, reveal_answer: bool = False) -> str:
    """Format a question for presentation. Never includes the key unless asked."""
    qt = qtype_of(question)
    parts = [str(question.get("stem") or "").strip(), ""]

    if question.get("code_block"):
        parts += ["```" + (question.get("code_language") or ""),
                  str(question["code_block"]).rstrip(), "```", ""]

    if qt in ("multiple_choice", "multiple_response", "domc"):
        for letter, text in (question.get("option_texts") or {}).items():
            parts.append(f"{letter}. {text}")
    elif qt == "matching":
        left = question.get("match_left") or []
        right = question.get("match_right") or []
        parts.append("Left: " + ", ".join(map(str, left)))
        parts.append("Right (choices): " + ", ".join(map(str, right)))
    elif qt == "hotspot":
        parts.append("Selectable regions: "
                     + ", ".join(map(str, question.get("hotspot_targets") or [])))
    elif qt == "build_list":
        parts.append("Steps to order: "
                     + ", ".join(map(str, question.get("build_items") or [])))
    elif qt == "fill_in_blank":
        parts.append("(Fill in the blank marked `____`.)")

    parts += ["", answer_instruction(question)]

    if reveal_answer:
        parts += ["", f"**Answer:** {question.get('drill_answer')}"]
        if question.get("drill_answer_short"):
            parts.append(f"**Short rationale:** {question['drill_answer_short']}")
    return "\n".join(parts).rstrip()


def is_letter_type(question: dict) -> bool:
    return qtype_of(question) not in NON_LETTER_TYPES
