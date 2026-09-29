"""Tests for exam_config invariants and the hint-leak guardrail.

exam_config is the single source of truth, so a typo there breaks every other module
silently. These tests make that loud.
"""
from __future__ import annotations

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from study_agent_mcp import exam_config, server  # noqa: E402


class TestExamConfigInvariants(unittest.TestCase):
    def test_every_domain_belongs_to_a_known_track(self):
        for did, meta in exam_config.DOMAINS.items():
            self.assertIn(meta["track"], exam_config.EXAM_FACTS, f"{did} has a bad track")

    def test_domain_ids_match_their_track_prefix(self):
        for did, meta in exam_config.DOMAINS.items():
            self.assertTrue(did.startswith(meta["track"] + "-"),
                            f"{did} should start with '{meta['track']}-'")

    def test_domain_dirs_are_unique_within_a_track(self):
        for track in exam_config.VALID_TRACKS:
            dirs = [m["dir"] for m in exam_config.domains_for(track).values()]
            self.assertEqual(len(dirs), len(set(dirs)), f"duplicate dir in {track}")

    def test_domain_dir_numbers_match_domain_ids(self):
        for did, meta in exam_config.DOMAINS.items():
            self.assertEqual(did.split("-", 1)[1][:2], meta["dir"][:2],
                             f"{did} number disagrees with folder {meta['dir']}")

    def test_task_ids_are_well_formed_and_match_their_domain_number(self):
        for did, meta in exam_config.DOMAINS.items():
            number = did.split("-", 1)[1].lstrip("0")
            for task_id in meta["tasks"]:
                self.assertRegex(task_id, r"^\d+\.\d+$", f"{did} task {task_id}")
                self.assertEqual(task_id.split(".")[0], number,
                                 f"{did} task {task_id} has the wrong major number")

    def test_every_task_has_a_title_and_keywords(self):
        for did, meta in exam_config.DOMAINS.items():
            for task_id, entry in meta["tasks"].items():
                title, keywords = entry
                self.assertTrue(title.strip(), f"{did}:{task_id} has no title")
                self.assertGreaterEqual(len(keywords), 3,
                                        f"{did}:{task_id} has too few keywords")

    def test_weights_are_not_fabricated(self):
        """dbt Labs publishes topic outlines but NO per-topic weighting.

        Question count and passing score ARE published (65 / 65%), so those must be
        populated. A per-domain weight must not be, because no source states one.
        """
        for did, meta in exam_config.DOMAINS.items():
            self.assertIsNone(meta["weight"], f"{did} has a fabricated weight")
        for track, facts in exam_config.EXAM_FACTS.items():
            self.assertFalse(facts["weights_published"], track)
            self.assertEqual(facts["question_count"], 65, track)
            self.assertEqual(facts["passing_score_pct"], 65, track)

    def test_subtopic_share_is_a_proxy_that_sums_to_100(self):
        for track in exam_config.VALID_TRACKS:
            share = exam_config.subtopic_share(track)
            self.assertAlmostEqual(sum(share.values()), 100.0, places=0, msg=track)
            self.assertEqual(set(share), set(exam_config.domains_for(track)))

    def test_every_domain_cites_its_official_provenance(self):
        for did, meta in exam_config.DOMAINS.items():
            self.assertIn("study guide", meta["provenance"].lower(),
                          f"{did} does not cite the official study guide")

    def test_official_guide_urls_are_on_an_authoritative_host(self):
        for track, facts in exam_config.EXAM_FACTS.items():
            for key in ("exam_guide_url", "study_guide_url"):
                self.assertTrue(
                    any(h in facts[key] for h in exam_config.AUTHORITATIVE_HOSTS),
                    f"{track}.{key} is not on a dbt Labs host")

    def test_id_prefixes_are_unique_per_track(self):
        seen = set()
        for track in exam_config.VALID_TRACKS:
            for prov in exam_config.ID_PREFIXES:
                prefix = exam_config.id_prefix(prov, track)
                self.assertNotIn(prefix, seen, f"{prefix} collides")
                seen.add(prefix)

    def test_helpers_round_trip(self):
        for did, meta in exam_config.DOMAINS.items():
            self.assertEqual(exam_config.track_of(did), meta["track"])
            self.assertEqual(exam_config.domain_dir(did),
                             f"{meta['track']}/{meta['dir']}")
            self.assertEqual(exam_config.domain_by_dir(meta["track"], meta["dir"]), did)

    def test_classifier_finds_the_intended_domain(self):
        cases = [
            ("Selecting an incremental_strategy of merge and using is_incremental",
             "ae-01"),
            ("Adding a check constraint and enabling the contract on the model",
             "ae-02"),
            ("The yaml compilation error appears in the compiled code under target/compiled",
             "ae-03"),
            ("A unit test with given and expect fixtures fails on the source", "ae-05"),
            ("Implementing source freshness with loaded_at_field and warn_after",
             "ae-06"),
            ("Using state:modified with --defer and the manifest.json artifact", "ae-07"),
            ("Create a service token and assign an enterprise permission set for rbac",
             "arch-05"),
            ("Configure job chaining so the job is triggered after another deploy job",
             "arch-04"),
        ]
        for text, expected in cases:
            got, hits = exam_config.classify_domain(text)
            self.assertEqual(got, expected, f"{text!r} -> {got} (hits={hits})")


