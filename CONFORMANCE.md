# MCP conformance

This file records how the three mcp-toolkit servers were verified
against the official Model Context Protocol specification, check by
check. It is the evidence behind the conformance sentence in
README.md. Anything not verified here is not claimed.

## Basis and method

- Specification: the MCP specification, version 2025-11-25, read at
  modelcontextprotocol.io on 2026-11-15 (Basic: Lifecycle, Basic:
  base protocol and Transports, Basic: Utilities/Ping, Server
  Features: Tools, Server Features: Resources). The servers
  negotiate protocol versions 2025-11-25, 2025-06-18, 2025-03-26,
  and 2024-11-05.
- Suite: tests/test_mcp_conformance.py, run with
  `python3 -m unittest tests.test_mcp_conformance`. Measured
  2026-11-15 on the Muse VM, Python 3.12.3: 59 tests, all passing.
  The full repository suite is 134 tests, all passing.
- Arms. Learn is exercised in process through handle(). Build is
  exercised over its real transport: a server subprocess driven
  through raw stdio pipes, not through the toolkit's own client.
  Deep is exercised over its real transport: a live HTTP server
  driven with raw urllib requests, not through the toolkit's own
  client. Fault injection (C13) runs in process against the same
  dispatch code the transports call.
- Result words: "pass" means the check ran and the observed behavior
  matched the cited specification text. "Not run" means the check
  did not run on that arm; the reason is stated, and no conformance
  is claimed for that arm.

## Summary

32 checks. Run: 32. Passed: 32. Failed: 0. Not run: 0 checks.
Individual arms not run: C08 at Learn (no serialization boundary in
process), C13 over the stdio and HTTP transports (fault injection
needs in-process control; the dispatch code path is identical), and
C20 to C22 at Deep (the Deep server offers no resources; that is
itself verified as C23).

## Checks

| Check | Specification | What is verified | Result | Evidence (suite tests) |
| --- | --- | --- | --- | --- |
| C01 | Lifecycle: version negotiation | initialize with a supported older version (2025-06-18) is answered with that same version | pass | Learn test_c01; Build test_c01_c03_c04; Deep test_c01 |
| C02 | Lifecycle: version negotiation | initialize with an unsupported version is answered with the newest supported version (2025-11-25) | pass | Learn test_c02; Build test_c02; Deep test_c02 |
| C03 | Lifecycle: InitializeResult | The initialize result carries protocolVersion, a capabilities object (tools, and resources where offered), and serverInfo with name and version | pass | Learn test_c03; Build test_c01_c03_c04; Deep test_c03 |
| C04 | Lifecycle; Base protocol: notifications | After initialize, the client sends notifications/initialized and the server sends no response to it | pass | Learn test_c04; Build test_c01_c03_c04; Deep test_c04_c29 |
| C05 | Lifecycle: initialization | Requests sent before the initialize exchange completes are rejected with an error, and succeed after it | pass | Learn test_c05; Build test_c05; Deep test_c05 |
| C06 | Utilities: Ping | A ping request is answered promptly with an empty result, before and after initialization | pass | Learn test_c06; Build test_c01_c03_c04 (ping after handshake); Deep test_c06 |
| C07 | Base protocol: JSON-RPC errors | An unknown method is answered with error code -32601 (method not found) | pass | Learn test_c07; Build test_c07_c09_c10_c11_c12_c14_c16_c17; Deep test_c07 |
| C08 | Base protocol: JSON-RPC errors | Malformed JSON is answered with error code -32700 (parse error) and a null id | pass (Learn arm not run: no serialization boundary in process) | Build test_c08; Deep test_c08 |
| C09 | Base protocol: message shapes | A request with no method, a request with jsonrpc other than "2.0", and a request with a null id are each answered with -32600 (invalid request); MCP request ids must not be null | pass | Learn test_c09; Build test_c07_c09_c10_c11_c12_c14_c16_c17; Deep test_c09 |
| C10 | Base protocol (batching removed in 2025-06-18) | A JSON-RPC batch array is answered with a single -32600 error object, not an array of responses | pass | Learn test_c10; Build test_c07_c09_c10_c11_c12_c14_c16_c17; Deep test_c10 |
| C11 | Base protocol: notifications | An unknown notification is never answered: no stdio line, and HTTP 202 with an empty body | pass | Learn test_c11; Build test_c07_c09_c10_c11_c12_c14_c16_c17; Deep test_c11 |
| C12 | Base protocol: responses | Responses carry jsonrpc "2.0" and echo the request id, including a string id | pass | Learn test_c12; Build test_c07_c09_c10_c11_c12_c14_c16_c17; Deep test_c12 |
| C13 | Base protocol: JSON-RPC errors | An unexpected server fault is answered with -32603 (internal error), never a traceback | pass in process on all three levels (transport arms not run: fault injection needs in-process control of the same dispatch code) | Learn test_c13; Build test_c13; Deep test_c13 |
| C14 | Server Features: Tools | Every tool in tools/list has a string name, a string description, and an inputSchema object of type "object"; the tools capability is declared as an object | pass | Learn test_c14; Build test_c07_c09_c10_c11_c12_c14_c16_c17; Deep test_c14 |
| C15 | Server Features: Tools (CallToolResult, structured content) | A successful tools/call returns a result whose content holds at least one text block, whose structuredContent is the tool payload, whose text block parses back to the same payload, and whose isError is false | pass | Learn test_c15; Build test_c15; Deep test_c15_c32 |
| C16 | Server Features: Tools (error handling) | An unknown tool name is a protocol error, code -32602 | pass | Learn test_c16; Build test_c07_c09_c10_c11_c12_c14_c16_c17; Deep test_c16 |
| C17 | Server Features: Tools (error handling) | A call missing a required argument is a protocol error, code -32602 | pass | Learn test_c17; Build test_c07_c09_c10_c11_c12_c14_c16_c17; Deep test_c17 |
| C18 | Server Features: Tools (error handling) | A tool execution failure (reading a file that does not exist) is a tool result with isError true, not a protocol error | pass | Learn test_c18; Build test_c18_c19_c22; Deep test_c18 |
| C19 | Server Features: Tools (error handling) | Safety refusals (path traversal, a non-SELECT statement) are tool results with isError true and the named reason in structuredContent | pass | Learn test_c19; Build test_c18_c19_c22; Deep test_c19 |
| C20 | Server Features: Resources (resources/list) | resources/list returns resource objects with uri and name | pass (Deep arm not applicable: Deep offers no resources, see C23) | Learn test_c20; Build test_c20_c21 |
| C21 | Server Features: Resources (resources/read) | resources/read returns a contents array; each item carries uri and text | pass (Deep arm not applicable, see C23) | Learn test_c21; Build test_c20_c21 |
| C22 | Server Features: Resources (error handling) | Reading a resource that does not exist is answered with error code -32002 | pass (Deep arm not applicable, see C23) | Learn test_c22; Build test_c18_c19_c22 |
| C23 | Lifecycle: capabilities; Resources | The Deep server does not declare a resources capability, and resources/list and resources/read over HTTP are answered with -32601 | pass | Deep test_c23 |
| C24 | Transports: stdio | Stdio messages are newline-delimited, each line is one complete JSON-RPC message, and nothing else is written to stdout | pass | Build test_c24 |
| C25 | Lifecycle: shutdown; Transports: stdio | The specification defines no shutdown message; over stdio, closing the input stream ends the server process with exit code 0 | pass | Build test_c25 |
| C26 | Lifecycle: shutdown | A request with method "shutdown" is answered with -32601 at every level: no such message exists | pass | Learn test_c26; Build test_c26; Deep test_c26 |
| C27 | Transports: streamable HTTP (GET) | GET on the MCP endpoint returns HTTP 405 (this server offers no SSE stream) | pass | Deep test_c27 |
| C28 | Transports: streamable HTTP (protocol version header) | After negotiation, a request carrying MCP-Protocol-Version with the negotiated version is accepted, and one carrying an unsupported version is answered with HTTP 400 | pass | Deep test_c28 |
| C29 | Transports: streamable HTTP (notifications) | A notification POST is answered with HTTP 202 and no body | pass | Deep test_c04_c29 |
| C30 | Transports: streamable HTTP (Origin security) | A POST with a foreign Origin header is answered with HTTP 403; a loopback Origin is accepted | pass | Deep test_c30 |
| C31 | Authorization framework (HTTP transports) | The toolkit's bearer token layer applies to initialize as well: initialize without a valid token is answered with HTTP 401 | pass | Deep test_c31 |
| C32 | Transports: streamable HTTP (POST responses) | A request POST is answered with Content-Type application/json and a single JSON object | pass | Deep test_c15_c32 |

