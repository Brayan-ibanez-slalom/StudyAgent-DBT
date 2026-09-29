#!/usr/bin/env python3
"""Quality gate for candidate exam items. Rejects anything that fails the spec.

This is the anti-hallucination component. The dangerous part of a generated item is
never the prose — it is the single documented fact that decides the answer. So every
candidate must declare a `decision_hinge` plus the dbt docs page it comes from, and this
script checks that the hinge's key terms actually appear in the CACHED TEXT of that page
on disk. No cached page, no pass. Terms not found, no pass.

The remaining checks enforce the structural rules in docs/item-authoring-spec.md so items
read like dbt Labs wrote them rather than like a model wrote them.

Several structural checks only make sense for the letter-option formats. For
fill_in_blank / matching / hotspot / build_list they are skipped as not-applicable, and
format-specific checks take over (see FORMAT_CHECKS).

Usage:
    python3 scripts/item_qa.py candidates.json
    python3 scripts/item_qa.py candidates.json --verbose
    python3 scripts/item_qa.py --audit
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "mcp-server"))

from study_agent_mcp import exam_config, grading  # noqa: E402

CACHE_RAW = REPO_ROOT / "sources" / "cache" / "_raw"
INDEX_JSON = REPO_ROOT / "question-bank" / "index.json"

STOPWORDS = set("""a an the and or of for to in on with by is are be that this these those
from as at into via can will must should you your it its if when where which what how
use uses using used solution solutions team teams project projects requirement
requirements meet meets least most best following want wants need needs""".split())

QUALIFIER_RE = re.compile(r"\b(LEAST|MOST|BEST|FEWEST|HIGHEST|LOWEST|ONLY|FIRST)\b")
REQUIREMENT_RE = re.compile(
    r"\b(must|needs? to|requires?|wants? to|wants? the|should|has to)\b", re.I)
DIAGNOSTIC_RE = re.compile(
    r"what is the cause|why (is|does|are|did)|root cause|what will resolve|"
    r"which action will resolve|fails with|returns an error|is not being", re.I)

MIN_CACHED_BODY = 200  # some pages cache as a near-empty file while reporting success

# Letter-option formats. Structural option checks apply only to these.
LETTER_FORMATS = {"multiple_choice", "multiple_response", "domc"}

# Delegated so the gate and the drill engine can never disagree about what format an
# item is, or about which letters its key names.
qtype_of = grading.qtype_of


def key_letters(item: dict) -> set[str]:
    return grading.letters(item.get("drill_answer")) \
        if not isinstance(item.get("drill_answer"), (dict, list)) else set()


def _skip(item: dict) -> tuple[bool, str]:
    return True, f"not applicable to {qtype_of(item)} items"


# --------------------------------------------------------------------------- #
# Cached-source verification
# --------------------------------------------------------------------------- #

def cached_text_for(url: str) -> str | None:
    """Return the cached body for a doc URL, or None if never usefully fetched.

    A body under MIN_CACHED_BODY is treated as missing: some pages write a near-empty
    file while the fetch reports success, and an item sourced to one of those would
    otherwise count as verifiable against nothing at all.
    """
    p = urlparse(url)
    if not p.netloc:
        return None

    def usable(path: Path) -> str | None:
        body = path.read_text(encoding="utf-8", errors="ignore")
        return body if len(body.strip()) >= MIN_CACHED_BODY else None

    candidate = CACHE_RAW / p.netloc / (p.path.lstrip("/") + ".txt")
    if candidate.exists():
        return usable(candidate)
    tail = Path(p.path).name
    for hit in CACHE_RAW.rglob(f"{tail}*"):
        if hit.is_file():
            return usable(hit)
    return None


def content_terms(text: str, min_len: int = 4) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-_.:]{%d,}" % (min_len - 1), (text or "").lower())
    return {w.strip(".") for w in words if w not in STOPWORDS}


def verify_claim(claim: str, sources: list) -> tuple[float, str | None, set[str]]:
    """How much of `claim` is present in the cached body of any cited URL."""
    terms = content_terms(claim)
    if not terms:
        return 0.0, None, set()
    best_ratio, best_url, missing = 0.0, None, terms
    for url in sources:
        if not str(url).startswith("http"):
            continue  # knowledge/*.md notes are checked by verify_seal instead
        body = cached_text_for(url)
        if body is None:
            continue
        present = {t for t in terms if t in body.lower()}
        ratio = len(present) / len(terms)
        if ratio > best_ratio:
            best_ratio, best_url, missing = ratio, url, terms - present
    return best_ratio, best_url, missing


def check_hinge_verified(item: dict) -> tuple[bool, str]:
    hinge = (item.get("decision_hinge") or "").strip()
    sources = item.get("sources") or []
    if not hinge:
        return False, "no decision_hinge declared"
    if not sources:
        return False, "no sources declared"
    if not content_terms(hinge):
        return False, "decision_hinge has no checkable terms"

    best_ratio, best_url, missing = verify_claim(hinge, sources)
    if best_url is None:
        return False, (f"no cited URL is cached on disk — run cache_fetch on it first "
                       f"({len(sources)} source(s) declared)")
    if best_ratio < 0.6:
        return False, (f"only {best_ratio:.0%} of hinge terms found in {best_url} — "
                       f"missing: {sorted(missing)[:6]}")
    return True, f"{best_ratio:.0%} of hinge terms confirmed in cached {best_url}"


def check_source_verifiable(item: dict) -> tuple[bool, str]:
    """Can this item's answer be re-checked against dbt docs at all?"""
    sources = item.get("sources") or []
    if not sources:
        return False, "no sources — answer cannot be re-verified"
    urls = [s for s in sources if str(s).startswith("http")]
    notes = [s for s in sources if str(s).startswith("knowledge/")]
    if not urls and not notes:
        return False, f"sources are prose, not a URL or knowledge note: {sources[:2]}"
    cached = [u for u in urls if cached_text_for(u) is not None]
    if urls and not cached:
        return False, f"{len(urls)} URL(s) cited but none cached — run cache_fetch"
    if notes and not urls:
        return True, f"{len(notes)} knowledge note(s), no external URL"
    return True, f"{len(cached)}/{len(urls)} cited URL(s) cached and checkable"


