"""Measure the Deep safety guards on a labelled corpus, and export the
request side of the 30 recorded Deep calls.

Run: python level-3-deep/guard_corpus.py
Writes two files, deterministically (sorted keys, no timing, no
temporary paths):

- level-3-deep/deep_plan.json: the inputs of calls D01 to D30 from
  run_deep.py (token label, method, tool, arguments) as data, so a
  reader can see what each recorded call sent.
- level-3-deep/results_guard.json: per-case verdicts of the SQL guard
  (ToolkitCore._check_sql) and the read_file path rules over a
  labelled list of benign and malicious inputs, with measured false
  positive and false negative counts, plus a replay of the 30 Deep
  plan inputs over real localhost HTTP.

The labels say what the tool contract intends: run_query is "one
read-only SELECT on the items table", read_file is "one text file
inside the sandbox". A false positive is an intended-allowed input
that the guard blocks; a false negative is an intended-blocked input
that the guard lets through. SQL cases are checked by the guard only
and never executed, so no expensive query runs here.

results_deep.json is not touched. The script exits non-zero if the
HTTP replay of the plan differs from results_deep.json.
"""
import json
import os
import shutil
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mcp_deep import (SAFETY_REASONS, HttpMcpClient, TokenStore,  # noqa: E402
                      ToolkitCore, make_request, make_server,
                      write_fixtures)
from run_deep import (OPERATOR_TEST_TOKEN, READER_TEST_TOKEN,  # noqa: E402
                      WRONG_TEST_TOKEN, categorize)

SANDBOX_MARK = "{SANDBOX}"
SELECT_SCORES = "SELECT name, score FROM items WHERE score >= 20 ORDER BY id"

# Inputs of run_deep.py calls D01 to D30, in order. oversize_repeat
# means arguments.text is "x " repeated that many times (D25).
DEEP_PLAN = [
    ("reader", 1, "initialize", None, None),
    ("reader", 2, "tools/list", None, None),
    ("reader", 3, "tools/call", "read_file", {"path": "hello.txt"}),
    ("reader", 4, "tools/call", "list_files", {}),
    ("reader", 5, "tools/call", "list_items", {}),
    ("reader", 6, "tools/call", "run_query", {"sql": SELECT_SCORES}),
    ("operator", 7, "tools/call", "calculate", {"op": "add", "a": 20, "b": 30}),
    ("operator", 8, "tools/call", "count_words", {"text": "tools need rules"}),
    ("none", 9, "tools/call", "read_file", {"path": "hello.txt"}),
    ("wrong", 10, "tools/call", "read_file", {"path": "hello.txt"}),
    ("none", 11, "initialize", None, None),
    ("reader", 12, "tools/call", "calculate", {"op": "add", "a": 1, "b": 2}),
    ("reader", 13, "tools/call", "count_words", {"text": "tools need rules"}),
    ("operator", 14, "tools/call", "read_file", {"path": "../secret.txt"}),
    ("reader", 15, "tools/call", "read_file", {"path": "../../etc/passwd"}),
    ("reader", 16, "tools/call", "read_file", {"path": "/etc/passwd"}),
    ("operator", 17, "tools/call", "write_file", {"path": "hello.txt", "content": "x"}),
    ("operator", 18, "tools/call", "delete_file", {"path": "hello.txt"}),
    ("reader", 19, "tools/call", "run_query", {"sql": "DROP TABLE items"}),
    ("reader", 20, "tools/call", "run_query", {"sql": "DELETE FROM items WHERE id = 1"}),
    ("reader", 21, "tools/call", "run_query", {"sql": "UPDATE items SET score = 0 WHERE id = 1"}),
    ("reader", 22, "tools/call", "run_query", {"sql": "INSERT INTO items VALUES (4, 'delta', 40)"}),
    ("reader", 23, "tools/call", "run_query", {"sql": "SELECT id FROM items; SELECT id FROM items"}),
    ("reader", 24, "tools/call", "run_query", {"sql": "SELECT id FROM items; DROP TABLE items"}),
    ("operator", 90, "tools/call", "count_words", "oversize"),
    ("operator", 26, "tools/call", "frobnicate", {}),
    ("reader", 27, "tools/call", "read_file", {"path": "missing.txt"}),
    ("operator", 28, "tools/call", "calculate", {"op": "divide", "a": 10, "b": 0}),
    ("operator", 29, "bogus/method", None, None),
    ("reader", 30, "tools/call", "run_query", {}),
]
OVERSIZE_REPEAT = 5000

