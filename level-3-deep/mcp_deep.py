"""MCP-style tool protocol, Deep level: authenticated HTTP transport.

This is a stdlib-only MCP-style implementation. It is not the official
MCP SDK and claims no spec compliance beyond the message shapes it
documents. Deep adds, over the stdio Build level:

- Remote transport: one JSON-RPC style server over real HTTP
  (http.server, localhost only), POST /mcp, plus a small client.
- Authentication: bearer tokens checked by hash comparison. The
  server stores only SHA-256 hashes of tokens. At real server start
  the hashes come from an environment variable (see server_main.py);
  no token value is stored anywhere in this module.
- Two roles with server-side tool allowlists: reader (read tools
  only) and operator (read tools plus calc tools).
- The full tool safety rules set, enforced server-side, each with a
  named block reason and an audit log entry: path traversal, absolute
  path outside the sandbox, write attempts, delete attempts, SQL
  that is not a single read-only SELECT (multi-statement input and
  DROP, DELETE, UPDATE, INSERT and friends), oversize requests, and
  unknown tools. Defensive only: nothing here performs a write, a
  delete, or a non-SELECT statement, ever.

Teaching design, not production identity: no TLS (localhost only),
no token expiry or rotation, no rate limiting. See README.md.
"""
import hashlib
import hmac
import json
import os
import re
import sqlite3
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROTOCOL_VERSION = "deep-1"
MAX_BODY_BYTES = 8192

ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_PARAMS = -32602
ERR_UNAUTHENTICATED = -32010
ERR_FORBIDDEN_ROLE = -32011
ERR_TOOL_NOT_FOUND = -32001
ERR_SAFETY_BLOCKED = -32012
ERR_NOT_FOUND = -32004
ERR_QUERY = -32005
ERR_CALC = -32006
ERR_TOO_LARGE = -32013

READ_TOOLS = ("read_file", "list_files", "list_items", "run_query")
CALC_TOOLS = ("calculate", "count_words")
ROLE_TOOLS = {
    "reader": READ_TOOLS,
    "operator": READ_TOOLS + CALC_TOOLS,
}
ALL_TOOLS = READ_TOOLS + CALC_TOOLS
WRITE_TOOLS = ("write_file", "create_file", "append_file")
DELETE_TOOLS = ("delete_file", "remove_file", "unlink_file")

SAFETY_REASONS = {
    "path_traversal", "absolute_path_blocked", "write_blocked",
    "delete_blocked", "sql_not_select", "sql_multi_statement",
    "request_too_large", "unknown_tool",
}

TOOL_DEFS = [
    {"name": "read_file", "server": "file",
     "description": "Read one text file inside the sandbox.",
     "inputSchema": {"type": "object",
                     "properties": {"path": {"type": "string"}},
                     "required": ["path"]}},
    {"name": "list_files", "server": "file",
     "description": "List files inside the sandbox, sorted.",
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "list_items", "server": "database",
     "description": "List every row of the items table, by id.",
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "run_query", "server": "database",
     "description": "Run one read-only SELECT on the items table.",
     "inputSchema": {"type": "object",
                     "properties": {"sql": {"type": "string"}},
                     "required": ["sql"]}},
    {"name": "calculate", "server": "calc",
     "description": "Safe arithmetic: add, subtract, multiply, divide.",
     "inputSchema": {"type": "object",
                     "properties": {"op": {"type": "string"},
                                    "a": {"type": "number"},
                                    "b": {"type": "number"}},
                     "required": ["op", "a", "b"]}},
    {"name": "count_words", "server": "calc",
     "description": "Count whitespace separated words in a text.",
     "inputSchema": {"type": "object",
                     "properties": {"text": {"type": "string"}},
                     "required": ["text"]}},
]

FIXTURE_FILES = {
    "guide.txt": "servers need hosts\n",
    "hello.txt": "hello mcp\n",
    "notes.txt": "tools need rules\n",
}

SEED_ROWS = [
    {"id": 1, "name": "alpha", "score": 10},
    {"id": 2, "name": "beta", "score": 20},
    {"id": 3, "name": "gamma", "score": 30},
]

BLOCKED_SQL_WORDS = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
                     "CREATE", "REPLACE", "TRUNCATE", "GRANT", "REVOKE",
                     "ATTACH", "DETACH", "VACUUM", "PRAGMA"}