def check_source_is_authoritative(item: dict) -> tuple[bool, str]:
    """dbt behaviour claims must cite dbt Labs, not a blog restating it."""
    urls = [str(s) for s in (item.get("sources") or []) if str(s).startswith("http")]
    if not urls:
        return True, "no external URL to judge"
    off = [u for u in urls
           if any(h in urlparse(u).netloc for h in exam_config.AUTHORITATIVE_HOSTS)]
    return bool(off), (f"{len(off)}/{len(urls)} source(s) on {exam_config.AUTHORITATIVE_HOSTS}"
                       if off else
                       f"no source on an official dbt Labs host: {[urlparse(u).netloc for u in urls]}")


# --------------------------------------------------------------------------- #
# Structural checks — letter formats
# --------------------------------------------------------------------------- #

def check_option_count(item: dict) -> tuple[bool, str]:
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    opts = item.get("option_texts") or {}
    n = len(opts)
    if qtype_of(item) == "domc":
        return 3 <= n <= 8, f"DOMC presents {n} options (3-8 is workable)"
    if len(key_letters(item)) > 1:
        return 4 <= n <= 6, f"multiple-response with {n} options (4-6 expected)"
    allowed = exam_config.OFFICIAL_OPTION_COUNTS
    return n in allowed, (f"single-answer with {n} options "
                          f"(official sample questions use {allowed})")


def check_option_parity(item: dict) -> tuple[bool, str]:
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    lengths = [len(t) for t in (item.get("option_texts") or {}).values()]
    if len(lengths) < 2:
        return False, "too few options to compare"
    med = statistics.median(lengths) or 1
    worst = max(abs(x - med) / med for x in lengths)
    return worst <= 0.45, f"longest/shortest deviate {worst:.0%} from median (allows 45%)"


def check_parallel_openings(item: dict) -> tuple[bool, str]:
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    firsts = [t.split()[0].lower() for t in (item.get("option_texts") or {}).values()
              if t.split()]
    distinct = len(set(firsts))
    return distinct <= max(2, len(firsts) // 2), (
        f"{distinct} distinct opening words across {len(firsts)} options: {sorted(set(firsts))}")


OPTION_WORDS_P90 = 32
OPTION_WORDS_MAX = 55
STEM_WORDS_P90 = 95
KEY_LENGTH_MARGIN_WARN = 8


