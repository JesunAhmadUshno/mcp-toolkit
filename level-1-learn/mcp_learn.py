"""Model Context Protocol tool server, taught from scratch, stdlib only.

This is an in-process teaching implementation of the MCP
specification (protocol version 2025-11-25, with negotiation back to
2024-11-05). It is not the official MCP SDK and it uses no network
transport. Messages are plain dicts following JSON-RPC 2.0 as the
specification requires: a request has jsonrpc, id, method, and
params; a response has either a result or an error object. Tool
execution outcomes, including the toolkit's named safety refusals,
are returned as tool results with isError set, as the specification's
tools page prescribes; protocol problems are JSON-RPC errors.
Conformance evidence: CONFORMANCE.md and tests/test_mcp_conformance.py
at the repository root. Servers never raise to the client: every
failure becomes a response object.

Servers:
- FileServer: sandboxed to one directory. Tools read_file, list_files.
  Resource URI form: sandbox://<name>
- DatabaseServer: in-memory sqlite, one seeded table, read-only.
  Tools list_items, run_query. Resource URI form: db://items

HostClient connects to both servers in process, aggregates their tool
lists, and routes tools/call and resources/read requests.
"""
import json
import os
import re
import sqlite3

# MCP specification versions this server can negotiate, newest first.
SUPPORTED_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18",
                               "2025-03-26", "2024-11-05")
PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]
SERVER_INFO_VERSION = "1.1"

ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_PARAMS = -32602
ERR_INTERNAL = -32603
ERR_RESOURCE_NOT_FOUND = -32002


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


def make_request(req_id, method, params=None):
    return {"jsonrpc": "2.0", "id": req_id, "method": method,
            "params": params or {}}


FIXTURE_FILES = {
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


class BaseServer:
    name = "base"
    tools = []
    # Lifecycle state (specification, Lifecycle): a fresh server has
    # not been initialized; it becomes ready when the client sends
    # notifications/initialized after the initialize exchange.
    _initialized = False
    _ready = False

    def handle(self, request):
        """Route one message. Returns a response dict, or None for a
        notification: the base protocol forbids answering one."""
        if isinstance(request, list):
            return error_response(
                None, ERR_INVALID_REQUEST,
                "invalid request: JSON-RPC batching is not part of MCP",
                "invalid_request")
        if not isinstance(request, dict):
            return error_response(None, ERR_INVALID_REQUEST,
                                  "invalid request", "invalid_request")
        is_notification = "id" not in request
        req_id = request.get("id")
        if not is_notification and req_id is None:
            return error_response(None, ERR_INVALID_REQUEST,
                                  "request id must not be null",
                                  "invalid_request")
        method = request.get("method")
        if not isinstance(method, str):
            if is_notification:
                return None
            return error_response(req_id, ERR_INVALID_REQUEST,
                                  "invalid request", "invalid_request")
        if is_notification:
            if method == "notifications/initialized":
                self._ready = True
            return None
        if request.get("jsonrpc") != "2.0":
            return error_response(req_id, ERR_INVALID_REQUEST,
                                  "jsonrpc must be \"2.0\"",
                                  "invalid_request")
        params = request.get("params") or {}
        if not isinstance(params, dict):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "params must be an object",
                                  "invalid_params")
        try:
            if method == "initialize":
                self._initialized = True
                return ok_response(req_id, {
                    "protocolVersion": negotiate_version(params),
                    "capabilities": {"tools": {}, "resources": {}},
                    "serverInfo": {
                        "name": "mcp-toolkit-" + self.name,
                        "version": SERVER_INFO_VERSION},
                    "server": self.name})
            if method == "ping":
                return ok_response(req_id, {})
            if not self._ready:
                return error_response(
                    req_id, ERR_INVALID_REQUEST,
                    "server not initialized: send initialize, then "
                    "notifications/initialized", "not_initialized")
            if method == "tools/list":
                return ok_response(req_id, {"tools": self.tools})
            if method == "tools/call":
                return self._call_tool(req_id, params)
            if method == "resources/list":
                return self._list_resources(req_id, params)
            if method == "resources/read":
                return self._read_resource(req_id, params)
            return error_response(req_id, ERR_METHOD_NOT_FOUND,
                                  "method not found", "method_not_found")
        except Exception as exc:  # never leak a traceback to the client
            return error_response(req_id, ERR_INTERNAL,
                                  "internal error: " + type(exc).__name__,
                                  "internal_error")

    def _call_tool(self, req_id, params):
        raise NotImplementedError

    def _list_resources(self, req_id, params):
        return error_response(req_id, ERR_METHOD_NOT_FOUND,
                              "method not found", "method_not_found")

    def _read_resource(self, req_id, params):
        return error_response(req_id, ERR_METHOD_NOT_FOUND,
                              "method not found", "method_not_found")


