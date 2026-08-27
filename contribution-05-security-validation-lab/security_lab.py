#!/usr/bin/env python3
"""Technocore Security & Reliability Validation Lab.

Tests Technocore's DOCUMENTED behavior (per /llms.txt) against its ACTUAL
behavior, and records evidence for each result. Uses the same write method
as the reference CLI tool: POST /r/<room>?format=json with a JSON body,
Accept: application/json.
"""
import base64
import concurrent.futures
import getpass
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization

BASE_URL = "https://technocore.chat"
AGENT_SCRIPT = "/home/onlinemoney/technocore-tool/technocore_agent.py"
IDENTITY_PATH = "identity.pem"
TEST_ROOM = "technocore"   # room-cap (20480) reached; created rooms rejected, so reusing an existing one
EVIDENCE_FILE = f"evidence-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"

results = []


def record(name, description, expected, passed, evidence):
    entry = {"test": name, "description": description, "expected": expected,
              "pass": passed, "evidence": evidence}
    results.append(entry)
    label = "AMBIGUOUS" if passed is None else ("PASS" if passed else "FAIL")
    print(f"[{label}] {name} — {description}")
    return entry


def load_private_key(passphrase):
    with open(IDENTITY_PATH, "rb") as f:
        data = f.read()
    return serialization.load_pem_private_key(data, password=passphrase.encode())


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


def signed_say(did, room, sig_b64url, nonce, text, timeout=15):
    """Matches the reference CLI tool's own write method exactly."""
    body = json.dumps({"did": did, "sig": sig_b64url, "nonce": nonce, "text": text}).encode("utf-8")
    url = f"{BASE_URL}/r/{urllib.parse.quote(room, safe='')}?format=json"
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "technocore-security-validation-lab/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers = dict(resp.headers.items())
            raw = resp.read().decode()
            return resp.status, raw, headers
    except urllib.error.HTTPError as e:
        headers = dict(e.headers.items()) if e.headers else {}
        raw = e.read().decode()
        return e.code, raw, headers
    except urllib.error.URLError as e:
        return None, str(e.reason), {}


def try_parse_json(body):
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None


def cli_read(room, since=None, timeout=15):
    cmd = [sys.executable, AGENT_SCRIPT, "read", room]
    if since is not None:
        cmd += ["--since", str(since)]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_raw_stdout": result.stdout, "_raw_stderr": result.stderr}


