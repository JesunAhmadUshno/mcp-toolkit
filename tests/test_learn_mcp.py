"""Unit tests for Level 1 Learn MCP-style protocol. Hand-computed."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "level-1-learn"))
from mcp_learn import (DatabaseServer, FileServer, HostClient,  # noqa: E402
                       SEED_ROWS, make_request, write_fixtures)


def make_host(tmp):
    sandbox = write_fixtures(os.path.join(tmp, "sandbox"))
    host = HostClient([FileServer(sandbox), DatabaseServer()])
    host.list_tools()
    return host


class TestLearnMcp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.host = make_host(self.tmp.name)

    def test_aggregation_counts_and_names(self):
        tools = self.host.list_tools()
        self.assertEqual(len(tools), 4)
        self.assertEqual(sorted(t["name"] for t in tools),
                         ["list_files", "list_items", "read_file", "run_query"])
        per = {}
        for t in tools:
            per[t["server"]] = per.get(t["server"], 0) + 1
        self.assertEqual(per, {"database": 2, "file": 2})

    def test_initialize_both_servers(self):
        for server in ("file", "database"):
            r = self.host.handle(server, make_request(1, "initialize"))
            self.assertEqual(r["result"]["server"], server)
            self.assertEqual(r["result"]["protocolVersion"], "learn-1")

    def test_file_read_success(self):
        r = self.host.call_tool(1, "read_file", {"path": "hello.txt"})
        self.assertEqual(r["result"], {"path": "hello.txt", "content": "hello mcp\n"})

    def test_list_files_success(self):
        r = self.host.call_tool(1, "list_files", {})
        self.assertEqual(r["result"]["files"], ["hello.txt", "notes.txt"])

    def test_db_list_items_exact_rows(self):
        r = self.host.call_tool(1, "list_items", {})
        self.assertEqual(r["result"]["rows"], SEED_ROWS)

    def test_db_query_exact_rows(self):
        # scores >= 20 are beta (20) and gamma (30), by id order
        r = self.host.call_tool(1, "run_query", {
            "sql": "SELECT name, score FROM items WHERE score >= 20 ORDER BY id"})
        self.assertEqual(r["result"]["rows"],
                         [{"name": "beta", "score": 20},
                          {"name": "gamma", "score": 30}])

    def test_resource_read_file(self):
        r = self.host.read_resource(1, "file", "sandbox://notes.txt")
        self.assertEqual(r["result"]["text"], "tools need rules\n")

    def test_resource_read_db(self):
        r = self.host.read_resource(1, "database", "db://items")
        self.assertEqual(r["result"]["rows"], SEED_ROWS)

    def test_traversal_relative_blocked(self):
        r = self.host.call_tool(1, "read_file", {"path": "../secret.txt"})
        self.assertEqual(r["error"]["code"], -32002)
        self.assertEqual(r["error"]["data"]["reason"], "path_traversal")

    def test_traversal_absolute_blocked(self):
        r = self.host.call_tool(1, "read_file", {"path": "/etc/passwd"})
        self.assertEqual(r["error"]["code"], -32002)
        self.assertEqual(r["error"]["data"]["reason"], "path_traversal")

    def test_write_drop_blocked(self):
        r = self.host.call_tool(1, "run_query", {"sql": "DROP TABLE items"})
        self.assertEqual(r["error"]["code"], -32003)
        self.assertEqual(r["error"]["data"]["reason"], "write_blocked")
        # table still intact after the blocked attempt
        r2 = self.host.call_tool(2, "list_items", {})
        self.assertEqual(r2["result"]["rows"], SEED_ROWS)

    def test_write_insert_blocked(self):
        r = self.host.call_tool(1, "run_query", {
            "sql": "INSERT INTO items VALUES (4, 'delta', 40)"})
        self.assertEqual(r["error"]["code"], -32003)

    def test_unknown_tool_error(self):
        r = self.host.handle("file", make_request(1, "tools/call",
                             {"name": "delete_file", "arguments": {}}))
        self.assertEqual(r["error"]["code"], -32001)
        self.assertEqual(r["error"]["data"]["reason"], "tool_not_found")
        self.assertNotIn("Traceback", str(r))

    def test_bad_argument_error(self):
        r = self.host.call_tool(1, "run_query", {})
        self.assertEqual(r["error"]["code"], -32602)
        self.assertEqual(r["error"]["data"]["reason"], "invalid_params")

    def test_bad_argument_type_error(self):
        r = self.host.call_tool(1, "read_file", {"path": 123})
        self.assertEqual(r["error"]["code"], -32602)

    def test_file_not_found_error(self):
        r = self.host.call_tool(1, "read_file", {"path": "missing.txt"})
        self.assertEqual(r["error"]["code"], -32004)
        self.assertEqual(r["error"]["data"]["reason"], "file_not_found")

    def test_unknown_method_error(self):
        r = self.host.handle("file", make_request(1, "bogus/method"))
        self.assertEqual(r["error"]["code"], -32601)
        self.assertEqual(r["error"]["data"]["reason"], "method_not_found")


if __name__ == "__main__":
    unittest.main()
