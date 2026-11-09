# Report: mcp-toolkit (P09)

Status: Build and a first evaluation are done; the repo is **not
pre-registered** (PROPOSAL.md says why), so no result below is
confirmatory and the verdict is capped at Functional. Every number here
comes from a committed file in this repo, named beside it, and the
consistency test (tests/test_results_consistency.py) fails if this file
and the results JSON disagree.

## Background

Agent tools are powerful by default, so a tool host needs a protocol
shape, a sandbox, and rules about what a tool may never do. This
project builds that shape three times, each a step closer to a real
deployment: in process (Learn, v0.1), over stdio subprocesses (Build,
v0.5) and over authenticated HTTP on localhost (Deep, v1.0). The prior
art is the MCP reference servers; nothing has been compared against
them yet (PROPOSAL.md, Proposed novelty).

State at the v1.0 ship, 2026-11-05 (from DOSSIER.md, Present):

Ship state, 2026-11-05: all three levels DONE, release v1.0.

- Learn: 18 protocol calls, 10 successes, 4 safety blocks, 4 errors, 4 tools, 17 unit tests at its level record.
- Build: 24 protocol calls over stdio, 14 successes, 4 blocked, 6 errors, 6 tools across 3 servers, 20 Build unit tests.
- Deep (compressed, December protocol): remote MCP over HTTP on localhost (POST /mcp), bearer token authentication checked by SHA-256 hash comparison with token hashes loaded from the environment at server start, two roles with server-side allowlists (reader: 4 read tools; operator: all 6 tools), and the full safety rules set with named block reasons and an audit log (path traversal, absolute path outside sandbox, write attempts, delete attempts, SQL that is not a single read-only SELECT including multi-statement input, oversize requests, unknown tools). Measured: 30 protocol calls, 8 successes, 3 unauthenticated rejections, 2 role blocks, 13 safety blocks, 4 errors, 18 audit entries. 28 Deep unit tests; 65 tests in the full suite, all passing. Limits named in level-3-deep/README.md (largest: localhost HTTP only with no TLS, and token auth as a teaching design).
- Evidence: level-1-learn/results_learn.json, level-2-build/results_build.json, level-3-deep/results_deep.json, each deterministic across two runs with hashes recorded in the level READMEs. Jev claim_check on the Deep main claim is recorded in the batch ledger for this goal.
- Current demand evidence: MCP is on the Apple preferred list [confirmed, fleet and scoring pass 2026-11-04]. The Round 3 research (2026-11-04) found the market centre at post-training, evals, environments, and inference depth [confirmed as the research finding; the report is at ~/workspace/research_notes/roadmap-v3-revaluation-research-20261104-0949/report.md].

## Method

- Each level has a scripted plan of protocol calls (Learn 18, Build 24,
  Deep 30), run by its runner (level-*/run_*.py) and written to a
  results JSON. The plans are deterministic, so CI reruns them and fails
  if any committed results file changes by a single byte.
- The Deep plan inputs are exported to level-3-deep/deep_plan.json and
  replayed over HTTP by level-3-deep/guard_corpus.py, which also runs
  the SQL guard and the read_file path rules over a hand-labelled corpus
  of benign and malicious inputs (results_guard.json).
- A small localhost latency measurement (level-3-deep/bench_latency.py,
  results_latency.json) is machine specific and kept out of the
  byte-for-byte check.
- The live dashboard rebuilds from the same files, and its build fails
  unless the JavaScript port of the Deep guard agrees with the recorded
  runs and the corpus verdicts (site/src/guard.check.mjs).

## Results

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

## Hypotheses

None were stated before the runs (not pre-registered). The 2026-11-07
self-review named one implicit hypothesis after the fact, scored here
so the miss is shown:

| Hypothesis (post hoc) | Evidence | Outcome |
| --- | --- | --- |
| The token and first-word SQL guard separates safe from unsafe SQL | level-3-deep/results_guard.json: 22 SQL cases, 8 true positives, 5 true negatives, 5 false positives, 4 false negatives | Refuted on this corpus |
| The path rules keep read_file inside the sandbox | level-3-deep/results_guard.json: 17 path cases, 0 false negatives, 1 false positive (sub/../hello.txt) | Holds on this corpus, with one over-block |

## Misses

- The SQL guard misses reads of sqlite_master (directly and through
  UNION), an expensive randomblob() call and a load_extension() call,
  and wrongly blocks five harmless queries (Results, guard corpus).
