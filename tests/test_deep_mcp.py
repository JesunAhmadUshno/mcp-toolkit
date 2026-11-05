"""Unit tests for Level 3 Deep: authenticated HTTP MCP-style server.

Starts the real HTTP server on an ephemeral localhost port and calls
it over HTTP. Hand-computed expectations.

TEST TOKENS: the tokens below are clearly labelled test tokens for
localhost tests only. They are set in-process and hashed in memory;
no real credential exists in this file or anywhere in the repo.
"""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "level-3-deep"))
from mcp_deep import (HttpMcpClient, TokenStore, ToolkitCore,  # noqa: E402
                      hash_token, make_request, make_server,
                      write_fixtures)

READER_TEST_TOKEN = "test-reader-token-p09-deep-tests-only"
OPERATOR_TEST_TOKEN = "test-operator-token-p09-deep-tests-only"
WRONG_TEST_TOKEN = "test-wrong-token-p09-deep-tests-only"


class TestTokenStore(unittest.TestCase):
    def test_hash_only_storage_and_auth(self):
        store = TokenStore.from_plaintext({"reader": READER_TEST_TOKEN})
        self.assertNotIn(READER_TEST_TOKEN, str(store.role_hashes))
        self.assertEqual(store.role_hashes["reader"],
                         hash_token(READER_TEST_TOKEN))
        self.assertEqual(store.authenticate(READER_TEST_TOKEN), "reader")
        self.assertIsNone(store.authenticate(WRONG_TEST_TOKEN))
        self.assertIsNone(store.authenticate(None))
        self.assertIsNone(store.authenticate(""))

    def test_from_env_missing_raises(self):
        os.environ.pop("MCP_TOOLKIT_TOKEN_HASHES", None)
        with self.assertRaises(ValueError):
            TokenStore.from_env()


class TestDeepHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        sandbox = write_fixtures(os.path.join(cls.tmp.name, "sandbox"))
        store = TokenStore.from_plaintext(
            {"reader": READER_TEST_TOKEN, "operator": OPERATOR_TEST_TOKEN})
        cls.core = ToolkitCore(sandbox)
        cls.server = make_server(cls.core, store)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        base = "http://127.0.0.1:%d" % cls.port
        cls.reader = HttpMcpClient(base, READER_TEST_TOKEN)
        cls.operator = HttpMcpClient(base, OPERATOR_TEST_TOKEN)
        cls.anon = HttpMcpClient(base, None)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_health(self):
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/health" % self.port, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(resp.status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["transport"], "http")

    def test_initialize_returns_role(self):
        status, payload = self.reader.initialize(1)
        self.assertEqual(status, 200)
        self.assertEqual(payload["result"]["role"], "reader")
        self.assertEqual(payload["result"]["protocolVersion"], "deep-1")
        self.assertEqual(payload["result"]["transport"], "http")

    def test_tools_list_filtered_by_role(self):
        _, payload = self.reader.list_tools(1)
        names = sorted(t["name"] for t in payload["result"]["tools"])
        self.assertEqual(names, ["list_files", "list_items",
                                 "read_file", "run_query"])
        _, payload = self.operator.list_tools(2)
        names = sorted(t["name"] for t in payload["result"]["tools"])
        self.assertEqual(names, ["calculate", "count_words", "list_files",
                                 "list_items", "read_file", "run_query"])

    def test_missing_token_401(self):
        status, payload = self.anon.call_tool(
            1, "read_file", {"path": "hello.txt"})
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["data"]["reason"],
                         "unauthenticated")

    def test_wrong_token_401(self):
        status, payload = self.reader.call_tool(
            1, "read_file", {"path": "hello.txt"}, token=WRONG_TEST_TOKEN)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["data"]["reason"],
                         "unauthenticated")

    def test_read_file_success(self):
        status, payload = self.reader.call_tool(
            1, "read_file", {"path": "hello.txt"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["result"],
                         {"path": "hello.txt", "content": "hello mcp\n"})

    def test_list_files_success(self):
        _, payload = self.reader.call_tool(1, "list_files", {})
        self.assertEqual(payload["result"]["files"],
                         ["guide.txt", "hello.txt", "notes.txt"])

    def test_list_items_success(self):
        _, payload = self.reader.call_tool(1, "list_items", {})
        self.assertEqual([r["name"] for r in payload["result"]["rows"]],
                         ["alpha", "beta", "gamma"])

    def test_run_query_success(self):
        _, payload = self.reader.call_tool(1, "run_query", {
            "sql": "SELECT name, score FROM items WHERE score >= 20 ORDER BY id"})
        self.assertEqual(payload["result"]["rows"],
                         [{"name": "beta", "score": 20},
                          {"name": "gamma", "score": 30}])

    def test_calculate_success_operator(self):
        _, payload = self.operator.call_tool(
            1, "calculate", {"op": "add", "a": 20, "b": 30})
        self.assertEqual(payload["result"]["value"], 50)

    def test_count_words_success_operator(self):
        _, payload = self.operator.call_tool(
            1, "count_words", {"text": "tools need rules"})
        self.assertEqual(payload["result"]["count"], 3)

    def test_reader_calculate_forbidden_role(self):
        status, payload = self.reader.call_tool(
            1, "calculate", {"op": "add", "a": 1, "b": 2})
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["data"]["reason"],
                         "forbidden_role")

    def test_reader_count_words_forbidden_role(self):
        status, payload = self.reader.call_tool(
            1, "count_words", {"text": "x"})
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"]["data"]["reason"],
                         "forbidden_role")

    def test_path_traversal_blocked(self):
        for path in ("../secret.txt", "../../etc/passwd", "a/../../secret.txt"):
            _, payload = self.operator.call_tool(
                1, "read_file", {"path": path})
            self.assertEqual(payload["error"]["data"]["reason"],
                             "path_traversal", path)

    def test_absolute_path_blocked(self):
        _, payload = self.reader.call_tool(
            1, "read_file", {"path": "/etc/passwd"})
        self.assertEqual(payload["error"]["data"]["reason"],
                         "absolute_path_blocked")

    def test_write_attempt_blocked(self):
        _, payload = self.operator.call_tool(
            1, "write_file", {"path": "hello.txt", "content": "x"})
        self.assertEqual(payload["error"]["data"]["reason"], "write_blocked")

    def test_delete_attempt_blocked(self):
        _, payload = self.operator.call_tool(
            1, "delete_file", {"path": "hello.txt"})
        self.assertEqual(payload["error"]["data"]["reason"], "delete_blocked")
        _, payload = self.reader.call_tool(
            2, "read_file", {"path": "hello.txt"})
        self.assertEqual(payload["result"]["content"], "hello mcp\n")

    def test_sql_not_select_blocked(self):
        for sql in ("DROP TABLE items", "DELETE FROM items WHERE id = 1",
                    "UPDATE items SET score = 0 WHERE id = 1",
                    "INSERT INTO items VALUES (4, 'delta', 40)"):
            _, payload = self.reader.call_tool(1, "run_query", {"sql": sql})
            self.assertEqual(payload["error"]["data"]["reason"],
                             "sql_not_select", sql)
        _, payload = self.reader.call_tool(2, "list_items", {})
        self.assertEqual(len(payload["result"]["rows"]), 3)

    def test_sql_multi_statement_blocked(self):
        for sql in ("SELECT id FROM items; SELECT id FROM items",
                    "SELECT id FROM items; DROP TABLE items"):
            _, payload = self.reader.call_tool(1, "run_query", {"sql": sql})
            self.assertEqual(payload["error"]["data"]["reason"],
                             "sql_multi_statement", sql)

    def test_oversize_request_blocked(self):
        body = json.dumps(make_request(1, "tools/call", {
            "name": "count_words",
            "arguments": {"text": "x " * 5000}})).encode()
        status, payload = self.operator.post_raw(body)
        self.assertEqual(status, 413)
        self.assertEqual(payload["error"]["data"]["reason"],
                         "request_too_large")

    def test_unknown_tool_blocked(self):
        _, payload = self.operator.call_tool(1, "frobnicate", {})
        self.assertEqual(payload["error"]["data"]["reason"], "unknown_tool")

    def test_file_not_found_error(self):
        _, payload = self.reader.call_tool(
            1, "read_file", {"path": "missing.txt"})
        self.assertEqual(payload["error"]["data"]["reason"],
                         "file_not_found")

    def test_divide_by_zero_error(self):
        _, payload = self.operator.call_tool(
            1, "calculate", {"op": "divide", "a": 1, "b": 0})
        self.assertEqual(payload["error"]["data"]["reason"], "calc_error")

    def test_unknown_method_error(self):
        _, payload = self.operator.post(make_request(1, "bogus/method"))
        self.assertEqual(payload["error"]["data"]["reason"],
                         "method_not_found")

    def test_invalid_params_error(self):
        _, payload = self.reader.call_tool(1, "run_query", {})
        self.assertEqual(payload["error"]["data"]["reason"],
                         "invalid_params")

    def test_audit_log_records_blocks(self):
        before = len(self.core.audit_snapshot())
        self.anon.call_tool(1, "read_file", {"path": "hello.txt"})
        self.reader.call_tool(2, "calculate", {"op": "add", "a": 1, "b": 2})
        self.operator.call_tool(3, "delete_file", {"path": "hello.txt"})
        entries = self.core.audit_snapshot()[before:]
        self.assertEqual([e["reason"] for e in entries],
                         ["unauthenticated", "forbidden_role",
                          "delete_blocked"])
        self.assertEqual([e["category"] for e in entries],
                         ["auth", "authorization", "safety"])


if __name__ == "__main__":
    unittest.main()
