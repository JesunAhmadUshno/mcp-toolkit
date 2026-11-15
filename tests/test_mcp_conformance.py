"""MCP conformance suite for mcp-toolkit.

Exercises the three servers against the official Model Context
Protocol specification (modelcontextprotocol.io, specification
2025-11-25, with the 2025-06-18 transports and tools pages where the
2025-11-25 text is unchanged). Every test is one numbered check in
CONFORMANCE.md at the repository root; the check id is in the test
name and the docstring cites the spec section. Checks that a level
cannot exercise (for example malformed JSON at the in-process Learn
level, which has no serialization boundary) are not silently
skipped: CONFORMANCE.md marks that arm "not run" with the reason.

Arms:
- Learn: in-process handle() calls on fresh server instances.
- Build: a real subprocess speaking NDJSON over stdio, driven with
  raw pipes (not the toolkit's own client), plus an in-process arm
  for fault injection.
- Deep: a real HTTP server on an ephemeral localhost port, driven
  with raw urllib requests (not the toolkit's own client), plus an
  in-process dispatch arm for fault injection.

TEST TOKENS: the tokens below are clearly labelled test tokens for
localhost runs only, hashed in memory by TokenStore.from_plaintext.
"""
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _level in ("level-1-learn", "level-2-build", "level-3-deep"):
    sys.path.insert(0, os.path.join(ROOT, _level))

import mcp_build  # noqa: E402
import mcp_deep  # noqa: E402
import mcp_learn  # noqa: E402

LATEST = "2025-11-25"
READER_TEST_TOKEN = "test-reader-token-conformance-only"
OPERATOR_TEST_TOKEN = "test-operator-token-conformance-only"


def init_request(req_id, version=LATEST):
    return {"jsonrpc": "2.0", "id": req_id, "method": "initialize",
            "params": {"protocolVersion": version, "capabilities": {},
                       "clientInfo": {"name": "conformance-suite",
                                      "version": "1.0"}}}


def initialized_note():
    return {"jsonrpc": "2.0", "method": "notifications/initialized"}


def call(req_id, method, params=None):
    return {"jsonrpc": "2.0", "id": req_id, "method": method,
            "params": params or {}}


# ---------------------------------------------------------------- Learn

