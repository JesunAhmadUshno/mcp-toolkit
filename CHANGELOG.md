# Changelog

All notable changes to this project. Format: Keep a Changelog 1.1.
Versions follow Semantic Versioning. v0.1, v0.5 and v1.0 were tagged
under the earlier Learn / Build / Deep ladder; no release has been cut
under the portfolio standard v2 yet.

## [Unreleased]

### Changed
- 2026-11-08: Restructured to the portfolio standard v2. README is the
  abstract (question, headline, field, job family, verdict, reproduce,
  lifecycle, layout). PROPOSAL.md replaces SPEC.md, NOVELTY.md and
  DOSSIER.md (Past) and records that the repo is not pre-registered.
  REPORT.md takes the measured results tables from the README, DOSSIER.md
  (Present), docs/research-review.md and the ROADMAP.md backlog (as
  Future work). PUBLICITY.md moved to fanout/ with the README fan-out
  list. Code and evidence stay in the level folders (decision 0001).
- 2026-11-08: Grades removed from every public file (level READMEs,
  README, DOSSIER, ROADMAP, research review scorecard, publicity log,
  fan-out drafts, dashboard). Each level README's grade section became
  a "Known limits" list with the same items, without point values. The
  dashboard's grade panel now shows those limits. The Jev-gated blog
  paragraph changed only by removing the grade figures.
- 2026-11-08: CI runs on Python 3.11 and 3.12 with read-only token
  permissions; tests/test_smoke.py now checks the standard's required
  files and that no public file carries a grade.

### Added
- 2026-11-08: CodeQL (Python, JavaScript), Dependabot (GitHub Actions,
  npm in site/), CHANGELOG.md, CITATION.cff, SECURITY.md,
  docs/decisions/0001.

### Security
- 2026-11-07: vite raised to 5.4.21 and then 6.4.5; npm audit in site/
  reports no high or critical advisories. The dev server may read only
  site/ and the files the page imports.

### Added (2026-11-07)
- Labelled guard corpus (level-3-deep/guard_corpus.py,
  results_guard.json): 22 SQL cases, 17 path cases, and an HTTP replay
  of the 30-call Deep plan (deep_plan.json).
- Localhost latency measurement (level-3-deep/bench_latency.py,
  results_latency.json), machine specific.
- Test that README counts match the results JSON; CI runs the full
  suite, reruns the runners and fails if a results file changes.
- Live dashboard (site/) with a JavaScript port of the Deep guard held
  to the Python runs by a build-time parity check; Pages workflow.
- Research review with threat model and costed gaps (now in REPORT.md).

## [1.0] - 2026-11-05

### Added
- Deep (compressed Deep under the December protocol): remote MCP over
  HTTP on localhost, bearer token authentication by hash comparison,
  reader and operator roles with server-side allowlists, the full tool
  safety rules set with named block reasons and an audit log, measured
  on 30 scripted calls. 28 Deep tests, 65 in the suite.
- Written fan-out set in fanout/.

## [0.5] - 2026-11-05

### Added
- Build: host over real stdio to 3 server processes, 6 tools, safety
  rules retained, measured on 24 scripted calls. 20 Build tests.

## [0.1] - 2026-11-05

### Added
- Learn: in-process MCP-style protocol, file and database servers,
  first safety rules, measured on 18 scripted calls. 17 tests.

## 2026-11-04

### Added
- Scaffold: SPEC.md, DOSSIER.md v1, NOVELTY.md draft, level folders,
  smoke test, CI, Apache-2.0 licence.
