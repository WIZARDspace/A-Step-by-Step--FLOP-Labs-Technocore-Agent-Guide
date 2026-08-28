# Contribution 7: Security-Focused Pull Request

An actual pull request submitted to the upstream `technocore-did-starter` repository, fixing a real gap in identity-file permission handling.

**PR:** https://github.com/zunmax/technocore-did-starter/pull/15
**Branch:** `add-identity-permission-check`

## The gap

`create_identity()` correctly sets `0o600` (owner read/write only) when generating a new `identity.pem`. But `load_identity()` never checked permissions on an *existing* file before reading and decrypting it. A key that gets copied between machines, synced through cloud storage, or restored from a backup can silently end up group- or world-readable — exposing the encrypted private key to other users on a shared system, with no warning from the tool.

This is directly informed by real experience earlier in this project: `identity.pem` was copied between multiple folders repeatedly across several contributions here, and at no point did the tool ever indicate whether those copies retained safe permissions.

## The fix

A non-blocking warning in `load_identity()`, checked once per load: if the file's permission bits include group or other read/write/execute access, print a warning to stderr with the actual mode and a suggested `chmod 600` fix. It intentionally does not block loading — some filesystems (WSL `/mnt` mounts, some network drives) don't support real POSIX permission enforcement, and a hard failure there would break legitimate use for those users.

## Testing performed

Verified locally before submission:
- A `644`-permission identity file triggers the warning with the correct reported mode, and still loads successfully.
- A correctly-permissioned `600` file loads silently, with no warning.
- The full file still parses as valid Python (`ast.parse`) after the change.

## Diff

```diff
+import stat

 def load_identity(...):
     resolved = path.expanduser().resolve()
+    try:
+        mode = resolved.stat().st_mode
+        if mode & (stat.S_IRWXG | stat.S_IRWXO):
+            sys.stderr.write(
+                "warning: " + str(resolved) + " is readable or writable by "
+                "group/other (mode " + oct(mode & 0o777) + "); consider "
+                "running: chmod 600 " + str(resolved) + "\n"
+            )
+    except OSError:
+        pass
     try:
         private_bytes = resolved.read_bytes()
```

---

*Submitted as an upstream contribution to Flop Labs' `technocore-did-starter`. This folder documents the change; the actual patch and history live in the linked PR.*
