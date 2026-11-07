# Research review: mcp-toolkit

Reviewed 2026-11-07 against a doctoral-level rubric for an engineering research project. Every number below comes from a committed file in this repo; the file is named beside it. Grades: A (meets the bar), B (mostly, small gaps), C (partial), D (missing).

## Summary

A clean, well-tested stdlib reproduction of an MCP-style tool server in three levels, with a named safety-rule set and written failure modes. Its evidence is correctness traces and a small labelled guard corpus, not a comparison against other systems. The largest open gaps are interop with the official MCP SDK and an adversarial evaluation of the safety rules at realistic size; both need work described below, not new hardware.

## Scorecard

| Criterion | Grade | Evidence and gap |
| --- | --- | --- |
| Research question | B | Implicit: can a small stdlib server enforce authentication, roles and named safety rules before any tool runs, and say why it refused? Stated in README and SPEC.md, but not phrased as a falsifiable question. |
| Hypotheses | C | No pre-stated hypotheses. The guard corpus (level-3-deep/results_guard.json) now tests an implicit one ("the token guard separates safe from unsafe SQL"), and it is partly refuted: 5 false positives and 4 false negatives on 22 SQL cases. |
| Method | B | Deterministic scripted plans per level (results_learn.json 18 calls, results_build.json 24, results_deep.json 30), replayed by CI byte for byte. Deep plan inputs are exported to level-3-deep/deep_plan.json and a replay matches results_deep.json call for call. |
| Baselines | D | No baseline. NOVELTY.md says NO MEASUREMENT YET against the MCP reference servers. |
| Statistics and uncertainty | C | Correctness traces are deterministic, so variance does not apply to them. The guard corpus reports counts, not rates, and says so. The latency run (results_latency.json) reports median and p95 over 300 calls per kind, one machine, one run, no confidence intervals. |
| Reproducibility | A | Stdlib Python only; .github/workflows/ci.yml runs 71 unit tests, all three runners and the guard corpus, then fails if any committed results file changes. The site rebuilds from the same files and its build fails unless the JavaScript guard port agrees with the recorded runs and the corpus verdicts (site/src/guard.check.mjs). |
| Threats to validity | C | Failure modes are written per level and the README states scope (MCP-style, localhost, no TLS). A threat model is added below; it was missing before this review. |
| Related work | C | DOSSIER.md and NOVELTY.md name the prior art (the MCP reference servers) but compare nothing against it. |
| Limitations | A | Each level README itemizes grade deductions that sum to 10,000 minus the grade (8,700 / 8,600 / 8,300); the site build fails if they do not. |
| Engineering rigor | B | 71 tests pass in under 2 s; tests check README counts against results JSON (tests/test_results_consistency.py). Gaps: no fuzzing, no query timeout or row cap, size cap trusts Content-Length. |

## Fixed during this review (cheap, done)

- CI ran only the scaffold smoke test; it now runs the full suite, the three runners and the guard corpus, with a byte-for-byte reproduction check.
- Anecdotal guard weaknesses became a measured, labelled corpus: level-3-deep/guard_corpus.py writes results_guard.json (22 SQL cases, 17 path cases, with true/false positive and negative counts).
- Deep plan inputs exported to deep_plan.json; results_deep.json left byte-identical.
- README "Benchmarks" renamed "Measured results", since the call tables are correctness traces.
- A small localhost latency measurement (level-3-deep/bench_latency.py, results_latency.json), labelled machine specific and kept out of the byte-for-byte check.
- NOVELTY.md "Honest size" now states the real current value instead of a placeholder.
- A test keeps README counts in step with the results files.
- A first threat model, below.

## Threat model (first version)

- Assets: files inside the sandbox directory, rows in the demo sqlite database, the audit log, the bearer token hashes.
- Trust boundary: the HTTP request. Everything in the body, headers and declared Content-Length is attacker controlled; the server process and its filesystem are trusted.
- Attacker capabilities considered: a caller with no token or a wrong token; a caller holding the reader token who tries operator tools; a caller with a valid token who sends crafted arguments (path traversal, absolute paths, multi-statement or non-SELECT SQL, oversized bodies).
- Out of scope today, stated not solved: a network attacker (no TLS), token theft or replay (no expiry or revocation), denial of service (no rate limit, no query timeout), a compromised host.
- Mapping: unauthenticated and forbidden_role answer the first two attackers; path_traversal, absolute_path_blocked, sql_multi_statement, sql_not_select, write_blocked, delete_blocked and request_too_large answer the third. The corpus false negatives (sqlite_master reads, randomblob, load_extension) are third-attacker cases the rules do not stop.

## Remaining gaps and exactly what each needs

| Gap | What closes it | Compute and data needed |
| --- | --- | --- |
| No interop evidence (ROADMAP item 4) | Connect the official MCP Python SDK client to a server built on the same tools; record which messages match and which do not. | One CPU machine, the official SDK installed from PyPI, about a day of work. No GPU, no paid API. |
| No baseline against the MCP reference servers | Run the same 30-call Deep plan against a reference filesystem and sqlite server through the official SDK; compare outcomes and refusal reasons. | Same as above, plus the reference servers from the MCP project; CPU only. |
| Guard evaluated on 39 hand-picked cases | A larger labelled corpus (several hundred benign queries from a public SQL workload plus known injection payloads), with rates and confidence intervals. | A public SQL query set and an injection payload list; labelling time; seconds of CPU. |
| SQL guard is a heuristic (ROADMAP item 5) | Replace with sqlite set_authorizer plus a progress-handler timeout and row cap; rerun the corpus and compare counts. | CPU only, stdlib sqlite3. |
| Latency is one machine, one run, tiny fixtures (ROADMAP items 8 and 9) | Rerun bench_latency.py several times on the fleet node BlackBoxV2 with larger fixtures; report spread across runs. | Access to BlackBoxV2 and bigger fixture files; minutes of CPU. |
| Security limits (ROADMAP items 1, 2, 3, 6) | TLS, token lifecycle, durable audit log, rate limiting and a streaming size cap, each with tests. | CPU only; engineering time. |
| Self-assigned grades | An external reviewer grades the levels against the same rubric. | A reviewer's time. |
| Deep lacks resources/read (ROADMAP item 7) | Port Build's resources/read to the HTTP server with role checks and tests. | CPU only. |
