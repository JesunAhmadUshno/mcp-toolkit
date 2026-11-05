# mcp-toolkit

An MCP server and host toolkit with authentication and tool safety rules.

Status: Learn DONE and Build DONE (2026-11-05, ROADMAP-V3-BATCH). Levels 1 and 2 are built, tested, and measured below. Deep is not started.
Project: P09. Fleet node: BlackBoxV2. Wave: Wave 4. Both levels were run on the Muse VM (CPU); see the level READMEs for the named deduction.

## Start here

1. Read SPEC.md for scope and acceptance criteria.
2. Read DOSSIER.md for the past, present, and future of this problem (v1).
3. Read NOVELTY.md for the proposed novelty (DRAFT, pending the Jev claim_check gate).
4. Start at level-1-learn/README.md, then level-2-build, then level-3-deep.

## Level map

- Level 1, Learn: the core idea, built small and clean, with a teaching path.
- Level 2, Build: a real working system other people can run.
- Level 3, Deep: benchmarks, optimization, evaluation, hard cases.

## Benchmarks

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

## Novelty

PROPOSED. See NOVELTY.md. The novelty text is a draft until the Jev claim_check gate passes on it.

## License

Code: Apache-2.0 (see LICENSE). Tutorials: CC BY 4.0. Ruled in D-V3-11, 2026-11-04.