def check_option_verbosity(item: dict) -> tuple[bool, str]:
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    lengths = [len(t.split()) for t in (item.get("option_texts") or {}).values()]
    if not lengths:
        return False, "no options"
    longest = max(lengths)
    ok = longest <= OPTION_WORDS_P90
    return ok, (f"longest option is {longest} words (limit {OPTION_WORDS_P90})" if ok
                else f"longest option is {longest} words, over the "
                     f"{OPTION_WORDS_P90}-word guideline")


def check_option_not_checklist(item: dict) -> tuple[bool, str]:
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    lengths = [len(t.split()) for t in (item.get("option_texts") or {}).values()]
    if not lengths:
        return False, "no options"
    longest = max(lengths)
    ok = longest <= OPTION_WORDS_MAX
    return ok, (f"longest option is {longest} words (hard limit {OPTION_WORDS_MAX})" if ok
                else f"longest option is {longest} words, beyond the "
                     f"{OPTION_WORDS_MAX}-word hard limit — almost certainly a "
                     f"checklist restating the stem")


def check_stem_verbosity(item: dict) -> tuple[bool, str]:
    words = len((item.get("stem") or "").split())
    ok = words <= STEM_WORDS_P90
    return ok, (f"stem is {words} words (limit {STEM_WORDS_P90})" if ok
                else f"stem is {words} words, over the {STEM_WORDS_P90}-word guideline")


def check_no_lexical_giveaway(item: dict) -> tuple[bool, str]:
    """The key must not be the only option echoing distinctive stem wording."""
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    opts = item.get("option_texts") or {}
    correct = key_letters(item)
    stem_terms = content_terms(item.get("stem") or "", min_len=5)
    if not stem_terms or not correct:
        return True, "not enough signal to judge"
    overlaps = {L: len(stem_terms & content_terms(t, min_len=5)) for L, t in opts.items()}
    key_overlap = max((overlaps.get(c, 0) for c in correct), default=0)
    others = [v for L, v in overlaps.items() if L not in correct]
    if not others:
        return True, "no distractors to compare"
    if key_overlap > max(others) + 2:
        return False, (f"key echoes {key_overlap} distinctive stem terms vs {max(others)} "
                       f"for the best distractor — findable without knowledge")
    return True, f"key echo {key_overlap} vs best distractor {max(others)}"


def check_no_leaked_term(item: dict) -> tuple[bool, str]:
    """No distinctive word may appear in the stem and the key but in no distractor.

    Aggregate overlap can look balanced while one loud word still points at the key.
    """
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    opts = item.get("option_texts") or {}
    correct = key_letters(item)
    if not correct or len(opts) < 2:
        return True, "not enough options to judge"
    stem_terms = content_terms(item.get("stem") or "", min_len=6)
    key_terms: set[str] = set()
    distractor_terms: set[str] = set()
    for letter, text in opts.items():
        (key_terms if letter in correct else distractor_terms).update(
            content_terms(text, min_len=6))
    leaked = sorted((stem_terms & key_terms) - distractor_terms)
    return (not leaked), (f"term(s) shared only by stem and key: {leaked[:5]}" if leaked
                          else "no term is unique to the stem and the key")


def check_key_not_odd_one_out(item: dict) -> tuple[bool, str]:
    """The key must not be the lone structural outlier among the options."""
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    opts = item.get("option_texts") or {}
    keys = key_letters(item)
    if len(opts) < 3 or len(keys) != 1:
        return True, "not a single-answer item with enough options to judge"

    def opener(text: str) -> str:
        words = re.findall(r"[A-Za-z]+", text or "")
        return words[0].lower() if words else ""

    key = next(iter(keys))
    key_open = opener(opts.get(key, ""))
    others = [opener(t) for L, t in opts.items() if L != key]
    if not key_open or not all(others):
        return True, "cannot read opening words"
    if key_open not in others and len(set(others)) == 1:
        return False, (f"every distractor opens with '{others[0]}' and the key opens with "
                       f"'{key_open}' — findable by shape alone")
    return True, f"key opens with '{key_open}', distractors with {sorted(set(others))}"


