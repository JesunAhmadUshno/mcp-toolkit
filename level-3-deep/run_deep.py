"""Run the Deep scenario end to end over HTTP and write results.

Run: python level-3-deep/run_deep.py
Starts the Deep server on an ephemeral localhost port, runs 30
protocol calls through real HTTP with the client in mcp_deep.py,
and writes level-3-deep/results_deep.json deterministically: no
timing fields, no randomness, sorted keys, so two runs produce
identical counts and an identical file.

TEST TOKENS: the two tokens below are clearly labelled test tokens
for localhost runs only. They are set in-process, hashed in memory
by TokenStore.from_plaintext, and never written to the results
file, the audit log, or anywhere else. A real server start takes
token hashes from the environment (see server_main.py).
"""
import json
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mcp_deep import (SAFETY_REASONS, HttpMcpClient, TokenStore,  # noqa: E402
                      ToolkitCore, make_request, make_server,
                      write_fixtures)

READER_TEST_TOKEN = "test-reader-token-p09-deep-localhost-only"
OPERATOR_TEST_TOKEN = "test-operator-token-p09-deep-localhost-only"
WRONG_TEST_TOKEN = "test-wrong-token-p09-deep-localhost-only"


def categorize(status, payload):
    if status == 401:
        return "unauthenticated", "unauthenticated"
    if status == 403:
        return "role_blocked", "forbidden_role"
    if status == 413:
        return "safety_blocked", "request_too_large"
    if "error" in payload:
        reason = payload["error"]["data"]["reason"]
        if reason in SAFETY_REASONS:
            return "safety_blocked", reason
        return "error", reason
    return "success", None


