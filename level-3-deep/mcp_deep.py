"""Model Context Protocol tool server, Deep level: authenticated HTTP
transport.

This is a stdlib-only implementation of the MCP specification
(protocol version 2025-11-25, with negotiation back to 2024-11-05)
over the specification's streamable HTTP transport, in its stateless
form: no session id is issued, and every request is answered with a
single JSON object. It is not the official MCP SDK. Tool execution
outcomes, including the named safety refusals, are returned as tool
results with isError set, as the specification's tools page
prescribes; protocol problems are JSON-RPC errors. The bearer token
layer is the toolkit's authorization choice under the
specification's Authorization framework. Conformance evidence:
CONFORMANCE.md and tests/test_mcp_conformance.py at the repository
root. Deep adds, over the stdio Build level:

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
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18",
                               "2025-03-26", "2024-11-05")
SERVER_INFO_VERSION = "1.1"
MAX_BODY_BYTES = 8192

ERR_PARSE = -32700
ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_PARAMS = -32602
ERR_INTERNAL = -32603
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


def negotiate_version(params):
    """MCP version negotiation: echo a supported version the client
    asked for; otherwise answer with the newest version supported."""
    requested = params.get("protocolVersion")
    if requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return PROTOCOL_VERSION


def tool_result(req_id, payload):
    """A successful CallToolResult: the payload as structuredContent
    plus its JSON serialization as a text content block."""
    return ok_response(req_id, {
        "content": [{"type": "text",
                     "text": json.dumps(payload, sort_keys=True)}],
        "structuredContent": payload,
        "isError": False})


def tool_error(req_id, reason, message):
    """A tool execution error, reported in band as the specification
    prescribes: a result with isError true, the message as text
    content, and the toolkit's named reason as structuredContent."""
    return ok_response(req_id, {
        "content": [{"type": "text", "text": message}],
        "structuredContent": {"reason": reason},
        "isError": True})


