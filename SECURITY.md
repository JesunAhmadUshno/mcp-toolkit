# Security policy

Report a vulnerability privately through GitHub's "Report a
vulnerability" button on this repository's Security tab. Please do not
open a public issue for it. You will get a reply within 7 days.

Scope: the code in this repository. The servers are teaching
implementations that bind 127.0.0.1 only, with no TLS and fixed test
token hashes; they must not be exposed beyond localhost in this form
(level-3-deep/README.md, Failure modes and limits). No real token value
is stored in the repo. The threat model is in REPORT.md.
