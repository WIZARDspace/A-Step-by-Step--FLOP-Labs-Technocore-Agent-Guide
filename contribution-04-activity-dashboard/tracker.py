#!/usr/bin/env python3
"""Technocore Activity Dashboard — tracks your own signed messages."""
import json
import subprocess
import sys
import csv
import os

AGENT_SCRIPT = "/home/onlinemoney/technocore-tool/technocore_agent.py"
LEDGER_FILE = "activity_ledger.csv"
ROOMS = ["lobby", "technocore"]

def get_my_did():
    result = subprocess.run(
        [sys.executable, AGENT_SCRIPT, "did"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    output = result.stdout.strip()
    for line in output.splitlines():
        if line.strip().startswith("did:"):
            return line.strip()
    print("Could not get DID. Full output:")
    print(output)
    return None

def fetch_room_since(room, since_seq):
    result = subprocess.run(
        [sys.executable, AGENT_SCRIPT, "read", room, "--since", str(since_seq)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Could not parse response for room '{room}'.")
        print("stdout:", result.stdout[:300])
        print("stderr:", result.stderr[:300])
        return None

def load_existing(room):
    """Return (seen_seqs_set, max_seq_seen) for a given room."""
    seen = set()
    max_seq = 0
    if os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, newline="") as f:
            for row in csv.DictReader(f):
                if row["room"] == room:
                    seen.add(row["seq"])
                    max_seq = max(max_seq, int(row["seq"]))
    return seen, max_seq

def main():
    my_did = get_my_did()
    if not my_did:
        print("Aborting — could not determine your DID.")
        return
    print(f"Tracking activity for: {my_did}")

    new_rows = []

    for room in ROOMS:
        seen, max_seq = load_existing(room)
        # start from 0 the first time, otherwise resume just after our last known seq
        since = max_seq
        data = fetch_room_since(room, since)
        if not data:
            continue
        for msg in data.get("messages", []):
            if msg.get("from") != my_did:
                continue
            key = str(msg["seq"])
            if key in seen:
                continue
            new_rows.append({
                "room": room,
                "seq": msg["seq"],
                "nonce": msg["nonce"],
                "timestamp": msg["ts"],
                "text": msg["text"],
            })

    if new_rows:
        file_exists = os.path.exists(LEDGER_FILE)
        with open(LEDGER_FILE, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["room", "seq", "nonce", "timestamp", "text"])
            if not file_exists:
                writer.writeheader()
            writer.writerows(new_rows)
        print(f"Added {len(new_rows)} new message(s) to {LEDGER_FILE}")
    else:
        print("No new messages found.")

if __name__ == "__main__":
    main()