def check_key_not_longest(item: dict) -> tuple[bool, str]:
    """Warn when a single-select key is so much longer than every distractor that
    length alone finds it. A hit is a prompt to read the item, not a verdict."""
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    opts = item.get("option_texts") or {}
    answer = sorted(key_letters(item))
    if not opts or not answer or any(a not in opts for a in answer):
        return True, "no key to compare"
    if len(answer) > 1:
        return True, "multi-select: picking the longest cannot identify the key set"
    distractors = [t for letter, t in opts.items() if letter not in answer]
    if not distractors:
        return True, "no distractors to compare"
    key_words = max(len(opts[a].split()) for a in answer)
    longest_distractor = max(len(t.split()) for t in distractors)
    margin = key_words - longest_distractor
    return margin < KEY_LENGTH_MARGIN_WARN, (
        f"key is {margin:+d} words against the longest distractor "
        f"({key_words} vs {longest_distractor})")


def check_key_not_the_longest_option(item: dict) -> tuple[bool, str]:
    """The key must not simply be the longest option on offer.

    Rank, not margin, is what "pick the longest and read nothing" actually exploits.
    A tie is not a giveaway.
    """
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    opts = item.get("option_texts") or {}
    answer = sorted(key_letters(item))
    if len(opts) < 3 or not answer or any(a not in opts for a in answer):
        return True, "no key to rank"
    words = {letter: len(text.split()) for letter, text in opts.items()}
    top = max(words.values())
    if sum(1 for v in words.values() if v == top) > 1:
        return True, f"longest option is tied at {top} words — not a giveaway"
    longest = max(words, key=lambda letter: words[letter])
    if longest not in answer:
        return True, f"longest option is {longest}, a distractor"
    runner_up = max(v for letter, v in words.items() if letter != longest)
    return False, (f"the key is the single longest option ({top} vs {runner_up} words) — "
                   f"answerable by picking the longest without reading")


# --------------------------------------------------------------------------- #
# Evidence checks — the item must prove its distractors are real rivals
# --------------------------------------------------------------------------- #

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def evidence_map(item: dict, field: str) -> dict[str, str]:
    raw = item.get(field)
    if isinstance(raw, dict):
        return {str(k).strip().upper(): str(v) for k, v in raw.items()}
    if isinstance(raw, list):
        return {str(k).strip().upper(): "" for k in raw}
    return {}


def elimination_map(item: dict) -> dict[str, dict]:
    """{letter: {"signal": quote, "requires_fact": str|None}}.

    A bare string means the option is ruled out by that stem signal alone — any reader
    can drop it without knowing anything about dbt. A dict with `requires_fact` means
    the signal only rules it out once you know a documented fact, which is a real test
    of knowledge, so that option still counts as a surviving rival.
    """
    out: dict[str, dict] = {}
    for letter, val in (item.get("eliminated_by") or {}).items():
        L = str(letter).strip().upper()
        if isinstance(val, dict):
            out[L] = {"signal": str(val.get("signal") or ""),
                      "requires_fact": (val.get("requires_fact") or "").strip() or None}
        else:
            out[L] = {"signal": str(val), "requires_fact": None}
    return out


def _quote_problem(quote: str, stem_norm: str, letter: str, opts: dict) -> str | None:
    if letter not in opts:
        return f"{letter} is not one of the options ({sorted(opts)})"
    if not quote.strip():
        return f"{letter} is claimed with no stem quote behind it"
    q = _norm(quote)
    if len(q) < 20:
        return f"{letter}'s quote is too short to be a real requirement: {quote!r}"
    if "?" in q:
        return f"{letter} cites the lead-in question, not a requirement: {quote!r}"
    if q not in stem_norm:
        return f"{letter}'s quote is not verbatim in the stem: {quote!r}"
    return None


def surviving_rivals(item: dict) -> tuple[list[str], list[str]]:
    """(rivals that survive without the tested fact, options that drop cheaply)."""
    opts = item.get("option_texts") or {}
    keys = key_letters(item)
    stem_norm = _norm(item.get("stem"))
    sources = item.get("sources") or []

    rivals, cheap = [], []
    for L, q in evidence_map(item, "plausible_options").items():
        if L not in keys and _quote_problem(q, stem_norm, L, opts) is None:
            rivals.append(L)
    for L, ev in elimination_map(item).items():
        if L in keys:
            continue
        fact = ev["requires_fact"]
        if fact and verify_claim(fact, sources)[0] >= 0.6:
            rivals.append(L)
        elif _quote_problem(ev["signal"], stem_norm, L, opts) is None:
            cheap.append(L)
    return sorted(set(rivals)), sorted(set(cheap))


