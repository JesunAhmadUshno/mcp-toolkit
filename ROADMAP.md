# ROADMAP: mcp-toolkit (P09)

## Shipped

- v0.1 Learn (2026-11-05): in-process MCP-style protocol, file and database servers, first safety rules.
- v0.5 Build (2026-11-05): host over real stdio to 3 server processes, 6 tools, safety rules retained.
- v1.0 Deep (2026-11-05, compressed Deep under the December protocol): remote MCP over HTTP on localhost, bearer token authentication by hash comparison, reader and operator roles with server-side allowlists, the full tool safety rules set with named block reasons and an audit log, benchmarked at 30 measured calls, grade 8,300 of 10,000.

## v1.1 backlog (the rest of the v2 Deep scope)

Named here at the v1.0 ship, per the December compression protocol. None of this is claimed as done.

1. TLS termination: a documented way to serve the HTTP endpoint behind TLS, so bearer tokens never cross a network in clear text. Localhost-only stays the default.
2. Token lifecycle: expiry, rotation, and revocation for token hashes, plus per-caller identities beyond the two fixed roles.
3. Durable audit log: append-only on-disk audit entries with the same categories and reasons, surviving server restarts.
4. Official MCP interop: connect a real MCP client and the official MCP SDK to this server shape and record what matches and what does not, instead of claiming compliance.
5. Stronger SQL safety: a real SQL parser or a sqlite authorizer in place of the first-word and token check, plus a query timeout and a row cap for permitted SELECT calls.
6. Server hardening: request timeouts, rate limiting and authentication throttling, a streaming body size cap that does not trust the declared Content-Length, and request ids correlated across the audit log.
7. Resources over HTTP: resources/read for sandbox and database resources, which Build has over stdio and Deep does not expose yet.
8. Scale fixtures: larger sandbox file sets and database tables, with the benchmark rerun and the grade re-taken on the bigger fixtures.
9. Fleet run: the full Deep benchmark rerun on BlackBoxV2, the assigned fleet node, replacing the Muse VM numbers or standing beside them with both named.

## Rules for this file

- An item leaves this backlog only when it ships with tests and measured results, the same gates as v1.0.
- New scope discovered during v1.1 work is added here with a date, never silently folded into a shipped claim.
