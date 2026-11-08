# Level 2, Build: mcp-toolkit

Status: DONE (2026-11-05). A host client connecting to three servers
end to end over a real stdio transport, built with the Python
standard library only.

## Honest scope line

This is an MCP-style implementation, not the official MCP SDK. It
claims no spec compliance beyond the message shapes documented here.
Transport is stdio only (newline-delimited JSON over subprocess
pipes). Remote MCP over HTTP and authentication are Deep scope and
are not in this level.

## BUILD-SPEC

1. Servers as separate processes. server_main.py starts one server
   per process: file, database, or calc. Each speaks NDJSON: one
   JSON-RPC style request per stdin line, one response per stdout
   line, flushed per message. Stdout carries protocol only.
2. Host client. StdioHostClient spawns all three servers, runs
   initialize and tools/list on each, aggregates 6 tools into one
   registry (2 per server), routes tools/call to the owning server
   process, routes resources/read by server name, and returns a
   named server_not_found error for an unknown server instead of
   raising. Closing the host closes every server process.
3. File server. Sandboxed to a demo directory with three fixture
   files (guide.txt, hello.txt, notes.txt, fixed content, written
   by the runner on every run). Tools: read_file, list_files.
   Resource form: sandbox://<name>. Paths are resolved to their
   real path first; absolute paths and paths escaping the sandbox
   are blocked before any file is opened.
4. Database server. In-memory sqlite for the life of its process,
   one seeded table, items, with three rows: (1, alpha, 10),
   (2, beta, 20), (3, gamma, 30). Tools: list_items, run_query.
   Resource form: db://items. Read-only by rule (see safety).
5. Calc server (new at Build). Tools: calculate (add, subtract,
   multiply, divide, computed directly, never with eval) and
   count_words. Division by zero is a named calc_error.
6. Safety rules, retained from Learn and tested over stdio. Path
   traversal blocked (code -32002, reason path_traversal). Database
   writes blocked (code -32003, reason write_blocked): one statement
   only, first word must be SELECT, blocked words anywhere block it.
   Unknown tool -32001, bad arguments -32602, missing file -32004,
   unknown method -32601, division by zero -32006, unknown or
   crashed server -32004 or -32007. Servers never raise to the
   client and never return a traceback.
7. In-process path kept working. InProcessHost uses the same server
   classes without subprocesses, so the Learn style path still runs
   and is covered by tests.

## Run it

    python level-2-build/run_build.py
    python -m unittest tests.test_build_mcp -v
    python -m unittest discover -s tests

The runner writes level-2-build/results_build.json
deterministically, with no timing fields: run it twice and the file
is identical (verified by hash on 2026-11-05, sha256 6e56a8d61e38
on both runs).

## Results (measured 2026-11-05, Muse VM, Python 3.12)

Main claim: P09 mcp-toolkit Level 2 Build ran 24 protocol calls end
to end over stdio subprocess transport with 14 successes, 4 blocked,
and 6 errors, aggregating 6 tools across 3 servers.

Summary: 24 protocol calls in total: 14 successes, 4 blocked, and
6 errors. Blocked by rule: path_traversal 2, write_blocked 2.
Tools: 6 in total, 2 each from the file, database, and calc
servers. Tests: 20 Build unit tests, 37 tests in the full suite,
all passing, plus the scaffold smoke test.

| Call | Server | Method or tool | Status | Detail |
| --- | --- | --- | --- | --- |
| B01 | file | initialize | success | protocolVersion build-1, transport stdio |
| B02 | database | initialize | success | protocolVersion build-1 |
| B03 | calc | initialize | success | protocolVersion build-1 |
| B04 | file | tools/list | success | read_file, list_files |
| B05 | database | tools/list | success | list_items, run_query |
| B06 | calc | tools/list | success | calculate, count_words |
| B07 | file | read_file hello.txt | success | content "hello mcp\n" |
| B08 | file | list_files | success | guide.txt, hello.txt, notes.txt |
| B09 | database | list_items | success | rows (1, alpha, 10), (2, beta, 20), (3, gamma, 30) |
| B10 | database | run_query score >= 20 | success | rows (beta, 20), (gamma, 30) |
| B11 | calc | calculate add 20, 30 | success | value 50 |
| B12 | calc | count_words "tools need rules" | success | count 3 |
| B13 | file | resources/read sandbox://notes.txt | success | text "tools need rules\n" |
| B14 | database | resources/read db://items | success | 3 rows, same as B09 |
| B15 | file | read_file ../secret.txt | blocked | -32002 path_traversal |
| B16 | file | read_file /etc/passwd | blocked | -32002 path_traversal |
| B17 | database | run_query DROP TABLE items | blocked | -32003 write_blocked |
| B18 | database | run_query INSERT INTO items | blocked | -32003 write_blocked |
| B19 | file | delete_file (unknown tool) | error | -32001 tool_not_found |
| B20 | database | run_query with no sql argument | error | -32602 invalid_params |
| B21 | file | read_file missing.txt | error | -32004 file_not_found |
| B22 | file | bogus/method | error | -32601 method_not_found |
| B23 | calc | calculate divide by zero | error | -32006 calc_error |
| B24 | nope | initialize (unknown server) | error | -32004 server_not_found |

Hand checks: successes are 3 initialize plus 3 tools/list plus 6
routed data calls (B07 to B12) plus 2 resources/read, which is 14.
Blocked are 2 traversal plus 2 write attempts, which is 4. Errors
are B19 to B24, which is 6. 14 plus 4 plus 6 is 24, the total.
Tools are 2 plus 2 plus 2, which is 6. Add gives 20 plus 30, which
is 50. Scores at or above 20 are beta at 20 and gamma at 30.

## Known limits

The scope limits of this level, largest first.

- Stdio transport only, no HTTP remote transport yet.
- Synthetic tiny fixtures (3 files, 3 database rows, toy calc tools).
- Run on the Muse VM, not the assigned fleet node BlackBoxV2.
- No authentication, which is Deep scope.
- Host is sequential with no request timeout or concurrency, and the database lives only in its process memory.
- SQL safety is a first word check plus a blocked word list, not a SQL parser or a sqlite authorizer.

## Failure modes and limits

- Stdio only. Nothing here speaks HTTP, and no real external MCP
  client has been connected. Framing is one line per message, so a
  payload containing a raw newline would break framing; payloads
  are JSON encoded by the host, which escapes newlines.
- A server that hangs would block the host read: there is no
  request timeout at this level. A server that exits is detected
  (server_crashed) on the next request, not pushed to the host.
- The database is in-memory per server process. It persists across
  calls inside one host session and resets when the host closes.
  There is no on-disk persistence and no authentication.
- The SQL guard is a teaching guard, not a proof. It blocks the
  named write words and multi-statement input, but it does not
  parse SQL, and a SELECT can still be expensive.
- The file sandbox check uses real path resolution. Symlink races
  and large files are out of scope at this level.
- Fixtures are tiny and synthetic by design: 3 files, 3 rows, and
  arithmetic prove the transport and routing path, not scale.
- This level was run on the Muse VM (CPU), not on its fleet node
  BlackBoxV2. It is listed under Known limits.

## What Deep adds next

Authentication, remote MCP over HTTP, and the full tool safety
rules set, per PROPOSAL.md. See the root README level map.
