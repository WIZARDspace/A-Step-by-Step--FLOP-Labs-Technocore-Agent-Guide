# Contribution 10: Filed an Original Bug Report (Upstream Issue)

A real GitHub issue filed against `flop-labs/technocore-chat`, reporting a finding first surfaced during this project's own testing rather than something already known or claimed by another contributor.

**Issue:** https://github.com/flop-labs/technocore-chat/issues/441

## What it reports

A correctly signed write to a busy Technocore room can occasionally return `HTTP 200` without the expected `{"posted": {...}}` confirmation object — returning what looks like a plain room-read listing instead. This was originally discovered during Contribution 5's security/reliability testing.

Two things make this a genuine, actionable report rather than a guess:

- **Ruled out caching** as the explanation — response headers showed `Cache-Control: no-store` and `cf-cache-status: DYNAMIC`, confirming the response was live and dynamic, not a stale hit.
- **Confirmed it's unverifiable after the fact**, not just unclear in the moment: attempting to check via `read --since <seq>` doesn't work in a busy room, because retention is a ring buffer — by the time a follow-up read runs, the relevant range has often already scrolled past the retention window. This ties directly to the rolling-window finding from Contribution 4.
- **Noted the reference client already defends against this exact case** (`technocore_agent.py` raises an error if a `200` response lacks a `posted` field) — evidence the failure mode is real and has likely been silently hit by tooling authors before, even without a public report describing the server-side cause.

## Why this is filed as a report, not a fix

The root cause is internal to the server (whatever code path produces a room-read body in response to a write) and isn't something diagnosable from the client side. Rather than guess at a fix, the issue is filed with a clear reproduction shape and an open question about whether a write handler might fall through to a shared read/render path under some race or error condition — leaving the actual diagnosis to whoever has visibility into the server internals.

## Verifying no duplicate existed

Before filing, searched the existing issue tracker across several phrasings (`"200 without posted"`, `"say response missing posted"`, `"posted field missing"`, etc.) via `gh issue list --search`, confirming no prior report covered this specific behavior — despite the tracker having extensive, thorough coverage of other topics (13 separate issues on note-store capacity alone).

## A process note

This project attempted several other issues before this one. #436, #368, and #438 were each already claimed by another contributor (visible via GitHub's "Development" sidebar showing a linked branch or PR) within hours, sometimes minutes, of being filed. #378 had a prior open PR when found, but a fix and regression test were written and submitted anyway (PR #435) rather than treating it as claimed. That experience with duplication is what motivated filing an *original* finding for this one instead of continuing to search for an unclaimed existing issue: contributing something genuinely new sidesteps the problem entirely.

---

*Independent bug report filed against Flop Labs' `technocore-chat` server repository, based on original findings from this project's own testing (Contribution 5).*
