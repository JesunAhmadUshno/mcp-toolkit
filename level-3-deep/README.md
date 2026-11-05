# Level 3, Deep: mcp-toolkit

Status: DONE (2026-11-05). Remote MCP over HTTP with bearer token
authentication, two roles, and the full tool safety rules set,
built with the Python standard library only. This is the compressed
Deep for December: the single hardest capability set in SPEC.md
(authentication, remote MCP over HTTP, full safety rules), built,
tested, benchmarked, with failure modes written. The rest of the
v2 Deep scope is the v1.1 backlog in the root ROADMAP.md.

## Honest scope line

This is an MCP-style implementation, not the official MCP SDK. It
claims no spec compliance beyond the message shapes documented
here. Transport is HTTP on localhost only, with no TLS. Token auth
is a teaching design (hash-compared bearer tokens, two fixed
roles), not production identity: no expiry, no rotation, no OAuth.

## DEEP-SPEC

1. HTTP server. mcp_deep.py serves one aggregated tool set over
   real HTTP (http.server ThreadingHTTPServer, 127.0.0.1) at
   POST /mcp, JSON-RPC style bodies, plus GET /health. Methods:
   initialize, tools/list, tools/call. server_main.py runs it as a
   process; the runner and the tests run it in-process on an
   ephemeral port. HttpMcpClient is the small client.
2. Tools. Six tools aggregated in one server: file (read_file,
   list_files, sandboxed, same fixtures as Build), database
   (list_items, run_query, in-memory sqlite, same 3 seed rows),
   calc (calculate, count_words, computed directly, never eval).
3. Authentication. Callers send Authorization: Bearer <token>.
   The server stores only the SHA-256 hash of each token and
   compares hashes with hmac.compare_digest. At real server start
   the hashes come from the MCP_TOOLKIT_TOKEN_HASHES environment
   variable (JSON role to hash map); a missing or malformed
   variable stops the start, so the server never runs open by
   accident. No token value is stored in the repo. Test code sets
   clearly labelled test tokens in-process for localhost tests
   only, hashed in memory at once. Missing or wrong token: HTTP
   401, reason unauthenticated, audit entry.
4. Roles, enforced server-side. reader may call the 4 read tools
   only; operator may call all 6 (read plus calc). tools/list is
   filtered per role (reader sees 4, operator sees 6). A known
   tool outside the role allowlist: HTTP 403, reason
   forbidden_role, audit entry.
5. Safety rules set, enforced server-side before any tool runs,
   each with a named block reason and an audit log entry (in
   memory, sequence numbered, categories auth, authorization,
   safety):
   - path_traversal: a path with a .. segment, or a resolved path
     escaping the sandbox.
   - absolute_path_blocked: an absolute path resolving outside
     the sandbox.
   - write_blocked: write_file, create_file, append_file. No write
     tool exists; the attempt itself is the block.
   - delete_blocked: delete_file, remove_file, unlink_file. Same
     pattern as writes.
   - sql_not_select: SQL whose first word is not SELECT, or with a
     blocked word (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
     REPLACE, TRUNCATE, GRANT, REVOKE, ATTACH, DETACH, VACUUM,
     PRAGMA) anywhere. Covers DROP, DELETE, UPDATE, INSERT.
   - sql_multi_statement: a semicolon anywhere except one
     trailing semicolon. Checked before the SELECT check.
   - request_too_large: request body over 8192 bytes, HTTP 413,
     rejected before JSON parsing or auth.
   - unknown_tool: any other tool name.
   Ordinary failures stay named protocol errors, not safety
   blocks: file_not_found, calc_error (division by zero),
   method_not_found, invalid_params, query_error.
6. Defensive only. Nothing in this level performs a write, a
   delete, or a non-SELECT statement. Blocked calls never touch
   the sandbox or the table, and tests re-read both after blocks
   to prove it.

## Run it

    python level-3-deep/run_deep.py
    python -m unittest tests.test_deep_mcp -v
    python -m unittest discover -s tests

Real server start (hashes from the environment, see
server_main.py for the hash recipe):

    MCP_TOOLKIT_TOKEN_HASHES='{"reader": "<sha256>", "operator": "<sha256>"}' \
        python level-3-deep/server_main.py

The runner writes level-3-deep/results_deep.json
deterministically, with no timing fields: run it twice and the
file is identical (verified by hash on 2026-11-05, sha256
8c1d115e520e on both runs).

## Results (measured 2026-11-05, Muse VM, Python 3.12)

Main claim: P09 mcp-toolkit Level 3 Deep ran 30 protocol calls
over authenticated HTTP with 8 successes, 3 unauthenticated
rejections, 2 role blocks, 13 safety blocks, and 4 errors,
exposing 6 tools under 2 roles.

Summary: 30 protocol calls in total: 8 successes, 3
unauthenticated (HTTP 401), 2 role blocks (HTTP 403), 13 safety
blocks, and 4 errors. Safety blocks by reason: path_traversal 2,
absolute_path_blocked 1, write_blocked 1, delete_blocked 1,
sql_not_select 4, sql_multi_statement 2, request_too_large 1,
unknown_tool 1. Audit log: 18 entries (3 auth, 2 authorization,
13 safety). Tools: 6 in total; reader sees 4, operator sees 6.
Tests: 28 Deep unit tests, 65 tests in the full suite, all
passing.

