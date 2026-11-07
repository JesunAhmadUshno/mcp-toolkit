"""Small latency and throughput measurement of the Deep HTTP server.

Run: python level-3-deep/bench_latency.py
Starts the Deep server on an ephemeral localhost port and times real
HTTP round trips with the stdlib client: sequential calls per request
kind (median and p95 in milliseconds), then a fixed concurrent load
for throughput. Writes level-3-deep/results_latency.json.

Unlike the other results files this one is machine specific and not
deterministic: it records the platform it ran on, and numbers will
differ between machines and runs. It is not part of the CI
reproducibility check. Localhost loopback only, tiny fixtures, so it
measures framework overhead, not a deployment.
"""
import datetime
import json
import os
import platform
import shutil
import statistics
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mcp_deep import (HttpMcpClient, TokenStore, ToolkitCore,  # noqa: E402
                      make_server, write_fixtures)
from run_deep import OPERATOR_TEST_TOKEN, READER_TEST_TOKEN  # noqa: E402

N_SEQ = 300
WARMUP = 20
THREADS = 8
PER_THREAD = 100

KINDS = [
    ("read_file_allowed", "reader", "read_file", {"path": "hello.txt"}),
    ("read_file_path_traversal", "reader", "read_file", {"path": "../secret.txt"}),
    ("run_query_select", "reader", "run_query",
     {"sql": "SELECT name, score FROM items WHERE score >= 20 ORDER BY id"}),
    ("calculate_role_blocked", "reader", "calculate", {"op": "add", "a": 1, "b": 2}),
    ("unauthenticated", None, "read_file", {"path": "hello.txt"}),
]


def pct(values, q):
    s = sorted(values)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def main():
    tmp = tempfile.mkdtemp(prefix="bench_")
    sandbox = write_fixtures(os.path.join(tmp, "sandbox"))
    store = TokenStore.from_plaintext(
        {"reader": READER_TEST_TOKEN, "operator": OPERATOR_TEST_TOKEN})
    server = make_server(ToolkitCore(sandbox), store)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % server.server_address[1]
    tokens = {"reader": READER_TEST_TOKEN, None: None}
    sequential = {}
    try:
        for name, role, tool, args in KINDS:
            client = HttpMcpClient(base, tokens[role])
            times = []
            for i in range(WARMUP + N_SEQ):
                t0 = time.perf_counter()
                client.call_tool(i, tool, args)
                if i >= WARMUP:
                    times.append((time.perf_counter() - t0) * 1000)
            sequential[name] = {"calls": N_SEQ,
                                "median_ms": round(statistics.median(times), 3),
                                "p95_ms": round(pct(times, 0.95), 3)}

        def worker():
            c = HttpMcpClient(base, READER_TEST_TOKEN)
            for i in range(PER_THREAD):
                c.call_tool(i, "read_file", {"path": "hello.txt"})

        threads = [threading.Thread(target=worker) for _ in range(THREADS)]
        t0 = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        wall = time.perf_counter() - t0
    finally:
        server.shutdown()
        server.server_close()
        shutil.rmtree(tmp)
    out = {
        "measured": datetime.date.today().isoformat(),
        "machine": {"python": platform.python_version(),
                    "machine": platform.machine(), "system": platform.system(),
                    "cpu_count": os.cpu_count()},
        "note": "machine specific, localhost loopback, tiny fixtures, not the fleet node",
        "sequential": sequential,
        "concurrent": {"threads": THREADS, "calls": THREADS * PER_THREAD,
                       "tool": "read_file", "wall_s": round(wall, 3),
                       "calls_per_s": round(THREADS * PER_THREAD / wall, 1)},
    }
    with open(os.path.join(HERE, "results_latency.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
