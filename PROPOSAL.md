# Proposal: mcp-toolkit (P09)

Status: NOT PRE-REGISTERED. This file was assembled on 2026-11-08, after
every result in the repo existed, from three earlier files: SPEC.md
(committed 2026-11-04 in the scaffold, before any code), NOVELTY.md and
DOSSIER.md (Past). The 2026-11-04 SPEC.md set scope and acceptance
criteria only; it named no hypotheses and no pass lines, so it does not
count as a locked plan, and no `proposal-v1` tag is placed. Until a
locked confirmatory cycle runs, the repo is capped at Functional
(portfolio standard v2, section 7). The text of the three source files
is kept below; only their grade and hiring-score lines were taken out
(grades are internal).

## Question

Can a small, standard-library MCP-style tool server enforce
authentication, roles and named safety rules before any tool runs, and
say why it refused?

## System under study

An MCP-style JSON-RPC protocol built three times with the Python
standard library only: in process (level-1-learn), over stdio
subprocesses (level-2-build), and over HTTP on localhost with bearer
tokens and two roles (level-3-deep). It is not the official MCP SDK and
claims no spec compliance beyond the message shapes documented in the
level READMEs.

## Prior work

The prior art is the MCP reference servers. The problem this project
works on: agent tools are powerful by default, so a tool host needs a
protocol shape, a sandbox, and rules about what a tool may never do, all
small enough to read end to end. (From DOSSIER.md, Past.)

## Scope (from SPEC.md, 2026-11-04)

Phase skill: spec-driven-development (house engineering pipeline).
Wave 0 scaffold spec, from Roadmap v2 text and the v3 decision pack.
Fleet node: BlackBoxV2. Wave: Wave 4.

mcp-toolkit: KEEP. Subject: agent protocols (MCP). v1 levels carry
over: a small MCP server over files and a database; a host client that
connects to several servers; Deep adds authentication, remote MCP over
HTTP, and tool safety rules. The Rust CLI that the register once placed
in this family now lives in P21 (change 13); this project's own scope
does not change.

Fan-out: book chapter "Tools With Rules". Paper angle: a tool safety
rules note (what a tool may never do, with the test set). Course module:
P09-mcp-toolkit.

## Acceptance criteria (from SPEC.md, scaffold level)

- Learn closes when the level-1-learn code runs, its README teaches the
  idea, and a fresh-eyes reader can follow it.
- Build closes when the system runs end to end, tests pass, and one
  benchmark or result table with method is in the README.
- Deep closes when the Deep scope in the section text is done, the
  failure modes are written, and the dossier is updated to ship state.
- No level closes on a claim. Evidence only: code, tests, numbers,
  links.

## Proposed novelty (from NOVELTY.md)

Status: DRAFT, PROPOSED, not verified. This text does not move into any
public post, paper, or profile until the Jev claim_check gate passes on
the exact text.

Against the MCP reference servers, this project aims to differ in the
way its scope text defines: a from-zero or self-hosted build, measured
in public, on a named home fleet, with the failure modes written down.

| Prior art | What it does | What this project does differently | Measured difference |
| --- | --- | --- | --- |
| the MCP reference servers | See Prior work above | PROPOSED, see the claim above | NO MEASUREMENT YET |

Honest size (updated 2026-11-07): no measured difference against the
MCP reference servers exists yet. No official MCP client or SDK has
been connected (REPORT.md, Future work item 4), so no interop or
comparison claim is made. The real current value is smaller and
concrete: a clean, stdlib-only reproduction of an MCP-style protocol at
three levels (in-process, stdio, authenticated HTTP), with a named and
tested safety rule set (8 block reasons, each with an audit entry),
deterministic per-call traces, written failure modes, and a small
labelled guard corpus (level-3-deep/results_guard.json) that measures
where the SQL guard and path rules are wrong. That is a teaching and
evaluation artifact, not a novel protocol or a novel defence.

## What a locked confirmatory cycle would need

Not locked; written here so a later proposal can start from it. A
`proposal-v2` would state, before any run: a larger labelled SQL and
path corpus drawn from a public workload plus known injection payloads,
with false positive and false negative rates and intervals as the
measures; a pass line for each; and a comparison run of the same plan
against the MCP reference servers through the official SDK. REPORT.md,
Remaining gaps, costs each item (CPU only, no paid API).