class FileServer(BaseServer):
    name = "file"
    tools = [
        {"name": "read_file", "server": "file",
         "description": "Read one text file inside the sandbox.",
         "inputSchema": {"type": "object",
                         "properties": {"path": {"type": "string"}},
                         "required": ["path"]}},
        {"name": "list_files", "server": "file",
         "description": "List files inside the sandbox, sorted.",
         "inputSchema": {"type": "object", "properties": {},
                         "required": []}},
    ]

    def __init__(self, sandbox_dir):
        self.sandbox = os.path.realpath(sandbox_dir)

    def _resolve(self, rel):
        """Return the real path if it stays inside the sandbox, else None."""
        if not isinstance(rel, str) or not rel:
            return None
        if os.path.isabs(rel):
            return None
        target = os.path.realpath(os.path.join(self.sandbox, rel))
        if target != self.sandbox and not target.startswith(self.sandbox + os.sep):
            return None
        return target

    def _call_tool(self, req_id, params):
        name = params.get("name")
        args = params.get("arguments")
        if name not in ("read_file", "list_files"):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "unknown tool", "tool_not_found")
        if not isinstance(args, dict):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "arguments must be an object",
                                  "invalid_params")
        if name == "list_files":
            files = sorted(os.listdir(self.sandbox))
            return tool_result(req_id, {"files": files})
        path = args.get("path")
        if not isinstance(path, str) or not path:
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "path must be a non-empty string",
                                  "invalid_params")
        target = self._resolve(path)
        if target is None:
            return tool_error(req_id, "path_traversal",
                              "path outside sandbox")
        if not os.path.isfile(target):
            return tool_error(req_id, "file_not_found", "file not found")
        with open(target, encoding="utf-8") as f:
            return tool_result(req_id, {"path": path, "content": f.read()})

    def _list_resources(self, req_id, params):
        resources = [{"uri": "sandbox://" + name, "name": name,
                      "mimeType": "text/plain"}
                     for name in sorted(os.listdir(self.sandbox))]
        return ok_response(req_id, {"resources": resources})

    def _read_resource(self, req_id, params):
        uri = params.get("uri")
        if not isinstance(uri, str) or not uri.startswith("sandbox://"):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "uri must start with sandbox://",
                                  "invalid_params")
        rel = uri[len("sandbox://"):]
        target = self._resolve(rel)
        if target is None:
            return error_response(req_id, ERR_RESOURCE_NOT_FOUND,
                                  "path outside sandbox", "path_traversal")
        if not os.path.isfile(target):
            return error_response(req_id, ERR_RESOURCE_NOT_FOUND,
                                  "resource not found", "resource_not_found")
        with open(target, encoding="utf-8") as f:
            text = f.read()
        return ok_response(req_id, {"contents": [{
            "uri": uri, "mimeType": "text/plain", "text": text}]})


class DatabaseServer(BaseServer):
    name = "database"
    tools = [
        {"name": "list_items", "server": "database",
         "description": "List every row of the items table, by id.",
         "inputSchema": {"type": "object", "properties": {},
                         "required": []}},
        {"name": "run_query", "server": "database",
         "description": "Run one read-only SELECT on the items table.",
         "inputSchema": {"type": "object",
                         "properties": {"sql": {"type": "string"}},
                         "required": ["sql"]}},
    ]

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute(
            "CREATE TABLE items (id INTEGER, name TEXT, score INTEGER)")
        self.conn.executemany(
            "INSERT INTO items VALUES (?, ?, ?)",
            [(r["id"], r["name"], r["score"]) for r in SEED_ROWS])
        self.conn.commit()

    def _rows(self, sql, args=()):
        cur = self.conn.execute(sql, args)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _check_sql(self, sql):
        """Return a blocked reason, or None if the SQL is a safe SELECT."""
        words = re.findall(r"[A-Za-z]+", sql.upper())
        if not words or words[0] != "SELECT":
            return "write_blocked"
        if any(w in BLOCKED_SQL_WORDS for w in words):
            return "write_blocked"
        stripped = sql.strip().rstrip(";")
        if ";" in stripped:
            return "write_blocked"
        return None

    def _call_tool(self, req_id, params):
        name = params.get("name")
        args = params.get("arguments")
        if name not in ("list_items", "run_query"):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "unknown tool", "tool_not_found")
        if not isinstance(args, dict):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "arguments must be an object",
                                  "invalid_params")
        if name == "list_items":
            return tool_result(req_id, {
                "rows": self._rows("SELECT id, name, score FROM items ORDER BY id")})
        sql = args.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "sql must be a non-empty string",
                                  "invalid_params")
        if self._check_sql(sql) is not None:
            return tool_error(req_id, "write_blocked",
                              "only read-only SELECT is allowed")
        try:
            rows = self._rows(sql)
        except sqlite3.Error as exc:
            return tool_error(req_id, "query_error",
                              "query error: " + str(exc))
        return tool_result(req_id, {"rows": rows})

    def _list_resources(self, req_id, params):
        return ok_response(req_id, {"resources": [{
            "uri": "db://items", "name": "items",
            "description": "Every row of the items table.",
            "mimeType": "application/json"}]})

    def _read_resource(self, req_id, params):
        uri = params.get("uri")
        if uri != "db://items":
            return error_response(req_id, ERR_RESOURCE_NOT_FOUND,
                                  "resource not found", "resource_not_found")
        rows = self._rows("SELECT id, name, score FROM items ORDER BY id")
        return ok_response(req_id, {"contents": [{
            "uri": uri, "mimeType": "application/json",
            "text": json.dumps({"rows": rows}, sort_keys=True)}]})