def hash_token(token):
    """SHA-256 hex digest of a bearer token. Only hashes are stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TokenStore:
    """Role to token-hash mapping. Holds hashes only, never tokens."""

    def __init__(self, role_hashes):
        self.role_hashes = dict(role_hashes)

    @classmethod
    def from_hashes(cls, role_hashes):
        return cls(role_hashes)

    @classmethod
    def from_plaintext(cls, role_tokens):
        """Test and local-run helper: hash plaintext tokens in memory.

        Callers pass clearly labelled test tokens only. The plaintext
        is hashed immediately and never stored on the store.
        """
        return cls({role: hash_token(tok) for role, tok in role_tokens.items()})

    @classmethod
    def from_env(cls, var="MCP_TOOLKIT_TOKEN_HASHES"):
        """Load role to SHA-256 hash mapping from an environment variable.

        Expected value: a JSON object like
        {"reader": "<sha256 hex>", "operator": "<sha256 hex>"}.
        Raises ValueError if the variable is missing or malformed, so
        a real server never starts unauthenticated by accident.
        """
        raw = os.environ.get(var)
        if not raw:
            raise ValueError("missing environment variable: " + var)
        data = json.loads(raw)
        if not isinstance(data, dict) or not data:
            raise ValueError(var + " must be a non-empty JSON object")
        for role, digest in data.items():
            if role not in ROLE_TOOLS:
                raise ValueError("unknown role in " + var + ": " + str(role))
            if not isinstance(digest, str) or len(digest) != 64:
                raise ValueError("token hash for role " + str(role)
                                 + " must be a 64 character sha256 hex digest")
        return cls(data)

    def authenticate(self, token):
        """Return the role for a bearer token, or None. Hash compared
        with hmac.compare_digest against every stored hash."""
        if not isinstance(token, str) or not token:
            return None
        digest = hash_token(token)
        matched = None
        for role, stored in self.role_hashes.items():
            if hmac.compare_digest(digest, stored):
                matched = role
        return matched


def error_response(req_id, code, message, reason):
    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": code, "message": message,
                      "data": {"reason": reason}}}


def ok_response(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def make_request(req_id, method, params=None):
    return {"jsonrpc": "2.0", "id": req_id, "method": method,
            "params": params or {}}


def write_fixtures(sandbox_dir):
    os.makedirs(sandbox_dir, exist_ok=True)
    for name in sorted(FIXTURE_FILES):
        with open(os.path.join(sandbox_dir, name), "w", encoding="utf-8") as f:
            f.write(FIXTURE_FILES[name])
    return sandbox_dir


class ToolkitCore:
    """The aggregated tool set behind the HTTP server, with safety."""

    def __init__(self, sandbox_dir):
        self.sandbox = os.path.realpath(sandbox_dir)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE items (id INTEGER, name TEXT, score INTEGER)")
        self.conn.executemany(
            "INSERT INTO items VALUES (?, ?, ?)",
            [(r["id"], r["name"], r["score"]) for r in SEED_ROWS])
        self.conn.commit()
        self.audit_log = []

    def audit(self, category, reason, tool, role):
        with self._lock:
            self.audit_log.append({
                "seq": len(self.audit_log) + 1, "category": category,
                "reason": reason, "tool": tool, "role": role})

    def audit_snapshot(self):
        with self._lock:
            return list(self.audit_log)

    def tools_for_role(self, role):
        allowed = ROLE_TOOLS[role]
        return [t for t in TOOL_DEFS if t["name"] in allowed]

    def dispatch(self, request, role):
        """Route one authenticated JSON-RPC request. Returns a response
        dict; the HTTP layer maps auth and role failures to status
        codes before this is called for tools/call (see handle_call)."""
        req_id = request.get("id") if isinstance(request, dict) else None
        if not isinstance(request, dict) or "method" not in request:
            return 200, error_response(req_id, ERR_INVALID_REQUEST,
                                       "invalid request", "invalid_request")
        method = request["method"]
        params = request.get("params") or {}
        if not isinstance(params, dict):
            return 200, error_response(req_id, ERR_INVALID_PARAMS,
                                       "params must be an object",
                                       "invalid_params")
        if method == "initialize":
            return 200, ok_response(req_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "server": "mcp-toolkit-deep",
                "transport": "http",
                "role": role,
                "capabilities": {"tools": True}})
        if method == "tools/list":
            return 200, ok_response(req_id, {"tools": self.tools_for_role(role)})
        if method == "tools/call":
            return self._call_tool(req_id, params, role)
        return 200, error_response(req_id, ERR_METHOD_NOT_FOUND,
                                   "method not found", "method_not_found")

    def _safety_block(self, req_id, reason, message, tool, role):
        self.audit("safety", reason, tool, role)
        return 200, error_response(req_id, ERR_SAFETY_BLOCKED,
                                   message, reason)

    def _call_tool(self, req_id, params, role):
        name = params.get("name")
        args = params.get("arguments")
        # Intent classification first: a write or delete attempt is a
        # safety block under its own name, not a role or lookup error,
        # so the audit log records what was attempted.
        if name in WRITE_TOOLS:
            return self._safety_block(req_id, "write_blocked",
                                      "write tools are not offered",
                                      name, role)
        if name in DELETE_TOOLS:
            return self._safety_block(req_id, "delete_blocked",
                                      "delete tools are not offered",
                                      name, role)
        if name not in ALL_TOOLS:
            return self._safety_block(req_id, "unknown_tool",
                                      "unknown tool",
                                      name if isinstance(name, str) else None,
                                      role)
        if name not in ROLE_TOOLS[role]:
            self.audit("authorization", "forbidden_role", name, role)
            return 403, error_response(
                req_id, ERR_FORBIDDEN_ROLE,
                "role " + role + " may not call " + name, "forbidden_role")
        if not isinstance(args, dict):
            return 200, error_response(req_id, ERR_INVALID_PARAMS,
                                       "arguments must be an object",
                                       "invalid_params")
        handler = {"read_file": self._read_file,
                   "list_files": self._list_files,
                   "list_items": self._list_items,
                   "run_query": self._run_query,
                   "calculate": self._calculate,
                   "count_words": self._count_words}[name]
        return 200, handler(req_id, args, role)

    def _resolve_in_sandbox(self, target):
        if target == self.sandbox or target.startswith(self.sandbox + os.sep):
            return target
        return None

    def _read_file(self, req_id, args, role):
        path = args.get("path")
        if not isinstance(path, str) or not path:
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "path must be a non-empty string",
                                  "invalid_params")
        parts = re.split(r"[/\\]", path)
        if ".." in parts:
            return self._safety_block(
                req_id, "path_traversal", "path traversal blocked",
                "read_file", role)[1]
        if os.path.isabs(path):
            target = self._resolve_in_sandbox(os.path.realpath(path))
            if target is None:
                return self._safety_block(
                    req_id, "absolute_path_blocked",
                    "absolute path outside sandbox blocked",
                    "read_file", role)[1]
        else:
            target = self._resolve_in_sandbox(
                os.path.realpath(os.path.join(self.sandbox, path)))
            if target is None:
                return self._safety_block(
                    req_id, "path_traversal", "path traversal blocked",
                    "read_file", role)[1]
        if not os.path.isfile(target):
            return error_response(req_id, ERR_NOT_FOUND,
                                  "file not found", "file_not_found")
        with open(target, encoding="utf-8") as f:
            return ok_response(req_id, {"path": path, "content": f.read()})

    def _list_files(self, req_id, args, role):
        return ok_response(req_id,
                           {"files": sorted(os.listdir(self.sandbox))})

    def _rows(self, sql):
        with self._lock:
            cur = self.conn.execute(sql)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _list_items(self, req_id, args, role):
        return ok_response(req_id, {
            "rows": self._rows(
                "SELECT id, name, score FROM items ORDER BY id")})

    def _check_sql(self, sql):
        """Return a safety reason, or None for a single read SELECT."""
        core = sql.strip().rstrip(";")
        if ";" in core:
            return "sql_multi_statement"
        words = re.findall(r"[A-Za-z]+", sql.upper())
        if not words or words[0] != "SELECT":
            return "sql_not_select"
        if any(w in BLOCKED_SQL_WORDS for w in words[1:]):
            return "sql_not_select"
        return None

    def _run_query(self, req_id, args, role):
        sql = args.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "sql must be a non-empty string",
                                  "invalid_params")
        reason = self._check_sql(sql)
        if reason is not None:
            return self._safety_block(
                req_id, reason, "only a single read-only SELECT is allowed",
                "run_query", role)[1]
        try:
            rows = self._rows(sql)
        except sqlite3.Error as exc:
            return error_response(req_id, ERR_QUERY,
                                  "query error: " + str(exc), "query_error")
        return ok_response(req_id, {"rows": rows})

    def _calculate(self, req_id, args, role):
        op, a, b = args.get("op"), args.get("a"), args.get("b")
        if op not in ("add", "subtract", "multiply", "divide"):
            return error_response(
                req_id, ERR_INVALID_PARAMS,
                "op must be add, subtract, multiply, or divide",
                "invalid_params")
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) \
                or isinstance(a, bool) or isinstance(b, bool):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "a and b must be numbers", "invalid_params")
        if op == "add":
            value = a + b
        elif op == "subtract":
            value = a - b
        elif op == "multiply":
            value = a * b
        else:
            if b == 0:
                return error_response(req_id, ERR_CALC,
                                      "division by zero", "calc_error")
            value = a / b
        return ok_response(req_id, {"op": op, "a": a, "b": b, "value": value})

    def _count_words(self, req_id, args, role):
        text = args.get("text")
        if not isinstance(text, str):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "text must be a string", "invalid_params")
        return ok_response(req_id, {"count": len(text.split())})


def make_handler(core, token_store):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            return None

        def _send_json(self, status, payload):
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self._send_json(200, {"status": "ok", "transport": "http",
                                      "protocolVersion": PROTOCOL_VERSION})
                return
            self._send_json(404, error_response(
                None, ERR_NOT_FOUND, "not found", "not_found"))

        def do_POST(self):
            if self.path != "/mcp":
                self._send_json(404, error_response(
                    None, ERR_NOT_FOUND, "not found", "not_found"))
                return
            length = self.headers.get("Content-Length")
            size = int(length) if length and length.isdigit() else 0
            if size > MAX_BODY_BYTES:
                core.audit("safety", "request_too_large", None, None)
                self._send_json(413, error_response(
                    None, ERR_TOO_LARGE, "request too large",
                    "request_too_large"))
                return
            raw = self.rfile.read(size) if size else b""
            auth = self.headers.get("Authorization") or ""
            token = auth[len("Bearer "):] if auth.startswith("Bearer ") else None
            role = token_store.authenticate(token)
            if role is None:
                tool = None
                try:
                    parsed = json.loads(raw.decode("utf-8")) if raw else {}
                    tool = (parsed.get("params") or {}).get("name")
                except ValueError:
                    tool = None
                core.audit("auth", "unauthenticated", tool, None)
                req_id = None
                try:
                    req_id = json.loads(raw.decode("utf-8")).get("id")
                except (ValueError, AttributeError):
                    req_id = None
                self._send_json(401, error_response(
                    req_id, ERR_UNAUTHENTICATED,
                    "missing or invalid bearer token", "unauthenticated"))
                return
            try:
                request = json.loads(raw.decode("utf-8")) if raw else {}
            except ValueError:
                self._send_json(200, error_response(
                    None, ERR_INVALID_REQUEST, "invalid json",
                    "invalid_request"))
                return
            status, payload = core.dispatch(request, role)
            self._send_json(status, payload)

    return Handler


def make_server(core, token_store, host="127.0.0.1", port=0):
    """Build a ThreadingHTTPServer. Port 0 picks an ephemeral port."""
    server = ThreadingHTTPServer((host, port), make_handler(core, token_store))
    server.daemon_threads = True
    server.core = core
    server.token_store = token_store
    return server


class HttpMcpClient:
    """Small client for the Deep HTTP server. Stdlib urllib only.

    Methods return (http_status, payload_dict). HTTP error statuses
    (401, 403, 413) are returned, not raised, so callers can count
    them. The token is held in memory only and never logged.
    """

    def __init__(self, base_url, token=None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def post_raw(self, raw_bytes, token="USE_CLIENT_TOKEN"):
        url = self.base_url + "/mcp"
        req = urllib.request.Request(url, data=raw_bytes, method="POST")
        req.add_header("Content-Type", "application/json")
        tok = self.token if token == "USE_CLIENT_TOKEN" else token
        if tok:
            req.add_header("Authorization", "Bearer " + tok)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            try:
                return exc.code, json.loads(body)
            except ValueError:
                return exc.code, {"error": {"data": {"reason": "http_error"}}}

    def post(self, payload, token="USE_CLIENT_TOKEN"):
        return self.post_raw(json.dumps(payload).encode("utf-8"), token=token)

    def initialize(self, req_id=1, token="USE_CLIENT_TOKEN"):
        return self.post(make_request(req_id, "initialize"), token=token)

    def list_tools(self, req_id=1, token="USE_CLIENT_TOKEN"):
        return self.post(make_request(req_id, "tools/list"), token=token)

    def call_tool(self, req_id, name, arguments, token="USE_CLIENT_TOKEN"):
        return self.post(make_request(
            req_id, "tools/call", {"name": name, "arguments": arguments}),
            token=token)
