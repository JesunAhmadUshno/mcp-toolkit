# Tools With Rules: Building mcp-toolkit in the Open

By Jesun Ahmad Ushno
Date: 2026-11-05
Status: DRAFT, written fan-out for P09 mcp-toolkit v1.0. Not posted.

## The problem

An agent tool is powerful by default. A file tool can read outside
its folder, a database tool can run a write, and a remote caller
can be anyone. A tool host that does not check who is calling,
which tools that caller may use, and what a call may never do is
not a toolkit. It is an open door with a protocol shape. This
project builds the closed version, small enough to read end to
end: a protocol, a sandbox, authentication, roles, and a named
list of things a tool call may never do.

This project, P09 in Roadmap v3, builds an MCP-style tool
toolkit in three levels: an in-process protocol with the first
safety rules; a host client that connects to three servers over
real stdio subprocess transport; then authenticated remote MCP
over real HTTP with two roles and the full safety rules set.
All code runs with the Python standard library only. Every level
is labelled MCP-style, not the official MCP SDK, and no level
claims spec compliance beyond the message shapes it documents.

Repository: https://github.com/JesunAhmadUshno/mcp-toolkit

## Past, present, future (the dossier, condensed)

Past: the MCP reference servers already exist, and the prior art
and the problem history are recorded in PROPOSAL.md and
REPORT.md in the repo. The novelty claim there stays marked
PROPOSED. This post makes no novelty claim beyond the measured
work below.

Present: v1.0 closes three levels on 2026-11-05. Learn built
the in-process protocol and the first safety rules on 18
protocol calls. Build put the same
rules over real stdio transport with three servers and a host
that aggregates their tools, on 24 protocol calls. Compressed Deep added bearer authentication checked
by SHA-256 hash comparison, two server-side roles, and the full
safety rules set over real HTTP on localhost, on 30 protocol
calls.

Future: the rest of the v2 Deep scope is named in REPORT.md
in the repo as the v1.1 backlog. It includes TLS termination
guidance, a token lifecycle with expiry and rotation, a
durable audit log, official MCP SDK and real client interop
testing, a real SQL parser or sqlite authorizer, request
timeouts and rate limiting, and larger fixtures. None of that
is done, and none of it is claimed here.

## Main results claim

At v1.0: Learn ran 18 protocol calls in process with 10 successes, 4 safety blocks (path_traversal 2, write_blocked 2), and 4 named protocol errors, aggregating 4 tools (2 file, 2 database), with 17 unit tests; Build ran 24 protocol calls end to end over stdio subprocess transport with 14 successes, 4 safety blocks (path_traversal 2, write_blocked 2), and 6 named errors, aggregating 6 tools across 3 servers (file, database, calc), with 20 Build unit tests and 37 tests in the full suite at that level; compressed Deep ran 30 protocol calls over authenticated HTTP on localhost (POST /mcp, GET /health) with 8 successes, 3 unauthenticated rejections at HTTP 401, 2 role blocks at HTTP 403 with reason forbidden_role, 13 safety blocks (path_traversal 2, absolute_path_blocked 1, write_blocked 1, delete_blocked 1, sql_not_select 4, sql_multi_statement 2, request_too_large 1 at the 8192-byte cap, unknown_tool 1), and 4 named errors, exposing 6 tools under 2 roles (reader sees the 4 read tools, operator sees all 6), writing 18 audit log entries (3 auth, 2 authorization, 13 safety), with 28 Deep unit tests and 65 tests in the full suite, all passing, where the Deep arithmetic is 8 plus 3 plus 2 plus 13 plus 4 equals 30 and the safety reasons sum 2 plus 1 plus 1 plus 1 plus 4 plus 2 plus 1 plus 1 equals 13.

Every number in that claim comes from a run recorded in the
level READMEs and results files in the repo. Read the limits
section below before quoting any of it.

## Results by level

Learn (v0.1): 18 calls. The successes are 2 initialize calls,
2 tools/list calls, and 6 data calls. The blocks are 2 path
traversal attempts and 2 write attempts against the database.
The errors are an unknown tool, missing arguments, a missing
file, and an unknown method, each returned as a named error
object. Servers never raise to the client and never return a
traceback.

Build (v0.5): 24 calls over stdio. Three server processes
(file, database, calc) speak newline-delimited JSON over
subprocess pipes. The host aggregates 6 tools, routes each
call to the owning process, and returns a named
server_not_found error for an unknown server instead of
raising. The safety rules from Learn hold over the wire:
traversal and write attempts are blocked with the same codes.

Deep (v1.0): 30 calls over HTTP. Authentication is a bearer
token checked by SHA-256 hash comparison with
hmac.compare_digest. The server stores only hashes, loaded
from the environment at real server start; no token value is
stored in the repo. Roles are enforced server-side: the
reader role may call the 4 read tools only, the operator role
may call all 6, and tools/list is filtered per role. A known
tool outside the role allowlist returns HTTP 403 with reason
forbidden_role. A missing or wrong token returns HTTP 401
with reason unauthenticated. Every auth, authorization, and
safety event writes a sequence-numbered audit entry: 18 in
the measured run.

## What the safety set actually blocks

The Deep safety set is enforced server-side before any tool
runs, and each block carries a named reason. Path traversal
and absolute paths outside the sandbox are blocked before any
file is opened. Write and delete tool names are blocked as
attempts: no write or delete tool exists. SQL is read-only by
rule: the first word must be SELECT, blocked words anywhere
block the call, and a semicolon anywhere except one trailing
semicolon blocks it as multi-statement. A request body over
8192 bytes is rejected at HTTP 413 before JSON parsing or
auth. Any other tool name is blocked as unknown_tool.
Ordinary failures stay named protocol errors, not safety
blocks: file_not_found, calc_error on division by zero,
method_not_found, invalid_params, and query_error. Blocked
calls never touch the sandbox or the table, and the tests
re-read both after blocks to prove it.

## Limits, stated plainly

- Localhost only, no TLS. The Deep server binds 127.0.0.1
  and must never be exposed beyond localhost in this form:
  the bearer token would travel in clear text.
- Teaching auth. Tokens are fixed bearer tokens with no
  expiry, no rotation, no revocation, and no per-user
  identity beyond the two role names. Anyone holding a token
  is the role.
- Toy fixtures. The sandbox holds 3 files and the database
  holds 3 rows. They prove the auth, role, and safety path,
  not scale or real data behaviour.
- Teaching SQL guard. The guard is a first-word and token
  check, not a SQL parser or a sqlite authorizer. A
  permitted read-only SELECT can still be expensive.
- In-memory state. The database and the audit log reset on
  restart. The audit log proves the rules fired in a run;
  it is not a durable audit trail.
- MCP-style, not the official SDK. No real MCP client
  interop was tested. That test is v1.1 backlog item 4.
- All levels ran on the Muse VM (CPU), not on the assigned
  fleet node BlackBoxV2. It is a named limit
  at every level.

## Why this shape

The book chapter for this project is called "Tools With
Rules". The rule this project keeps is simple: a tool call
should fail with a name, not with damage. Every rejection in
the measured runs has a reason a reader can grep for, a test
that proves it fires, and an audit entry that shows it fired.
That is the whole claim. The v1.1 backlog is the list of
things that would have to be true before any of this is
called production identity or production transport.

License: code Apache-2.0, tutorials CC BY 4.0.
