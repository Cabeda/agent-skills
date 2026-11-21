"""Checks on the review and factory skills' own files. Run: python3 -m unittest discover -s skills/forge/tests

A description with ": " in it is a YAML mapping, and the skills installer skips the whole
skill without failing the build. These tests make that a failure here instead.
"""

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
FACTORY = [
    "code-factory",
    "forge",
    "merge-pass",
    "issue-worker",
    "codebase-audit",
    "expert-review",
    "review-loop",
    "dependency-update",
]
EXPERTS = SKILLS / "expert-review" / "experts"


def frontmatter(path):
    """Read the fields between the ``---`` lines. A one-line ``key: value`` parser, like the installer's."""
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.DOTALL)
    if not match:
        raise AssertionError(f"{path}: no frontmatter")
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(": ")
        fields[key] = value
    return fields


class SkillFileTests(unittest.TestCase):
    def test_every_factory_skill_has_a_name_that_matches_its_folder(self):
        for name in FACTORY:
            with self.subTest(skill=name):
                self.assertEqual(frontmatter(SKILLS / name / "SKILL.md")["name"], name)

    def test_no_description_or_use_when_contains_a_colon_and_space(self):
        files = [SKILLS / n / "SKILL.md" for n in FACTORY] + sorted(EXPERTS.glob("*.md"))
        for path in files:
            for key in ("description", "use-when"):
                value = frontmatter(path).get(key)
                if value is None:
                    continue
                with self.subTest(file=str(path.relative_to(SKILLS)), key=key):
                    self.assertNotIn(
                        ": ", value.strip("\"'"), "quote the value or reword it: YAML reads ': ' as a mapping"
                    )

    def test_descriptions_stay_short_because_they_are_always_loaded(self):
        for name in FACTORY:
            with self.subTest(skill=name):
                self.assertLessEqual(len(frontmatter(SKILLS / name / "SKILL.md")["description"].split()), 45)

    def test_every_expert_has_the_fields_the_picker_reads(self):
        for path in sorted(EXPERTS.glob("*.md")):
            with self.subTest(expert=path.stem):
                fields = frontmatter(path)
                self.assertEqual(fields["name"], path.stem)
                self.assertTrue(fields["use-when"])

    def test_every_leave_to_reference_names_an_expert_that_exists(self):
        names = {p.stem for p in EXPERTS.glob("*.md")}
        for path in sorted(EXPERTS.glob("*.md")):
            with self.subTest(expert=path.stem):
                referenced = set(re.findall(r"to `([a-z-]+)`", path.read_text()))
                self.assertLessEqual(referenced, names)

    def test_every_relative_link_in_the_factory_docs_resolves(self):
        docs = [SKILLS / n / "SKILL.md" for n in FACTORY] + [
            SKILLS / "code-factory" / "SETUP.md",
            SKILLS / "expert-review" / "ADDING-EXPERTS.md",
        ]
        for doc in docs:
            for link in re.findall(r"\]\(((?!https?:|#)[^)\s]+)\)", doc.read_text()):
                with self.subTest(doc=str(doc.relative_to(SKILLS)), link=link):
                    self.assertTrue((doc.parent / link.split("#")[0]).exists())

    def test_the_example_config_loads_and_opts_in_nothing_but_a_placeholder(self):
        import sys

        sys.path.insert(0, str(SKILLS / "forge" / "scripts"))
        import tempfile

        import forge

        folder = Path(tempfile.mkdtemp())
        (folder / "factory.toml").write_text((SKILLS / "code-factory" / "factory.example.toml").read_text())
        cfg = forge.load_config(folder)
        self.assertTrue(cfg["defaults"]["dry-run"])
        self.assertFalse(cfg["defaults"].get("auto-merge", False))
        self.assertTrue(cfg["defaults"]["skip"])


if __name__ == "__main__":
    unittest.main()
