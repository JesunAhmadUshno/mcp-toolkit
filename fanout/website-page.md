# Website project page copy: mcp-toolkit

Site: jesunahmadushno.com
Status: COPY ONLY, draft for the project page. Dated 2026-11-05.
Nothing on any website was changed by this file.

## Headline

mcp-toolkit: an MCP-style tool server and host with bearer authentication, server-side roles, and a named safety rules set, built in the open

## Summary

mcp-toolkit is an open agent-protocols project built by Jesun
Ahmad Ushno as project P09 in Roadmap v3. It builds a tool
toolkit in three levels: an in-process MCP-style protocol with
the first safety rules; a host client connecting to three
servers over real stdio subprocess transport; and authenticated
remote MCP over real HTTP on localhost, with bearer tokens
checked by SHA-256 hash comparison, two roles enforced
server-side (reader sees 4 read tools, operator sees all 6),
and the full safety rules set with named block reasons and an
audit log. It runs on the Python standard library only. It is
MCP-style, not the official MCP SDK.

Status: v1.0, 2026-11-05. Learn, Build, and compressed Deep
are done. Total tests: 65, all passing at v1.0. Level grades:
Learn 8,700 of 10,000, Build 8,600 of 10,000, Deep 8,300 of
10,000.

## Results

All results below are measured runs recorded in the level
READMEs in the GitHub repo.

| Level | Set | Headline result | Notes |
| --- | --- | --- | --- |
| Learn | 18 protocol calls, in process | 10 successes, 4 safety blocks, 4 named errors | 4 tools (2 file, 2 database); 17 tests |
| Build | 24 protocol calls over stdio | 14 successes, 4 safety blocks, 6 named errors | 6 tools across 3 servers (file, database, calc); 20 tests, 37 total |
| Deep (compressed) | 30 protocol calls over authenticated HTTP | 8 successes, 3 unauthenticated at 401, 2 role blocks at 403, 13 safety blocks, 4 named errors | Safety reasons: path_traversal 2, absolute_path_blocked 1, write_blocked 1, delete_blocked 1, sql_not_select 4, sql_multi_statement 2, request_too_large 1, unknown_tool 1; 18 audit entries; 28 tests, 65 total |

## Honest limits

- Localhost only, no TLS. The server binds 127.0.0.1 and must
  never be exposed beyond localhost in this form.
- Teaching auth: fixed bearer tokens, hash-compared, with no
  expiry, rotation, revocation, or per-user identity.
- Toy fixtures: 3 sandbox files and 3 database rows prove the
  auth, role, and safety path, not scale.
- The SQL guard is a first-word and token check, not a SQL
  parser or a sqlite authorizer.
- Compressed Deep is not the full v2 Deep scope. The
  remainder is the v1.1 backlog in the repo ROADMAP.md.

## Links

- GitHub repo: https://github.com/JesunAhmadUshno/mcp-toolkit
- Release v0.1 (Learn): https://github.com/JesunAhmadUshno/mcp-toolkit/releases/tag/v0.1
- Release v0.5 (Build): https://github.com/JesunAhmadUshno/mcp-toolkit/releases/tag/v0.5
- Release v1.0 (Learn, Build, compressed Deep): https://github.com/JesunAhmadUshno/mcp-toolkit/releases/tag/v1.0
- Tutorial: fanout/tutorial.md in the GitHub repo
- Blog post draft: fanout/blog-post.md in the GitHub repo

## License note

Code: Apache-2.0. Tutorials: CC BY 4.0.
