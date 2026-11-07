# NOVELTY: mcp-toolkit (P09)

Status: DRAFT, PROPOSED. Not verified. This text does not move into any public post, paper, or profile until the Jev claim_check gate passes on the exact text.

## Proposed claim

Against the MCP reference servers: this project aims to differ in the way its SPEC.md section text defines (a from-zero or self-hosted build, measured in public, on a named home fleet, with the failure modes written down). The exact difference is stated at the project's wave, after the prior art is re-read.

## Prior art table

| Prior art | What it does | What this project does differently | Measured difference |
| --- | --- | --- | --- |
| the MCP reference servers | See DOSSIER.md, Past | PROPOSED, see the claim above | NO MEASUREMENT YET |

## Honest size

Updated 2026-11-07. No measured difference against the MCP reference servers exists yet: no official MCP client or SDK has been connected (ROADMAP v1.1 item 4), so no interop or comparison claim is made.

The real current value is smaller and concrete: a clean, stdlib-only reproduction of an MCP-style protocol at three levels (in-process, stdio, authenticated HTTP), with a named and tested safety rule set (8 block reasons, each with an audit entry), deterministic per-call traces, written failure modes, and a small labelled guard corpus (level-3-deep/results_guard.json) that measures where the SQL guard and path rules are wrong. That is a teaching and evaluation artifact, not a novel protocol or a novel defence.
