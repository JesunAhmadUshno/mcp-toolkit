"""Docs and data cannot drift apart.

1. The README tables and level README summaries quote the same counts
   as the summary blocks of the committed results JSON files.
2. The committed guard corpus results and Deep plan export are exactly
   what level-3-deep/guard_corpus.py produces now, and the HTTP replay
   of the plan still matches results_deep.json.
"""
import io
import json
import os
import re
import sys
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "level-3-deep"))
import guard_corpus  # noqa: E402


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def text(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return " ".join(f.read().split())


class TestDocsMatchResults(unittest.TestCase):
    def setUp(self):
        self.readme = text("README.md")
        self.learn = load("level-1-learn/results_learn.json")["summary"]
        self.build = load("level-2-build/results_build.json")["summary"]
        self.deep_all = load("level-3-deep/results_deep.json")
        self.deep = self.deep_all["summary"]

    def assertQuoted(self, needle, doc=None):
        self.assertIn(needle, doc if doc is not None else self.readme)

    def test_learn_and_build_rows(self):
        for name, s in (("Learn", self.learn), ("Build", self.build)):
            self.assertQuoted("| %s protocol calls | %d total |" % (name, s["total_calls"]))
            self.assertQuoted("| Calls succeeded | %d of %d |" % (s["successes"], s["total_calls"]))
            rules = s["blocked_by_rule"]
            self.assertQuoted("| Calls blocked by safety rules | %d (path_traversal %d, write_blocked %d) |"
                              % (s["blocked"], rules["path_traversal"], rules["write_blocked"]))
            self.assertQuoted("| Calls returned named protocol errors | %d |" % s["errors"])
        self.assertQuoted("| Tools aggregated by the host | %d (file 2, database 2) |" % self.learn["total_tools"])
        self.assertQuoted("| Tools aggregated by the host | %d (file 2, database 2, calc 2) |" % self.build["total_tools"])

    def test_deep_rows(self):
        s = self.deep
        self.assertQuoted("| Deep protocol calls | %d total |" % s["total_calls"])
        self.assertQuoted("| Calls succeeded | %d of %d |" % (s["successes"], s["total_calls"]))
        self.assertQuoted("| Unauthenticated rejections (HTTP 401) | %d |" % s["unauthenticated"])
        self.assertQuoted("| Role blocks (HTTP 403, forbidden_role) | %d |" % s["role_blocked"])
        row = re.search(r"\| Calls blocked by safety rules \| (\d+) \(([^)]*)\) \|", self.readme.split("Deep protocol calls")[1])
        self.assertEqual(int(row.group(1)), s["safety_blocked"])
        quoted = dict((k, int(v)) for k, v in re.findall(r"(\w+) (\d+)", row.group(2)))
        self.assertEqual(quoted, s["safety_by_reason"])
        cats = {}
        for e in self.deep_all["audit_log"]:
            cats[e["category"]] = cats.get(e["category"], 0) + 1
        self.assertEqual(len(self.deep_all["audit_log"]), s["audit_entries"])
        self.assertQuoted("| Audit log entries | %d (%d auth, %d authorization, %d safety) |"
                          % (s["audit_entries"], cats["auth"], cats["authorization"], cats["safety"]))
        self.assertQuoted("| Tools exposed | %d (reader sees %d, operator sees %d) |"
                          % (s["total_tools"], s["reader_tools"], s["operator_tools"]))

    def test_level_summaries(self):
        self.assertQuoted("Summary: %d protocol calls in total: %d successes, %d blocked, and %d errors."
                          % (self.learn["total_calls"], self.learn["successes"], self.learn["blocked"],
                             self.learn["errors"]), text("level-1-learn/README.md"))
        self.assertQuoted("Summary: %d protocol calls in total: %d successes, %d blocked, and %d errors."
                          % (self.build["total_calls"], self.build["successes"], self.build["blocked"],
                             self.build["errors"]), text("level-2-build/README.md"))
        s = self.deep
        self.assertQuoted("Summary: %d protocol calls in total: %d successes, %d unauthenticated (HTTP 401), "
                          "%d role blocks (HTTP 403), %d safety blocks, and %d errors."
                          % (s["total_calls"], s["successes"], s["unauthenticated"], s["role_blocked"],
                             s["safety_blocked"], s["errors"]), text("level-3-deep/README.md"))

    def test_guard_corpus_row(self):
        g = load("level-3-deep/results_guard.json")["summary"]
        for name in ("sql", "path"):
            c = g[name]
            self.assertRegex(self.readme, r"\b%d cases: %d false positives?, %d false negatives?\b"
                             % (c["cases"], c["false_positive"], c["false_negative"]))


class TestGuardCorpusReproduces(unittest.TestCase):
    def test_committed_files_match_a_fresh_run(self):
        paths = [os.path.join(ROOT, "level-3-deep", n)
                 for n in ("results_guard.json", "deep_plan.json")]
        before = [open(p, "rb").read() for p in paths]
        with redirect_stdout(io.StringIO()):
            code = guard_corpus.main()
        after = [open(p, "rb").read() for p in paths]
        self.assertEqual(code, 0, "Deep plan replay no longer matches results_deep.json")
        self.assertEqual(before, after, "committed guard files are stale; rerun guard_corpus.py")

    def test_plan_has_thirty_calls(self):
        self.assertEqual(len(load("level-3-deep/deep_plan.json")), 30)


if __name__ == "__main__":
    unittest.main()