def check_plausibility_evidence(item: dict) -> tuple[bool, str]:
    """Every option called plausible must quote the stem clause it satisfies."""
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    opts = item.get("option_texts") or {}
    plausible = evidence_map(item, "plausible_options")
    if not plausible:
        return True, "no plausible options declared"
    stem_norm = _norm(item.get("stem"))
    problems = [p for L, q in plausible.items()
                if (p := _quote_problem(q, stem_norm, L, opts))]
    return (not problems), ("; ".join(problems[:3]) if problems
                            else f"{len(plausible)} plausible option(s) cite a verbatim stem clause")


def check_elimination_coverage(item: dict) -> tuple[bool, str]:
    """Each remaining distractor must name the stem signal that rules it out."""
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    opts = item.get("option_texts") or {}
    keys = key_letters(item)
    distractors = {L for L in opts if L not in keys}
    plausible = set(evidence_map(item, "plausible_options")) - keys
    eliminated = elimination_map(item)
    sources = item.get("sources") or []
    stem_norm = _norm(item.get("stem"))

    problems = []
    for L, ev in sorted(eliminated.items()):
        fact = ev["requires_fact"]
        if ev["signal"].strip() or not fact:
            if p := _quote_problem(ev["signal"], stem_norm, L, opts):
                problems.append(p)
        elif L not in opts:
            problems.append(f"{L} is not one of the options ({sorted(opts)})")
        if fact and verify_claim(fact, sources)[0] < 0.6:
            problems.append(
                f"{L}'s requires_fact is not supported by a cached source: {fact[:60]!r}")
    if both := plausible & set(eliminated):
        problems.append(f"{sorted(both)} declared both surviving and eliminated")
    if unclaimed := distractors - plausible - set(eliminated):
        problems.append(f"no verdict for distractor(s) {sorted(unclaimed)}")
    if distractors and not (distractors - plausible):
        problems.append("every distractor is declared plausible — the key is not uniquely correct")
    if problems:
        return False, "; ".join(problems[:3])
    rivals, cheap = surviving_rivals(item)
    return True, (f"verdicts for all {len(distractors)} distractor(s); {len(rivals)} survive "
                  f"without the tested fact, {len(cheap)} drop cheaply")


def check_not_pure_elimination(item: dict) -> tuple[bool, str]:
    """At least one distractor must not be droppable without dbt knowledge."""
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    opts = item.get("option_texts") or {}
    if len({L for L in opts if L not in key_letters(item)}) < 2:
        return True, "too few distractors to judge"
    rivals, cheap = surviving_rivals(item)
    if rivals:
        return True, f"rival(s) {rivals} survive for a reader without the tested fact"
    return False, (f"all {len(cheap)} distractor(s) drop to a stem signal alone — solvable "
                   f"by elimination without the tested fact")


def check_elimination_signals_distinct(item: dict) -> tuple[bool, str]:
    """One sentence must not sweep the board."""
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    signals = {L: _norm(ev["signal"]) for L, ev in elimination_map(item).items()
               if ev["signal"].strip()}
    if len(signals) < 3:
        return True, f"{len(signals)} eliminated distractor(s) — no sweep possible"
    distinct = len(set(signals.values()))
    if distinct < 2:
        return False, (f"a single stem signal eliminates all {len(signals)} distractors — "
                       f"solvable by elimination")
    return True, f"{distinct} distinct elimination signals across {len(signals)} distractors"


IMPOSSIBLE_IF_PLAUSIBLE = {"T1", "T4"}


def check_trap_consistency(item: dict) -> tuple[bool, str]:
    """Cross-check two independently written fields against each other."""
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    plausible = set(evidence_map(item, "plausible_options")) - key_letters(item)
    traps = {str(L).strip().upper(): str(v)
             for L, v in (item.get("distractor_traps") or {}).items()}
    clashes = [f"{L} is plausible but tagged {fam}" for L in sorted(plausible)
               if (fam := traps.get(L, "").split(":")[0].strip().upper())
               in IMPOSSIBLE_IF_PLAUSIBLE]
    return (not clashes), ("; ".join(clashes) if clashes
                           else "no option is both a surviving rival and a "
                                "fabricated/requirement-breaking trap")


