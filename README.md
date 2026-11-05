# mcp-toolkit

An MCP server and host toolkit with authentication and tool safety rules.

Status: Learn DONE (2026-11-05, ROADMAP-V3-BATCH). Level 1 is built, tested, and measured below. Build and Deep are not started.
Project: P09. Fleet node: BlackBoxV2. Wave: Wave 4. Learn was run on the Muse VM (CPU); see the level README for the named deduction.

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

## Novelty

PROPOSED. See NOVELTY.md. The novelty text is a draft until the Jev claim_check gate passes on it.

## License

Code: Apache-2.0 (see LICENSE). Tutorials: CC BY 4.0. Ruled in D-V3-11, 2026-11-04.
