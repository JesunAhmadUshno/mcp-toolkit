# Level 1, Learn: mcp-toolkit

Status: DONE (2026-11-05). An MCP-style tool protocol taught from
scratch, built with the Python standard library only.

## Honest scope line

This is an in-process teaching implementation. It is not the official
MCP SDK, it claims no spec compliance beyond the message shapes it
documents here, and it has no network transport: no HTTP and no stdio
transport yet. Requests and responses are Python dicts passed in
process between a host client and two servers.

## Method

1. Message handling. A request is a JSON-RPC style dict with
   jsonrpc, id, method, and params. A response carries either result
   or an error object with code, message, and data.reason. Servers
   never raise to the client and never return a traceback: every
   failure becomes a named error object.
2. Methods. initialize returns the server name, protocol version
   learn-1, and capabilities. tools/list returns the server tool
   definitions with input schemas. tools/call runs one tool by name.
   resources/read reads one resource by URI.
3. File server. Sandboxed to a small demo directory with two fixture
   files (hello.txt and notes.txt, fixed content, written by the
   runner on every run). Tools: read_file and list_files. Resource
   URI form: sandbox://<name>. A requested path is resolved to its
   real path first, and any path that is absolute or escapes the
   sandbox is blocked before any file is opened.
4. Database server. An in-memory sqlite database with one seeded
   table, items, with three rows: (1, alpha, 10), (2, beta, 20),
   (3, gamma, 30). Tools: list_items and run_query. Resource URI:
   db://items. The server is read-only by rule (see safety below).
5. Host client. HostClient connects to both servers in process,
   aggregates their tool lists into one registry (4 tools in total,
   2 per server), routes tools/call by tool name, and routes
   resources/read by server name.
6. Safety rules, enforced and tested. Path traversal outside the
   sandbox is blocked (code -32002, reason path_traversal). Write or
   DROP style database requests are blocked (code -32003, reason
   write_blocked): run_query accepts one statement only, its first
   word must be SELECT, and blocked words (INSERT, UPDATE, DELETE,
   DROP, ALTER, CREATE, REPLACE and others) anywhere in the SQL block
   it. Unknown tools return code -32001, reason tool_not_found. Bad
   or missing arguments return code -32602, reason invalid_params.
   Unknown methods return -32601 and a missing file returns -32004.

## Protocol message examples (from real runs)

Request, a successful file read (call C05):

    {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
     "params": {"name": "read_file", "arguments": {"path": "hello.txt"}}}

Response:

    {"jsonrpc": "2.0", "id": 5,
     "result": {"path": "hello.txt", "content": "hello mcp\n"}}

Request, a traversal attempt (call C11, path ../secret.txt). Response:

    {"jsonrpc": "2.0", "id": 11,
     "error": {"code": -32002, "message": "path outside sandbox",
               "data": {"reason": "path_traversal"}}}

Request, a write attempt (call C13, sql "DROP TABLE items"). Response:

    {"jsonrpc": "2.0", "id": 13,
     "error": {"code": -32003,
               "message": "only read-only SELECT is allowed",
               "data": {"reason": "write_blocked"}}}

## Run it

    python level-1-learn/run_learn.py
    python -m unittest tests.test_learn_mcp -v
    python tests/test_smoke.py

The runner writes level-1-learn/results_learn.json deterministically:
run it twice and the file is identical (verified by hash on
2026-11-05, sha256 ba7fa2cd0815 on both runs).

## Results (measured 2026-11-05, Muse VM, Python 3.12)

Summary: 18 protocol calls in total: 10 successes, 4 blocked, and
4 errors. Blocked by rule: path_traversal 2, write_blocked 2.
Tools: 4 in total, 2 from the file server and 2 from the database
server. Unit tests: 17 tests, all passing, plus the scaffold smoke
test.

| Call | Server | Method or tool | Status | Detail |
| --- | --- | --- | --- | --- |
| C01 | file | initialize | success | protocolVersion learn-1 |
| C02 | database | initialize | success | protocolVersion learn-1 |
| C03 | file | tools/list | success | read_file, list_files |
| C04 | database | tools/list | success | list_items, run_query |
| C05 | file | read_file hello.txt | success | content "hello mcp\n" |
| C06 | file | list_files | success | hello.txt, notes.txt |
| C07 | database | list_items | success | rows (1, alpha, 10), (2, beta, 20), (3, gamma, 30) |
| C08 | database | run_query score >= 20 | success | rows (beta, 20), (gamma, 30) |
| C09 | file | resources/read sandbox://notes.txt | success | text "tools need rules\n" |
| C10 | database | resources/read db://items | success | 3 rows, same as C07 |
| C11 | file | read_file ../secret.txt | blocked | -32002 path_traversal |
| C12 | file | read_file /etc/passwd | blocked | -32002 path_traversal |
| C13 | database | run_query DROP TABLE items | blocked | -32003 write_blocked |
| C14 | database | run_query INSERT INTO items | blocked | -32003 write_blocked |
| C15 | file | delete_file (unknown tool) | error | -32001 tool_not_found |
| C16 | database | run_query with no sql argument | error | -32602 invalid_params |
| C17 | file | read_file missing.txt | error | -32004 file_not_found |
| C18 | file | bogus/method | error | -32601 method_not_found |

Hand checks: successes are 2 initialize plus 2 tools/list plus 6
data calls (C05 to C10), which is 10. Blocked are 2 traversal plus
2 write attempts, which is 4. Errors are C15 to C18, which is 4.
10 plus 4 plus 4 is 18, the total. Scores at or above 20 in the seed
table are beta at 20 and gamma at 30, exactly the C08 rows. The seed
scores sum to 10 plus 20 plus 30, which is 60.

## Known limits

The scope limits of this level, largest first.

- In-process transport only, no HTTP or stdio transport yet.
- Synthetic tiny fixtures (2 files, 3 database rows).
- Run on the Muse VM, not the assigned fleet node BlackBoxV2.
- No authentication, which is Deep scope.
- SQL safety is a first word check plus a blocked word list, not a SQL parser or a sqlite authorizer, so a crafted read query is only partly constrained.
- Resources/read is minimal (two URI forms, no resources/list and no subscriptions).

## Failure modes and limits

- Transport is in-process dict passing only. Nothing here speaks to
  a real MCP client, and wire format, framing, and concurrency are
  untested.
- The SQL guard is a teaching guard, not a proof. It blocks the
  named write words and multi-statement input, but it does not parse
  SQL, and a SELECT can still read any table in this one-table
  database or be expensive.
- The file sandbox check uses real path resolution, which handles
  dot-dot and absolute paths in the tests. Symlink handling beyond
  real path resolution, race conditions, and large files are out of
  scope at this level.
- The database is in-memory and resets on every start. Nothing
  persists, and there is no authentication or per-caller permission.
- Fixtures are tiny and synthetic by design: 2 files and 3 rows prove
  the protocol path, not scale or real data behaviour.
- Error coverage is the named set in the results table. Malformed
  requests outside that set return a generic internal error object,
  still with no traceback to the client.
- This level was run on the Muse VM (CPU), not on its fleet node
  BlackBoxV2. It is listed under Known limits.

## What Build adds next

A real transport (stdio first), a persistent database, more servers
and tools, and a wider safety test set. Deep adds authentication,
remote MCP over HTTP, and the full tool safety rules. See the root
README level map.