## Design decisions and limits

- Stateless HTTP. The Deep server issues no Mcp-Session-Id. The
  transports text says a server MAY assign a session id at
  initialization; not assigning one is conformant. Lifecycle state
  (which roles completed the initialize exchange) is kept server
  side per role.
- Protocol version header fallback. The transports text says a
  server that receives no MCP-Protocol-Version header and cannot
  identify the version otherwise SHOULD assume 2025-03-26. This
  server identifies the version from the initialize exchange, so
  the fallback does not apply; an unsupported header value is
  answered with 400, as the text requires.
- Pre-initialization rejections. The lifecycle text requires
  initialization to be the first interaction but names no error
  code for early requests. The toolkit answers -32600 with
  data.reason "not_initialized". C05 verifies the rejection and
  the recovery after a proper handshake; the specific code is a
  toolkit choice, not a specification value.
- Unknown tools at Deep. The wire answer is the protocol error
  -32602 (C16). The attempt is also written to the toolkit's safety
  audit log with reason "unknown_tool"; the audit log is a toolkit
  feature, not specification behavior.
- Traversal on resources/read. A sandbox URI that resolves outside
  the sandbox is answered with -32002 and data.reason
  "path_traversal": the resources text fixes -32002 for a resource
  that is not found, and a path outside the sandbox is not a
  resource of this server.
- Authorization. The specification provides an Authorization
  framework for HTTP-based transports. Deep's static bearer tokens
  with two roles (reader, operator) are the toolkit's choice under
  that framework, unchanged from v1.0, including its HTTP statuses
  (401 for a missing or invalid token, 403 for a role that may not
  call a tool). This is a teaching design: no OAuth, no expiry, no
  rotation (level-3-deep/README.md, Honest scope line).
- Complete lists. tools/list and resources/list return complete
  lists in one response, without a pagination cursor.
- Not offered, and not claimed: prompts, sampling, roots,
  elicitation, logging, tasks, and SSE streaming. The servers
  declare only the capabilities they implement (tools at all three
  levels, resources at Learn and Build).
- Specification text only. Conformance was verified against the
  written specification. The official MCP SDK was not connected;
  that interop run remains open as REPORT.md Future work 4, and
  nothing here claims it.