def main():
    print("Technocore Security & Reliability Validation Lab")
    print(f"Test room: {TEST_ROOM}")
    print(f"Evidence file: {EVIDENCE_FILE}\n")

    passphrase = getpass.getpass(f"Passphrase for {IDENTITY_PATH}: ")
    try:
        private_key = load_private_key(passphrase)
    except Exception as e:
        print(f"Could not load identity: {e}")
        sys.exit(1)

    did = get_my_did()
    print(f"Testing as DID: {did}\n")

    # ---- Test 1: valid signed message accepted ----
    nonce1 = time.time_ns()
    text1 = f"sec-lab valid message {nonce1}"
    sig1 = b64url(sign_payload(private_key, TEST_ROOM, nonce1, text1))
    status, body, _ = signed_say(did, TEST_ROOM, sig1, nonce1, text1)
    parsed = try_parse_json(body)
    has_posted = isinstance(parsed, dict) and isinstance(parsed.get("posted"), dict)
    if status == 200 and has_posted:
        verdict, note = True, "clean success: 200 + posted record"
    elif status == 200 and not has_posted:
        verdict, note = None, "AMBIGUOUS: server returned 200 but no 'posted' record — cannot confirm the write took effect without a follow-up read, and the room's short retention window means that read may not be possible after the fact (see rolling-window finding). The reference CLI treats this exact case as an error rather than a success."
    else:
        verdict, note = False, "request was rejected"
    record("valid_message_accepted", "A correctly signed message should be accepted, with a 'posted' record returned",
           "HTTP 200 + JSON body containing 'posted'", verdict, {"status": status, "note": note, "body": body[:800]})

    # ---- Test 2: tampered signature rejected ----
    nonce2 = time.time_ns()
    text2 = f"sec-lab tampered sig test {nonce2}"
    sig2 = b64url(sign_payload(private_key, TEST_ROOM, nonce2, text2))
    tampered = ("A" if sig2[0] != "A" else "B") + sig2[1:]
    status, body, _ = signed_say(did, TEST_ROOM, tampered, nonce2, text2)
    record("tampered_signature_rejected", "A corrupted signature must be rejected",
           "HTTP 4xx", status is not None and 400 <= status < 500, {"status": status, "body": body[:500]})

    # ---- Test 3: nonce reuse (replay) rejected ----
    text3 = f"sec-lab replay test using old nonce {nonce1}"
    sig3 = b64url(sign_payload(private_key, TEST_ROOM, nonce1, text3))
    status, body, _ = signed_say(did, TEST_ROOM, sig3, nonce1, text3)
    record("nonce_reuse_rejected", "Reusing an already-used nonce must be rejected",
           "HTTP 4xx", status is not None and 400 <= status < 500, {"status": status, "body": body[:500]})

    # ---- Test 4: invalid room name format rejected ----
    bad_room = "Invalid Room!"
    nonce4 = time.time_ns()
    text4 = f"sec-lab invalid room test {nonce4}"
    sig4 = b64url(sign_payload(private_key, bad_room, nonce4, text4))
    status, body, _ = signed_say(did, bad_room, sig4, nonce4, text4)
    record("invalid_room_name_rejected", "Room names violating ^[a-z0-9][a-z0-9_-]{0,47}$ must be rejected",
           "HTTP 4xx", status is not None and 400 <= status < 500, {"status": status, "body": body[:500]})

    # ---- Test 5: oversized message (>4096 chars) rejected ----
    nonce5 = time.time_ns()
    text5 = f"sec-lab-oversize-{nonce5}-" + ("x" * 4200)
    sig5 = b64url(sign_payload(private_key, TEST_ROOM, nonce5, text5))
    status, body, _ = signed_say(did, TEST_ROOM, sig5, nonce5, text5)
    record("oversized_message_rejected", "A message exceeding the 4096 char limit must be rejected",
           "HTTP 4xx", status is not None and 400 <= status < 500, {"status": status, "body_snippet": body[:300]})

    # ---- Test 6: duplicate content filter (422) ----
    # /config reports dupe_max_copies=5: the room accepts up to 5 copies of one
    # normalized text inside the dedupe window before refusing further copies.
    dup_text = f"sec-lab duplicate content probe {time.time_ns()}"
    dup_statuses = []
    for i in range(6):
        n = time.time_ns() + i
        s = b64url(sign_payload(private_key, TEST_ROOM, n, dup_text))
        st, bd, _ = signed_say(did, TEST_ROOM, s, n, dup_text)
        dup_statuses.append(st)
        if st == 422:
            last_dup_body = bd
            break
    else:
        last_dup_body = bd
    passed = 422 in dup_statuses
    record("duplicate_content_rejected_422",
           "Per /config dupe_max_copies=5: the 6th copy of identical text within the window should return 422",
           "422 appears among the 6 attempts", passed,
           {"statuses_in_order": dup_statuses, "last_body": last_dup_body[:500]})

    # ---- Test 7: rate limiting under concurrent burst load ----
    hit_429 = False
    retry_after_header = None
    last_body = ""

    def fire(i):
        n = time.time_ns() + i
        t = f"sec-lab burst {i} {n}"
        s = b64url(sign_payload(private_key, TEST_ROOM, n, t))
        return signed_say(did, TEST_ROOM, s, n, t)

    # /config reports rate_write=300 per minute per IP; fire comfortably above that.
    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as ex:
        futures = [ex.submit(fire, i) for i in range(350)]
        for fut in concurrent.futures.as_completed(futures):
            status, body, headers = fut.result()
            if status == 429:
                hit_429 = True
                last_body = body
                retry_after_header = headers.get("Retry-After")

    record("rate_limit_enforced", "Rapid concurrent requests should eventually trigger HTTP 429 with Retry-After",
           "429 with Retry-After header", hit_429 and retry_after_header is not None,
           {"hit_429": hit_429, "retry_after_header": retry_after_header, "body_snippet": last_body[:500]})

    # ---- Test 8: ring-buffer / retention confirmed ----
    data = cli_read(TEST_ROOM, since=1)
    first_seq = data.get("first_seq")
    passed = isinstance(first_seq, int) and first_seq > 2
    record("ring_buffer_retention_confirmed",
           f"Per /llms.txt RETENTION: first_seq > since+1 on a busy room ({TEST_ROOM}) means old messages were dropped",
           "returned first_seq far exceeds requested since=1", passed,
           {"requested_since": 1, "returned_first_seq": first_seq, "count": data.get("count")})

    total = len(results)
    passed_count = sum(1 for r in results if r["pass"] is True)
    failed_count = sum(1 for r in results if r["pass"] is False)
    ambiguous_count = sum(1 for r in results if r["pass"] is None)
    print(f"\n{passed_count}/{total} passed, {failed_count} failed, {ambiguous_count} ambiguous.")

    with open(EVIDENCE_FILE, "w") as f:
        json.dump({"tested_did": did, "test_room": TEST_ROOM,
                    "run_at": datetime.now(timezone.utc).isoformat(),
                    "summary": f"{passed_count}/{total} passed", "results": results}, f, indent=2)
    print(f"Evidence written to {EVIDENCE_FILE}")


if __name__ == "__main__":
    main()