def check_qualifier_has_rivals(item: dict) -> tuple[bool, str]:
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    if not QUALIFIER_RE.search(item.get("stem") or ""):
        return True, "no CAPS qualifier — a single functionally-correct option is fine"
    plausible = evidence_map(item, "plausible_options")
    if len(plausible) < 2:
        return False, ("stem uses a CAPS qualifier but fewer than 2 options are declared "
                       "functionally correct — the qualifier is decorative")
    return True, f"{len(plausible)} options satisfy all requirements; the qualifier decides"


def check_requirements(item: dict) -> tuple[bool, str]:
    n = len(REQUIREMENT_RE.findall(item.get("stem") or ""))
    return n >= 1, f"{n} requirement clause(s) in stem (want >= 1)"


def check_requires_fact_addresses_its_option(item: dict) -> tuple[bool, str]:
    """A `requires_fact` must say something about the option it kills, not restate the key.

    `requires_fact` is verified at the same 60% bar against the hinge's own cited page,
    so any restatement of the key would otherwise pass as elimination evidence for any
    distractor. Overlap alone is a bad signal — often the fact that supports the key
    genuinely is the fact that kills the rival. Two conditions together are precise: the
    fact is almost wholly contained in the hinge AND shares no distinctive term with the
    option text it is supposed to eliminate.
    """
    hinge = content_terms(item.get("decision_hinge") or "", min_len=5)
    opts = item.get("option_texts") or {}
    weak = []
    for letter, evidence in (item.get("eliminated_by") or {}).items():
        if not isinstance(evidence, dict) or "requires_fact" not in evidence:
            continue
        fact = content_terms(evidence["requires_fact"], min_len=5)
        L = str(letter).strip().upper()
        if not fact or L not in opts:
            continue
        restates_key = len(fact & hinge) / len(fact) >= 0.9
        if restates_key and not (fact & content_terms(opts[L], min_len=5)):
            weak.append(L)
    return (not weak), (
        f"option(s) {sorted(weak)} are killed by a fact that restates the key and never "
        f"mentions them — check it really eliminates that option" if weak
        else "every requires_fact names something in the option it eliminates")


def check_trap_diversity(item: dict) -> tuple[bool, str]:
    if qtype_of(item) not in LETTER_FORMATS:
        return _skip(item)
    fams = {str(v).split(":")[0].strip().upper()
            for v in (item.get("distractor_traps") or {}).values()}
    return len(fams) >= 2, f"{len(fams)} distinct trap families: {sorted(fams)}"


# --------------------------------------------------------------------------- #
# Format-specific checks
# --------------------------------------------------------------------------- #

def check_format_payload(item: dict) -> tuple[bool, str]:
    """Non-letter formats must ship the extra fields their renderer and grader need."""
    qt = qtype_of(item)
    required = {
        "fill_in_blank": ["accepted_answers"],
        "matching": ["match_left", "match_right"],
        "hotspot": ["hotspot_targets"],
        "build_list": ["build_items"],
    }.get(qt)
    if not required:
        return True, f"{qt} needs no extra payload"
    missing = [f for f in required if not item.get(f)]
    if missing:
        return False, f"{qt} item is missing {missing}"

    if qt == "fill_in_blank" and "____" not in (item.get("stem") or ""):
        return False, "fill_in_blank stem contains no '____' blank marker"
    if qt == "build_list":
        items = {str(x).strip().lower() for x in item["build_items"]}
        answer = {str(x).strip().lower()
                  for x in (item.get("drill_answer") or [])} if isinstance(
                      item.get("drill_answer"), list) else {
                      p.strip().lower() for p in str(item.get("drill_answer") or "").split(",")}
        if answer - items:
            return False, f"ordered key references items not in build_items: {sorted(answer - items)}"
    if qt == "matching":
        left = {str(x).strip().lower() for x in item["match_left"]}
        right = {str(x).strip().lower() for x in item["match_right"]}
        if len(right) <= len(left):
            return False, ("matching needs more right-hand choices than left-hand items, "
                           "or the last pair is free by elimination")
    return True, f"{qt} payload complete"


def check_distractor_plausible_for_format(item: dict) -> tuple[bool, str]:
    """Non-letter formats still need decoys, or they are recall-only."""
    qt = qtype_of(item)
    if qt == "matching":
        extra = len(item.get("match_right") or []) - len(item.get("match_left") or [])
        return extra >= 1, f"{extra} unused right-hand option(s) acting as decoys"
    if qt == "hotspot":
        n = len(item.get("hotspot_targets") or [])
        return n >= 3, f"{n} selectable region(s) (want >= 3)"
    if qt == "build_list":
        n = len(item.get("build_items") or [])
        return n >= 3, f"{n} orderable step(s) (want >= 3)"
    if qt == "fill_in_blank":
        n = len(item.get("accepted_answers") or [])
        return n >= 1, f"{n} accepted answer variant(s)"
    return True, f"not applicable to {qt}"


