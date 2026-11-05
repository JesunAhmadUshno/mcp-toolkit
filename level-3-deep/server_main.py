"""Run the Deep MCP-style HTTP server as a standalone process.

Token hashes come from the environment at start. No token value and
no hash is stored in this repo. Generate a hash for a token you
choose locally with:

    python -c "import hashlib; print(hashlib.sha256(b'your token').hexdigest())"

Then start with, for example:

    MCP_TOOLKIT_TOKEN_HASHES='{"reader": "<hash>", "operator": "<hash>"}' \
        python level-3-deep/server_main.py

Environment:
    MCP_TOOLKIT_TOKEN_HASHES  required, JSON role to sha256 hex map
    MCP_TOOLKIT_PORT           optional, default 8765, localhost only
    MCP_TOOLKIT_SANDBOX        optional, default demo_sandbox beside
                               this file, fixtures written on start
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mcp_deep import TokenStore, ToolkitCore, make_server, write_fixtures  # noqa: E402


def main():
    token_store = TokenStore.from_env()
    sandbox = write_fixtures(os.environ.get(
        "MCP_TOOLKIT_SANDBOX", os.path.join(HERE, "demo_sandbox")))
    port = int(os.environ.get("MCP_TOOLKIT_PORT", "8765"))
    server = make_server(ToolkitCore(sandbox), token_store,
                         host="127.0.0.1", port=port)
    print("mcp-toolkit deep server on http://127.0.0.1:%d/mcp" % port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