def initialize_params():
    """The initialize params a spec-conforming client sends."""
    return {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
            "clientInfo": {"name": "mcp-toolkit-http-client",
                           "version": SERVER_INFO_VERSION}}


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
        # Lifecycle state (specification, Lifecycle): the roles that
        # have completed the initialize exchange. The HTTP layer also
        # calls mark_initialized when notifications/initialized
        # arrives for a role.
        self._ready_roles = set()

    def mark_initialized(self, role):
        if role is not None:
            self._ready_roles.add(role)

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
        """Route one authenticated JSON-RPC request. Returns an
        (http_status, response dict) pair; the HTTP layer maps auth
        and role failures to status codes before this is called for
        tools/call (see _call_tool). Requests that arrive before the
        role completed the initialize exchange are rejected, as the
        specification's lifecycle rules require."""
        if isinstance(request, list):
            return 200, error_response(
                None, ERR_INVALID_REQUEST,
                "invalid request: JSON-RPC batching is not part of MCP",
                "invalid_request")
        if not isinstance(request, dict):
            return 200, error_response(None, ERR_INVALID_REQUEST,
                                       "invalid request", "invalid_request")
        req_id = request.get("id")
        if "id" in request and req_id is None:
            return 200, error_response(None, ERR_INVALID_REQUEST,
                                       "request id must not be null",
                                       "invalid_request")
        method = request.get("method")
        if not isinstance(method, str):
            return 200, error_response(req_id, ERR_INVALID_REQUEST,
                                       "invalid request", "invalid_request")
        if request.get("jsonrpc") != "2.0":
            return 200, error_response(req_id, ERR_INVALID_REQUEST,
                                       "jsonrpc must be \"2.0\"",
                                       "invalid_request")
        params = request.get("params") or {}
        if not isinstance(params, dict):
            return 200, error_response(req_id, ERR_INVALID_PARAMS,
                                       "params must be an object",
                                       "invalid_params")
        try:
            if method == "initialize":
                self._ready_roles.add(role)
                return 200, ok_response(req_id, {
                    "protocolVersion": negotiate_version(params),
                    "server": "mcp-toolkit-deep",
                    "transport": "http",
                    "role": role,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mcp-toolkit-deep",
                                   "version": SERVER_INFO_VERSION}})
            if method == "ping":
                return 200, ok_response(req_id, {})
            if role not in self._ready_roles:
                return 200, error_response(
                    req_id, ERR_INVALID_REQUEST,
                    "server not initialized: send initialize, then "
                    "notifications/initialized", "not_initialized")
            if method == "tools/list":
                return 200, ok_response(
                    req_id, {"tools": self.tools_for_role(role)})
            if method == "tools/call":
                return self._call_tool(req_id, params, role)
            return 200, error_response(req_id, ERR_METHOD_NOT_FOUND,
                                       "method not found", "method_not_found")
        except Exception as exc:
            return 200, error_response(
                req_id, ERR_INTERNAL,
                "internal error: " + type(exc).__name__, "internal_error")

    def _safety_block(self, req_id, reason, message, tool, role):
        self.audit("safety", reason, tool, role)
        return 200, tool_error(req_id, reason, message)

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
            # The attempt is audited as a safety event, and the wire
            # answer is the protocol error the specification assigns
            # to an unknown tool: invalid params.
            self.audit("safety", "unknown_tool",
                       name if isinstance(name, str) else None, role)
            return 200, error_response(req_id, ERR_INVALID_PARAMS,
                                       "unknown tool", "unknown_tool")
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
            return tool_error(req_id, "file_not_found", "file not found")
        with open(target, encoding="utf-8") as f:
            return tool_result(req_id, {"path": path, "content": f.read()})

    def _list_files(self, req_id, args, role):
        return tool_result(req_id,
                           {"files": sorted(os.listdir(self.sandbox))})

    def _rows(self, sql):
        with self._lock:
            cur = self.conn.execute(sql)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _list_items(self, req_id, args, role):
        return tool_result(req_id, {
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
            return tool_error(req_id, "query_error",
                              "query error: " + str(exc))
        return tool_result(req_id, {"rows": rows})

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
                return tool_error(req_id, "calc_error", "division by zero")
            value = a / b
        return tool_result(req_id, {"op": op, "a": a, "b": b, "value": value})

    def _count_words(self, req_id, args, role):
        text = args.get("text")
        if not isinstance(text, str):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "text must be a string", "invalid_params")
        return tool_result(req_id, {"count": len(text.split())})


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

        def _send_empty(self, status):
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            if self.path == "/health":
                self._send_json(200, {"status": "ok", "transport": "http",
                                      "protocolVersion": PROTOCOL_VERSION})
                return
            if self.path == "/mcp":
                # Streamable HTTP: this server offers no server-push
                # stream, so GET on the MCP endpoint is refused with
                # 405, as the specification allows.
                self._send_json(405, error_response(
                    None, ERR_METHOD_NOT_FOUND, "method not allowed",
                    "method_not_allowed"))
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
            origin = self.headers.get("Origin")
            if origin is not None:
                # Streamable HTTP security rule: validate the Origin
                # header against DNS rebinding. This server is local,
                # so only loopback origins are accepted.
                host = urllib.parse.urlparse(origin).hostname
                if host not in ("localhost", "127.0.0.1", "::1"):
                    self._send_json(403, error_response(
                        None, ERR_FORBIDDEN_ROLE,
                        "origin not allowed", "origin_forbidden"))
                    return
            version_header = self.headers.get("MCP-Protocol-Version")
            if version_header is not None \
                    and version_header not in SUPPORTED_PROTOCOL_VERSIONS:
                self._send_json(400, error_response(
                    None, ERR_INVALID_REQUEST,
                    "unsupported MCP-Protocol-Version header",
                    "invalid_request"))
                return
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
                    None, ERR_PARSE, "parse error", "parse_error"))
                return
            if isinstance(request, dict) and "id" not in request:
                # A notification: accepted with 202 and no body, and
                # never answered, as the base protocol requires.
                if isinstance(request.get("method"), str):
                    if request["method"] == "notifications/initialized":
                        core.mark_initialized(role)
                    self._send_empty(202)
                else:
                    self._send_json(400, error_response(
                        None, ERR_INVALID_REQUEST, "invalid request",
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

    The client follows the specification's lifecycle: a successful
    initialize is completed with a notifications/initialized
    notification, later requests carry the negotiated version in the
    MCP-Protocol-Version header, and if a request is answered with a
    not_initialized error the client performs the handshake once and
    retries the request once.
    """

    def __init__(self, base_url, token=None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._handshaken = set()
        self._negotiated = {}
        self._handshake_id = 9000

    def _effective_token(self, token):
        return self.token if token == "USE_CLIENT_TOKEN" else token

    def post_raw(self, raw_bytes, token="USE_CLIENT_TOKEN"):
        url = self.base_url + "/mcp"
        req = urllib.request.Request(url, data=raw_bytes, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        tok = self._effective_token(token)
        if tok:
            req.add_header("Authorization", "Bearer " + tok)
        version = self._negotiated.get(tok)
        if version:
            req.add_header("MCP-Protocol-Version", version)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
                if not body.strip():
                    return resp.status, {}
                return resp.status, json.loads(body)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            if not body.strip():
                return exc.code, {}
            try:
                return exc.code, json.loads(body)
            except ValueError:
                return exc.code, {"error": {"data": {"reason": "http_error"}}}

    def _handshake(self, token):
        tok = self._effective_token(token)
        self._handshake_id += 1
        status, resp = self.post_raw(json.dumps({
            "jsonrpc": "2.0", "id": self._handshake_id,
            "method": "initialize", "params": initialize_params(),
        }).encode("utf-8"), token=token)
        if status == 200 and isinstance(resp, dict) and "result" in resp:
            self._negotiated[tok] = resp["result"].get(
                "protocolVersion", PROTOCOL_VERSION)
            self.post_raw(json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }).encode("utf-8"), token=token)
        self._handshaken.add(tok)

    def post(self, payload, token="USE_CLIENT_TOKEN"):
        raw = json.dumps(payload).encode("utf-8")
        if isinstance(payload, dict) and payload.get("method") == "initialize" \
                and "id" in payload:
            status, resp = self.post_raw(raw, token=token)
            if status == 200 and isinstance(resp, dict) and "result" in resp:
                tok = self._effective_token(token)
                self._negotiated[tok] = resp["result"].get(
                    "protocolVersion", PROTOCOL_VERSION)
                self.post_raw(json.dumps({
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                }).encode("utf-8"), token=token)
                self._handshaken.add(tok)
            return status, resp
        status, resp = self.post_raw(raw, token=token)
        tok = self._effective_token(token)
        reason = None
        if isinstance(resp, dict):
            reason = (resp.get("error") or {}).get("data", {}).get("reason")
        if status == 200 and reason == "not_initialized" \
                and tok not in self._handshaken \
                and isinstance(payload, dict) and "id" in payload:
            self._handshake(token)
            status, resp = self.post_raw(raw, token=token)
        return status, resp

    def initialize(self, req_id=1, token="USE_CLIENT_TOKEN"):
        return self.post({"jsonrpc": "2.0", "id": req_id,
                          "method": "initialize",
                          "params": initialize_params()}, token=token)

    def list_tools(self, req_id=1, token="USE_CLIENT_TOKEN"):
        return self.post(make_request(req_id, "tools/list"), token=token)

    def call_tool(self, req_id, name, arguments, token="USE_CLIENT_TOKEN"):
        return self.post(make_request(
            req_id, "tools/call", {"name": name, "arguments": arguments}),
            token=token)