- No baseline: nothing is compared against the MCP reference servers or
  the official SDK.
- Software product profile, not yet met: coverage is not reported,
  there is no secret scan or Python dependency audit beyond CodeQL and
  Dependabot, and there is no written upgrade path for users. Tests do
  run through the public interface (protocol messages, HTTP), input
  validation is the subject of the safety rules, release notes exist
  (fanout/release-notes.md, GitHub releases v0.1, v0.5, v1.0) and npm
  audit on site/ is clean.
- Every run was on the Muse VM or a Linux aarch64 workstation, not the
  assigned fleet node BlackBoxV2.

## Threats to validity

- Assets: files inside the sandbox directory, rows in the demo sqlite database, the audit log, the bearer token hashes.
- Trust boundary: the HTTP request. Everything in the body, headers and declared Content-Length is attacker controlled; the server process and its filesystem are trusted.
- Attacker capabilities considered: a caller with no token or a wrong token; a caller holding the reader token who tries operator tools; a caller with a valid token who sends crafted arguments (path traversal, absolute paths, multi-statement or non-SELECT SQL, oversized bodies).
- Out of scope today, stated not solved: a network attacker (no TLS), token theft or replay (no expiry or revocation), denial of service (no rate limit, no query timeout), a compromised host.
- Mapping: unauthenticated and forbidden_role answer the first two attackers; path_traversal, absolute_path_blocked, sql_multi_statement, sql_not_select, write_blocked, delete_blocked and request_too_large answer the third. The corpus false negatives (sqlite_master reads, randomblob, load_extension) are third-attacker cases the rules do not stop.

## Self-review against a research rubric (2026-11-07)

Moved from docs/research-review.md. The letter grades were removed
(grades are internal); the evidence and gaps are kept.

| Criterion | Evidence and gap |
| --- | --- |
| Research question | Implicit: can a small stdlib server enforce authentication, roles and named safety rules before any tool runs, and say why it refused? Now stated in README and PROPOSAL.md, but not phrased as a falsifiable question. |
| Hypotheses | No pre-stated hypotheses. The guard corpus (level-3-deep/results_guard.json) now tests an implicit one ("the token guard separates safe from unsafe SQL"), and it is partly refuted: 5 false positives and 4 false negatives on 22 SQL cases. |
| Method | Deterministic scripted plans per level (results_learn.json 18 calls, results_build.json 24, results_deep.json 30), replayed by CI byte for byte. Deep plan inputs are exported to level-3-deep/deep_plan.json and a replay matches results_deep.json call for call. |
| Baselines | No baseline. PROPOSAL.md (Proposed novelty) says NO MEASUREMENT YET against the MCP reference servers. |
| Statistics and uncertainty | Correctness traces are deterministic, so variance does not apply to them. The guard corpus reports counts, not rates, and says so. The latency run (results_latency.json) reports median and p95 over 300 calls per kind, one machine, one run, no confidence intervals. |
| Reproducibility | Stdlib Python only; .github/workflows/ci.yml runs 71 unit tests, all three runners and the guard corpus, then fails if any committed results file changes. The site rebuilds from the same files and its build fails unless the JavaScript guard port agrees with the recorded runs and the corpus verdicts (site/src/guard.check.mjs). |
| Threats to validity | Failure modes are written per level and the README states scope (MCP-style, localhost, no TLS). A threat model is added below; it was missing before this review. |
| Related work | PROPOSAL.md names the prior art (the MCP reference servers) but compare nothing against it. |
| Limitations | Each level README itemizes its known limits, largest first, and the Deep README lists its failure modes; the site build fails if those sections go missing. |
| Engineering rigor | 71 tests pass in under 2 s; tests check README counts against results JSON (tests/test_results_consistency.py). Gaps: no fuzzing, no query timeout or row cap, size cap trusts Content-Length. |

Fixed during that review:

- CI ran only the scaffold smoke test; it now runs the full suite, the three runners and the guard corpus, with a byte-for-byte reproduction check.
- Anecdotal guard weaknesses became a measured, labelled corpus: level-3-deep/guard_corpus.py writes results_guard.json (22 SQL cases, 17 path cases, with true/false positive and negative counts).
- Deep plan inputs exported to deep_plan.json; results_deep.json left byte-identical.
- README "Benchmarks" renamed "Measured results", since the call tables are correctness traces.
- A small localhost latency measurement (level-3-deep/bench_latency.py, results_latency.json), labelled machine specific and kept out of the byte-for-byte check.
- The "Honest size" note (now in PROPOSAL.md) now states the real current value instead of a placeholder.
- A test keeps README counts in step with the results files.
- A first threat model, below.

