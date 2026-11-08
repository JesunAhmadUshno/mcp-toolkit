"""Portfolio standard checks: the required files exist and no public file carries a grade.

Runs under unittest discovery and as a script (CI calls it directly).
There is no lock test: the repo is not pre-registered (PROPOSAL.md).
"""
import glob
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = ["README.md", "PROPOSAL.md", "REPORT.md", "CHANGELOG.md", "CITATION.cff", "SECURITY.md", "LICENSE",
            "docs/decisions/0001-keep-level-folders.md",
            "level-1-learn/run_learn.py", "level-1-learn/results_learn.json",
            "level-2-build/run_build.py", "level-2-build/results_build.json",
            "level-3-deep/run_deep.py", "level-3-deep/results_deep.json",
            "level-3-deep/guard_corpus.py", "level-3-deep/results_guard.json"]
# Grades are internal (portfolio standard v2, section 5).
GRADE = re.compile(r"of 10,000|/ ?10,?000\b|\bGrade:|^#+ .*\bGrades?\b|/1000\b|\bgrade (\| )?[\d,]+", re.I | re.M)


def public_files():
    pats = ["*.md", "docs/**/*.md", "fanout/*.md", "level-*/README.md", "site/index.html", "site/src/*.js*",
            "site/src/*.mjs"]
    for pat in pats:
        yield from glob.glob(os.path.join(ROOT, pat), recursive=True)


class TestLayout(unittest.TestCase):
    def test_required_files_exist(self):
        missing = [p for p in REQUIRED if not os.path.exists(os.path.join(ROOT, p))]
        self.assertFalse(missing, "missing: " + ", ".join(missing))

    def test_readme_abstract(self):
        text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
        for field in ("**Question.**", "**Headline.**", "**Field.**", "**Job family.**", "**Verdict.**",
                      "## Reproduce", "## Lifecycle", "## Layout"):
            self.assertIn(field, text)

    def test_no_public_grade(self):
        hits = []
        for path in public_files():
            for n, line in enumerate(open(path, encoding="utf-8"), 1):
                if GRADE.search(line):
                    hits.append("%s:%d: %s" % (os.path.relpath(path, ROOT), n, line.strip()))
        self.assertFalse(hits, "grades are internal:\n" + "\n".join(hits))

    def test_grade_pattern_catches_a_grade(self):
        for bad in ("Grade 8,300 of 10,000", "| Build grade | 8,600 |", "## Grade", "Grade: A", "Total /1000"):
            self.assertTrue(GRADE.search(bad), bad)


if __name__ == "__main__":
    unittest.main()