# --------------------------------------------------------------------------- #
# Check registry
# --------------------------------------------------------------------------- #

CHECKS = [
    ("hinge verified against cached dbt doc", check_hinge_verified, True),
    ("source is an official dbt Labs host", check_source_is_authoritative, True),
    ("format payload is complete", check_format_payload, True),
    ("option count matches format", check_option_count, True),
    ("qualifier has >=2 plausible options", check_qualifier_has_rivals, True),
    ("not solvable by elimination alone", check_not_pure_elimination, True),
    ("plausible options cite a stem clause", check_plausibility_evidence, True),
    ("every distractor has a quoted verdict", check_elimination_coverage, True),
    ("elimination evidence addresses its option",
     check_requires_fact_addresses_its_option, False),
    ("elimination signals are not one sweep", check_elimination_signals_distinct, True),
    ("plausible options are not T1/T4 traps", check_trap_consistency, True),
    ("no lexical giveaway in the key", check_no_lexical_giveaway, True),
    ("no term leaks from stem to key alone", check_no_leaked_term, True),
    ("key is not the odd one out", check_key_not_odd_one_out, True),
    ("options are not checklists", check_option_not_checklist, True),
    ("format has real decoys", check_distractor_plausible_for_format, False),
    ("key is not the longest option", check_key_not_longest, False),
    ("option length parity", check_option_parity, False),
    ("options stay terse", check_option_verbosity, False),
    ("stem stays terse", check_stem_verbosity, False),
    ("parallel option openings", check_parallel_openings, False),
    (">=1 requirement clause", check_requirements, False),
    (">=2 distinct trap families", check_trap_diversity, False),
]

# Checks safe to run against already-sealed bank items (no authoring-only fields).
AUDIT_CHECKS = [
    ("answer is re-verifiable", check_source_verifiable, True),
    ("source is an official dbt Labs host", check_source_is_authoritative, True),
    ("format payload is complete", check_format_payload, True),
    ("no lexical giveaway in the key", check_no_lexical_giveaway, True),
    ("key is not the odd one out", check_key_not_odd_one_out, True),
    ("key is not the longest option", check_key_not_longest, False),
    ("key does not rank longest", check_key_not_the_longest_option, False),
    ("option count matches format", check_option_count, False),
    ("option length parity", check_option_parity, False),
    (">=2 distinct trap families", check_trap_diversity, False),
]


# --------------------------------------------------------------------------- #
# Batch property: key position balance
# --------------------------------------------------------------------------- #

def _binomial_tail(k: int, n: int, p: float) -> float:
    from math import comb
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def check_key_balance(items: list[dict]) -> tuple[bool, str]:
    """The correct answer must not sit on the same letter across a batch.

    A learner who spots the pattern scores without reading. This is a batch property,
    so no single item can fail it on its own.
    """
    from collections import Counter
    singles = [i for i in items
               if qtype_of(i) in LETTER_FORMATS and len(key_letters(i)) == 1]
    if len(singles) < 4:
        return True, f"only {len(singles)} single-answer item(s) — too few to judge"
    counts = Counter(next(iter(key_letters(i))) for i in singles)
    n = len(singles)
    letter, top = counts.most_common(1)[0]
    n_options = max(len(i.get("option_texts") or {}) for i in singles) or 4
    p_any = min(1.0, n_options * _binomial_tail(top, n, 1 / n_options))
    spread = ", ".join(f"{L}={counts.get(L, 0)}" for L in sorted("ABCDEF"[:n_options]))
    if p_any < 0.05:
        return False, (f"key is {letter} in {top} of {n} items ({spread}) — that lands by "
                       f"chance about {p_any:.1%} of the time")
    return True, f"key positions are spread across the batch ({spread})"


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #

