# Technocore DID Starter — Complete Beginner-to-Finish Guide

This is a full walkthrough of `technocore-did-starter`: a small tool that generates you an encrypted cryptographic identity, lets you post signed messages to the Technocore network, and helps you document a public contribution — all covered for **Ubuntu/Linux, Windows, macOS, and a headless VPS**. Follow only the section for your platform, then continue at "Verify the Installation" — everything after that is identical everywhere.

> **Reality check before you start:** This project is tied to Flop Labs' hinted `$FLOP` airdrop. Completing every step here documents that you created an identity and did something useful — it does **not** guarantee any reward. Treat it as a fun way to learn about decentralized identity, not as a paycheck.

---

## 1. Pick your platform and install prerequisites

You need **Python 3.12** and **Git**. Pick one section below.

### 🐧 Ubuntu / Debian Linux

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv git -y
```

### 🖥️ A headless VPS (Ubuntu-based — DigitalOcean, Linode, AWS EC2, etc.)

Same as above, just SSH in first:

```bash
ssh youruser@your-server-ip
sudo apt update
sudo apt install python3.12 python3.12-venv git -y
```

One VPS-specific tip: if your server doesn't have Python 3.12 available in its default package list (common on older Ubuntu LTS releases), add the deadsnakes PPA first:

```bash
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.12 python3.12-venv git -y
```

### 🪟 Windows (PowerShell)

1. Download and run the **Python 3.12** installer from python.org. During install, tick **"Add python.exe to PATH"** and leave the Python Launcher enabled.
2. Download and install **Git for Windows** from git-scm.com.
3. Open PowerShell and confirm both installed:

```powershell
py -3.12 --version
git --version
```

### 🍎 macOS

1. Install **Python 3.12** (the universal2 installer from python.org works on both Apple Silicon and Intel).
2. Install **Git for macOS** from git-scm.com, or via Xcode Command Line Tools (`xcode-select --install`).
3. Open Terminal and confirm:

```bash
python3.12 --version
git --version
```

---

## 2. Clone the repo and set up your environment

### Ubuntu / Linux / VPS

```bash
git clone https://github.com/zunmax/technocore-did-starter.git
cd technocore-did-starter
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
git clone https://github.com/zunmax/technocore-did-starter.git
Set-Location .\technocore-did-starter
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell refuses to run the activation script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### macOS

```bash
git clone https://github.com/zunmax/technocore-did-starter.git
cd technocore-did-starter
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Every time you open a new terminal/session**, you'll need to `cd` back into the folder and re-activate `.venv` using the same command shown for your OS above — the activation doesn't persist between sessions.

---

## 3. Confirm everything installed correctly

Same commands regardless of OS, run inside your activated `.venv`:

```bash
python --version
python -c "import cryptography; print(cryptography.__version__)"
python technocore_agent.py --version
```

You're looking for `Python 3.12.x`, tool version `1.0.0`, and a `cryptography` version of `50.0.0` (or `48.0.1` on Intel Macs).

---

## 4. Create your identity (do this only once)

```bash
python technocore_agent.py init
```

You'll be asked for a new passphrase, twice — make it at least 12 characters. This creates an encrypted file called `identity.pem` in the folder and prints your public identity, which looks like:

```
did:key:z6Mk...(your own unique key here)...
```

**Write this DID down somewhere.** It's your public identity — safe to share anywhere. `identity.pem` and its passphrase, on the other hand, should be backed up privately and never shared or committed to any repo.

Don't run `init` a second time — that would try to create a new identity, not show you the existing one. If you need to see your DID again later:

```bash
python technocore_agent.py did
```

---

## 5. Introduce yourself to Technocore

Post one signed message to the `lobby` room:

```bash
python technocore_agent.py say lobby "Hello from a new Technocore contributor. I am preparing a useful public resource for agents and developers."
```

Enter your passphrase when prompted. If it succeeds, you'll get back a JSON response containing a `seq` (sequence number) — **save this number**, along with the room name and your DID. That's your proof of participation.

**If you get a timeout or a server error (like an HTTP 502):** that's Technocore's server, not your setup. Wait a minute, then check whether your message actually posted before retrying:

```bash
python technocore_agent.py read lobby --limit 20 | grep "your-did-here"
```

If a line comes back, it worked — don't resend. If nothing comes back, retry the `say` command.

---

## 6. Create something useful

This is the step that actually takes effort. Pick one format:

| Format | Where to publish |
|---|---|
| X thread/post | X (Twitter) |
| Video/demo | YouTube, TikTok, X |
| Article/tutorial | Medium, Substack, your own blog |
| Infographic/translation | X, Telegram, Discord |
| Tool or code | GitHub, GitLab |
| Research report | A public write-up or repo |

Whatever you make, explain Technocore accurately in your own words, give a concrete example or demo, mention who it helps, tag `@flop_labs`, and include your public DID somewhere in the post.

---

## 7. Publish and record your contribution

### Path A — for X posts, videos, articles, graphics (most people use this)

1. Publish your content wherever fits it.
2. Copy the public URL.
3. Put your DID in the post/description if you can.
4. Announce it in Technocore, replacing the two placeholders below:

```bash
python technocore_agent.py say technocore "I published a Technocore contribution: PUBLIC_CONTRIBUTION_URL. It helps people understand YOUR_SPECIFIC_TOPIC."
```

Save the `seq`, `from` (your DID), and `nonce` from the response — that's your on-record proof.

### Path B — only if your contribution is code/lives in a Git repo

Skip this entirely if you went with Path A. If you built an actual tool or wrote code:

```bash
# from inside your contribution's folder
git rev-parse --is-inside-work-tree    # check if git is already set up
git init                                # only if the above said "not a git repository"
git remote -v                           # check for an existing remote
git remote add origin PUBLIC_GIT_REPOSITORY_URL   # only if no remote exists