def main():
    sandbox = write_fixtures(os.path.join(HERE, "demo_sandbox"))
    store = TokenStore.from_plaintext(
        {"reader": READER_TEST_TOKEN, "operator": OPERATOR_TEST_TOKEN})
    core = ToolkitCore(sandbox)
    server = make_server(core, store)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % port
    reader = HttpMcpClient(base, READER_TEST_TOKEN)
    operator = HttpMcpClient(base, OPERATOR_TEST_TOKEN)
    anon = HttpMcpClient(base, None)

    # Uncounted registry read: how many tools each role may see.
    _, op_list = operator.list_tools(0)
    operator_tools = len(op_list["result"]["tools"])

    select_scores = "SELECT name, score FROM items WHERE score >= 20 ORDER BY id"
    oversize_body = json.dumps(make_request(90, "tools/call", {
        "name": "count_words", "arguments": {"text": "x " * 5000}})).encode()

    plan = [
        ("reader", "initialize", lambda: reader.initialize(1)),
        ("reader", "tools/list", lambda: reader.list_tools(2)),
        ("reader", "read_file", lambda: reader.call_tool(
            3, "read_file", {"path": "hello.txt"})),
        ("reader", "list_files", lambda: reader.call_tool(4, "list_files", {})),
        ("reader", "list_items", lambda: reader.call_tool(5, "list_items", {})),
        ("reader", "run_query", lambda: reader.call_tool(
            6, "run_query", {"sql": select_scores})),
        ("operator", "calculate", lambda: operator.call_tool(
            7, "calculate", {"op": "add", "a": 20, "b": 30})),
        ("operator", "count_words", lambda: operator.call_tool(
            8, "count_words", {"text": "tools need rules"})),
        ("none", "read_file", lambda: anon.call_tool(
            9, "read_file", {"path": "hello.txt"})),
        ("wrong", "read_file", lambda: reader.call_tool(
            10, "read_file", {"path": "hello.txt"}, token=WRONG_TEST_TOKEN)),
        ("none", "initialize", lambda: anon.initialize(11)),
        ("reader", "calculate", lambda: reader.call_tool(
            12, "calculate", {"op": "add", "a": 1, "b": 2})),
        ("reader", "count_words", lambda: reader.call_tool(
            13, "count_words", {"text": "tools need rules"})),
        ("operator", "read_file", lambda: operator.call_tool(
            14, "read_file", {"path": "../secret.txt"})),
        ("reader", "read_file", lambda: reader.call_tool(
            15, "read_file", {"path": "../../etc/passwd"})),
        ("reader", "read_file", lambda: reader.call_tool(
            16, "read_file", {"path": "/etc/passwd"})),
        ("operator", "write_file", lambda: operator.call_tool(
            17, "write_file", {"path": "hello.txt", "content": "x"})),
        ("operator", "delete_file", lambda: operator.call_tool(
            18, "delete_file", {"path": "hello.txt"})),
        ("reader", "run_query", lambda: reader.call_tool(
            19, "run_query", {"sql": "DROP TABLE items"})),
        ("reader", "run_query", lambda: reader.call_tool(
            20, "run_query", {"sql": "DELETE FROM items WHERE id = 1"})),
        ("reader", "run_query", lambda: reader.call_tool(
            21, "run_query", {"sql": "UPDATE items SET score = 0 WHERE id = 1"})),
        ("reader", "run_query", lambda: reader.call_tool(
            22, "run_query",
            {"sql": "INSERT INTO items VALUES (4, 'delta', 40)"})),
        ("reader", "run_query", lambda: reader.call_tool(
            23, "run_query",
            {"sql": "SELECT id FROM items; SELECT id FROM items"})),
        ("reader", "run_query", lambda: reader.call_tool(
            24, "run_query", {"sql": "SELECT id FROM items; DROP TABLE items"})),
        ("operator", "count_words", lambda: operator.post_raw(oversize_body)),
        ("operator", "frobnicate", lambda: operator.call_tool(
            26, "frobnicate", {})),
        ("reader", "read_file", lambda: reader.call_tool(
            27, "read_file", {"path": "missing.txt"})),
        ("operator", "calculate", lambda: operator.call_tool(
            28, "calculate", {"op": "divide", "a": 10, "b": 0})),
        ("operator", "bogus/method", lambda: operator.post(
            make_request(29, "bogus/method"))),
        ("reader", "run_query", lambda: reader.call_tool(30, "run_query", {})),
    ]

    calls = []
    for seq, (role_label, label, fn) in enumerate(plan, start=1):
        status, payload = fn()
        category, reason = categorize(status, payload)
        entry = {"seq": seq, "role": role_label, "label": label,
                 "http_status": status, "status": category}
        if category == "success":
            entry["result"] = payload["result"]
        else:
            entry["error_reason"] = reason
            if "error" in payload:
                entry["error_code"] = payload["error"]["code"]
        calls.append(entry)
        print("D%02d %s %s: %s (http %d) %s" % (
            seq, role_label, label, category, status, reason or ""))

    server.shutdown()
    server.server_close()

    audit = core.audit_snapshot()
    successes = sum(1 for c in calls if c["status"] == "success")
    unauth = sum(1 for c in calls if c["status"] == "unauthenticated")
    role_blocked = sum(1 for c in calls if c["status"] == "role_blocked")
    safety = [c for c in calls if c["status"] == "safety_blocked"]
    errors = sum(1 for c in calls if c["status"] == "error")
    by_reason = {}
    for c in safety:
        by_reason[c["error_reason"]] = by_reason.get(c["error_reason"], 0) + 1
    summary = {
        "total_calls": len(calls), "successes": successes,
        "unauthenticated": unauth, "role_blocked": role_blocked,
        "safety_blocked": len(safety), "errors": errors,
        "safety_by_reason": by_reason,
        "audit_entries": len(audit),
        "total_tools": 6, "reader_tools": 4,
        "operator_tools": operator_tools,
        "transport": "http", "endpoint": "POST /mcp",
        "roles": ["reader", "operator"],
    }
    out = {"summary": summary, "calls": calls, "audit_log": audit}
    path = os.path.join(HERE, "results_deep.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    print("Summary:", summary)
    print("Wrote", path)
    expected = {"total_calls": 30, "successes": 8, "unauthenticated": 3,
                "role_blocked": 2, "safety_blocked": 13, "errors": 4,
                "audit_entries": 18, "operator_tools": 6}
    ok = all(summary[k] == v for k, v in expected.items())
    expected_reasons = {"path_traversal": 2, "absolute_path_blocked": 1,
                        "write_blocked": 1, "delete_blocked": 1,
                        "sql_not_select": 4, "sql_multi_statement": 2,
                        "request_too_large": 1, "unknown_tool": 1}
    ok = ok and by_reason == expected_reasons
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
