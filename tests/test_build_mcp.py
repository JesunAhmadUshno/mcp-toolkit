"""Unit tests for Level 2 Build MCP-style stdio transport. Hand-computed."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "level-2-build"))
from mcp_build import (CalcServer, DatabaseServer, FileServer,  # noqa: E402
                       InProcessHost, SEED_ROWS, StdioHostClient,
                       make_request, write_fixtures)


class TestInProcessBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        sandbox = write_fixtures(os.path.join(self.tmp.name, "sandbox"))
        self.host = InProcessHost(
            [FileServer(sandbox), DatabaseServer(), CalcServer()])
        self.host.list_tools()

    def test_aggregation_six_tools_three_servers(self):
        tools = self.host.list_tools()
        self.assertEqual(len(tools), 6)
        self.assertEqual(sorted(t["name"] for t in tools),
                         ["calculate", "count_words", "list_files",
                          "list_items", "read_file", "run_query"])
        per = {}
        for t in tools:
            per[t["server"]] = per.get(t["server"], 0) + 1
        self.assertEqual(per, {"calc": 2, "database": 2, "file": 2})

    def test_calc_add_and_word_count(self):
        r = self.host.call_tool(1, "calculate", {"op": "add", "a": 20, "b": 30})
        self.assertEqual(r["result"]["value"], 50)
        r = self.host.call_tool(2, "count_words", {"text": "tools need rules"})
        self.assertEqual(r["result"]["count"], 3)

    def test_calc_divide_by_zero(self):
        r = self.host.call_tool(1, "calculate",
                                {"op": "divide", "a": 10, "b": 0})
        self.assertEqual(r["error"]["code"], -32006)
        self.assertEqual(r["error"]["data"]["reason"], "calc_error")

    def test_unknown_server_in_process(self):
        r = self.host.handle("nope", make_request(1, "initialize"))
        self.assertEqual(r["error"]["data"]["reason"], "server_not_found")


class TestStdioBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        sandbox = write_fixtures(os.path.join(self.tmp.name, "sandbox"))
        self.host = StdioHostClient(sandbox)
        self.addCleanup(self.host.close)
        self.host.list_tools()

    def test_stdio_processes_alive(self):
        for conn in self.host.connections.values():
            self.assertIsNone(conn.proc.poll())

    def test_stdio_initialize_all(self):
        out = self.host.initialize_all()
        self.assertEqual(sorted(out), ["calc", "database", "file"])
        for name, resp in out.items():
            self.assertEqual(resp["result"]["server"], name)
            self.assertEqual(resp["result"]["protocolVersion"], "build-1")
            self.assertEqual(resp["result"]["transport"], "stdio")

    def test_stdio_aggregation(self):
        tools = self.host.list_tools()
        self.assertEqual(len(tools), 6)

    def test_stdio_file_read(self):
        r = self.host.call_tool(1, "read_file", {"path": "hello.txt"})
        self.assertEqual(r["result"], {"path": "hello.txt",
                                       "content": "hello mcp\n"})

    def test_stdio_list_files(self):
        r = self.host.call_tool(1, "list_files", {})
        self.assertEqual(r["result"]["files"],
                         ["guide.txt", "hello.txt", "notes.txt"])

    def test_stdio_db_rows_and_query(self):
        r = self.host.call_tool(1, "list_items", {})
        self.assertEqual(r["result"]["rows"], SEED_ROWS)
        r = self.host.call_tool(2, "run_query", {
            "sql": "SELECT name, score FROM items WHERE score >= 20 ORDER BY id"})
        self.assertEqual(r["result"]["rows"],
                         [{"name": "beta", "score": 20},
                          {"name": "gamma", "score": 30}])

    def test_stdio_calc_routing(self):
        # calculate is owned by calc, not file or database: routing works
        # only if the registry maps it to the calc subprocess.
        r = self.host.call_tool(1, "calculate",
                                {"op": "multiply", "a": 6, "b": 7})
        self.assertEqual(r["result"]["value"], 42)

    def test_stdio_resources(self):
        r = self.host.read_resource(1, "file", "sandbox://notes.txt")
        self.assertEqual(r["result"]["text"], "tools need rules\n")
        r = self.host.read_resource(2, "database", "db://items")
        self.assertEqual(r["result"]["rows"], SEED_ROWS)

    def test_stdio_traversal_blocked(self):
        for path in ("../secret.txt", "/etc/passwd"):
            r = self.host.call_tool(1, "read_file", {"path": path})
            self.assertEqual(r["error"]["code"], -32002)
            self.assertEqual(r["error"]["data"]["reason"], "path_traversal")

    def test_stdio_write_blocked_and_table_intact(self):
        for sql in ("DROP TABLE items",
                    "INSERT INTO items VALUES (4, 'delta', 40)"):
            r = self.host.call_tool(1, "run_query", {"sql": sql})
            self.assertEqual(r["error"]["code"], -32003)
            self.assertEqual(r["error"]["data"]["reason"], "write_blocked")
        r = self.host.call_tool(2, "list_items", {})
        self.assertEqual(r["result"]["rows"], SEED_ROWS)

    def test_stdio_unknown_tool(self):
        r = self.host.handle("file", make_request(1, "tools/call",
                             {"name": "delete_file", "arguments": {}}))
        self.assertEqual(r["error"]["code"], -32001)
        self.assertNotIn("Traceback", str(r))

    def test_stdio_invalid_params(self):
        r = self.host.call_tool(1, "run_query", {})
        self.assertEqual(r["error"]["code"], -32602)

    def test_stdio_file_not_found(self):
        r = self.host.call_tool(1, "read_file", {"path": "missing.txt"})
        self.assertEqual(r["error"]["code"], -32004)

    def test_stdio_unknown_method(self):
        r = self.host.handle("file", make_request(1, "bogus/method"))
        self.assertEqual(r["error"]["code"], -32601)

    def test_stdio_unknown_server(self):
        r = self.host.handle("nope", make_request(1, "initialize"))
        self.assertEqual(r["error"]["data"]["reason"], "server_not_found")

    def test_stdio_divide_by_zero(self):
        r = self.host.call_tool(1, "calculate",
                                {"op": "divide", "a": 1, "b": 0})
        self.assertEqual(r["error"]["code"], -32006)


if __name__ == "__main__":
    unittest.main()