# (id, sql, intended, note)
SQL_CASES = [
    ("S01", SELECT_SCORES, "allow", "the recorded D06 query"),
    ("S02", "select id from items", "allow", "lower case keywords"),
    ("S03", "SELECT 1;", "allow", "one trailing semicolon"),
    ("S04", "  SELECT id FROM items  ", "allow", "surrounding whitespace"),
    ("S05", "SELECT name AS deleted FROM items", "allow", "alias that looks like a keyword"),
    ("S06", "WITH x AS (SELECT 1) SELECT * FROM x", "allow", "read-only common table expression"),
    ("S07", "SELECT name FROM items WHERE name = 'drop'", "allow", "blocked word inside a string literal"),
    ("S08", "SELECT replace(name, 'a', 'b') FROM items", "allow", "replace() string function"),
    ("S09", "/* read */ SELECT id FROM items", "allow", "leading comment"),
    ("S10", "SELECT id FROM items -- ; note", "allow", "semicolon inside a comment"),
    ("S11", "DROP TABLE items", "block", "drop"),
    ("S12", "DELETE FROM items WHERE id = 1", "block", "delete"),
    ("S13", "INSERT INTO items VALUES (4, 'delta', 40)", "block", "insert"),
    ("S14", "SELECT id FROM items; DROP TABLE items", "block", "stacked statement"),
    ("S15", "sElEcT id FrOm items; dRoP table items", "block", "mixed case stacked statement"),
    ("S16", "PRAGMA table_info(items)", "block", "pragma"),
    ("S17", "ATTACH DATABASE 'other.db' AS other", "block", "attach another database"),
    ("S18", "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT x FROM c",
     "block", "unbounded recursive query (blocked only because it starts with WITH)"),
    ("S19", "SELECT * FROM sqlite_master", "block", "schema read outside the items table"),
    ("S20", "SELECT name FROM items UNION SELECT sql FROM sqlite_master", "block",
     "schema read appended with UNION"),
    ("S21", "SELECT randomblob(100000000)", "block", "expensive allocation, no row or time cap"),
    ("S22", "SELECT load_extension('x')", "block",
     "extension load attempt (sqlite3 disables extension loading by default, so it would fail at run time)"),
]

# (id, path, intended, note). intended "block" means the read would
# leave the sandbox if unchecked.
PATH_CASES = [
    ("P01", "hello.txt", "allow", "plain fixture"),
    ("P02", "./notes.txt", "allow", "dot segment"),
    ("P03", "guide.txt/", "allow", "trailing slash"),
    ("P04", "missing.txt", "allow", "missing file stays inside"),
    ("P05", SANDBOX_MARK + "/hello.txt", "allow", "absolute path inside the sandbox"),
    ("P06", "%2e%2e/secret.txt", "allow", "URL-encoded dots are not decoded, so it is a literal name"),
    ("P07", "~/.ssh/id_rsa", "allow", "no home expansion, literal name"),
    ("P08", "\\etc\\passwd", "allow", "backslashes are literal characters on POSIX"),
    ("P09", ".", "allow", "the sandbox root is not a file"),
    ("P10", "sub/../hello.txt", "allow", "a .. segment that stays inside"),
    ("P11", "../secret.txt", "block", "parent directory"),
    ("P12", "..\\secret.txt", "block", "backslash parent directory"),
    ("P13", "hello.txt/../../etc/passwd", "block", "escape after a real name"),
    ("P14", "/etc/passwd", "block", "absolute path outside"),
    ("P15", "/", "block", "filesystem root"),
    ("P16", SANDBOX_MARK + "x/hello.txt", "block", "sibling directory sharing the sandbox prefix"),
    ("P17", SANDBOX_MARK + "/../secret.txt", "block", "absolute path that climbs out"),
]


def outcome(intended, blocked):
    if intended == "allow":
        return "false_positive" if blocked else "true_negative"
    return "true_positive" if blocked else "false_negative"


