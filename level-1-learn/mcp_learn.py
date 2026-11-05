"""MCP-style tool protocol, taught from scratch, stdlib only.

This is an in-process teaching implementation. It is not the official
MCP SDK and it uses no network transport. Messages are plain dicts in
JSON-RPC style: a request has jsonrpc, id, method, and params; a
response has either result or a named error object. Servers never
raise to the client: every failure becomes an error object.

Servers:
- FileServer: sandboxed to one directory. Tools read_file, list_files.
  Resource URI form: sandbox://<name>
- DatabaseServer: in-memory sqlite, one seeded table, read-only.
  Tools list_items, run_query. Resource URI form: db://items

HostClient connects to both servers in process, aggregates their tool
lists, and routes tools/call and resources/read requests.
"""
import os
import re
import sqlite3

PROTOCOL_VERSION = "learn-1"

ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_PARAMS = -32602
ERR_TOOL_NOT_FOUND = -32001
ERR_SANDBOX_BLOCKED = -32002
ERR_WRITE_BLOCKED = -32003
ERR_NOT_FOUND = -32004
ERR_QUERY = -32005


def error_response(req_id, code, message, reason):
    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": code, "message": message,
                      "data": {"reason": reason}}}


def ok_response(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


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

    def handle(self, request):
        req_id = request.get("id") if isinstance(request, dict) else None
        try:
            if not isinstance(request, dict) or "method" not in request:
                return error_response(req_id, ERR_INVALID_REQUEST,
                                      "invalid request", "invalid_request")
            method = request["method"]
            params = request.get("params") or {}
            if not isinstance(params, dict):
                return error_response(req_id, ERR_INVALID_PARAMS,
                                      "params must be an object",
                                      "invalid_params")
            if method == "initialize":
                return ok_response(req_id, {
                    "protocolVersion": PROTOCOL_VERSION,
                    "server": self.name,
                    "capabilities": {"tools": True, "resources": True}})
            if method == "tools/list":
                return ok_response(req_id, {"tools": self.tools})
            if method == "tools/call":
                return self._call_tool(req_id, params)
            if method == "resources/read":
                return self._read_resource(req_id, params)
            return error_response(req_id, ERR_METHOD_NOT_FOUND,
                                  "method not found", "method_not_found")
        except Exception as exc:  # never leak a traceback to the client
            return error_response(req_id, ERR_QUERY,
                                  "internal error: " + type(exc).__name__,
                                  "internal_error")

    def _call_tool(self, req_id, params):
        raise NotImplementedError

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
            return error_response(req_id, ERR_TOOL_NOT_FOUND,
                                  "unknown tool", "tool_not_found")
        if not isinstance(args, dict):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "arguments must be an object",
                                  "invalid_params")
        if name == "list_files":
            files = sorted(os.listdir(self.sandbox))
            return ok_response(req_id, {"files": files})
        path = args.get("path")
        if not isinstance(path, str) or not path:
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "path must be a non-empty string",
                                  "invalid_params")
        target = self._resolve(path)
        if target is None:
            return error_response(req_id, ERR_SANDBOX_BLOCKED,
                                  "path outside sandbox", "path_traversal")
        if not os.path.isfile(target):
            return error_response(req_id, ERR_NOT_FOUND,
                                  "file not found", "file_not_found")
        with open(target, encoding="utf-8") as f:
            return ok_response(req_id, {"path": path, "content": f.read()})

    def _read_resource(self, req_id, params):
        uri = params.get("uri")
        if not isinstance(uri, str) or not uri.startswith("sandbox://"):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "uri must start with sandbox://",
                                  "invalid_params")
        rel = uri[len("sandbox://"):]
        target = self._resolve(rel)
        if target is None:
            return error_response(req_id, ERR_SANDBOX_BLOCKED,
                                  "path outside sandbox", "path_traversal")
        if not os.path.isfile(target):
            return error_response(req_id, ERR_NOT_FOUND,
                                  "file not found", "file_not_found")
        with open(target, encoding="utf-8") as f:
            return ok_response(req_id, {"uri": uri, "text": f.read()})


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
            return error_response(req_id, ERR_TOOL_NOT_FOUND,
                                  "unknown tool", "tool_not_found")
        if not isinstance(args, dict):
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "arguments must be an object",
                                  "invalid_params")
        if name == "list_items":
            return ok_response(req_id, {
                "rows": self._rows("SELECT id, name, score FROM items ORDER BY id")})
        sql = args.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            return error_response(req_id, ERR_INVALID_PARAMS,
                                  "sql must be a non-empty string",
                                  "invalid_params")
        if self._check_sql(sql) is not None:
            return error_response(req_id, ERR_WRITE_BLOCKED,
                                  "only read-only SELECT is allowed",
                                  "write_blocked")
        try:
            rows = self._rows(sql)
        except sqlite3.Error as exc:
            return error_response(req_id, ERR_QUERY,
                                  "query error: " + str(exc), "query_error")
        return ok_response(req_id, {"rows": rows})

    def _read_resource(self, req_id, params):
        uri = params.get("uri")
        if uri != "db://items":
            return error_response(req_id, ERR_NOT_FOUND,
                                  "resource not found", "resource_not_found")
        return ok_response(req_id, {
            "uri": uri,
            "rows": self._rows("SELECT id, name, score FROM items ORDER BY id")})


def write_fixtures(sandbox_dir):
    os.makedirs(sandbox_dir, exist_ok=True)
    for name in sorted(FIXTURE_FILES):
        with open(os.path.join(sandbox_dir, name), "w", encoding="utf-8") as f:
            f.write(FIXTURE_FILES[name])
    return sandbox_dir


class HostClient:
    """Connects to both servers in process and routes calls by tool name."""

    def __init__(self, servers):
        self.servers = {s.name: s for s in servers}
        self._tool_owner = {}

    def handle(self, server_name, request):
        server = self.servers.get(server_name)
        if server is None:
            req_id = request.get("id") if isinstance(request, dict) else None
            return error_response(req_id, ERR_NOT_FOUND,
                                  "unknown server", "server_not_found")
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
            resp = self.servers[name].handle(
                make_request(0, "tools/list"))
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
