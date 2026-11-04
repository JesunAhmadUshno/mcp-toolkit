# SPEC: mcp-toolkit (P09)

Phase skill: spec-driven-development (house engineering pipeline).
Status: Wave 0 scaffold spec, from Roadmap v2 text and the v3 decision pack. Scope and acceptance criteria below are the v2 section text, kept as the source of truth until the project's wave opens its own spec pass.

Fleet node: BlackBoxV2. Wave: Wave 4.
Hiring evidence: 3 of 5 (MCP in Apple preferred list) [confirmed, fleet and scoring pass 2026-11-04, or the decision pack for P23 to P29].

## Project section text (Roadmap v2, or the v3 candidate text for P23 to P29)

mcp-toolkit: KEEP

Subject: agent protocols (MCP). v1 levels carry over: a small MCP server over files and a database; a host client that connects to several servers; Deep adds authentication, remote MCP over HTTP, and tool safety rules. The Rust CLI that the register once placed in this family now lives in P21 (change 13); this project's own scope does not change.
Fan-out: Book chapter "Tools With Rules". Paper angle: a tool safety rules note (what a tool may never do, with the test set). Course module: P09-mcp-toolkit.

## Acceptance criteria (scaffold level)

- Learn closes when the level-1-learn code runs, its README teaches the idea, and a fresh-eyes reader can follow it.
- Build closes when the system runs end to end, tests pass, and one benchmark or result table with method is in the README.
- Deep closes when the Deep scope in the section text is done, the failure modes are written, and the dossier is updated to ship state.
- No level closes on a claim. Evidence only: code, tests, numbers, links.
