# mcp-toolkit

**Question.** Can a small, standard-library MCP-style tool server
enforce authentication, roles and named safety rules before any tool
runs, and say why it refused?

**Headline.** Over authenticated HTTP on localhost, a scripted 30-call
plan got 8 successes and 18 refusals, each with a named reason and an
audit entry (3 unauthenticated, 2 role blocks, 13 safety blocks), plus 4
named errors; on a 22-case hand-labelled corpus the SQL guard made 5
false positives and 4 false negatives. These are exact counts on fixed,
deterministic inputs, so no interval applies; they are not rates for
real traffic.

**Field.** Software product. **Job family.** AI agent and tooling
engineering.

**Verdict.** Functional, not pre-registered. Tests pass in CI on Python
3.11 and 3.12, the three level runners reproduce every committed trace
byte for byte by one command each, and the Deep server has run end to
end over real HTTP (level-3-deep/results_deep.json). No plan was locked
before the results, so the verdict is capped at Functional; the
Software product profile is not yet met (REPORT.md, Misses).

Live dashboard: https://jesunahmadushno.github.io/mcp-toolkit/ (built
from the committed results files; the safety rule playground runs a
JavaScript port of the Deep guard in your browser, checked against the
recorded runs at build time).

## Reproduce

```text
python3 -m unittest discover -s tests -p "test_*.py" -v
python3 level-1-learn/run_learn.py
python3 level-2-build/run_build.py
python3 level-3-deep/run_deep.py
python3 level-3-deep/guard_corpus.py
git diff --exit-code -- level-1-learn level-2-build level-3-deep
```

Python 3 standard library only, CPU, under a few seconds. The last line
proves the committed results were regenerated unchanged.
level-3-deep/bench_latency.py is machine specific and is not part of
the byte-for-byte check.

## Lifecycle

- Question: DONE 2026-11-04
- Proposal: NOT PRE-REGISTERED 2026-11-08
- Baseline: DONE 2026-11-05
- Build: DONE 2026-11-05
- Evaluate: PARTIAL 2026-11-07
- Report: DONE 2026-11-08
- Review: OPEN
- Release: OPEN

v0.1, v0.5 and v1.0 are earlier tags from the Learn / Build / Deep
ladder; no release has been cut under the portfolio standard v2 yet.

## Layout

| Path | What it holds |
| --- | --- |
| PROPOSAL.md | Question, scope, prior work and proposed novelty (not pre-registered; replaces SPEC.md, NOVELTY.md, DOSSIER.md) |
| REPORT.md | Background, method, results tables, post-hoc hypotheses, misses, threat model, remaining gaps, future work (replaces ROADMAP.md and docs/research-review.md) |
| level-1-learn/ | Code, runner and evidence for the in-process protocol: mcp_learn.py, run_learn.py, results_learn.json |
| level-2-build/ | Code, runner and evidence over stdio subprocesses: mcp_build.py, server_main.py, run_build.py, results_build.json |
| level-3-deep/ | Code, runners and evidence over authenticated HTTP: mcp_deep.py, run_deep.py, guard_corpus.py, bench_latency.py, deep_plan.json, results_deep.json, results_guard.json, results_latency.json |
| tests/ | Unit tests per level, docs-match-results test, layout and no-public-grade test |
| docs/decisions/ | Records of hard-to-reverse choices |
| fanout/ | Dated drafts (blog, tutorial, paper candidate, release notes) and the publicity log |
| site/ | The live dashboard, built from the files above |
| CHANGELOG.md, CITATION.cff, SECURITY.md, LICENSE | Release history, citation, vulnerability reporting, licence |

There is no src/, experiments/ or results/ folder: each level keeps its
code, its scripted plan and its results file together, because the
runners, tests, dashboard and Pages workflow all address them there
(docs/decisions/0001).

## License

Code: Apache-2.0 (see LICENSE). Tutorials: CC BY 4.0. Ruled in D-V3-11, 2026-11-04.