class TestLearnConformance(unittest.TestCase):
    """In-process arm: mcp_learn servers, fresh instance per test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sandbox = mcp_learn.write_fixtures(
            os.path.join(self.tmp.name, "sandbox"))
        self.server = mcp_learn.FileServer(self.sandbox)

    def handshake(self, server=None, version=LATEST):
        server = server or self.server
        resp = server.handle(init_request(1, version))
        server.handle(initialized_note())
        return resp

    def test_c01_version_negotiation_echoes_supported(self):
        """C01: Lifecycle, version negotiation."""
        resp = self.server.handle(init_request(1, "2025-06-18"))
        self.assertEqual(resp["result"]["protocolVersion"], "2025-06-18")

    def test_c02_unsupported_version_gets_latest(self):
        """C02: Lifecycle, version negotiation."""
        resp = self.server.handle(init_request(1, "1999-01-01"))
        self.assertEqual(resp["result"]["protocolVersion"], LATEST)

    def test_c03_initialize_result_shape(self):
        """C03: Lifecycle, InitializeResult."""
        resp = self.server.handle(init_request(1))
        result = resp["result"]
        self.assertEqual(result["protocolVersion"], LATEST)
        self.assertIsInstance(result["capabilities"]["tools"], dict)
        self.assertIsInstance(result["capabilities"]["resources"], dict)
        self.assertEqual(result["serverInfo"]["name"], "mcp-toolkit-file")
        self.assertTrue(result["serverInfo"]["version"])

    def test_c04_initialized_notification_has_no_response(self):
        """C04: Lifecycle and Base Protocol (notifications)."""
        self.server.handle(init_request(1))
        self.assertIsNone(self.server.handle(initialized_note()))

    def test_c05_requests_before_ready_are_rejected(self):
        """C05: Lifecycle, initialization must come first."""
        resp = self.server.handle(call(1, "tools/list"))
        self.assertEqual(resp["error"]["code"], -32600)
        self.assertEqual(resp["error"]["data"]["reason"], "not_initialized")
        # initialize alone is not enough: the notification completes it
        self.server.handle(init_request(2))
        resp = self.server.handle(call(3, "tools/list"))
        self.assertEqual(resp["error"]["data"]["reason"], "not_initialized")
        self.server.handle(initialized_note())
        resp = self.server.handle(call(4, "tools/list"))
        self.assertIn("tools", resp["result"])

    def test_c06_ping_empty_result_any_state(self):
        """C06: Utilities, Ping."""
        resp = self.server.handle(call(1, "ping"))
        self.assertEqual(resp["result"], {})
        self.handshake()
        resp = self.server.handle(call(2, "ping"))
        self.assertEqual(resp["result"], {})

    def test_c07_unknown_method(self):
        """C07: Base Protocol, JSON-RPC error codes."""
        self.handshake()
        resp = self.server.handle(call(9, "bogus/method"))
        self.assertEqual(resp["error"]["code"], -32601)

    def test_c09_invalid_requests(self):
        """C09: Base Protocol, JSON-RPC message shapes."""
        self.handshake()
        resp = self.server.handle({"jsonrpc": "2.0", "id": 1})
        self.assertEqual(resp["error"]["code"], -32600)
        resp = self.server.handle(
            {"jsonrpc": "1.0", "id": 2, "method": "ping"})
        self.assertEqual(resp["error"]["code"], -32600)
        resp = self.server.handle(
            {"jsonrpc": "2.0", "id": None, "method": "ping"})
        self.assertEqual(resp["error"]["code"], -32600)
        self.assertIsNone(resp["id"])

    def test_c10_batch_is_a_single_error(self):
        """C10: Base Protocol (batching removed in 2025-06-18)."""
        resp = self.server.handle([call(1, "ping")])
        self.assertIsInstance(resp, dict)
        self.assertEqual(resp["error"]["code"], -32600)

    def test_c11_unknown_notification_has_no_response(self):
        """C11: Base Protocol (notifications are never answered)."""
        self.assertIsNone(self.server.handle(
            {"jsonrpc": "2.0", "method": "notifications/cancelled"}))

    def test_c12_response_envelope_and_string_id(self):
        """C12: Base Protocol, response shape."""
        resp = self.server.handle(init_request("req-abc"))
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], "req-abc")
        self.assertIn("result", resp)

    def test_c13_internal_error_code(self):
        """C13: Base Protocol, JSON-RPC error codes (-32603)."""

        class Boom(mcp_learn.FileServer):
            def _call_tool(self, req_id, params):
                raise RuntimeError("injected fault")

        server = Boom(self.sandbox)
        self.handshake(server)
        resp = server.handle(call(5, "tools/call",
                                  {"name": "read_file",
                                   "arguments": {"path": "hello.txt"}}))
        self.assertEqual(resp["error"]["code"], -32603)

    def test_c14_tools_list_schema(self):
        """C14: Server Features, Tools (tool definitions)."""
        self.handshake()
        resp = self.server.handle(call(2, "tools/list"))
        self.assertTrue(resp["result"]["tools"])
        for tool in resp["result"]["tools"]:
            self.assertIsInstance(tool["name"], str)
            self.assertIsInstance(tool["description"], str)
            self.assertIsInstance(tool["inputSchema"], dict)
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_c15_tool_call_success_shape(self):
        """C15: Server Features, Tools (CallToolResult)."""
        self.handshake()
        resp = self.server.handle(call(2, "tools/call",
                                       {"name": "read_file",
                                        "arguments": {"path": "hello.txt"}}))
        result = resp["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"],
                         {"path": "hello.txt", "content": "hello mcp\n"})
        texts = [c for c in result["content"] if c["type"] == "text"]
        self.assertTrue(texts)
        self.assertEqual(json.loads(texts[0]["text"]),
                         result["structuredContent"])

    def test_c16_unknown_tool_is_invalid_params(self):
        """C16: Server Features, Tools (protocol errors)."""
        self.handshake()
        resp = self.server.handle(call(2, "tools/call",
                                       {"name": "frobnicate",
                                        "arguments": {}}))
        self.assertEqual(resp["error"]["code"], -32602)

    def test_c17_missing_argument_is_invalid_params(self):
        """C17: Server Features, Tools (protocol errors)."""
        self.handshake()
        resp = self.server.handle(call(2, "tools/call",
                                       {"name": "read_file",
                                        "arguments": {}}))
        self.assertEqual(resp["error"]["code"], -32602)

    def test_c18_execution_failure_is_an_error_result(self):
        """C18: Server Features, Tools (tool execution errors)."""
        self.handshake()
        resp = self.server.handle(call(2, "tools/call",
                                       {"name": "read_file",
                                        "arguments": {"path": "missing.txt"}}))
        self.assertNotIn("error", resp)
        self.assertTrue(resp["result"]["isError"])
        self.assertEqual(
            resp["result"]["structuredContent"]["reason"], "file_not_found")

    def test_c19_safety_refusals_are_error_results(self):
        """C19: Server Features, Tools (tool execution errors)."""
        self.handshake()
        resp = self.server.handle(call(2, "tools/call",
                                       {"name": "read_file",
                                        "arguments": {"path": "../secret.txt"}}))
        self.assertTrue(resp["result"]["isError"])
        self.assertEqual(
            resp["result"]["structuredContent"]["reason"], "path_traversal")
        db = mcp_learn.DatabaseServer()
        self.handshake(db)
        resp = db.handle(call(3, "tools/call",
                              {"name": "run_query",
                               "arguments": {"sql": "DROP TABLE items"}}))
        self.assertTrue(resp["result"]["isError"])
        self.assertEqual(
            resp["result"]["structuredContent"]["reason"], "write_blocked")

    def test_c20_resources_list(self):
        """C20: Server Features, Resources (resources/list)."""
        self.handshake()
        resp = self.server.handle(call(2, "resources/list"))
        resources = resp["result"]["resources"]
        self.assertTrue(resources)
        for resource in resources:
            self.assertIn("uri", resource)
            self.assertIn("name", resource)
        self.assertIn("sandbox://hello.txt",
                      [r["uri"] for r in resources])

    def test_c21_resources_read_contents(self):
        """C21: Server Features, Resources (resources/read)."""
        self.handshake()
        resp = self.server.handle(call(2, "resources/read",
                                       {"uri": "sandbox://notes.txt"}))
        contents = resp["result"]["contents"]
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0]["uri"], "sandbox://notes.txt")
        self.assertEqual(contents[0]["text"], "tools need rules\n")

    def test_c22_resource_not_found_code(self):
        """C22: Server Features, Resources (error handling, -32002)."""
        self.handshake()
        resp = self.server.handle(call(2, "resources/read",
                                       {"uri": "sandbox://missing.txt"}))
        self.assertEqual(resp["error"]["code"], -32002)

    def test_c26_no_shutdown_message(self):
        """C26: Lifecycle, shutdown (no shutdown message is defined)."""
        self.handshake()
        resp = self.server.handle(call(9, "shutdown"))
        self.assertEqual(resp["error"]["code"], -32601)


# ---------------------------------------------------------------- Build

class StdioServer:
    """One Build server subprocess driven over raw pipes."""

    def __init__(self, kind, sandbox=None):
        main = os.path.join(ROOT, "level-2-build", "server_main.py")
        cmd = [sys.executable, main, kind]
        if kind == "file":
            cmd.append(sandbox or "")
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8")
        self.lines = queue.Queue()
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()

    def _pump(self):
        for line in self.proc.stdout:
            self.lines.put(line)

    def send(self, payload):
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def send_raw(self, text):
        self.proc.stdin.write(text + "\n")
        self.proc.stdin.flush()

    def read(self, timeout=5):
        line = self.lines.get(timeout=timeout)
        return line, json.loads(line)

    def expect_silence(self, timeout=0.8):
        try:
            line = self.lines.get(timeout=timeout)
        except queue.Empty:
            return
        raise AssertionError("expected no output, got: " + line)

    def handshake(self, version=LATEST):
        self.send(init_request(1, version))
        _, resp = self.read()
        self.send(initialized_note())
        return resp

    def close(self):
        try:
            self.proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        code = self.proc.wait(timeout=5)
        self.proc.stdout.close()
        self.proc.stderr.close()
        return code


class TestBuildStdioConformance(unittest.TestCase):
    """Stdio arm: raw NDJSON pipes to level-2-build/server_main.py."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sandbox = mcp_build.write_fixtures(
            os.path.join(self.tmp.name, "sandbox"))
        self.calc = StdioServer("calc")
        self.addCleanup(self._close_quietly, self.calc)

    def _close_quietly(self, server):
        try:
            server.close()
        except Exception:
            server.proc.kill()

    def test_c01_c03_c04_handshake_shape_and_notification_silence(self):
        """C01, C03, C04: Lifecycle; Transports (stdio)."""
        resp = self.calc.handshake("2025-06-18")
        result = resp["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertIsInstance(result["capabilities"]["tools"], dict)
        self.assertIsInstance(result["capabilities"]["resources"], dict)
        self.assertEqual(result["serverInfo"]["name"], "mcp-toolkit-calc")
        self.assertTrue(result["serverInfo"]["version"])
        # The notification produced no line: the next line out is the
        # answer to the ping sent after it.
        self.calc.send(call(7, "ping"))
        _, resp = self.calc.read()
        self.assertEqual(resp["id"], 7)
        self.assertEqual(resp["result"], {})

    def test_c02_unsupported_version_gets_latest_over_stdio(self):
        """C02: Lifecycle, version negotiation."""
        self.calc.send(init_request(1, "1999-01-01"))
        _, resp = self.calc.read()
        self.assertEqual(resp["result"]["protocolVersion"], LATEST)
        self.calc.send(initialized_note())

    def test_c07_c09_c10_c11_c12_c14_c16_c17_over_stdio(self):
        """C07, C09, C10, C11, C12, C14, C16, C17 over stdio."""
        self.calc.handshake()
        # C07 unknown method
        self.calc.send(call(10, "bogus/method"))
        _, resp = self.calc.read()
        self.assertEqual(resp["error"]["code"], -32601)
        # C09 invalid requests: null id, wrong jsonrpc version
        self.calc.send({"jsonrpc": "2.0", "id": None, "method": "ping"})
        _, resp = self.calc.read()
        self.assertEqual(resp["error"]["code"], -32600)
        self.calc.send({"jsonrpc": "1.0", "id": 11, "method": "ping"})
        _, resp = self.calc.read()
        self.assertEqual(resp["error"]["code"], -32600)
        # C10 a batch is answered with one error object, not an array
        self.calc.send([call(12, "ping")])
        _, resp = self.calc.read()
        self.assertIsInstance(resp, dict)
        self.assertEqual(resp["error"]["code"], -32600)
        # C11 an unknown notification is never answered: the next line
        # out belongs to the ping sent after it
        self.calc.send({"jsonrpc": "2.0",
                        "method": "notifications/cancelled"})
        self.calc.send(call(13, "ping"))
        _, resp = self.calc.read()
        self.assertEqual(resp["id"], 13)
        # C12 a string id is echoed
        self.calc.send(init_request("req-xyz"))
        _, resp = self.calc.read()
        self.assertEqual(resp["id"], "req-xyz")
        self.calc.send(initialized_note())
        # C14 tools/list schema
        self.calc.send(call(14, "tools/list"))
        _, resp = self.calc.read()
        for tool in resp["result"]["tools"]:
            self.assertIsInstance(tool["name"], str)
            self.assertIsInstance(tool["description"], str)
            self.assertEqual(tool["inputSchema"]["type"], "object")
        # C16 unknown tool, C17 missing argument
        self.calc.send(call(15, "tools/call",
                            {"name": "frobnicate", "arguments": {}}))
        _, resp = self.calc.read()
        self.assertEqual(resp["error"]["code"], -32602)
        self.calc.send(call(16, "tools/call",
                            {"name": "calculate", "arguments": {}}))
        _, resp = self.calc.read()
        self.assertEqual(resp["error"]["code"], -32602)

    def test_c18_c19_c22_over_stdio(self):
        """C18, C19, C22 over stdio (file and database servers)."""
        server = StdioServer("file", self.sandbox)
        self.addCleanup(self._close_quietly, server)
        server.handshake()
        server.send(call(3, "tools/call",
                         {"name": "read_file",
                          "arguments": {"path": "missing.txt"}}))
        _, resp = server.read()
        self.assertTrue(resp["result"]["isError"])
        self.assertEqual(resp["result"]["structuredContent"]["reason"],
                         "file_not_found")
        server.send(call(4, "tools/call",
                         {"name": "read_file",
                          "arguments": {"path": "../secret.txt"}}))
        _, resp = server.read()
        self.assertTrue(resp["result"]["isError"])
        self.assertEqual(resp["result"]["structuredContent"]["reason"],
                         "path_traversal")
        server.send(call(5, "resources/read",
                         {"uri": "sandbox://missing.txt"}))
        _, resp = server.read()
        self.assertEqual(resp["error"]["code"], -32002)
        db = StdioServer("database")
        self.addCleanup(self._close_quietly, db)
        db.handshake()
        db.send(call(6, "tools/call",
                     {"name": "run_query",
                      "arguments": {"sql": "DROP TABLE items"}}))
        _, resp = db.read()
        self.assertTrue(resp["result"]["isError"])
        self.assertEqual(resp["result"]["structuredContent"]["reason"],
                         "write_blocked")

    def test_c05_preinitialization_rejected_over_stdio(self):
        """C05: Lifecycle, initialization must come first."""
        self.calc.send(call(1, "tools/list"))
        _, resp = self.calc.read()
        self.assertEqual(resp["error"]["code"], -32600)
        self.assertEqual(resp["error"]["data"]["reason"], "not_initialized")

    def test_c08_malformed_json_is_parse_error(self):
        """C08: Base Protocol, JSON-RPC error codes (-32700)."""
        self.calc.send_raw("{not json")
        _, resp = self.calc.read()
        self.assertEqual(resp["error"]["code"], -32700)
        self.assertIsNone(resp["id"])

    def test_c15_tool_call_success_shape_over_stdio(self):
        """C15: Server Features, Tools (CallToolResult)."""
        self.calc.handshake()
        self.calc.send(call(3, "tools/call",
                            {"name": "calculate",
                             "arguments": {"op": "add", "a": 2, "b": 3}}))
        _, resp = self.calc.read()
        result = resp["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["value"], 5)

    def test_c20_c21_resources_over_stdio(self):
        """C20, C21: Server Features, Resources."""
        server = StdioServer("file", self.sandbox)
        self.addCleanup(self._close_quietly, server)
        server.handshake()
        server.send(call(3, "resources/list"))
        _, resp = server.read()
        self.assertIn("sandbox://hello.txt",
                      [r["uri"] for r in resp["result"]["resources"]])
        server.send(call(4, "resources/read",
                         {"uri": "sandbox://hello.txt"}))
        _, resp = server.read()
        self.assertEqual(resp["result"]["contents"][0]["text"],
                         "hello mcp\n")

    def test_c24_stdio_framing(self):
        """C24: Transports (stdio): newline-delimited JSON only."""
        raw_lines = []
        self.calc.send(init_request(1))
        line, _ = self.calc.read()
        raw_lines.append(line)
        self.calc.send(initialized_note())
        self.calc.send(call(2, "tools/list"))
        line, _ = self.calc.read()
        raw_lines.append(line)
        self.calc.send(call(3, "tools/call",
                            {"name": "count_words",
                             "arguments": {"text": "one two"}}))
        line, _ = self.calc.read()
        raw_lines.append(line)
        for line in raw_lines:
            self.assertTrue(line.endswith("\n"))
            parsed = json.loads(line)
            self.assertEqual(parsed["jsonrpc"], "2.0")
            self.assertIn("result", parsed)

    def test_c25_stdio_shutdown_on_stdin_close(self):
        """C25: Lifecycle, shutdown; Transports (stdio)."""
        self.calc.handshake()
        code = self.calc.close()
        self.assertEqual(code, 0)

    def test_c26_no_shutdown_message_over_stdio(self):
        """C26: Lifecycle, shutdown."""
        self.calc.handshake()
        self.calc.send(call(9, "shutdown"))
        _, resp = self.calc.read()
        self.assertEqual(resp["error"]["code"], -32601)

    def test_c13_internal_error_code_in_process(self):
        """C13: Base Protocol, JSON-RPC error codes (-32603)."""

        class Boom(mcp_build.CalcServer):
            def _call_tool(self, req_id, params):
                raise RuntimeError("injected fault")

        server = Boom()
        server.handle(init_request(1))
        server.handle(initialized_note())
        resp = server.handle(call(5, "tools/call",
                                  {"name": "calculate",
                                   "arguments": {"op": "add",
                                                 "a": 1, "b": 2}}))
        self.assertEqual(resp["error"]["code"], -32603)


# ----------------------------------------------------------------- Deep

class TestDeepHttpConformance(unittest.TestCase):
    """HTTP arm: raw urllib against a fresh Deep server per test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        sandbox = mcp_deep.write_fixtures(
            os.path.join(self.tmp.name, "sandbox"))
        store = mcp_deep.TokenStore.from_plaintext(
            {"reader": READER_TEST_TOKEN,
             "operator": OPERATOR_TEST_TOKEN})
        self.core = mcp_deep.ToolkitCore(sandbox)
        self.server = mcp_deep.make_server(self.core, store)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)
        self.url = "http://127.0.0.1:%d/mcp" % self.port

    def raw(self, body, token=READER_TEST_TOKEN, headers=None,
            method="POST", path=None):
        req = urllib.request.Request(
            path or self.url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def post(self, payload, token=READER_TEST_TOKEN, headers=None):
        status, hdrs, body = self.raw(
            json.dumps(payload).encode("utf-8"), token, headers)
        return status, hdrs, json.loads(body) if body else {}

    def handshake(self, version=LATEST, token=READER_TEST_TOKEN):
        status, _, payload = self.post(init_request(1, version), token)
        assert status == 200 and "result" in payload, payload
        note_status, _, note_body = self.raw(
            json.dumps(initialized_note()).encode("utf-8"), token)
        assert note_status == 202 and note_body == b"", note_status
        return payload

    def test_c01_version_negotiation_echoes_supported(self):
        """C01: Lifecycle, version negotiation."""
        payload = self.handshake("2025-06-18")
        self.assertEqual(payload["result"]["protocolVersion"],
                         "2025-06-18")

    def test_c02_unsupported_version_gets_latest(self):
        """C02: Lifecycle, version negotiation."""
        _, _, payload = self.post(init_request(1, "1999-01-01"))
        self.assertEqual(payload["result"]["protocolVersion"], LATEST)

    def test_c03_initialize_result_shape(self):
        """C03: Lifecycle, InitializeResult."""
        _, _, payload = self.post(init_request(1))
        result = payload["result"]
        self.assertIsInstance(result["capabilities"]["tools"], dict)
        self.assertNotIn("resources", result["capabilities"])
        self.assertEqual(result["serverInfo"]["name"], "mcp-toolkit-deep")
        self.assertTrue(result["serverInfo"]["version"])

    def test_c04_c29_notification_accepted_202_empty(self):
        """C04, C29: Base Protocol; Transports (streamable HTTP)."""
        self.post(init_request(1))
        status, _, body = self.raw(
            json.dumps(initialized_note()).encode("utf-8"))
        self.assertEqual(status, 202)
        self.assertEqual(body, b"")

    def test_c11_unknown_notification_accepted_202(self):
        """C11: Base Protocol (notifications are never answered)."""
        self.handshake()
        status, _, body = self.raw(json.dumps(
            {"jsonrpc": "2.0",
             "method": "notifications/cancelled"}).encode("utf-8"))
        self.assertEqual(status, 202)
        self.assertEqual(body, b"")

    def test_c26_no_shutdown_message_over_http(self):
        """C26: Lifecycle, shutdown (no shutdown message is defined)."""
        self.handshake()
        _, _, payload = self.post(call(9, "shutdown"))
        self.assertEqual(payload["error"]["code"], -32601)

    def test_c05_requests_before_ready_are_rejected(self):
        """C05: Lifecycle, initialization must come first."""
        _, _, payload = self.post(call(1, "tools/call",
                                       {"name": "read_file",
                                        "arguments": {"path": "hello.txt"}}))
        self.assertEqual(payload["error"]["code"], -32600)
        self.assertEqual(payload["error"]["data"]["reason"],
                         "not_initialized")

    def test_c06_ping_empty_result_any_state(self):
        """C06: Utilities, Ping."""
        _, _, payload = self.post(call(1, "ping"))
        self.assertEqual(payload["result"], {})
        self.handshake()
        _, _, payload = self.post(call(2, "ping"))
        self.assertEqual(payload["result"], {})

    def test_c07_unknown_method(self):
        """C07: Base Protocol, JSON-RPC error codes."""
        self.handshake()
        _, _, payload = self.post(call(9, "bogus/method"))
        self.assertEqual(payload["error"]["code"], -32601)

    def test_c08_malformed_json_is_parse_error(self):
        """C08: Base Protocol, JSON-RPC error codes (-32700)."""
        status, _, body = self.raw(b"{not json")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["error"]["code"], -32700)
        self.assertIsNone(payload["id"])

    def test_c09_invalid_requests(self):
        """C09: Base Protocol, JSON-RPC message shapes."""
        _, _, payload = self.post(
            {"jsonrpc": "1.0", "id": 1, "method": "ping"})
        self.assertEqual(payload["error"]["code"], -32600)
        _, _, payload = self.post(
            {"jsonrpc": "2.0", "id": None, "method": "ping"})
        self.assertEqual(payload["error"]["code"], -32600)

    def test_c10_batch_is_a_single_error(self):
        """C10: Base Protocol (batching removed in 2025-06-18)."""
        _, _, body = self.raw(json.dumps([call(1, "ping")]).encode())
        payload = json.loads(body)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["error"]["code"], -32600)

    def test_c12_response_envelope_and_string_id(self):
        """C12: Base Protocol, response shape."""
        _, _, payload = self.post(init_request("req-abc"))
        self.assertEqual(payload["jsonrpc"], "2.0")
        self.assertEqual(payload["id"], "req-abc")

    def test_c13_internal_error_code_in_process(self):
        """C13: Base Protocol, JSON-RPC error codes (-32603)."""

        class Boom(mcp_deep.ToolkitCore):
            def _list_items(self, req_id, args, role):
                raise RuntimeError("injected fault")

        core = Boom(os.path.join(self.tmp.name, "sandbox"))
        _, payload = core.dispatch(init_request(1), "reader")
        self.assertIn("result", payload)
        _, payload = core.dispatch(call(5, "tools/call",
                                        {"name": "list_items",
                                         "arguments": {}}), "reader")
        self.assertEqual(payload["error"]["code"], -32603)

    def test_c14_tools_list_schema(self):
        """C14: Server Features, Tools (tool definitions)."""
        self.handshake()
        _, _, payload = self.post(call(2, "tools/list"))
        tools = payload["result"]["tools"]
        self.assertTrue(tools)
        for tool in tools:
            self.assertIsInstance(tool["name"], str)
            self.assertIsInstance(tool["description"], str)
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_c15_c32_tool_call_success_shape_and_content_type(self):
        """C15, C32: Tools (CallToolResult); Transports (HTTP)."""
        self.handshake()
        status, hdrs, payload = self.post(call(
            2, "tools/call", {"name": "read_file",
                              "arguments": {"path": "hello.txt"}}))
        self.assertEqual(status, 200)
        self.assertTrue(
            hdrs.get("Content-Type", "").startswith("application/json"))
        result = payload["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"],
                         {"path": "hello.txt", "content": "hello mcp\n"})
        texts = [c for c in result["content"] if c["type"] == "text"]
        self.assertEqual(json.loads(texts[0]["text"]),
                         result["structuredContent"])

    def test_c16_unknown_tool_is_invalid_params(self):
        """C16: Server Features, Tools (protocol errors)."""
        self.handshake()
        _, _, payload = self.post(call(2, "tools/call",
                                       {"name": "frobnicate",
                                        "arguments": {}}))
        self.assertEqual(payload["error"]["code"], -32602)
        self.assertEqual(payload["error"]["data"]["reason"], "unknown_tool")

    def test_c17_missing_argument_is_invalid_params(self):
        """C17: Server Features, Tools (protocol errors)."""
        self.handshake()
        _, _, payload = self.post(call(2, "tools/call",
                                       {"name": "run_query",
                                        "arguments": {}}))
        self.assertEqual(payload["error"]["code"], -32602)

    def test_c18_execution_failure_is_an_error_result(self):
        """C18: Server Features, Tools (tool execution errors)."""
        self.handshake()
        _, _, payload = self.post(call(2, "tools/call",
                                       {"name": "read_file",
                                        "arguments": {"path": "missing.txt"}}))
        self.assertNotIn("error", payload)
        self.assertTrue(payload["result"]["isError"])
        self.assertEqual(
            payload["result"]["structuredContent"]["reason"],
            "file_not_found")

    def test_c19_safety_refusals_are_error_results(self):
        """C19: Server Features, Tools (tool execution errors)."""
        self.handshake()
        _, _, payload = self.post(call(2, "tools/call",
                                       {"name": "read_file",
                                        "arguments": {"path": "../secret.txt"}}))
        self.assertTrue(payload["result"]["isError"])
        self.assertEqual(
            payload["result"]["structuredContent"]["reason"],
            "path_traversal")
        _, _, payload = self.post(call(3, "tools/call",
                                       {"name": "run_query",
                                        "arguments": {"sql": "DROP TABLE items"}}))
        self.assertTrue(payload["result"]["isError"])
        self.assertEqual(
            payload["result"]["structuredContent"]["reason"],
            "sql_not_select")

    def test_c23_resources_not_offered_over_http(self):
        """C23: Lifecycle (capabilities); Resources."""
        self.handshake()
        _, _, payload = self.post(call(2, "resources/list"))
        self.assertEqual(payload["error"]["code"], -32601)
        _, _, payload = self.post(call(3, "resources/read",
                                       {"uri": "sandbox://hello.txt"}))
        self.assertEqual(payload["error"]["code"], -32601)

    def test_c27_get_on_mcp_endpoint_is_405(self):
        """C27: Transports (streamable HTTP, GET)."""
        status, _, _ = self.raw(None, method="GET")
        self.assertEqual(status, 405)

    def test_c28_protocol_version_header(self):
        """C28: Transports (streamable HTTP, protocol version header)."""
        self.handshake()
        status, _, _ = self.post(
            call(2, "tools/list"),
            headers={"MCP-Protocol-Version": "2025-11-25"})
        self.assertEqual(status, 200)
        status, _, _ = self.raw(
            json.dumps(call(3, "tools/list")).encode(),
            headers={"MCP-Protocol-Version": "1999-01-01"})
        self.assertEqual(status, 400)

    def test_c30_origin_validation(self):
        """C30: Transports (streamable HTTP, Origin security)."""
        status, _, _ = self.post(
            init_request(1), headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 403)
        status, _, _ = self.post(
            init_request(1), headers={"Origin": "http://localhost:3000"})
        self.assertEqual(status, 200)

    def test_c31_initialize_requires_the_token(self):
        """C31: Authorization framework (toolkit bearer layer)."""
        status, _, _ = self.post(init_request(1), token=None)
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