def score(rows):
    counts = {"cases": len(rows), "true_positive": 0, "true_negative": 0,
              "false_positive": 0, "false_negative": 0}
    for r in rows:
        counts[r["outcome"]] += 1
    return counts


def run_sql_cases(core):
    rows = []
    for cid, sql, intended, note in SQL_CASES:
        reason = core._check_sql(sql)
        rows.append({"id": cid, "sql": sql, "intended": intended,
                     "note": note, "verdict": reason or "allowed",
                     "outcome": outcome(intended, reason is not None)})
    return rows


def run_path_cases(core, sandbox):
    rows = []
    for cid, path, intended, note in PATH_CASES:
        resp = core._read_file(1, {"path": path.replace(SANDBOX_MARK, sandbox)},
                               "reader")
        verdict = resp["error"]["data"]["reason"] if "error" in resp else "allowed"
        blocked = verdict in SAFETY_REASONS
        rows.append({"id": cid, "path": path, "intended": intended,
                     "note": note, "verdict": verdict,
                     "outcome": outcome(intended, blocked)})
    return rows


def plan_as_data():
    out = []
    for i, (token, req_id, method, tool, args) in enumerate(DEEP_PLAN, start=1):
        entry = {"call": "D%02d" % i, "token": token, "request_id": req_id,
                 "method": method}
        if tool is not None:
            entry["tool"] = tool
            if args == "oversize":
                entry["oversize_repeat"] = OVERSIZE_REPEAT
            else:
                entry["arguments"] = args
        out.append(entry)
    return out


def replay_plan(plan, sandbox):
    store = TokenStore.from_plaintext(
        {"reader": READER_TEST_TOKEN, "operator": OPERATOR_TEST_TOKEN})
    core = ToolkitCore(sandbox)
    server = make_server(core, store)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    client = HttpMcpClient("http://127.0.0.1:%d" % server.server_address[1])
    tokens = {"reader": READER_TEST_TOKEN, "operator": OPERATOR_TEST_TOKEN,
              "wrong": WRONG_TEST_TOKEN, "none": None}
    rows = []
    try:
        for p in plan:
            params = None
            if "tool" in p:
                args = p.get("arguments")
                if "oversize_repeat" in p:
                    args = {"text": "x " * p["oversize_repeat"]}
                params = {"name": p["tool"], "arguments": args}
            status, payload = client.post(
                make_request(p["request_id"], p["method"], params),
                token=tokens[p["token"]])
            category, reason = categorize(status, payload)
            rows.append({"call": p["call"], "http_status": status,
                         "status": category, "error_reason": reason})
    finally:
        server.shutdown()
        server.server_close()
    return rows, core.audit_snapshot()


def matches_recorded(replay, audit):
    with open(os.path.join(HERE, "results_deep.json"), encoding="utf-8") as f:
        recorded = json.load(f)
    want = [{"call": "D%02d" % c["seq"], "http_status": c["http_status"],
             "status": c["status"], "error_reason": c.get("error_reason")}
            for c in recorded["calls"]]
    return replay == want and audit == recorded["audit_log"]


def main():
    tmp = tempfile.mkdtemp(prefix="guard_corpus_")
    try:
        sandbox = write_fixtures(os.path.join(tmp, "sandbox"))
        core = ToolkitCore(sandbox)
        sql_rows = run_sql_cases(core)
        path_rows = run_path_cases(core, sandbox)
        plan = plan_as_data()
        replay, audit = replay_plan(plan, write_fixtures(os.path.join(tmp, "deep")))
    finally:
        shutil.rmtree(tmp)
    same = matches_recorded(replay, audit)
    guard = {
        "sql": sql_rows, "path": path_rows,
        "summary": {"sql": score(sql_rows), "path": score(path_rows),
                    "deep_replay_calls": len(replay),
                    "deep_replay_matches_results_deep": same},
        "deep_replay": replay,
        "sandbox_placeholder": SANDBOX_MARK,
    }
    for name, data in (("deep_plan.json", plan), ("results_guard.json", guard)):
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
    print("SQL guard:", guard["summary"]["sql"])
    print("Path rules:", guard["summary"]["path"])
    print("Deep plan replay matches results_deep.json:", same)
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
