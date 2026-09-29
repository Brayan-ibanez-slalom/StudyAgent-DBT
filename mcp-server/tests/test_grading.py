"""Unit tests for grading.py — the multi-format answer engine.

These are the tests that matter most in this repo: a grading bug silently teaches the
wrong thing. Run with:  python3 mcp-server/tests/test_grading.py
"""
from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from study_agent_mcp import grading  # noqa: E402
from study_agent_mcp.grading import AnswerFormatError  # noqa: E402


def mc(**kw):
    base = {"qtype": "multiple_choice", "stem": "Which one?",
            "option_texts": {"A": "a", "B": "b", "C": "c", "D": "d"},
            "drill_answer": "B"}
    return {**base, **kw}


class TestMultipleChoice(unittest.TestCase):
    def test_exact(self):
        r = grading.grade(mc(), "B")
        self.assertTrue(r["correct"])

    def test_lowercase_and_noise(self):
        self.assertTrue(grading.grade(mc(), "b.")["correct"])
        self.assertTrue(grading.grade(mc(), "answer: B")["correct"])

    def test_wrong(self):
        r = grading.grade(mc(), "C")
        self.assertFalse(r["correct"])
        self.assertIn("B", r["detail"])

    def test_two_letters_rejected(self):
        with self.assertRaises(AnswerFormatError):
            grading.grade(mc(), "B,C")

    def test_empty_rejected(self):
        with self.assertRaises(AnswerFormatError):
            grading.grade(mc(), "   ")


class TestMultipleResponse(unittest.TestCase):
    def setUp(self):
        self.q = mc(qtype="multiple_response", drill_answer="A,C")

    def test_exact_set_any_order(self):
        self.assertTrue(grading.grade(self.q, "C,A")["correct"])
        self.assertTrue(grading.grade(self.q, ["a", "c"])["correct"])

    def test_partial_is_wrong_but_scores(self):
        r = grading.grade(self.q, "A")
        self.assertFalse(r["correct"])
        self.assertEqual(r["score"], 0.5)

    def test_superset_is_wrong(self):
        r = grading.grade(self.q, "A,B,C")
        self.assertFalse(r["correct"])
        self.assertIn("B", r["detail"])


class TestFillInBlank(unittest.TestCase):
    def setUp(self):
        self.q = {"qtype": "fill_in_blank",
                  "stem": "The ____ macro guards incremental logic.",
                  "drill_answer": "is_incremental()",
                  "accepted_answers": ["is_incremental()", "is_incremental"]}

    def test_canonical(self):
        self.assertTrue(grading.grade(self.q, "is_incremental()")["correct"])

    def test_variant(self):
        self.assertTrue(grading.grade(self.q, "is_incremental")["correct"])

    def test_case_and_backticks(self):
        self.assertTrue(grading.grade(self.q, "`IS_INCREMENTAL()`")["correct"])

    def test_wrong(self):
        self.assertFalse(grading.grade(self.q, "is_full_refresh")["correct"])

    def test_empty_rejected(self):
        with self.assertRaises(AnswerFormatError):
            grading.grade(self.q, "")


class TestMatching(unittest.TestCase):
    def setUp(self):
        self.q = {"qtype": "matching", "stem": "Match them.",
                  "match_left": ["snapshot", "seed"],
                  "match_right": ["SCD Type 2", "CSV load", "CTE inline"],
                  "drill_answer": {"snapshot": "SCD Type 2", "seed": "CSV load"}}

    def test_all_pairs(self):
        r = grading.grade(self.q, {"snapshot": "SCD Type 2", "seed": "CSV load"})
        self.assertTrue(r["correct"])
        self.assertEqual(r["score"], 1.0)

    def test_arrow_string_form(self):
        r = grading.grade(self.q, "snapshot -> SCD Type 2, seed -> CSV load")
        self.assertTrue(r["correct"])

    def test_partial_credit_but_incorrect(self):
        r = grading.grade(self.q, {"snapshot": "SCD Type 2", "seed": "CTE inline"})
        self.assertFalse(r["correct"])
        self.assertEqual(r["score"], 0.5)

    def test_unparseable(self):
        with self.assertRaises(AnswerFormatError):
            grading.grade(self.q, "snapshot and seed")


