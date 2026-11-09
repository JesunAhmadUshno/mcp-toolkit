# PUBLICITY: mcp-toolkit (P09)

Publicity log under the documentation and publishing standard,
Section 7. Every finished level produces its written fan-out set.
Pieces are reviewed internally before release; review scores are kept
outside this repo. Drafts are prepared by the loop. Actual social posting follows
the standing platform rules and gates. The loop itself never posts
to social.

Fan-out set date: 2026-11-05. Project state: v1.0, Learn, Build,
and compressed Deep done 2026-11-05, 65 tests passing. Deep
detail: an MCP-style JSON-RPC server
over real HTTP (Python standard library, localhost, POST /mcp,
GET /health), bearer authentication by SHA-256 hash comparison
(no token value in the repo), two roles (reader sees the 4 read
tools, operator sees all 6), and a safety rules set with named
blocks and an audit log. Measured over 30 protocol calls on
authenticated HTTP: 8 successes, 3 unauthenticated rejections at
HTTP 401, 2 role blocks at HTTP 403, 13 safety blocks
(path_traversal 2, absolute_path_blocked 1, write_blocked 1,
delete_blocked 1, sql_not_select 4, sql_multi_statement 2,
request_too_large 1 at the 8192-byte cap, unknown_tool 1), and
4 named errors, with 18 audit log entries. Labelled honestly:
localhost only, no TLS, teaching auth (no expiry or rotation),
toy fixtures of 3 files and 3 rows, MCP-style and not the
official SDK.

## Fan-out set (moved from the root README)

Written fan-out set for v1.0, dated 2026-11-05, in this folder (fanout/):

- blog-post.md: "Tools With Rules", the full story with
  the main results claim gated by Jev claim_check (model
  jev-1.13.0, noul 0.84, route REVIEW, no block).
- tutorial.md: course module P09-mcp-toolkit. Every
  command in it was executed and passed on 2026-11-05 (all
  three runners, all per-level tests, full suite at 65 tests).
- website-page.md: project page copy only, not published.
- linkedin-post.md: DRAFT NOT POSTED, link as the
  first-comment line per the LinkedIn rule.
- paper-candidate.md: tool safety rules note at
  CANDIDATE. Submission is Jesun's tap, nothing submitted.
- release-notes.md: draft notes for the live releases
  v0.1, v0.5, and v1.0.

The loop never posts to social: all social channels are held with
named reasons in the channel log below.

## Channel log (2026-11-05)

| Channel | Outcome on 2026-11-05 |
| --- | --- |
| GitHub releases | Live: v0.1 https://github.com/JesunAhmadUshno/mcp-toolkit/releases/tag/v0.1 , v0.5 https://github.com/JesunAhmadUshno/mcp-toolkit/releases/tag/v0.5 , v1.0 https://github.com/JesunAhmadUshno/mcp-toolkit/releases/tag/v1.0 (verified with gh release list, 2026-11-05). Draft release notes for all three are in fanout/release-notes.md. No new release was created for the fan-out. |
| Portfolio index | Held: fan-out links are ready, the index update is a coordinator step outside this cycle. Named reason: held for coordinator refresh. |
| Website page | Draft in fanout/website-page.md. Held: not published to jesunahmadushno.com. |
| Blog | Draft in fanout/blog-post.md. Held: not posted. |
| Tutorial | In repo: fanout/tutorial.md. Every command in it was run and verified on 2026-11-05 (three runners, three per-level test modules, scaffold smoke test, full suite at 65 tests). |
| LinkedIn post | Draft in fanout/linkedin-post.md, marked DRAFT NOT POSTED, link carried as the first-comment line per the LinkedIn rule. Held: not posted, loop never posts. |
| X | Draft held: no X copy is shipped in this set beyond the LinkedIn draft source text. Held under the standing social rules; posting is outside the loop. |
| Facebook | Draft held: no Facebook copy posted. Standing rule applies (no link in body or comments, keyword call to action fulfilled by DM). Held: not posted, loop never posts. |
| Instagram | Draft held: no Instagram copy posted. Standing rule applies (no clickable link in caption, link in bio). Held: not posted, loop never posts. |
| Threads | Draft held: no Threads copy posted. Threads waits for Jesun's tap per post, hash-locked on exact text and media. Held: awaiting Jesun's tap. |
| Video | Held: engine queue, January production for lab projects per the December Compression Protocol. No video was produced in this cycle. |
| Book chapter | Draft angle in fanout/blog-post.md and PROPOSAL.md ("Tools With Rules"). Held: chapter draft follows the finished project set; not a published chapter. |
| Paper candidate | Draft brief in fanout/paper-candidate.md (tool safety rules note, measured call-set form). Submission is Jesun's tap. Nothing submitted, no venue contacted. The publications tracker is updated by the coordinator, not by this cycle. |

## Jev gate (2026-11-05)

claim_check on the blog main results paragraph, extracted
byte-exact from fanout/blog-post.md by script. Spec:
hidden_files/jev-p09-fanout-claim-spec-2026-11-05.json in the
goal workspace. Results:
hidden_files/jev-p09-fanout-claim-results-2026-11-05.json. Model
jev-1.13.0, question id supported, noul 0.84, route REVIEW
(clear at 0.85 or above, block at 0.10 or below, review
between), input tokens 1328, output tokens 20. Arithmetic was
pre-computed in the spec evidence (8 plus 3 plus 2 plus 13
plus 4 is 30; 2 plus 1 plus 1 plus 1 plus 4 plus 2 plus 1 plus
1 is 13; 3 plus 2 plus 13 is 18; 17 plus 20 is 37 and 37 plus
28 is 65). No claim was blocked.
