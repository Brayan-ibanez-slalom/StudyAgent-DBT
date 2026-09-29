"""Guard the docs against drifting away from exam_config.py.

Every stale-domain finding in the 2026-09-29 audit was a markdown file naming a
knowledge/ folder that no longer existed after the domains were rewritten. Prose does
not fail a build, so it silently rotted. These tests make it fail loudly instead.
"""
from __future__ import annotations

import pathlib
import re
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "mcp-server"))

from study_agent_mcp import exam_config  # noqa: E402

# Every markdown file that can legitimately reference the domain layout.
DOC_GLOBS = ("README.md", "docs/*.md", "knowledge/*.md", "question-bank/*.md",
             ".github/*.md", ".github/**/*.md")

# knowledge/<track>/<domain-dir>/... appearing anywhere in prose, a path, or JSON.
KNOWLEDGE_PATH_RE = re.compile(r"knowledge/(ae|arch)/([0-9a-z][0-9a-z\-]+)")

# A bare '<track>/<domain-dir>/<note>' planned-topic id, which ingest_seal also accepts.
PLANNED_TOPIC_RE = re.compile(r"(?<![\w/])(ae|arch)/(\d{2}-[a-z][a-z0-9\-]+)/[a-z]")

DOMAIN_ID_RE = re.compile(r"\b(ae|arch)-(\d{2})\b")


def _docs() -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for pattern in DOC_GLOBS:
        found.extend(p for p in REPO_ROOT.glob(pattern) if p.is_file())
    return sorted(set(found))


class TestDocsMatchExamConfig(unittest.TestCase):
    def setUp(self):
        self.valid_dirs = {
            (m["track"], m["dir"]) for m in exam_config.DOMAINS.values()}
        self.docs = _docs()

    def test_there_are_docs_to_check(self):
        self.assertGreater(len(self.docs), 10, "doc discovery globs matched almost nothing")

    def test_every_knowledge_path_names_a_real_domain_folder(self):
        bad = []
        for doc in self.docs:
            for lineno, line in enumerate(doc.read_text().splitlines(), 1):
                for track, dirname in KNOWLEDGE_PATH_RE.findall(line):
                    if (track, dirname) not in self.valid_dirs:
                        bad.append(f"{doc.relative_to(REPO_ROOT)}:{lineno} -> "
                                   f"knowledge/{track}/{dirname}")
        self.assertEqual(bad, [], "docs reference knowledge folders that do not exist:\n"
                                  + "\n".join(bad))

    def test_every_planned_topic_id_names_a_real_domain_folder(self):
        bad = []
        for doc in self.docs:
            for lineno, line in enumerate(doc.read_text().splitlines(), 1):
                for track, dirname in PLANNED_TOPIC_RE.findall(line):
                    if (track, dirname) not in self.valid_dirs:
                        bad.append(f"{doc.relative_to(REPO_ROOT)}:{lineno} -> "
                                   f"{track}/{dirname}")
        self.assertEqual(bad, [], "docs use planned topic ids for unknown domains:\n"
                                  + "\n".join(bad))

    def test_every_domain_id_mentioned_in_docs_exists(self):
        bad = []
        for doc in self.docs:
            for lineno, line in enumerate(doc.read_text().splitlines(), 1):
                for track, num in DOMAIN_ID_RE.findall(line):
                    did = f"{track}-{num}"
                    if did not in exam_config.VALID_DOMAINS:
                        bad.append(f"{doc.relative_to(REPO_ROOT)}:{lineno} -> {did}")
        self.assertEqual(bad, [], "docs mention domain ids that do not exist:\n"
                                  + "\n".join(bad))

    def test_knowledge_folders_on_disk_match_exam_config(self):
        kdir = REPO_ROOT / "knowledge"
        on_disk = {(t.name, d.name)
                   for t in kdir.iterdir() if t.is_dir() and not t.name.startswith("_")
                   for d in t.iterdir() if d.is_dir()}
        self.assertEqual(
            on_disk, self.valid_dirs,
            "knowledge/ folders disagree with exam_config.DOMAINS — run "
            "scripts/bootstrap_repo.py")


class TestAuthoredDraftsMatchExamConfig(unittest.TestCase):
    """A draft pointing at a dead domain would be rejected at ingest; catch it earlier."""

    def test_authored_drafts_use_real_domains_and_tasks(self):
        import json
        authored = REPO_ROOT / "question-bank" / "authored"
        problems = []
        for path in sorted(authored.glob("*.json")):
            payload = json.loads(path.read_text())
            for item in (payload if isinstance(payload, list) else [payload]):
                did = item.get("domain")
                task = item.get("blueprint_task")
                if did not in exam_config.VALID_DOMAINS:
                    problems.append(f"{path.name}: domain {did!r} does not exist")
                elif task and task not in exam_config.DOMAINS[did]["tasks"]:
                    problems.append(f"{path.name}: task {task!r} not in {did}")
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
