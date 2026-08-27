#!/usr/bin/env python3
"""Wrapper around `technocore_agent.py say` that logs every message you post
to a permanent local ledger at the moment of posting — since Technocore's
`read` endpoint only exposes a small rolling window and cannot be used to
reconstruct history after the fact."""
import json
import subprocess
import sys
import csv
import os
import re

AGENT_SCRIPT = "/home/onlinemoney/technocore-tool/technocore_agent.py"
LEDGER_FILE = "activity_ledger.csv"
FIELDNAMES = ["room", "seq", "nonce", "timestamp", "text", "did"]

def main():
    if len(sys.argv) < 3:
        print("Usage: python log_say.py <room> \"<message text>\"")
        sys.exit(1)

    room = sys.argv[1]
    text = sys.argv[2]

    # Run the real `say` command, letting stdin/stdout pass through live
    # so the passphrase prompt still works normally.
    result = subprocess.run(
        [sys.executable, AGENT_SCRIPT, "say", room, text],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    output = result.stdout
    print(output)  # show the user exactly what the tool printed

    if result.returncode != 0:
        print("Command failed — nothing logged.")
        sys.exit(1)

    # Try to parse the JSON response embedded in the output
    match = re.search(r"\{.*\}", output, re.DOTALL)
    if not match:
        print("Could not find a JSON response to log — check manually if it posted.")
        sys.exit(1)

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        print("Could not parse JSON response — check manually if it posted.")
        sys.exit(1)

    posted = data.get("posted")
    if not posted:
        print("No 'posted' field found in response — nothing logged.")
        sys.exit(1)

    file_exists = os.path.exists(LEDGER_FILE)
    with open(LEDGER_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "room": room,
            "seq": posted["seq"],
            "nonce": posted["nonce"],
            "timestamp": posted["ts"],
            "text": posted["text"],
            "did": posted["from"],
        })
    print(f"Logged: room={room} seq={posted['seq']}")

if __name__ == "__main__":
    main()
