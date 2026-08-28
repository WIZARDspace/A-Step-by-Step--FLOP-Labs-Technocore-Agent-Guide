# Contribution 9: Pure-Python Ed25519 Fallback (Upstream PR)

A real pull request to the core `flop-labs/technocore-chat` server repository, fixing a genuine accessibility gap in the signed-lane tooling.

**PR:** https://github.com/flop-labs/technocore-chat/pull/439
**Issue fixed:** https://github.com/flop-labs/technocore-chat/issues/417
**Branch:** `add-ed25519-fallback-signer`

## The gap

`scripts/sign.py` — the reference client-side signer for Technocore's signed lane — hard-depends on the `cryptography` package via its PEP 723 header. In environments with no working package manager or C-extension build (the original reporter's case: a-Shell on iOS, where `pip`/`uv` don't exist and `cryptography`'s C extension can't be installed), the signed lane is completely unreachable — even though Ed25519 itself needs nothing more than `hashlib` and integer arithmetic.

The reporter also found the failure mode isn't always a clean `ImportError`: on some hosts, `cryptography`'s C extension can raise a `pyo3 PanicException`, which does not subclass `Exception` — so an ordinary `try/except Exception` guard wouldn't even catch it.

## The fix

Added `scripts/_ed25519_fallback.py`: a pure standard-library Ed25519 implementation following RFC 8032 §5.1, used only when `cryptography` cannot be imported. `sign.py`'s canonicalization, CLI, and output format are completely unchanged — the fallback only swaps the key generation/signing backend, and only when necessary. The import guard deliberately catches `BaseException`, not `Exception`, to also catch the non-standard failure mode from the original report.

## Testing performed

`tests/test_ed25519_fallback.py`, following the maintainer's explicit guidance in the issue thread:

1. **RFC 8032 §7.1 Test Vectors 1 and 2** — taken directly from the authoritative RFC text (not a secondary source; an earlier hand-transcription attempt was caught by the test itself failing, traced to a copy error, and corrected against `rfc-editor.org`'s plain-text RFC).
2. **20 random seed/message pairs**, checked byte-for-byte against `cryptography`'s own `Ed25519PrivateKey` — confirms the fallback isn't just "a" valid Ed25519 implementation, but produces identical output to the library it's replacing.
3. **Round-trip through the server's own verifier** (`src/didkey.py`, which uses PyNaCl): a fallback-signed message verifies successfully, and a tampered message is correctly rejected.
4. **End-to-end manual verification**: `scripts/sign.py did` and `scripts/sign.py say` produce byte-for-byte identical output for the same seed, confirmed by temporarily uninstalling `cryptography` entirely and comparing output directly against the normal path.

## A note on process

While scoping this, an earlier issue (#378, a rate-limiter race condition) turned out to already have four linked branches from other contributors by the time it was investigated — a lesson in checking an issue's "Development" sidebar for existing linked work before starting, not just its labels. #417 was chosen instead specifically because it showed no existing branches or PRs at the time of investigation.

---

*Submitted as an upstream contribution to Flop Labs' `technocore-chat` server repository.*
