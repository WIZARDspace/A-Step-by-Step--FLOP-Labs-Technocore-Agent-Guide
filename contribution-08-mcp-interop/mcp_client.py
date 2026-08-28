#!/usr/bin/env python3
"""Minimal MCP (Model Context Protocol) stdio client for testing the
official technocore-mcp server. Speaks raw JSON-RPC 2.0 over stdin/stdout,
newline-delimited, per the MCP stdio transport spec — no external MCP
SDK dependency, so this is transparent about exactly what's sent/received.
"""
import json
import subprocess
import sys
import threading
import queue
import time


class MCPClient:
    def __init__(self, command):
        self.proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
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

    def _next_id(self):
        self._id += 1
        return self._id

    def request(self, method, params=None, timeout=10):
        msg_id = self._next_id()
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
        raise TimeoutError(f"No response to {method} (id={msg_id}) within {timeout}s")

    def notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

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


def main():
    results = {"steps": []}

    def record(name, ok, detail):
        results["steps"].append({"step": name, "ok": ok, "detail": detail})
        print(f"[{'OK' if ok else 'FAIL'}] {name}")

    client = MCPClient(["uvx", "technocore-mcp"])
    try:
        # ---- Step 1: initialize ----
        resp = client.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "technocore-interop-test", "version": "1.0.0"},
        })
        ok = "result" in resp and "serverInfo" in resp.get("result", {})
        record("initialize", ok, resp)

        client.notify("notifications/initialized")
        time.sleep(0.3)

        # ---- Step 2: list tools ----
        resp = client.request("tools/list")
        tools = resp.get("result", {}).get("tools", [])
        record("tools/list", len(tools) > 0, {"tool_count": len(tools), "tool_names": [t.get("name") for t in tools]})

        with open("tools_list_raw.json", "w") as f:
            json.dump(resp, f, indent=2)

        # Save full tool schemas for the writeup
        tool_names = [t.get("name") for t in tools]
        print(f"\nDiscovered tools: {tool_names}\n")

        results["discovered_tools"] = tool_names
        results["tool_count"] = len(tools)

        # ---- Step 3: call a read-like tool if present ----
        read_tool = next((t for t in tool_names if "read" in t.lower() or "list_rooms" in t.lower()), None)
        if read_tool:
            # try calling with minimal/no args first to see what's required
            resp = client.request("tools/call", {"name": read_tool, "arguments": {}})
            record(f"tools/call({read_tool}, no args)", "result" in resp, resp)

        with open("mcp_interop_results.json", "w") as f:
            json.dump(results, f, indent=2)

    finally:
        stderr_out = client.stderr_output()
        if stderr_out:
            print("\n--- server stderr ---")
            print(stderr_out)
        client.close()


if __name__ == "__main__":
    main()