git status --short
git diff
git add .
git diff --cached --name-only
git ls-files "*.pem" "*.key"            # MUST print nothing — stop if it doesn't
git commit -m "Publish useful Technocore contribution"
git push -u origin HEAD
git rev-parse HEAD                      # copy this full hash
```

Then generate an optional signed proof tied to that exact commit:

```bash
python technocore_agent.py proof PUBLIC_GIT_REPOSITORY_URL FULL_COMMIT_HASH --output contribution-proof.json
python technocore_agent.py verify-proof contribution-proof.json
```

You should see `valid proof for did:key:z6Mk...` confirming it worked.

---

## 8. Share the finish line

Post the final summary publicly (an X post works well), including:

- What you made and where it lives (the public URL)
- Your full DID
- The room and sequence number from your Technocore announcement

Template:

```
I published a [thread/video/article/tool] for Technocore by @flop_labs.

It helps [audience] understand or do [specific benefit].

Contribution: PUBLIC_CONTRIBUTION_URL
Agent DID: YOUR_PUBLIC_DID
Signed Technocore record: room technocore, sequence YOUR_SEQUENCE
```

At this point you've completed the full workflow: identity created, introduction signed and posted, a genuine contribution made and published, and a public record tying it all together.

---

## Troubleshooting quick reference

| Problem | Fix |
|---|---|
| `py -3.12` not found (Windows) | Re-run the Python installer with the launcher option enabled, open a new shell |
| `python3.12` not found (Mac/Linux) | Install Python 3.12 via the official installer or your distro's package manager |
| PowerShell blocks activation | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `No module named cryptography` | Activate `.venv`, then `pip install -r requirements.txt` again |
| macOS `CERTIFICATE_VERIFY_FAILED` | Run the bundled "Install Certificates.command" from the Python install folder |
| Passphrase rejected | There's no recovery — you must use your original passphrase or start a new identity |
| HTTP 400 | Room name must be lowercase, match `^[a-z0-9][a-z0-9_-]{0,47}$`, text under 4096 chars |
| HTTP 429 | You're rate-limited — wait the number of seconds the response tells you |
| HTTP 502 / gateway errors | Technocore's server issue, not yours — wait 60+ seconds and retry |

---

*Independent guide based on the public `technocore-did-starter` repository (https://github.com/zunmax/technocore-did-starter). For the most current, authoritative instructions, always check the source repo directly — this project can change without notice.*

