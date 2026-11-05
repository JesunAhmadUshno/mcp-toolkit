# Tutorial: P09 mcp-toolkit, course module

Module: P09-mcp-toolkit
By Jesun Ahmad Ushno
Date: 2026-11-05
License for this tutorial: CC BY 4.0. Code in the repo: Apache-2.0.

## What you will do

You will clone the mcp-toolkit repo, run all three levels, run
the test suite for each level, and read your own results
against the recorded v1.0 numbers. Every command below exists
in the repo as shipped at v1.0 and was run by the author of
this module on 2026-11-05 to verify it. The project needs
Python 3.11 or 3.12 and uses the standard library only. No
model, no API, and no credential are needed.

Honest scope, before the first command: this is an MCP-style
implementation, not the official MCP SDK. Deep serves HTTP on
localhost only, with no TLS, and its token auth is a teaching
design with no expiry or rotation. The fixtures are toy size
by design: 3 files and 3 database rows.

## Step 0: Clone and enter the repo

```text
git clone https://github.com/JesunAhmadUshno/mcp-toolkit.git
cd mcp-toolkit
```

## Step 1: Level 1, Learn, the in-process protocol

Read level-1-learn/README.md first. It explains the JSON-RPC
style message shapes, the file sandbox, the read-only database
rule, and the host that aggregates 4 tools from 2 servers.

Run the Learn task set:

```text
python3 level-1-learn/run_learn.py
```

Run the Learn tests:

```text
python3 -m unittest tests.test_learn_mcp -v
```

Run the scaffold smoke test:

```text
python3 tests/test_smoke.py
```

Check your results against the recorded run: 18 protocol
calls, 10 successes, 4 blocked (path_traversal 2,
write_blocked 2), 4 errors, 4 tools in total. The runner
writes level-1-learn/results_learn.json deterministically:
run it twice and the file is identical.

Try it by hand: read the request and response examples in the
Learn README. Call C11 asks for a path outside the sandbox
and is blocked with reason path_traversal. Call C13 asks the
database to drop its table and is blocked with reason
write_blocked. Both failures are named error objects, never
tracebacks.

## Step 2: Level 2, Build, three servers over stdio

Read level-2-build/README.md. The same servers now run as
separate processes speaking newline-delimited JSON over
subprocess pipes, and a third server (calc) joins the set.

Run the Build task set:

```text
python3 level-2-build/run_build.py
```

Run the Build tests:

```text
python3 -m unittest tests.test_build_mcp -v
```

Check your results: 24 protocol calls over stdio, 14
successes, 4 blocked, 6 errors, 6 tools across 3 servers.
Call B11 adds 20 and 30 and returns 50. Call B24 asks for an
unknown server and returns the named server_not_found error.
The runner writes level-2-build/results_build.json
deterministically, with no timing fields.

## Step 3: Level 3, Deep, authenticated HTTP with roles

Read level-3-deep/README.md. One server now serves all 6
tools over real HTTP at POST /mcp, with GET /health.
Callers send a bearer token. The server stores only the
SHA-256 hash of each token and compares hashes. No token
value is stored in the repo, and this tutorial prints no
token value: the runner and the tests set clearly labelled
test tokens in-process for localhost tests only, hashed in
memory at once.

Run the Deep task set:

```text
python3 level-3-deep/run_deep.py
```

Run the Deep tests:

```text
python3 -m unittest tests.test_deep_mcp -v
```

Check your results: 30 protocol calls, 8 successes, 3
unauthenticated rejections at HTTP 401, 2 role blocks at
HTTP 403, 13 safety blocks, and 4 errors. The safety blocks
by reason are path_traversal 2, absolute_path_blocked 1,
write_blocked 1, delete_blocked 1, sql_not_select 4,
sql_multi_statement 2, request_too_large 1, unknown_tool 1.
The audit log holds 18 entries. Hand check: 8 plus 3 plus 2
plus 13 plus 4 is 30.

Read the results table in the Deep README call by call.
Calls D12 and D13 are the role lesson: the reader role holds
a valid token and still cannot call the calc tools, because
the allowlist is enforced server-side and tools/list itself
is filtered per role (reader sees 4 tools, operator sees 6).
Call D25 is the size lesson: a body over the 8192-byte cap
is rejected at HTTP 413 before JSON parsing or auth.

To run the real server yourself, the hashes come from the
environment at start, and a missing or malformed variable
stops the start so the server never runs open by accident.
The hash recipe is in level-3-deep/server_main.py. Keep the
server on localhost: there is no TLS in v1.0.

## Step 4: The full suite

```text
python3 -m unittest discover -s tests
```

Expected at v1.0: 65 tests, all passing (17 Learn, 20 Build,
28 Deep, plus the scaffold smoke test run in Step 1).

## What to vary, and what should happen

- Ask the reader role for a calc tool. Expect HTTP 403,
  reason forbidden_role, and one authorization audit entry.
- Send a call with no token, then with a wrong token.
  Expect HTTP 401, reason unauthenticated, both times.
- Ask run_query for a DELETE, then for two statements
  joined by a semicolon. Expect sql_not_select, then
  sql_multi_statement.
- After any block, list the files and the table rows again.
  Expect no change: blocked calls never touch the sandbox
  or the table.

## Limits this module does not hide

Localhost only, no TLS. Teaching auth with no expiry,
rotation, or revocation. Toy fixtures (3 files, 3 rows).
The SQL guard is a first-word and token check, not a
parser. The audit log and the database live in memory and
reset on restart. MCP-style message shapes, not the
official SDK, and no real client interop was tested. The
rest of the Deep scope is the v1.1 backlog in ROADMAP.md.
