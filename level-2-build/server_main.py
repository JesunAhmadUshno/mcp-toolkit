"""Stdio server entrypoint. Usage: server_main.py <file|database|calc> [sandbox]

Speaks NDJSON over stdio: requests on stdin, responses on stdout.
Diagnostics, if any, go to stderr only, so stdout stays pure protocol.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mcp_build import make_server, serve_stdio  # noqa: E402


def main(argv):
    if len(argv) < 2 or argv[1] not in ("file", "database", "calc"):
        print("usage: server_main.py <file|database|calc> [sandbox]",
              file=sys.stderr)
        return 2
    sandbox = argv[2] if len(argv) > 2 and argv[2] else os.path.join(
        HERE, "demo_sandbox")
    serve_stdio(make_server(argv[1], sandbox))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
