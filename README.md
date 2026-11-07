# mcp-toolkit

An MCP server and host toolkit with authentication and tool safety rules.

Live dashboard: https://jesunahmadushno.github.io/mcp-toolkit/ (built from the committed results files in this repo; the safety rule playground runs a JavaScript port of the Deep guard in your browser, checked against the recorded runs at build time).

Status: Learn DONE, Build DONE, and Deep DONE (2026-11-05, ROADMAP-V3-BATCH). All three levels are built, tested, and measured below. Deep ships as v1.0; the rest of the v2 Deep scope is the v1.1 backlog in ROADMAP.md.
Project: P09. Fleet node: BlackBoxV2. Wave: Wave 4. All levels were run on the Muse VM (CPU); see the level READMEs for the named deduction.

## Start here

1. Read SPEC.md for scope and acceptance criteria.
2. Read DOSSIER.md for the past, present, and future of this problem (v1).
3. Read NOVELTY.md for the proposed novelty (DRAFT, pending the Jev claim_check gate).
4. Start at level-1-learn/README.md, then level-2-build, then level-3-deep.

## Level map

- Level 1, Learn: the core idea, built small and clean, with a teaching path.
- Level 2, Build: a real working system other people can run.
- Level 3, Deep: benchmarks, optimization, evaluation, hard cases.

## Measured results

The call tables are deterministic correctness traces of protocol calls, not performance benchmarks. A separate small localhost latency measurement, machine specific and not deterministic, follows the guard corpus at the end of this section.

Measured 2026-11-05 with level-1-learn/run_learn.py on the Muse VM, Python 3.12. The implementation is an in-process MCP-style teaching protocol, not the official MCP SDK.

| Test | Result |
| --- | --- |
| Learn protocol calls | 18 total |
| Calls succeeded | 10 of 18 |
| Calls blocked by safety rules | 4 (path_traversal 2, write_blocked 2) |
| Calls returned named protocol errors | 4 |
| Tools aggregated by the host | 4 (file 2, database 2) |
| Unit tests | 17 passed |
| Determinism | results_learn.json identical across two runs (hash verified) |

Measured 2026-11-05 with level-2-build/run_build.py on the Muse VM, Python 3.12. The Build implementation is an MCP-style protocol over stdio subprocess transport, not the official MCP SDK.

Main claim: P09 mcp-toolkit Level 2 Build ran 24 protocol calls end to end over stdio subprocess transport with 14 successes, 4 blocked, and 6 errors, aggregating 6 tools across 3 servers.

| Test | Result |
| --- | --- |
| Build protocol calls | 24 total |
| Calls succeeded | 14 of 24 |
| Calls blocked by safety rules | 4 (path_traversal 2, write_blocked 2) |
| Calls returned named protocol errors | 6 |
| Tools aggregated by the host | 6 (file 2, database 2, calc 2) |
| Servers connected over stdio | 3 (file, database, calc) |
| Build unit tests | 20 passed (37 in the full suite) |
| Build grade | 8,600 of 10,000 |
| Determinism | results_build.json identical across two runs, sha256 6e56a8d61e38 |

Measured 2026-11-05 with level-3-deep/run_deep.py on the Muse VM, Python 3.12. The Deep implementation is an MCP-style protocol over real HTTP on localhost with bearer token authentication, not the official MCP SDK.

Main claim: P09 mcp-toolkit Level 3 Deep ran 30 protocol calls over authenticated HTTP with 8 successes, 3 unauthenticated rejections, 2 role blocks, 13 safety blocks, and 4 errors, exposing 6 tools under 2 roles.

