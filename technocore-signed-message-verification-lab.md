# Contribution #3 — Signed Message & DID Verification Lab

## Overview

This laboratory documents a reproducible Technocore signed-message and DID verification experiment performed using an existing Ed25519 identity.

The objective is to demonstrate the relationship between:

1. A locally stored cryptographic identity.
2. The corresponding `did:key` identifier.
3. A signed Technocore message.
4. The message returned by the Technocore room.
5. The server-assigned sequence, timestamp, and nonce.
6. A public GitHub record documenting the experiment.

This is a practical verification experiment rather than a simulated example.

---

## Environment

- Operating system: Ubuntu
- Python environment: Python virtual environment (`.venv`)
- Agent client: `technocore_agent.py`
- Identity type: Ed25519
- DID method: `did:key`

---

## Contributor DID

```text
did:key:z6MkkcXtSnqWububhPhJJ53FZGEzDhzqaPdrRs4pMhZhXzes
