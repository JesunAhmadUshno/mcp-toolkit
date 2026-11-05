"""Run the Learn protocol scenario and write deterministic results.

Run: python level-1-learn/run_learn.py
Writes level-1-learn/results_learn.json. No timestamps, no randomness,
so two runs produce an identical file. Fixture files are written into
level-1-learn/demo_sandbox with fixed content on every run.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mcp_learn import (DatabaseServer, FileServer, HostClient,  # noqa: E402
                       make_request, write_fixtures)

BLOCKED_REASONS = {"path_traversal", "write_blocked"}


def main():
    sandbox = write_fixtures(os.path.join(HERE, "demo_sandbox"))
    host = HostClient([FileServer(sandbox), DatabaseServer()])
    host.list_tools()  # local aggregation, not counted as a protocol call

    plan = [
        ("file", make_request(1, "initialize"), None),
        ("database", make_request(2, "initialize"), None),
        ("file", make_request(3, "tools/list"), None),
        ("database", make_request(4, "tools/list"), None),
        ("file", make_request(5, "tools/call",
         {"name": "read_file", "arguments": {"path": "hello.txt"}}), "read_file"),
        ("file", make_request(6, "tools/call",
         {"name": "list_files", "arguments": {}}), "list_files"),
        ("database", make_request(7, "tools/call",
         {"name": "list_items", "arguments": {}}), "list_items"),
        ("database", make_request(8, "tools/call",
         {"name": "run_query", "arguments": {
             "sql": "SELECT name, score FROM items WHERE score >= 20 ORDER BY id"}}),
         "run_query"),
        ("file", make_request(9, "resources/read",
         {"uri": "sandbox://notes.txt"}), None),
        ("database", make_request(10, "resources/read",
         {"uri": "db://items"}), None),
        ("file", make_request(11, "tools/call",
         {"name": "read_file", "arguments": {"path": "../secret.txt"}}), "read_file"),
        ("file", make_request(12, "tools/call",
         {"name": "read_file", "arguments": {"path": "/etc/passwd"}}), "read_file"),
        ("database", make_request(13, "tools/call",
         {"name": "run_query", "arguments": {"sql": "DROP TABLE items"}}), "run_query"),
        ("database", make_request(14, "tools/call",
         {"name": "run_query", "arguments": {
             "sql": "INSERT INTO items VALUES (4, 'delta', 40)"}}), "run_query"),
        ("file", make_request(15, "tools/call",
         {"name": "delete_file", "arguments": {"path": "hello.txt"}}), "delete_file"),
        ("database", make_request(16, "tools/call",
         {"name": "run_query", "arguments": {}}), "run_query"),
        ("file", make_request(17, "tools/call",
         {"name": "read_file", "arguments": {"path": "missing.txt"}}), "read_file"),
        ("file", make_request(18, "bogus/method"), None),
    ]

    calls = []
    for seq, (server, request, tool) in enumerate(plan, start=1):
        resp = host.handle(server, request)
        if "error" in resp:
            reason = resp["error"]["data"]["reason"]
            status = "blocked" if reason in BLOCKED_REASONS else "error"
            detail = {"error_code": resp["error"]["code"],
                      "error_reason": reason,
                      "error_message": resp["error"]["message"]}
        else:
            status = "success"
            detail = {"result": resp["result"]}
        label = tool or request["method"]
        if request["method"] == "resources/read":
            label = "resources/read " + request["params"]["uri"]
        entry = {"seq": seq, "server": server, "method": request["method"],
                 "label": label, "status": status}
        entry.update(detail)
        calls.append(entry)
        print(f"C{seq:02d} {server} {label}: {status} {detail}")

    successes = sum(1 for c in calls if c["status"] == "success")
    blocked = [c for c in calls if c["status"] == "blocked"]
    errors = sum(1 for c in calls if c["status"] == "error")
    by_rule = {}
    for c in blocked:
        by_rule[c["error_reason"]] = by_rule.get(c["error_reason"], 0) + 1
    tools = host.list_tools()
    per_server = {}
    for t in tools:
        per_server[t["server"]] = per_server.get(t["server"], 0) + 1
    summary = {"total_calls": len(calls), "successes": successes,
               "blocked": len(blocked), "errors": errors,
               "blocked_by_rule": by_rule,
               "tools_per_server": per_server,
               "total_tools": len(tools)}
    out = {"summary": summary, "calls": calls}
    path = os.path.join(HERE, "results_learn.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"Summary: {summary}")
    print("Wrote", path)
    expected = {"total_calls": 18, "successes": 10, "blocked": 4, "errors": 4}
    return 0 if all(summary[k] == v for k, v in expected.items()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