class TestHotspot(unittest.TestCase):
    def setUp(self):
        self.q = {"qtype": "hotspot", "stem": "Click the broken line.",
                  "hotspot_targets": ["line-1", "line-2", "line-3"],
                  "drill_answer": "line-2"}

    def test_correct(self):
        self.assertTrue(grading.grade(self.q, "line-2")["correct"])

    def test_off_target_rejected(self):
        with self.assertRaises(AnswerFormatError):
            grading.grade(self.q, "line-9")

    def test_extra_selection_is_wrong(self):
        r = grading.grade(self.q, "line-1, line-2")
        self.assertFalse(r["correct"])
        self.assertIn("spurious", r["detail"])


class TestBuildList(unittest.TestCase):
    def setUp(self):
        self.q = {"qtype": "build_list", "stem": "Order the steps.",
                  "build_items": ["deps", "seed", "run", "test"],
                  "drill_answer": ["deps", "seed", "run", "test"]}

    def test_correct_order(self):
        r = grading.grade(self.q, "deps, seed, run, test")
        self.assertTrue(r["correct"])
        self.assertEqual(r["score"], 1.0)

    def test_right_items_wrong_order(self):
        r = grading.grade(self.q, "seed, deps, run, test")
        self.assertFalse(r["correct"])
        self.assertIn("wrong order", r["detail"])

    def test_numbered_list_form(self):
        r = grading.grade(self.q, "1. deps\n2. seed\n3. run\n4. test")
        self.assertTrue(r["correct"])

    def test_missing_item(self):
        r = grading.grade(self.q, "deps, seed, run")
        self.assertFalse(r["correct"])
        self.assertIn("item set differs", r["detail"])


class TestDOMC(unittest.TestCase):
    def setUp(self):
        self.q = mc(qtype="domc", drill_answer="B",
                    option_texts={"A": "a", "B": "b", "C": "c"})

    def test_all_verdicts_right(self):
        r = grading.grade(self.q, {"A": "N", "B": "Y", "C": "N"})
        self.assertTrue(r["correct"])

    def test_accepting_a_distractor_is_wrong(self):
        r = grading.grade(self.q, {"A": "Y", "B": "Y", "C": "N"})
        self.assertFalse(r["correct"])
        self.assertIn("A", r["detail"])

    def test_string_form(self):
        self.assertTrue(grading.grade(self.q, "A:N, B:Y, C:N")["correct"])

    def test_missing_verdict_is_incorrect(self):
        r = grading.grade(self.q, "B:Y")
        self.assertFalse(r["correct"])
        self.assertIn("no verdict", r["detail"])

    def test_bad_verdict_rejected(self):
        with self.assertRaises(AnswerFormatError):
            grading.grade(self.q, "A:maybe")


class TestRenderingNeverLeaks(unittest.TestCase):
    def test_key_absent_from_drill_rendering(self):
        q = mc(drill_answer="B", drill_answer_short="because B")
        body = grading.render_question(q, reveal_answer=False)
        self.assertNotIn("Answer:", body)
        self.assertNotIn("because B", body)

    def test_review_rendering_includes_key(self):
        q = mc(drill_answer="B", drill_answer_short="because B")
        body = grading.render_question(q, reveal_answer=True)
        self.assertIn("**Answer:** B", body)

    def test_every_format_has_an_instruction(self):
        from study_agent_mcp.exam_config import QUESTION_TYPES
        for qt in QUESTION_TYPES:
            self.assertTrue(grading.answer_instruction({"qtype": qt}).strip(),
                            f"{qt} has no answer instruction")

    def test_fill_in_blank_rendering_does_not_show_accepted_answers(self):
        q = {"qtype": "fill_in_blank", "stem": "Use ____ here.",
             "drill_answer": "ephemeral", "accepted_answers": ["ephemeral"]}
        self.assertNotIn("ephemeral", grading.render_question(q, reveal_answer=False))


class TestQtypeInference(unittest.TestCase):
    def test_legacy_single_letter(self):
        self.assertEqual(grading.qtype_of({"drill_answer": "B"}), "multiple_choice")

    def test_legacy_multi_letter(self):
        self.assertEqual(grading.qtype_of({"drill_answer": "A,C"}), "multiple_response")

    def test_explicit_wins(self):
        self.assertEqual(
            grading.qtype_of({"qtype": "build_list", "drill_answer": "A"}), "build_list")

    def test_unknown_qtype_raises(self):
        with self.assertRaises(AnswerFormatError):
            grading.grade({"qtype": "essay", "drill_answer": "x"}, "x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
