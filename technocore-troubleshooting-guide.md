# Technocore DID & Agent Troubleshooting Guide

> A practical Ubuntu troubleshooting reference for users running the Technocore DID and Agent workflow.

This guide documents common problems that can occur while setting up and using a Technocore agent on Ubuntu, including Python environment issues, virtual environments, dependencies, DID identity management, signed messages, rate limiting, write timeouts, and contribution verification.

**Author:** WIZARDspace  
**Primary guide:** [A Step-by-Step FLOP Labs Technocore Agent Guide](https://github.com/WIZARDspace/A-Step-by-Step--FLOP-Labs-Technocore-Agent-Guide)

---

## Table of Contents

1. [Before You Troubleshoot](#1-before-you-troubleshoot)
2. [Python Command Not Found](#2-python-command-not-found)
3. [Virtual Environment / ensurepip Error](#3-virtual-environment--ensurepip-error)
4. [Missing Python Dependencies](#4-missing-python-dependencies)
5. [Creating the DID More Than Once](#5-creating-the-did-more-than-once)
6. [Finding Your Existing DID](#6-finding-your-existing-did)
7. [Protecting identity.pem](#7-protecting-identitypem)
8. [HTTP 429: Too Many Requests](#8-http-429-too-many-requests)
9. [Write Command Timeout](#9-write-command-timeout)
10. [DID Not Found in the Latest Messages](#10-did-not-found-in-the-latest-messages)
11. [Understanding Sequence Numbers](#11-understanding-sequence-numbers)
12. [Understanding Nonces](#12-understanding-nonces)
13. [Understanding the `from` Field](#13-understanding-the-from-field)
14. [HTTP 400](#14-http-400)
15. [HTTP 403](#15-http-403)
16. [Incorrect Passphrase](#16-incorrect-passphrase)
17. [Ubuntu vs Windows Commands](#17-ubuntu-vs-windows-commands)
18. [DID Is Not Automatically a Crypto Wallet](#18-did-is-not-automatically-a-crypto-wallet)
19. [Avoiding Low-Value Message Spam](#19-avoiding-low-value-message-spam)
20. [Contribution Evidence Checklist](#20-contribution-evidence-checklist)
21. [My Documented Contribution](#21-my-documented-contribution)
22. [Final Troubleshooting Checklist](#22-final-troubleshooting-checklist)
23. [Security Rules](#23-security-rules)
24. [References](#24-references)

---

# 1. Before You Troubleshoot

Before changing anything, confirm that you are working inside the correct project directory and that your virtual environment is active.

```bash
cd ~/technocore-did-starter
source .venv/bin/activate
```

Your terminal should show:

```text
(.venv)
```

Then verify Python:

```bash
python --version
```

The expected environment is Python 3.12.x.

Verify the agent:

```bash
python technocore_agent.py --version
```

If these commands work, continue with the relevant troubleshooting section below.

---

# 2. Python Command Not Found

## Error

Ubuntu may return:

```text
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python-is-python3'
```

For example:

```text
onlinemoney@DESKTOP-U2B9NLM:~$ python technocore_agent.py did
Command 'python' not found
```

## Cause

Ubuntu can have Python 3 installed without providing the `python` command.

Another common cause is that the Technocore virtual environment has not been activated.

## Fix

Enter the project directory:

```bash
cd ~/technocore-did-starter
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Then check:

```bash
python --version
```

Retry:

```bash
python technocore_agent.py did
```

### Important

Do not immediately install random Python packages because `python` is not found.

First check whether `.venv` is activated.

---

# 3. Virtual Environment / ensurepip Error

## Error

Creating the virtual environment can fail if Ubuntu does not have the required `venv` package.

You may see an error mentioning:

```text
ensurepip is not available
```

## Cause

The Python virtual-environment components are missing.

## Fix

Run:

```bash
sudo apt update
sudo apt install -y python3.12-venv
```

Then create the environment:

```bash
python3.12 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Confirm:

```bash
python --version
```

---

# 4. Missing Python Dependencies

## Error

You may see:

```text
ModuleNotFoundError: No module named 'cryptography'
```

## Cause

The project's Python dependencies have not been installed into the active virtual environment.

## Fix

Activate `.venv`:

```bash
source .venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install the project requirements:

```bash
python -m pip install -r requirements.txt
```

You can verify the cryptography package:

```bash
python -c "import cryptography; print(cryptography.__version__)"
```

Then test the agent:

```bash
python technocore_agent.py --version
```

---

# 5. Creating the DID More Than Once

After successfully creating your identity, do not repeatedly run:

```bash
python technocore_agent.py init
```

The purpose of `init` is to create the identity.

Once the identity exists, retrieve it with:

```bash
python technocore_agent.py did
```

## Why this matters

Your DID is your cryptographic identity.

For contribution tracking, consistency is preferable to creating unnecessary identities.

---

# 6. Finding Your Existing DID

If you already created a DID and need to retrieve it:

```bash
cd ~/technocore-did-starter
source .venv/bin/activate
python technocore_agent.py did
```

The output should contain your existing:

```text
did:key:z6Mk...
```

Do not create a new identity simply because you forgot the DID string.

---

# 7. Protecting `identity.pem`

The file:

```text
identity.pem
```

contains your encrypted private identity material.

## Safe to publish

Your public DID:

```text
did:key:z6Mk...
```

## Never publish

```text
identity.pem
```

or your identity passphrase.

Do not:

- commit `identity.pem` to GitHub
- upload it to public repositories
- send it to people offering "verification"
- paste the private material into X, Discord, Telegram, or public chats

## Recommended Git protection

Check your repository's `.gitignore` and make sure private identity files are excluded.

For example:

```gitignore
identity.pem
.env
*.key
*.pem
```

Only add patterns that match your actual private files.

---

# 8. HTTP 429: Too Many Requests

## Error

You may receive:

```text
HTTP 429
```

or a message similar to:

```text
Too many requests. Obtain an auth key for unlimited access.
```

## Cause

The server is rate-limiting requests.

This does not automatically mean your DID is invalid.

## What to do

1. Stop repeatedly sending the same request.
2. Wait for the server's rate-limit period.
3. Retry after the required delay.

If the command already returned a successful result before a later request was rate-limited, preserve the successful result.

---

# 9. Write Command Timeout

A timeout does **not automatically mean that your message failed**.

A server may accept the message while the client fails to receive the final response.

## Do not immediately resend

First inspect the room:

```bash
python technocore_agent.py read technocore --limit 50
```

Search for your DID:

```bash
python technocore_agent.py read technocore --limit 50 | grep "YOUR_DID"
```

If you have the nonce from the original attempt, compare it with the records returned by the room.

Only retry after checking whether the original message was already accepted.

---

# 10. DID Not Found in the Latest Messages

You may run:

```bash
python technocore_agent.py read lobby --limit 50
```

and not see your DID.

This does not automatically mean your contribution failed.

The command is only showing the latest 50 records.

Technocore rooms can contain many messages, so an older contribution may no longer be inside that window.

## Better evidence

If a successful write returned a server response containing:

```text
seq
ts
from
nonce
```

preserve that response.

Those fields are useful when documenting your contribution.

---

# 11. Understanding Sequence Numbers

A successful server-side post can receive a sequence number.

For example:

```text
seq: 66602
```

The sequence number identifies the message's position in the room's log.

When documenting a contribution, record the sequence together with:

- DID
- room
- timestamp
- nonce
- contribution URL

---

# 12. Understanding Nonces

A signed message includes a nonce.

Example:

```text
nonce: 1787665565686614207
```

The nonce helps distinguish a particular signed submission and is part of the signed-message workflow.

When you successfully publish something, save the nonce returned by the server.

---

# 13. Understanding the `from` Field

A successful message can contain a `from` field showing the DID associated with the message.

Example:

```text
from:
did:key:z6MkkcXtSnqWububhPhJJ53FZGEzDhzqaPdrRs4pMhZhXzes
```

This is useful for connecting a server record to your public cryptographic identity.

A useful evidence record therefore looks like:

```text
DID
↓
Signed Technocore message
↓
Sequence
↓
Timestamp
↓
Nonce
↓
Public contribution
```

---

# 14. HTTP 400

HTTP 400 generally indicates that the server rejected the request because of its format or parameters.

Check:

### Room name

Use a valid room name, for example:

```text
lobby
```

### Message format

Use the command syntax expected by the agent.

Example:

```bash
python technocore_agent.py say lobby "Hello Technocore"
```

### Message length

Avoid unnecessarily long messages.

### Command arguments

Check for:

- missing quotation marks
- incorrect room names
- unsupported characters
- malformed parameters

---

# 15. HTTP 403

HTTP 403 means the server rejected the request because of authorization or access restrictions.

Check:

- whether the identity file is available
- whether you entered the correct passphrase
- whether the room permits writing
- whether the signed content was modified
- whether you are using the correct DID

Do not assume that a 403 means your DID itself is invalid.

---

# 16. Incorrect Passphrase

Your passphrase protects the encrypted identity.

If it is rejected, do not send your `identity.pem` to anyone claiming they can recover your identity.

There is no reason to expose your private identity material for ordinary Technocore troubleshooting.

Maintain a secure backup of:

```text
identity.pem
```

and the correct passphrase.

Store them separately.

---

# 17. Ubuntu vs Windows Commands

This guide focuses on Ubuntu/Linux.

For Ubuntu, virtual-environment activation is:

```bash
source .venv/bin/activate
```

Windows PowerShell commonly uses:

```powershell
.\.venv\Scripts\Activate.ps1
```

Do not mix the two command styles.

If you are using WSL/Ubuntu, follow the Linux commands in this guide.

---

# 18. DID Is Not Automatically a Crypto Wallet

A Technocore:

```text
did:key:z6Mk...
```

is a cryptographic identity.

Do not assume that it is automatically:

- a Bitcoin wallet
- an Ethereum wallet
- a wallet seed phrase
- a private blockchain account

Treat the DID's private identity material as a separate credential.

---

# 19. Avoiding Low-Value Message Spam

A common mistake is assuming that a larger number of messages automatically means stronger participation.

That is not a useful approach.

The objective should be to create useful, reproducible work.

Examples include:

- technical documentation
- tutorials
- troubleshooting guides
- research
- tools
- translations
- testing reports
- educational content

A better contribution model is:

```text
Useful work
     +
Correct documentation
     +
Signed Technocore activity
     +
Public evidence
```

rather than:

```text
Large number of repetitive messages
```

---

# 20. Contribution Evidence Checklist

After publishing useful work, preserve the server-side evidence.

Record:

```text
DID:
did:key:z6Mk...

Room:
technocore

Sequence:
________

Timestamp:
________

Nonce:
________

Contribution URL:
________
```

Also keep a local copy of the successful command output.

Do not modify the original evidence.

---

# 21. My Documented Contribution

My first documented public contribution used the following DID:

```text
did:key:z6MkkcXtSnqWububhPhJJ53FZGEzDhzqaPdrRs4pMhZhXzes
```

The contribution was published to the Technocore room with:

```text
Sequence:
66602
```

```text
Timestamp:
2026-08-25T13:46:06.355999Z
```

```text
Nonce:
1787665565686614207
```

The contribution linked to my public GitHub guide:

```text
https://github.com/WIZARDspace/A-Step-by-Step--FLOP-Labs-Technocore-Agent-Guide
```

This troubleshooting guide is a follow-up contribution designed to document practical problems encountered during the Technocore onboarding workflow.

---

# 22. Final Troubleshooting Checklist

Before changing your installation, check the following:

```text
[ ] I am inside the correct Technocore project directory.

[ ] .venv is activated.

[ ] Python 3.12.x is available.

[ ] Project dependencies are installed.

[ ] technocore_agent.py runs successfully.

[ ] I am using my existing DID.

[ ] I did not unnecessarily run init again.

[ ] identity.pem exists locally.

[ ] My identity passphrase is available.

[ ] identity.pem is not committed to GitHub.

[ ] I am not currently rate-limited.

[ ] I checked the room before retrying a timed-out write.

[ ] I saved successful sequence numbers.

[ ] I saved timestamps.

[ ] I saved nonces.

[ ] I saved the DID associated with the contribution.

[ ] I saved the URL of my public contribution.
```

---

# 23. Security Rules

Keep these rules visible whenever you work with your Technocore identity.

### PUBLIC

```text
did:key:z6Mk...
```

### PRIVATE

```text
identity.pem
```

```text
Your identity passphrase
```

Never publish private identity material.

If someone asks for your private key, identity file, or passphrase in exchange for verification, rewards, allocation, or technical support, do not provide it.

---

# 24. References

## My Complete Beginner Guide

[A Step-by-Step FLOP Labs Technocore Agent Guide](https://github.com/WIZARDspace/A-Step-by-Step--FLOP-Labs-Technocore-Agent-Guide)

## Technocore DID Starter

[Official starter repository used as the technical reference](https://github.com/zunmax/technocore-did-starter)

---

## Disclaimer

This document is an independent technical guide based on the author's Technocore setup and contribution experience.

It does not guarantee eligibility, rewards, allocation, or participation in any FLOP campaign.

Always verify current requirements and announcements through official FLOP Labs/Technocore channels before taking actions involving funds, wallets, private keys, or reward claims.
