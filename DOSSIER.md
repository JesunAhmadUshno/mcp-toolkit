# DOSSIER: mcp-toolkit (P09), ship state v1.0, 2026-11-05

Written under the documentation and publishing standard (past, present, future). Updated at ship time. Earlier version: v1, 2026-11-04 (scaffold).

## Past

Prior art for this project is named in NOVELTY.md (the MCP reference servers). The problem this project works on: agent tools are powerful by default, so a tool host needs a protocol shape, a sandbox, and rules about what a tool may never do, all small enough to read end to end. Learn (v0.1) built the in-process protocol and the first safety rules; Build (v0.5) put the same rules over real stdio subprocess transport with three servers and a host that aggregates their tools.

## Present

Ship state, 2026-11-05: all three levels DONE, release v1.0.

- Learn: 18 protocol calls, 10 successes, 4 safety blocks, 4 errors, 4 tools, 17 unit tests at its level record.
- Build: 24 protocol calls over stdio, 14 successes, 4 blocked, 6 errors, 6 tools across 3 servers, 20 Build unit tests, grade 8,600 of 10,000.
- Deep (compressed, December protocol): remote MCP over HTTP on localhost (POST /mcp), bearer token authentication checked by SHA-256 hash comparison with token hashes loaded from the environment at server start, two roles with server-side allowlists (reader: 4 read tools; operator: all 6 tools), and the full safety rules set with named block reasons and an audit log (path traversal, absolute path outside sandbox, write attempts, delete attempts, SQL that is not a single read-only SELECT including multi-statement input, oversize requests, unknown tools). Measured: 30 protocol calls, 8 successes, 3 unauthenticated rejections, 2 role blocks, 13 safety blocks, 4 errors, 18 audit entries. 28 Deep unit tests; 65 tests in the full suite, all passing. Grade 8,300 of 10,000 with deductions named in level-3-deep/README.md (largest: localhost HTTP only with no TLS, and token auth as a teaching design, 400 each).
- Evidence: level-1-learn/results_learn.json, level-2-build/results_build.json, level-3-deep/results_deep.json, each deterministic across two runs with hashes recorded in the level READMEs. Jev claim_check on the Deep main claim is recorded in the batch ledger for this goal.
- Current demand evidence: hiring value 3 of 5 (MCP in Apple preferred list) [confirmed, fleet and scoring pass 2026-11-04]. The Round 3 research (2026-11-04) found the market centre at post-training, evals, environments, and inference depth [confirmed as the research finding; the report is at ~/workspace/research_notes/roadmap-v3-revaluation-research-20261104-0949/report.md].

## Future

The rest of the v2 Deep scope is the named v1.1 backlog in ROADMAP.md: TLS termination guidance, token lifecycle (expiry, rotation, revocation), durable audit log, official MCP SDK and real client interop testing, a SQL parser or sqlite authorizer in place of the token check, request timeouts and rate limiting, and larger fixtures. Any forecast about this field is [unverified] unless a dated primary source is added here.