| Test | Result |
| --- | --- |
| Deep protocol calls | 30 total |
| Calls succeeded | 8 of 30 |
| Unauthenticated rejections (HTTP 401) | 3 |
| Role blocks (HTTP 403, forbidden_role) | 2 |
| Calls blocked by safety rules | 13 (path_traversal 2, absolute_path_blocked 1, write_blocked 1, delete_blocked 1, sql_not_select 4, sql_multi_statement 2, request_too_large 1, unknown_tool 1) |
| Calls returned named protocol errors | 4 |
| Audit log entries | 18 (3 auth, 2 authorization, 13 safety) |
| Tools exposed | 6 (reader sees 4, operator sees 6) |
| Roles | 2 (reader, operator) |
| Deep unit tests | 28 passed (65 in the full suite) |
| Deep grade | 8,300 of 10,000 |
| Determinism | results_deep.json identical across two runs, sha256 8c1d115e520e |

Guard corpus, measured 2026-11-07 with level-3-deep/guard_corpus.py (CPU, under 1 second). It runs the Deep SQL guard and the read_file path rules over a labelled list of benign and malicious inputs and writes level-3-deep/results_guard.json. Labels follow the tool contracts: run_query is one read-only SELECT on the items table, read_file is one file inside the sandbox. SQL cases are checked by the guard only, never executed.

| Guard | Result |
| --- | --- |
| SQL guard (_check_sql) | 22 cases: 5 false positives, 4 false negatives |
| Path rules (read_file) | 17 cases: 1 false positive, 0 false negatives |
| Deep plan replay | the 30 inputs in level-3-deep/deep_plan.json, replayed over HTTP, match results_deep.json call for call |

False positives on SQL: a read-only CTE (WITH ... SELECT), the word drop inside a string literal, the replace() function, a leading comment, and a semicolon inside a comment. False negatives on SQL: reads of sqlite_master (directly and through UNION), an expensive randomblob() call, and a load_extension() call. The path false positive is sub/../hello.txt, which stays inside the sandbox but is blocked by the strict .. rule. The corpus is small and hand-labelled, so these are counts on these cases, not rates for real traffic.

Latency, measured 2026-11-07 with level-3-deep/bench_latency.py on a Linux aarch64 machine (20 CPUs, Python 3.12.3), not the fleet node. Localhost loopback and tiny fixtures, so this is framework overhead, not a deployment benchmark; results_latency.json records the machine and differs between runs.

| Request kind (300 sequential calls each) | Median | p95 |
| --- | --- | --- |
| calculate_role_blocked | 0.634 ms | 0.876 ms |
| read_file_allowed | 0.573 ms | 0.921 ms |
| read_file_path_traversal | 0.528 ms | 0.842 ms |
| run_query_select | 0.579 ms | 0.876 ms |
| unauthenticated | 0.632 ms | 0.876 ms |
| 8 threads, 800 read_file calls | 624.7 calls/s | wall 1.281 s |

## Novelty

PROPOSED. See NOVELTY.md. The novelty text is a draft until the Jev claim_check gate passes on it.

## Fan-out

Written fan-out set for v1.0, dated 2026-11-05, in fanout/:

- fanout/blog-post.md: "Tools With Rules", the full story with
  the main results claim gated by Jev claim_check (model
  jev-1.13.0, noul 0.84, route REVIEW, no block).
- fanout/tutorial.md: course module P09-mcp-toolkit. Every
  command in it was executed and passed on 2026-11-05 (all
  three runners, all per-level tests, full suite at 65 tests).
- fanout/website-page.md: project page copy only, not published.
- fanout/linkedin-post.md: DRAFT NOT POSTED, link as the
  first-comment line per the LinkedIn rule.
- fanout/paper-candidate.md: tool safety rules note at
  CANDIDATE. Submission is Jesun's tap, nothing submitted.
- fanout/release-notes.md: draft notes for the live releases
  v0.1, v0.5, and v1.0.

Publicity grades and the channel log are in PUBLICITY.md.
Overall fan-out grade: 9,533 of 10,000. The loop never posts
to social: all social channels are held with named reasons in
PUBLICITY.md.

## License

Code: Apache-2.0 (see LICENSE). Tutorials: CC BY 4.0. Ruled in D-V3-11, 2026-11-04.