def write_fixtures(sandbox_dir):
    os.makedirs(sandbox_dir, exist_ok=True)
    for name in sorted(FIXTURE_FILES):
        with open(os.path.join(sandbox_dir, name), "w", encoding="utf-8") as f:
            f.write(FIXTURE_FILES[name])
    return sandbox_dir


def initialize_params():
    """The initialize params a spec-conforming client sends."""
    return {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
            "clientInfo": {"name": "mcp-toolkit-host",
                           "version": SERVER_INFO_VERSION}}


def make_initialize_request(req_id):
    return {"jsonrpc": "2.0", "id": req_id, "method": "initialize",
            "params": initialize_params()}


def make_initialized_notification():
    return {"jsonrpc": "2.0", "method": "notifications/initialized"}


class HostClient:
    """Connects to both servers in process and routes calls by tool name.

    Like a real MCP host, it completes the lifecycle handshake with
    each server (initialize, then notifications/initialized) before
    the first ordinary request to that server.
    """

    def __init__(self, servers):
        self.servers = {s.name: s for s in servers}
        self._tool_owner = {}
        self._handshaken = set()
        self._handshake_id = 100000

    def _ensure_handshake(self, server_name):
        if server_name in self._handshaken:
            return
        server = self.servers[server_name]
        self._handshake_id += 1
        server.handle(make_initialize_request(self._handshake_id))
        server.handle(make_initialized_notification())
        self._handshaken.add(server_name)

    def handle(self, server_name, request):
        server = self.servers.get(server_name)
        if server is None:
            req_id = request.get("id") if isinstance(request, dict) else None
            return error_response(req_id, ERR_RESOURCE_NOT_FOUND,
                                  "unknown server", "server_not_found")
        if isinstance(request, dict) and request.get("method") == "initialize":
            response = server.handle(request)
            server.handle(make_initialized_notification())
            self._handshaken.add(server_name)
            return response
        self._ensure_handshake(server_name)
        return server.handle(request)

    def initialize_all(self, start_id=1):
        out, req_id = {}, start_id
        for name in sorted(self.servers):
            out[name] = self.handle(name, make_request(req_id, "initialize"))
            req_id += 1
        return out

    def list_tools(self):
        """Aggregate tool lists. Local aggregation, not a protocol call."""
        agg = []
        for name in sorted(self.servers):
            resp = self.handle(name, make_request(0, "tools/list"))
            for tool in resp["result"]["tools"]:
                agg.append(tool)
                self._tool_owner[tool["name"]] = name
        return agg

    def call_tool(self, req_id, tool_name, arguments):
        owner = self._tool_owner.get(tool_name)
        if owner is None:
            # Still route through a server so the error is a protocol
            # error from the protocol path, not a client exception.
            first = sorted(self.servers)[0]
            return self.handle(first, make_request(
                req_id, "tools/call",
                {"name": tool_name, "arguments": arguments}))
        return self.handle(owner, make_request(
            req_id, "tools/call", {"name": tool_name, "arguments": arguments}))

    def read_resource(self, req_id, server_name, uri):
        return self.handle(server_name, make_request(
            req_id, "resources/read", {"uri": uri}))