def gate_report(items: list[dict]) -> dict:
    results = []
    for item in items:
        checks = []
        for name, fn, fatal in CHECKS:
            ok, detail = fn(item)
            checks.append({"check": name, "passed": ok, "detail": detail, "fatal": fatal})
        fatal_fails = [c for c in checks if not c["passed"] and c["fatal"]]
        results.append({
            "id": item.get("id") or (item.get("stem") or "")[:60],
            "qtype": qtype_of(item),
            "verdict": "REJECT" if fatal_fails else "ACCEPT",
            "fatal_failures": fatal_fails,
            "warnings": [c for c in checks if not c["passed"] and not c["fatal"]],
        })
    balanced, detail = check_key_balance(items)
    return {"items": results,
            "accepted": sum(1 for r in results if r["verdict"] == "ACCEPT"),
            "rejected": sum(1 for r in results if r["verdict"] == "REJECT"),
            "key_balance": {"passed": balanced, "detail": detail}}


def audit_report() -> dict:
    from collections import Counter, defaultdict
    if not INDEX_JSON.exists():
        return {"audited": 0, "checks": [], "by_provenance": {},
                "note": "question-bank/index.json does not exist yet"}
    index = json.loads(INDEX_JSON.read_text())
    items = [q for q in index.get("questions", []) if q.get("verified")]

    fail_counts: Counter = Counter()
    by_prov: dict[str, Counter] = defaultdict(Counter)
    offenders: dict[str, list[str]] = defaultdict(list)

    for item in items:
        prov = item.get("source", "?")
        by_prov[prov]["total"] += 1
        for name, fn, _ in AUDIT_CHECKS:
            ok, detail = fn(item)
            if ok:
                continue
            fail_counts[name] += 1
            by_prov[prov][name] += 1
            if len(offenders[name]) < 6:
                offenders[name].append(f"{item['id']}: {detail[:90]}")

    return {
        "audited": len(items),
        "checks": [{"check": name, "failing": fail_counts[name],
                    "pct": round(100 * fail_counts[name] / max(1, len(items))),
                    "blocks_reuse": bool(fatal and fail_counts[name]),
                    "examples": offenders[name]}
                   for name, _, fatal in AUDIT_CHECKS],
        "by_provenance": {src: dict(c) for src, c in by_prov.items()},
    }


def review(item: dict, verbose: bool) -> bool:
    label = item.get("id") or (item.get("stem") or "")[:60] + "..."
    results = [(name, *fn(item), fatal) for name, fn, fatal in CHECKS]
    fatal_fails = [r for r in results if not r[1] and r[3]]
    warns = [r for r in results if not r[1] and not r[3]]
    verdict = "REJECT" if fatal_fails else ("ACCEPT (with warnings)" if warns else "ACCEPT")
    print(f"\n{verdict}  {label}  [{qtype_of(item)}]")
    for name, ok, detail, fatal in results:
        if ok and not verbose:
            continue
        mark = "  ok  " if ok else ("  FAIL" if fatal else "  warn")
        print(f"  {mark}  {name}: {detail}")
    return not fatal_fails


def audit_bank(verbose: bool) -> int:
    report = audit_report()
    n = report["audited"]
    print(f"Audited {n} sealed items\n")
    print(f"{'check':<40}{'failing':>9}{'  %':>7}")
    for row in report["checks"]:
        flag = "  <-- blocks reuse" if row["blocks_reuse"] else ""
        print(f"{row['check']:<40}{row['failing']:>9}{row['pct']:>6}%{flag}")
    if verbose:
        for entry in report["checks"]:
            if entry["examples"]:
                print(f"\n{entry['check']} — examples:")
                for line in entry["examples"]:
                    print(f"   {line}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="JSON file with one item or a list of items")
    ap.add_argument("--audit", action="store_true",
                    help="run applicable checks over the existing question bank")
    ap.add_argument("--verbose", action="store_true", help="show passing checks / examples")
    args = ap.parse_args()

    if args.audit:
        return audit_bank(args.verbose)
    if not args.path:
        ap.error("provide a candidates file, or use --audit")

    data = json.loads(Path(args.path).read_text())
    items = data if isinstance(data, list) else [data]
    accepted = sum(review(item, args.verbose) for item in items)
    balanced, detail = check_key_balance(items)
    print(f"\n  {'ok  ' if balanced else 'FAIL'}  key position balance: {detail}")
    print(f"\n{accepted}/{len(items)} accepted, {len(items) - accepted} rejected")
    return 0 if accepted == len(items) and balanced else 1


if __name__ == "__main__":
    sys.exit(main())