| Call | Role | Tool or method | HTTP | Status | Detail |
| --- | --- | --- | --- | --- | --- |
| D01 | reader | initialize | 200 | success | protocolVersion deep-1, role reader |
| D02 | reader | tools/list | 200 | success | 4 tools (read only) |
| D03 | reader | read_file hello.txt | 200 | success | content "hello mcp\n" |
| D04 | reader | list_files | 200 | success | guide.txt, hello.txt, notes.txt |
| D05 | reader | list_items | 200 | success | rows alpha 10, beta 20, gamma 30 |
| D06 | reader | run_query score >= 20 | 200 | success | rows beta 20, gamma 30 |
| D07 | operator | calculate add 20, 30 | 200 | success | value 50 |
| D08 | operator | count_words "tools need rules" | 200 | success | count 3 |
| D09 | none | read_file | 401 | unauthenticated | unauthenticated |
| D10 | wrong | read_file | 401 | unauthenticated | unauthenticated |
| D11 | none | initialize | 401 | unauthenticated | unauthenticated |
| D12 | reader | calculate | 403 | role_blocked | forbidden_role |
| D13 | reader | count_words | 403 | role_blocked | forbidden_role |
| D14 | operator | read_file ../secret.txt | 200 | safety_blocked | path_traversal |
| D15 | reader | read_file ../../etc/passwd | 200 | safety_blocked | path_traversal |
| D16 | reader | read_file /etc/passwd | 200 | safety_blocked | absolute_path_blocked |
| D17 | operator | write_file | 200 | safety_blocked | write_blocked |
| D18 | operator | delete_file | 200 | safety_blocked | delete_blocked |
| D19 | reader | run_query DROP TABLE items | 200 | safety_blocked | sql_not_select |
| D20 | reader | run_query DELETE FROM items | 200 | safety_blocked | sql_not_select |
| D21 | reader | run_query UPDATE items | 200 | safety_blocked | sql_not_select |
| D22 | reader | run_query INSERT INTO items | 200 | safety_blocked | sql_not_select |
| D23 | reader | run_query SELECT; SELECT | 200 | safety_blocked | sql_multi_statement |
| D24 | reader | run_query SELECT; DROP | 200 | safety_blocked | sql_multi_statement |
| D25 | operator | count_words oversize body | 413 | safety_blocked | request_too_large |
| D26 | operator | frobnicate (unknown tool) | 200 | safety_blocked | unknown_tool |
| D27 | reader | read_file missing.txt | 200 | error | file_not_found |
| D28 | operator | calculate divide by zero | 200 | error | calc_error |
| D29 | operator | bogus/method | 200 | error | method_not_found |
| D30 | reader | run_query with no sql argument | 200 | error | invalid_params |

Hand checks: successes are 2 session calls (D01, D02) plus 4
reader data calls (D03 to D06) plus 2 operator calc calls (D07,
D08), which is 8. Unauthenticated are D09 to D11, which is 3.
Role blocks are D12 and D13, which is 2. Safety blocks are D14
to D26, which is 13: 2 plus 1 plus 1 plus 1 plus 4 plus 2 plus
1 plus 1 by reason is 13. Errors are D27 to D30, which is 4.
8 plus 3 plus 2 plus 13 plus 4 is 30, the total. Audit entries
are 3 plus 2 plus 13, which is 18. Add gives 20 plus 30, which
is 50. Scores at or above 20 are beta at 20 and gamma at 30.

## Grade

8,300 of 10,000. Deductions, itemized and summing to 1,700:
localhost HTTP only with no TLS, so tokens and data cross the
wire in clear text on the loopback interface, 400; token auth is
a teaching design (fixed bearer hashes, no expiry, rotation,
revocation, or per-user identity), 400; synthetic tiny fixtures
(3 files, 3 database rows, toy calc tools), 300; run on the Muse
VM, not the assigned fleet node BlackBoxV2, 200; no persistence
or rate limiting (in-memory database and audit log, unbounded
request rate under the size cap), 200; the SQL guard is a token
and first-word check, not a full SQL parser or a sqlite
authorizer, so a read-only SELECT can still be expensive or
oddly shaped, 200. 10,000 minus 1,700 is 8,300.

## Failure modes and limits

- No TLS. The server binds 127.0.0.1 and must never be exposed
  beyond localhost in this form: bearer tokens would travel in
  clear text. A public deployment needs a TLS terminator and a
  real identity system; both are v1.1 and later scope.
- Token auth is a teaching design. Anyone holding a token is the
  role, with no expiry, revocation, or audit identity beyond the
  role name. A leaked test token is harmless (localhost fixtures
  only); a leaked real token would need a server restart with new
  hashes, because there is no revocation list.
- Oversize is checked on the declared Content-Length before the
  body is read. A client that lies about length or streams
  without one is bounded by the socket read of the declared size,
  not by a streaming cap.
- The audit log lives in server memory and resets on restart.
  It proves the rules fired in a run; it is not a durable audit
  trail, and entries carry role and tool names only, never token
  values or file contents.
- The database is in-memory per server process and resets on
  restart. The SQL guard blocks the named write shapes; it does
  not parse SQL, and a permitted SELECT can still be slow. No
  query timeout is enforced.
- Threading is per-request with a lock around the database and
  the audit log. There is no rate limiting, no request queue
  bound, and no authentication throttling, so a local flood is
  possible by design at this level.
- The file sandbox check uses real path resolution. Symlink
  races and large in-sandbox files are out of scope.
- Fixtures are tiny and synthetic by design: 3 files, 3 rows,
  and arithmetic prove the auth, role, and safety path over HTTP,
  not scale.
- This level was run on the Muse VM (CPU), not on its fleet
  node BlackBoxV2. That costs a grade deduction, named in the
  grade.

## What remains

The rest of the v2 Deep scope is the v1.1 backlog in the root
ROADMAP.md: TLS termination, token lifecycle, durable audit,
official MCP SDK interop testing, and scale fixtures.
