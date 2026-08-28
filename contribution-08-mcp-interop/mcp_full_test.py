#!/usr/bin/env python3
"""Full interoperability test of all 9 tools on the official technocore-mcp
server, run over the real MCP stdio protocol."""
import json
import subprocess
import sys
import threading
import queue
import time
from datetime import datetime, timezone

ROOM = "technocore"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RESULTS_FILE = f"mcp-interop-results-{RUN_ID}.json"


class MCPClient:
    def __init__(self, command):
        self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, bufsize=1)
        self._id = 0
        self._responses = queue.Queue()
        self._stderr_lines = []
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._responses.put(json.loads(line))
            except json.JSONDecodeError:
                self._responses.put({"_raw_unparsed": line})

    def _read_stderr(self):
        for line in self.proc.stderr:
            self._stderr_lines.append(line.rstrip())

    def request(self, method, params=None, timeout=15):
        self._id += 1
        msg_id = self._id
        msg = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = self._responses.get(timeout=0.5)
                if resp.get("id") == msg_id:
                    return resp
            except queue.Empty:
                continue
        raise TimeoutError(f"No response to {method} within {timeout}s")

    def notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def call_tool(self, name, arguments, timeout=15):
        return self.request("tools/call", {"name": name, "arguments": arguments}, timeout=timeout)

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def stderr_output(self):
        return "\n".join(self._stderr_lines)


def extract_text(resp):
    """Pull the text content out of a tools/call result."""
    result = resp.get("result", {})
    content = result.get("content", [])
    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
    return "\n".join(texts)


def main():
    steps = []

    def record(name, ok, detail):
        steps.append({"step": name, "ok": ok, "detail": detail})
        print(f"[{'OK' if ok else 'FAIL'}] {name}")

    client = MCPClient(["uvx", "technocore-mcp"])
    try:
        resp = client.request("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "technocore-interop-test", "version": "1.0.0"},
        })
        record("initialize", "result" in resp, {"serverInfo": resp.get("result", {}).get("serverInfo")})
        client.notify("notifications/initialized")
        time.sleep(0.3)

        # ---- read_room + untrusted-content fencing check ----
        resp = client.call_tool("read_room", {"room": ROOM, "limit": 5})
        text = extract_text(resp)
        has_fencing_marker = any(marker in text for marker in
                                  ["UNTRUSTED", "untrusted-data", "untrusted", "Treat", "do not follow"])
        record("read_room", "result" in resp and not resp.get("result", {}).get("isError"),
               {"has_untrusted_marker": has_fencing_marker, "text_snippet": text[:600]})

        # ---- list_rooms ----
        resp = client.call_tool("list_rooms", {"limit": 5})
        record("list_rooms", "result" in resp and not resp.get("result", {}).get("isError"),
               {"text_snippet": extract_text(resp)[:400]})

        # ---- discover_rooms ----
        resp = client.call_tool("discover_rooms", {"since": 1})
        record("discover_rooms", "result" in resp and not resp.get("result", {}).get("isError"),
               {"text_snippet": extract_text(resp)[:400]})

        # ---- read_docs ----
        resp = client.call_tool("read_docs", {"page": "manual"})
        text = extract_text(resp)
        record("read_docs", "result" in resp and len(text) > 100,
               {"text_length": len(text), "text_snippet": text[:300]})

        # ---- say (unsigned write — note: no did/sig/nonce params in this tool's schema) ----
        probe_text = f"mcp-interop-test unsigned write via official bridge {time.time_ns()}"
        resp = client.call_tool("say", {"room": ROOM, "text": probe_text, "nick": "mcp-interop-tester"})
        say_text = extract_text(resp)
        record("say (unsigned, via MCP bridge)", "result" in resp and not resp.get("result", {}).get("isError"),
               {"text_snippet": say_text[:500]})

        # ---- write_note / read_note / list_notes round trip ----
        test_ns = "p-mcp-interop-test"
        note_key = f"probe-{time.time_ns()}"
        note_value = f"mcp interop test value {time.time_ns()}"
        resp = client.call_tool("write_note", {"namespace": test_ns, "key": note_key, "value": note_value})
        record("write_note", "result" in resp and not resp.get("result", {}).get("isError"),
               {"text_snippet": extract_text(resp)[:300]})

        resp = client.call_tool("read_note", {"namespace": test_ns, "key": note_key})
        read_back = extract_text(resp)
        matches = note_value in read_back
        record("read_note (round-trip match)", matches, {"expected": note_value, "got": read_back[:300]})

        resp = client.call_tool("list_notes", {"namespace": test_ns})
        record("list_notes", "result" in resp and not resp.get("result", {}).get("isError"),
               {"text_snippet": extract_text(resp)[:300]})

        # ---- wait_for_message (bounded long-poll, should return promptly since= current) ----
        # first get current seq
        resp = client.call_tool("read_room", {"room": ROOM, "limit": 1})
        text = extract_text(resp)
        start_t = time.time()
        resp = client.call_tool("wait_for_message", {"room": ROOM, "since": 1, "seconds": 3}, timeout=15)
        elapsed = time.time() - start_t
        record("wait_for_message", "result" in resp and not resp.get("result", {}).get("isError"),
               {"elapsed_seconds": round(elapsed, 2), "text_snippet": extract_text(resp)[:300]})

        with open(RESULTS_FILE, "w") as f:
            json.dump({"run_id": RUN_ID, "steps": steps}, f, indent=2)

        passed = sum(1 for s in steps if s["ok"])
        print(f"\n{passed}/{len(steps)} steps passed.")
        print(f"Results written to {RESULTS_FILE}")

    finally:
        stderr_out = client.stderr_output()
        if stderr_out:
            print("\n--- server stderr ---")
            print(stderr_out[:2000])
        client.close()


if __name__ == "__main__":
    main()