## Remaining gaps and what each needs

| Gap | What closes it | Compute and data needed |
| --- | --- | --- |
| No interop evidence (Future work 4) | Connect the official MCP Python SDK client to a server built on the same tools; record which messages match and which do not. | One CPU machine, the official SDK installed from PyPI, about a day of work. No GPU, no paid API. |
| No baseline against the MCP reference servers | Run the same 30-call Deep plan against a reference filesystem and sqlite server through the official SDK; compare outcomes and refusal reasons. | Same as above, plus the reference servers from the MCP project; CPU only. |
| Guard evaluated on 39 hand-picked cases | A larger labelled corpus (several hundred benign queries from a public SQL workload plus known injection payloads), with rates and confidence intervals. | A public SQL query set and an injection payload list; labelling time; seconds of CPU. |
| SQL guard is a heuristic (Future work 5) | Replace with sqlite set_authorizer plus a progress-handler timeout and row cap; rerun the corpus and compare counts. | CPU only, stdlib sqlite3. |
| Latency is one machine, one run, tiny fixtures (Future work 8 and 9) | Rerun bench_latency.py several times on the fleet node BlackBoxV2 with larger fixtures; report spread across runs. | Access to BlackBoxV2 and bigger fixture files; minutes of CPU. |
| Security limits (Future work 1, 2, 3, 6) | TLS, token lifecycle, durable audit log, rate limiting and a streaming size cap, each with tests. | CPU only; engineering time. |
| Self-assessed limits only | An external reviewer re-derives the headline numbers and checks the verdict gates (portfolio standard v2, Review stage). | A reviewer's time. |
| Deep lacks resources/read (Future work 7) | Port Build's resources/read to the HTTP server with role checks and tests. | CPU only. |
| `npm audit` in site/ reports 1 high (vite 5.4.11) and 1 moderate (esbuild 0.21) advisory | All advisories affect the local dev server only; the published dist is static files. The dev server is now limited to site/, the three level folders and the root docs it reads (server.fs.allow). Cleared on 2026-11-07: vite was raised to 5.4.21 and then 6.4.5, and npm audit reported no high or critical advisories (commits 955b123, 85a8f7c). | No compute; a one-line pin change plus a rebuild and browser gate. |

## Future work

The rest of the v2 Deep scope, named at the v1.0 ship (moved from
ROADMAP.md). None of this is claimed as done.

Named here at the v1.0 ship, per the December compression protocol. None of this is claimed as done.

1. TLS termination: a documented way to serve the HTTP endpoint behind TLS, so bearer tokens never cross a network in clear text. Localhost-only stays the default.
2. Token lifecycle: expiry, rotation, and revocation for token hashes, plus per-caller identities beyond the two fixed roles.
3. Durable audit log: append-only on-disk audit entries with the same categories and reasons, surviving server restarts.
4. Official MCP interop: connect a real MCP client and the official MCP SDK to this server shape and record what matches and what does not, instead of claiming compliance.
5. Stronger SQL safety: a real SQL parser or a sqlite authorizer in place of the first-word and token check, plus a query timeout and a row cap for permitted SELECT calls.
6. Server hardening: request timeouts, rate limiting and authentication throttling, a streaming body size cap that does not trust the declared Content-Length, and request ids correlated across the audit log.
7. Resources over HTTP: resources/read for sandbox and database resources, which Build has over stdio and Deep does not expose yet.
8. Scale fixtures: larger sandbox file sets and database tables, with the benchmark rerun and the limits re-stated on the bigger fixtures.
9. Fleet run: the full Deep benchmark rerun on BlackBoxV2, the assigned fleet node, replacing the Muse VM numbers or standing beside them with both named.

Rules for this list:

- An item leaves this list only when it ships with tests and measured results, the same gates as v1.0.
- New scope discovered during v1.1 work is added here with a date, never silently folded into a shipped claim.

## Conclusion

On the scripted plans the server does what it claims: every call that
should be refused is refused before the tool runs, with a named reason
and an audit entry, and the traces reproduce byte for byte. The labelled
corpus shows where that claim stops: the SQL guard is a heuristic that
both over- and under-blocks. The next useful step is a locked
confirmatory cycle with a larger corpus and an SDK interop run
(PROPOSAL.md, last section).
