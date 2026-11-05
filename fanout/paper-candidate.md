# Paper candidate brief: tool safety rules for MCP-style servers

Project: P09 mcp-toolkit
Status: CANDIDATE, brief written 2026-11-05
Submission note: submission is Jesun's tap. Nothing is submitted by
this brief, and no venue has been contacted. The publications
tracker is updated by the coordinator, not by this file.

## Working title

What a tool may never do: a named safety and authorization rule
set for an MCP-style tool server, measured over authenticated
HTTP with role allowlists and an audit log

## Abstract draft

Based only on the measured v1.0 results recorded in the repo.
The server is MCP-style, not the official MCP SDK. Fixtures are
toy size and are stated as such. No token value appears in this
brief or in the repo.

Agent tools act on files, databases, and networks, so a tool
server needs rules about what a call may never do, enforced
where the caller cannot switch them off. This work presents an
open, dependency-free MCP-style toolkit and measures its
authorization and safety layer over real HTTP. At Learn level,
an in-process protocol with a sandboxed file server and a
read-only database server ran 18 calls with 10 successes, 4
safety blocks, and 4 named errors, with 17 unit tests. At Build
level, three server processes over stdio ran 24 calls with 14
successes, 4 blocks, and 6 errors, aggregating 6 tools, with
20 tests (37 in total). At Deep level, one server over HTTP on
localhost with bearer tokens checked by SHA-256 hash
comparison and two server-side roles (reader: 4 read tools;
operator: all 6 tools) ran 30 calls: 8 successes, 3
unauthenticated rejections at HTTP 401, 2 role blocks at HTTP
403, 13 safety blocks, and 4 named errors, with 18 audit log
entries and 28 tests (65 in total). The safety blocks cover
path traversal (2), absolute paths outside the sandbox (1),
write attempts (1), delete attempts (1), SQL that is not a
single read-only SELECT (4), multi-statement SQL (2),
requests over the 8192-byte cap (1), and unknown tools (1).
Blocked calls never modified the sandbox or the table, and
the tests re-read both after blocks. The paper claims the
rule set, its server-side placement, and its measured
behaviour on this fixed call set, including the recorded
limits of the teaching auth design and the token-check SQL
guard, not production security.

## Method outline

1. Protocol layer: JSON-RPC style requests and responses over
   three transports in sequence (in-process dicts, stdio
   subprocess pipes, HTTP POST /mcp with GET /health), with
   every failure returned as a named error object.
2. Authentication: bearer token presented per call, SHA-256
   hash comparison with hmac.compare_digest, hashes loaded
   from the environment at server start, fail-closed start
   on a missing or malformed hash map.
3. Authorization: two fixed roles with server-side tool
   allowlists, and tools/list filtered per role so a caller
   cannot see tools it may not call.
4. Safety rules, checked server-side before any tool runs:
   sandbox path resolution, write and delete attempt blocks,
   read-only single-statement SQL rules, a request size cap
   enforced before parsing or auth, and unknown tool blocks.
5. Audit log: in-memory, sequence numbered, with categories
   auth, authorization, and safety, carrying role and tool
   names only, never token values or file contents.
6. Fixed call sets: 18 Learn calls, 24 Build calls, and 30
   Deep calls, each call recorded with its expected outcome
   in the level README before grading, and each results file
   deterministic across two runs.
7. Post-block integrity: tests re-read the sandbox files and
   the database rows after the blocked calls and assert no
   change.

## Results table

Measured 2026-11-05, from the level READMEs in the repo.

| Level | Set | Headline result | Auth and safety detail | Tests |
| --- | --- | --- | --- | --- |
| Learn | 18 calls, in process | 10 successes, 4 blocks, 4 errors | path_traversal 2, write_blocked 2; no auth at this level | 17 |
| Build | 24 calls over stdio | 14 successes, 4 blocks, 6 errors | Same rules over real transport; 6 tools, 3 servers | 20 (37 total) |
| Deep | 30 calls over HTTP | 8 successes, 3 at 401, 2 at 403, 13 safety blocks, 4 errors | 8 named safety reasons; 18 audit entries; reader 4 tools, operator 6 | 28 (65 total) |

## Venue class note

Per SPEC.md, the paper angle for P09 is a tool safety rules
note (what a tool may never do, with the test set). This brief
is that note in measured form. Venue class is a workshop or
conference in ML systems, agent infrastructure, or software
security practice, or a journal of the AJSE class, per the
publications pipeline tracker rules. One venue at a time. No
venue is named as submitted, accepted, or contacted in this
brief. Fees, if any, arise only after acceptance and remain
Jesun's call under the free-only rule.

## Limits the paper must carry

- Localhost only, no TLS. Nothing here measures network
  exposure, and the server must not be deployed beyond
  localhost in this form.
- Teaching auth. Fixed bearer tokens with no expiry,
  rotation, revocation, or per-user identity. The measured
  result is about rule placement and naming, not about
  production identity strength.
- Toy fixtures: 3 files and 3 rows. The call sets prove the
  rules fire; they do not measure bypass rates against an
  adversarial corpus.
- The SQL guard is a first-word and token check, not a
  parser or a sqlite authorizer. A permitted SELECT can
  still be expensive or oddly shaped.
- MCP-style message shapes, not the official SDK. No real
  MCP client interop was tested; that is v1.1 backlog.
- The audit log is in memory and resets on restart. It is
  run evidence, not a durable audit trail.
- Compressed Deep only. The v1.1 backlog (TLS guidance,
  token lifecycle, durable audit, SDK interop, SQL parser,
  timeouts and rate limiting, larger fixtures) is future
  work, named in ROADMAP.md in the repo.

## Submission gate

Submission is Jesun's tap and nothing is submitted. This brief is
the candidate only.
