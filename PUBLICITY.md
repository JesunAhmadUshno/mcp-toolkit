# PUBLICITY: mcp-toolkit (P09)

Publicity log under the documentation and publishing standard,
Section 7. Every finished level produces its written fan-out set,
each piece graded on the 1,000-point publicity rubric (accuracy 300,
research 200, gap fit 200, clarity 150, reach format 150), ship line
900. Drafts are prepared by the loop. Actual social posting follows
the standing platform rules and gates. The loop itself never posts
to social.

Fan-out set date: 2026-11-05. Project state: v1.0, Learn, Build,
and compressed Deep done 2026-11-05, 65 tests passing. Level
grades on record: Learn 8,700 of 10,000, Build 8,600 of 10,000,
Deep 8,300 of 10,000. Deep detail: an MCP-style JSON-RPC server
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
| Book chapter | Draft angle in fanout/blog-post.md and SPEC.md ("Tools With Rules"). Held: chapter draft follows the finished project set; not a published chapter. |
| Paper candidate | Draft brief in fanout/paper-candidate.md (tool safety rules note, measured call-set form). Submission is Jesun's tap. Nothing submitted, no venue contacted. The publications tracker is updated by the coordinator, not by this cycle. |

## Publicity grades (1,000-point rubric, ship line 900)

| Piece | Accuracy /300 | Research /200 | Gap fit /200 | Clarity /150 | Reach format /150 | Total /1000 |
| --- | --- | --- | --- | --- | --- | --- |
| fanout/blog-post.md | 295 | 188 | 194 | 145 | 140 | 962 |
| fanout/tutorial.md | 298 | 185 | 195 | 148 | 142 | 968 |
| fanout/website-page.md | 293 | 180 | 190 | 147 | 145 | 955 |
| fanout/linkedin-post.md | 288 | 175 | 190 | 145 | 140 | 938 |
| fanout/paper-candidate.md | 293 | 195 | 194 | 140 | 130 | 952 |
| fanout/release-notes.md | 296 | 183 | 184 | 144 | 138 | 945 |

All six pieces are at or above the 900 ship line. No piece was
shipped ungraded. Overall fan-out grade: 9,533 of 10,000 (mean of
the six piece totals, 953 of 1,000).

## Named deductions (unclosable in this cycle)

- Blog post, minus 38: research is condensed from DOSSIER.md v1,
  whose prior art section is brief (minus 12 research); toy
  fixtures and localhost-only scope limit how far the results
  travel, stated in the piece (minus 10 reach, minus 5 accuracy
  for reader interpretation risk, minus 6 gap fit, minus 5
  clarity).
- Tutorial, minus 32: research framing is thinner than the blog
  by design, because the module teaches runs rather than the
  field (minus 15 research); no worked example beyond the
  shipped call sets (minus 5 gap fit, minus 2 clarity, minus 8
  reach, minus 2 accuracy).
- Website page, minus 45: condensed research (minus 20),
  condensed gap framing (minus 10), and the page is copy only,
  not a live page (minus 5 reach, minus 7 accuracy, minus 3
  clarity).
- LinkedIn post, minus 62: short form compresses the research
  and the failure mode detail (minus 25 research, minus 12
  accuracy, minus 10 gap fit, minus 5 clarity, minus 10 reach,
  because the post is a held draft and carries no live link in
  the body by rule).
- Paper candidate, minus 48: this is a brief, not a drafted
  paper (minus 20 reach, minus 10 clarity); venue is classed,
  not named (minus 5 research, minus 6 gap fit, minus 7
  accuracy for the toy-fixture evidence base the paper must
  carry).
- Release notes, minus 55: notes summarise releases that
  already exist, so research and gap framing are summary grade
  (minus 17 research, minus 16 gap fit); format is repo-bound
  (minus 12 reach, minus 4 accuracy, minus 6 clarity).

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
