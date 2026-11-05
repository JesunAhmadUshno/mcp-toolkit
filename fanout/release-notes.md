# Release notes draft: mcp-toolkit

Status: DRAFT notes for releases that already exist. Dated 2026-11-05.
These notes summarise the existing GitHub releases. No new release is
created by this file.

Releases verified with gh release list on 2026-11-05:
v0.1, v0.5, and v1.0, at the URLs below.

## v0.1, Learn: MCP-style tool protocol

URL: https://github.com/JesunAhmadUshno/mcp-toolkit/releases/tag/v0.1

- An in-process MCP-style teaching protocol, built with the
  Python standard library only. Two servers (file, sandboxed;
  database, in-memory sqlite, read-only by rule), a host that
  aggregates their 4 tools, and the first safety rules. Not
  the official MCP SDK, and no network transport at this
  level.
- Measured run: 18 protocol calls, 10 successes, 4 blocked
  (path_traversal 2, write_blocked 2), 4 named errors.
- Tests: 17 unit tests in tests/test_learn_mcp.py, plus the
  scaffold smoke test.
- Grade: 8,700 of 10,000, deductions itemized in the Learn
  README.
- Limits carried in the release: in-process only, tiny
  fixtures (2 files, 3 rows), no authentication, teaching
  SQL guard.

## v0.5, Build: stdio host client with three MCP-style servers

URL: https://github.com/JesunAhmadUshno/mcp-toolkit/releases/tag/v0.5

- The Learn servers as separate processes over real stdio
  transport (newline-delimited JSON over subprocess pipes),
  a third calc server, and a host client that aggregates 6
  tools across 3 servers and routes each call to the owning
  process. The Learn safety rules are retained and tested
  over the wire.
- Measured run: 24 protocol calls, 14 successes, 4 blocked
  (path_traversal 2, write_blocked 2), 6 named errors.
- Tests: 20 Build unit tests, 37 in total with Learn.
- Grade: 8,600 of 10,000, deductions itemized in the Build
  README.
- Limits carried in the release: stdio only, tiny fixtures
  (3 files, 3 rows), no authentication, no request timeout,
  in-memory database per server process.

## v1.0, Deep: authenticated remote MCP over HTTP with safety rules

URL: https://github.com/JesunAhmadUshno/mcp-toolkit/releases/tag/v1.0

- Compressed Deep under the December Compression Protocol:
  remote MCP over real HTTP on localhost (POST /mcp, GET
  /health), bearer authentication by SHA-256 hash comparison
  with hashes loaded from the environment at server start,
  two roles with server-side allowlists (reader: 4 read
  tools; operator: all 6), and the full safety rules set
  with named block reasons and an audit log. MCP-style, not
  the official MCP SDK. No token value is stored in the
  repo.
- Measured run: 30 protocol calls, 8 successes, 3
  unauthenticated rejections at HTTP 401, 2 role blocks at
  HTTP 403, 13 safety blocks (path_traversal 2,
  absolute_path_blocked 1, write_blocked 1, delete_blocked
  1, sql_not_select 4, sql_multi_statement 2,
  request_too_large 1 at the 8192-byte cap, unknown_tool 1),
  4 named errors, and 18 audit log entries.
- Tests: 28 Deep unit tests, 65 in total with Learn and
  Build.
- Grade: 8,300 of 10,000, deductions itemized in the Deep
  README (total deductions 1,700).
- The rest of the v2 Deep scope is the v1.1 backlog in
  ROADMAP.md. It is not part of v1.0 and is not claimed by
  these notes.
