# LinkedIn post draft: P09 mcp-toolkit v1.0

Status: DRAFT NOT POSTED
Date drafted: 2026-11-05
Author: Jesun Ahmad Ushno
Rule for this platform: the link goes in the first comment, not in the
post body. The first comment line is at the end of this file.

## Post body

An agent tool that nobody authenticated, with no role limits
and no list of forbidden actions, is not a feature. It is an
open door. So I built the version with rules, and measured
every rejection by name.

mcp-toolkit v1.0 is done: Learn, Build, and a compressed Deep,
Python standard library only. MCP-style throughout, not the
official MCP SDK, and labelled that way in the repo.

Learn: an in-process protocol with a sandboxed file server, a
read-only database server, and the first safety rules. 18
calls: 10 successes, 4 blocked, 4 named errors. 4 tools.
17 tests.

Build: the same servers as real processes over stdio, plus a
calc server, with a host that aggregates their tools. 24
calls: 14 successes, 4 blocked, 6 named errors. 6 tools
across 3 servers. 37 tests in total.

Deep (compressed): remote MCP over real HTTP on localhost,
bearer tokens checked by SHA-256 hash comparison (the server
stores hashes only), and two roles enforced server-side.
Reader sees the 4 read tools. Operator sees all 6. 30 calls:
8 successes, 3 unauthenticated at HTTP 401, 2 role blocks at
HTTP 403, 13 safety blocks, 4 named errors, 18 audit entries.
The 13 safety blocks, by reason: path traversal 2, absolute
path 1, write attempt 1, delete attempt 1, SQL that is not a
single read-only SELECT 4, multi-statement SQL 2, oversize
request at the 8192-byte cap 1, unknown tool 1. 65 tests in
total, with limits named in the repo.

The honest limits, in the post and not in a footnote:
localhost only with no TLS, so this server never leaves the
loopback interface in this form; teaching auth with no
expiry, rotation, or revocation; toy fixtures of 3 files and
3 rows; and a SQL guard that is a token check, not a parser.
The rest of the Deep scope is named as the v1.1 backlog in
the repo, not claimed as done.

If you ship agent tools: where do your safety rules live, in
the prompt, in the client, or on the server where the caller
cannot switch them off?

## First comment (post this as the first comment, per the standing rule)

Repo, releases v0.1, v0.5, and v1.0, and the full tutorial: https://github.com/JesunAhmadUshno/mcp-toolkit
