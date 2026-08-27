#!/usr/bin/env python3
"""Technocore Reliability / HTTP Benchmark.

Measures real latency and success-rate characteristics of the Technocore
API: sequential read latency, concurrent read latency under load, and
sequential write latency. Read tests are side-effect free and run at
volume; write tests are deliberately modest to limit public room impact.
"""
import base64
import concurrent.futures
import csv
import getpass
import json
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization

BASE_URL = "https://technocore.chat"
AGENT_SCRIPT = "/home/onlinemoney/technocore-tool/technocore_agent.py"
IDENTITY_PATH = "identity.pem"
ROOM = "technocore"

READ_SEQUENTIAL_SAMPLES = 100
READ_CONCURRENT_SAMPLES = 50
READ_CONCURRENT_WORKERS = 20
WRITE_SAMPLES = 20
WRITE_SPACING_SECONDS = 1.0   # 20 writes over ~20s stays far under 300/min

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RAW_CSV = f"benchmark-raw-{RUN_ID}.csv"
SUMMARY_JSON = f"benchmark-summary-{RUN_ID}.json"

raw_records = []


def log_record(kind, status, latency_ms, note=""):
    raw_records.append({
        "kind": kind,
        "ts": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "latency_ms": round(latency_ms, 2),
        "note": note,
    })


def timed_get(url, headers=None):
    req = urllib.request.Request(url, method="GET", headers=headers or {"Accept": "application/json"})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        e.read()
        status = e.code
    except urllib.error.URLError:
        status = None
    latency_ms = (time.monotonic() - start) * 1000
    return status, latency_ms


def percentiles(values):
    if not values:
        return {"p50": None, "p90": None, "p99": None, "mean": None, "min": None, "max": None}
    s = sorted(values)
    def pct(p):
        idx = min(len(s) - 1, int(len(s) * p))
        return round(s[idx], 2)
    return {
        "p50": pct(0.50), "p90": pct(0.90), "p99": pct(0.99),
        "mean": round(statistics.mean(s), 2), "min": round(min(s), 2), "max": round(max(s), 2),
    }


def get_my_did():
    result = subprocess.run([sys.executable, AGENT_SCRIPT, "did"],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in result.stdout.splitlines():
        if line.strip().startswith("did:"):
            return line.strip()
    raise RuntimeError(f"Could not determine DID:\n{result.stdout}")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def sign_payload(private_key, room, nonce, text) -> bytes:
    return private_key.sign(f"{room}|{nonce}|{text}".encode())


def timed_signed_write(private_key, did, room, text):
    nonce = time.time_ns()
    sig = b64url(sign_payload(private_key, room, nonce, text))
    body = json.dumps({"did": did, "sig": sig, "nonce": nonce, "text": text}).encode()
    req = urllib.request.Request(f"{BASE_URL}/r/{room}?format=json", data=body, method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json; charset=utf-8"})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body_out = resp.read().decode()
            status = resp.status
    except urllib.error.HTTPError as e:
        body_out = e.read().decode()
        status = e.code
    except urllib.error.URLError:
        body_out, status = "", None
    latency_ms = (time.monotonic() - start) * 1000
    has_posted = False
    try:
        parsed = json.loads(body_out)
        has_posted = isinstance(parsed, dict) and isinstance(parsed.get("posted"), dict)
    except json.JSONDecodeError:
        pass
    return status, latency_ms, has_posted


def main():
    print("Technocore Reliability / HTTP Benchmark")
    print(f"Room: {ROOM}")
    print(f"Raw output: {RAW_CSV}")
    print(f"Summary output: {SUMMARY_JSON}\n")

    # ---- Phase 1: sequential read latency ----
    print(f"Phase 1: {READ_SEQUENTIAL_SAMPLES} sequential reads...")
    seq_read_latencies = []
    seq_read_statuses = {}
    url = f"{BASE_URL}/r/{ROOM}?format=json&limit=1"
    for i in range(READ_SEQUENTIAL_SAMPLES):
        status, latency_ms = timed_get(url)
        log_record("read_sequential", status, latency_ms)
        seq_read_statuses[status] = seq_read_statuses.get(status, 0) + 1
        if status == 200:
            seq_read_latencies.append(latency_ms)
    print(f"  done. status breakdown: {seq_read_statuses}")

    # ---- Phase 2: concurrent read latency ----
    print(f"Phase 2: {READ_CONCURRENT_SAMPLES} concurrent reads ({READ_CONCURRENT_WORKERS} workers)...")
    conc_read_latencies = []
    conc_read_statuses = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=READ_CONCURRENT_WORKERS) as ex:
        futures = [ex.submit(timed_get, url) for _ in range(READ_CONCURRENT_SAMPLES)]
        for fut in concurrent.futures.as_completed(futures):
            status, latency_ms = fut.result()
            log_record("read_concurrent", status, latency_ms)
            conc_read_statuses[status] = conc_read_statuses.get(status, 0) + 1
            if status == 200:
                conc_read_latencies.append(latency_ms)
    print(f"  done. status breakdown: {conc_read_statuses}")

    # ---- Phase 3: sequential write latency ----
    print(f"Phase 3: {WRITE_SAMPLES} sequential writes (spaced {WRITE_SPACING_SECONDS}s apart)...")
    passphrase = getpass.getpass(f"Passphrase for {IDENTITY_PATH}: ")
    with open(IDENTITY_PATH, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=passphrase.encode())
    did = get_my_did()

    write_latencies = []
    write_statuses = {}
    ambiguous_count = 0
    for i in range(WRITE_SAMPLES):
        text = f"sec-bench write latency sample {i} {time.time_ns()}"
        status, latency_ms, has_posted = timed_signed_write(private_key, did, ROOM, text)
        note = "posted-confirmed" if has_posted else ("ambiguous-200" if status == 200 else "")
        log_record("write_sequential", status, latency_ms, note)
        write_statuses[status] = write_statuses.get(status, 0) + 1
        if status == 200:
            write_latencies.append(latency_ms)
            if not has_posted:
                ambiguous_count += 1
        time.sleep(WRITE_SPACING_SECONDS)
    print(f"  done. status breakdown: {write_statuses}, ambiguous 200s: {ambiguous_count}")

    # ---- Write raw CSV ----
    with open(RAW_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["kind", "ts", "status", "latency_ms", "note"])
        writer.writeheader()
        writer.writerows(raw_records)

    # ---- Summary ----
    summary = {
        "run_id": RUN_ID,
        "room": ROOM,
        "read_sequential": {
            "samples": READ_SEQUENTIAL_SAMPLES,
            "status_breakdown": seq_read_statuses,
            "latency_ms": percentiles(seq_read_latencies),
        },
        "read_concurrent": {
            "samples": READ_CONCURRENT_SAMPLES,
            "workers": READ_CONCURRENT_WORKERS,
            "status_breakdown": conc_read_statuses,
            "latency_ms": percentiles(conc_read_latencies),
        },
        "write_sequential": {
            "samples": WRITE_SAMPLES,
            "status_breakdown": write_statuses,
            "ambiguous_200_count": ambiguous_count,
            "latency_ms": percentiles(write_latencies),
        },
    }
    with open(SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"\nRaw data: {RAW_CSV}")
    print(f"Summary: {SUMMARY_JSON}")


if __name__ == "__main__":
    main()