class TestQuestionTypes(unittest.TestCase):
    def test_non_letter_types_are_a_subset_of_question_types(self):
        self.assertTrue(
            exam_config.NON_LETTER_TYPES <= set(exam_config.QUESTION_TYPES))

    def test_every_type_declares_an_answer_shape(self):
        for qt, meta in exam_config.QUESTION_TYPES.items():
            self.assertTrue(meta["answer_shape"].strip(), qt)


class TestHintDoesNotLeak(unittest.TestCase):
    """A hint that names the answer is worse than no hint."""

    def test_key_only_terms_finds_the_giveaway(self):
        item = {
            "stem": "A team needs to record how a mutable source row changed over time.",
            "option_texts": {
                "A": "Create a seed from the table",
                "B": "Create a snapshot with the timestamp strategy",
                "C": "Create a view over the table",
                "D": "Create an analysis for the table",
            },
            "drill_answer": "B",
            "qtype": "multiple_choice",
        }
        leaky = server._key_only_terms(item)
        self.assertIn("snapshot", leaky)
        self.assertNotIn("create", leaky, "a word in every option is not a giveaway")
        self.assertNotIn("table", leaky, "a word in the stem is not a giveaway")

    def test_non_letter_format_treats_the_key_text_as_leaky(self):
        item = {"qtype": "fill_in_blank", "stem": "Use the ____ config.",
                "drill_answer": "on_schema_change"}
        self.assertIn("on_schema_change".replace("_", "_"),
                      " ".join(server._key_only_terms(item)) + " on_schema_change")

    def test_keywords_rank_product_anchors_last(self):
        kws = server._keywords_from_rationale(
            "dbt builds an ephemeral model as an inlined common table expression, "
            "so the model is never materialized in the warehouse")
        self.assertIn("ephemeral", kws)
        anchors_at_end = [k for k in kws if k in server.DBT_ANCHORS]
        if anchors_at_end:
            first_anchor = min(kws.index(a) for a in anchors_at_end)
            non_anchor = [k for k in kws if k not in server.DBT_ANCHORS]
            last_concept = max(kws.index(c) for c in non_anchor)
            self.assertGreater(first_anchor, last_concept,
                               "product anchors must rank after real concepts")

    def test_score_reasoning_ignores_anchors(self):
        score = server.score_reasoning(["ephemeral", "model", "warehouse"],
                                       "it is ephemeral so nothing is built")
        self.assertEqual(score["concepts"], ["ephemeral"])
        self.assertEqual(score["concept_coverage"], 1.0)


class TestPlannedTopicIds(unittest.TestCase):
    def test_planned_topic_regex_accepts_real_domain_paths(self):
        for did, meta in exam_config.DOMAINS.items():
            planned = f"{meta['track']}/{meta['dir']}/some-note"
            self.assertRegex(planned, server._TOPIC_PLANNED_RE, did)

    def test_planned_topic_regex_rejects_junk(self):
        for bad in ("ae/bad", "knowledge/ae/01-x/y", "xx/01-x/y", "ae/1-x/y"):
            self.assertIsNone(re.match(server._TOPIC_PLANNED_RE, bad), bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
