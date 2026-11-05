"""MCP-style tool protocol, Build level: real stdio transport.

This is a stdlib-only MCP-style implementation. It is not the official
MCP SDK and claims no spec compliance beyond the message shapes it
documents. Build adds, over the in-process Learn level:

- Real transport: each server runs as a separate subprocess and speaks
  newline-delimited JSON (NDJSON) JSON-RPC style messages over stdio.
  One request per line on stdin, one response per line on stdout.
- Three servers: file (sandboxed), database (read-only sqlite), and
  calc (safe arithmetic and word counting, no eval).
- A host client that spawns the servers, aggregates tools/list across
  all of them into one registry, and routes tools/call by tool name.
- The in-process path from Learn is kept working via InProcessHost,
  using the same server classes, so tests can run without subprocesses.
- Safety rules retained from Learn: path traversal blocked, database
  writes blocked. Servers never raise to the client and never return
  a traceback: every failure becomes a named error object.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys

PROTOCOL_VERSION = "build-1"

ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_PARAMS = -32602
ERR_TOOL_NOT_FOUND = -32001
ERR_SANDBOX_BLOCKED = -32002
ERR_WRITE_BLOCKED = -32003
ERR_NOT_FOUND = -32004
ERR_QUERY = -32005
ERR_CALC = -32006
ERR_SERVER = -32007


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
                    "transport": "stdio",
                    "capabilities": {"tools": True, "resources": True}})
            if method == "tools/list":
                return ok_response(req_id, {"tools": self.tools})
            if method == "tools/call":
                return self._call_tool(req_id, params)
            if method == "resources/read":
                return self._read_resource(req_id, params)
            return error_response(req_id, ERR_METHOD_NOT_FOUND,
                                  "method not found", "method_not_found")
        except Exception as exc:
            return error_response(req_id, ERR_QUERY,
                                  "internal error: " + type(exc).__name__,
                                  "internal_error")

    def _call_tool(self, req_id, params):
        raise NotImplementedError

    def _read_resource(self, req_id, params):
        return error_response(req_id, ERR_METHOD_NOT_FOUND,
                              "method not found", "method_not_found")

    def _check_call(self, req_id, params, allowed):
        name = params.get("name")
        args = params.get("arguments")
        if name not in allowed:
            return None, None, error_response(
                req_id, ERR_TOOL_NOT_FOUND, "unknown tool", "tool_not_found")
        if not isinstance(args, dict):
            return None, None, error_response(
                req_id, ERR_INVALID_PARAMS, "arguments must be an object",
                "invalid_params")
        return name, args, None


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
        if not isinstance(rel, str) or not rel:
            return None
        if os.path.isabs(rel):
            return None
        target = os.path.realpath(os.path.join(self.sandbox, rel))
        if target != self.sandbox and not target.startswith(self.sandbox + os.sep):
            return None
        return target

    def _call_tool(self, req_id, params):
        name, args, err = self._check_call(
            req_id, params, ("read_file", "list_files"))
        if err:
            return err
        if name == "list_files":
            return ok_response(req_id, {"files": sorted(os.listdir(self.sandbox))})
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
        target = self._resolve(uri[len("sandbox://"):])
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

    def _rows(self, sql):
        cur = self.conn.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _check_sql(self, sql):
        words = re.findall(r"[A-Za-z]+", sql.upper())
        if not words or words[0] != "SELECT":
            return "write_blocked"
        if any(w in BLOCKED_SQL_WORDS for w in words):
            return "write_blocked"
        if ";" in sql.strip().rstrip(";"):
            return "write_blocked"
        return None

    def _call_tool(self, req_id, params):
        name, args, err = self._check_call(
            req_id, params, ("list_items", "run_query"))
        if err:
            return err
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


class CalcServer(BaseServer):
    name = "calc"
    tools = [
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

    def _call_tool(self, req_id, params):
        name, args, err = self._check_call(
            req_id, params, ("calculate", "count_words"))
        if err:
            return err
        if name == "count_words":
            text = args.get("text")
            if not isinstance(text, str):
                return error_response(req_id, ERR_INVALID_PARAMS,
                                      "text must be a string", "invalid_params")
            return ok_response(req_id, {"count": len(text.split())})
        op, a, b = args.get("op"), args.get("a"), args.get("b")
        if op not in ("add", "subtract", "multiply", "divide"):
            return error_response(req_id, ERR_INVALID_PARAMS,
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

    def _read_resource(self, req_id, params):
        if params.get("uri") != "calc://ops":
            return error_response(req_id, ERR_NOT_FOUND,
                                  "resource not found", "resource_not_found")
        return ok_response(req_id, {"uri": "calc://ops",
                                     "ops": ["add", "subtract",
                                             "multiply", "divide"]})


def write_fixtures(sandbox_dir):
    os.makedirs(sandbox_dir, exist_ok=True)
    for name in sorted(FIXTURE_FILES):
        with open(os.path.join(sandbox_dir, name), "w", encoding="utf-8") as f:
            f.write(FIXTURE_FILES[name])
    return sandbox_dir


def make_server(kind, sandbox_dir=None):
    if kind == "file":
        return FileServer(sandbox_dir)
    if kind == "database":
        return DatabaseServer()
    if kind == "calc":
        return CalcServer()
    raise ValueError("unknown server kind: " + str(kind))


def serve_stdio(server, instream=None, outstream=None):
    """NDJSON loop: one JSON request per input line, one response per line."""
    instream = instream or sys.stdin
    outstream = outstream or sys.stdout
    for line in instream:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            response = error_response(None, ERR_INVALID_REQUEST,
                                      "invalid json", "invalid_request")
        else:
            response = server.handle(request)
        outstream.write(json.dumps(response, sort_keys=True) + "\n")
        outstream.flush()


class InProcessHost:
    """Learn path kept working: same server classes, no subprocess."""

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

    def list_tools(self):
        agg = []
        for name in sorted(self.servers):
            resp = self.servers[name].handle(make_request(0, "tools/list"))
            for tool in resp["result"]["tools"]:
                agg.append(tool)
                self._tool_owner[tool["name"]] = name
        return agg

    def call_tool(self, req_id, tool_name, arguments):
        owner = self._tool_owner.get(tool_name)
        if owner is None:
            first = sorted(self.servers)[0]
            return self.handle(first, make_request(
                req_id, "tools/call",
                {"name": tool_name, "arguments": arguments}))
        return self.handle(owner, make_request(
            req_id, "tools/call", {"name": tool_name, "arguments": arguments}))

    def read_resource(self, req_id, server_name, uri):
        return self.handle(server_name, make_request(
            req_id, "resources/read", {"uri": uri}))

    def close(self):
        return None


class StdioConnection:
    """One server subprocess speaking NDJSON over its stdio pipes."""

    def __init__(self, kind, sandbox_dir=None):
        here = os.path.dirname(os.path.abspath(__file__))
        cmd = [sys.executable, os.path.join(here, "server_main.py"), kind]
        if kind == "file":
            cmd.append(sandbox_dir or "")
        self.kind = kind
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8")

    def request(self, request):
        req_id = request.get("id") if isinstance(request, dict) else None
        if self.proc.poll() is not None:
            return error_response(req_id, ERR_SERVER,
                                  "server process exited", "server_crashed")
        try:
            self.proc.stdin.write(json.dumps(request) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
        except (BrokenPipeError, OSError):
            return error_response(req_id, ERR_SERVER,
                                  "server transport failed", "server_crashed")
        if not line:
            return error_response(req_id, ERR_SERVER,
                                  "server closed its output", "server_crashed")
        try:
            return json.loads(line)
        except ValueError:
            return error_response(req_id, ERR_SERVER,
                                  "server sent invalid json", "server_error")

    def close(self):
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            self.proc.wait(timeout=5)


class StdioHostClient:
    """Host client connecting to several stdio servers end to end."""

    def __init__(self, sandbox_dir):
        self.connections = {
            "calc": StdioConnection("calc"),
            "database": StdioConnection("database"),
            "file": StdioConnection("file", sandbox_dir),
        }
        self._tool_owner = {}

    def handle(self, server_name, request):
        conn = self.connections.get(server_name)
        if conn is None:
            req_id = request.get("id") if isinstance(request, dict) else None
            return error_response(req_id, ERR_NOT_FOUND,
                                  "unknown server", "server_not_found")
        return conn.request(request)

    def initialize_all(self, start_id=1):
        out, req_id = {}, start_id
        for name in sorted(self.connections):
            out[name] = self.handle(name, make_request(req_id, "initialize"))
            req_id += 1
        return out

    def list_tools(self):
        agg = []
        for name in sorted(self.connections):
            resp = self.handle(name, make_request(0, "tools/list"))
            if "error" in resp:
                continue
            for tool in resp["result"]["tools"]:
                agg.append(tool)
                self._tool_owner[tool["name"]] = name
        return agg

    def call_tool(self, req_id, tool_name, arguments):
        owner = self._tool_owner.get(tool_name)
        if owner is None:
            first = sorted(self.connections)[0]
            return self.handle(first, make_request(
                req_id, "tools/call",
                {"name": tool_name, "arguments": arguments}))
        return self.handle(owner, make_request(
            req_id, "tools/call", {"name": tool_name, "arguments": arguments}))

    def read_resource(self, req_id, server_name, uri):
        return self.handle(server_name, make_request(
            req_id, "resources/read", {"uri": uri}))

    def close(self):
        for conn in self.connections.values():
            conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False
