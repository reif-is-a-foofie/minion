#!/usr/bin/env bash
set -euo pipefail

# Best-effort cleanup for macOS Finder moves / Gatekeeper friction.
# This does NOT sign/notarize; it only removes common extended attributes
# and ensures the bundle is user-readable.

app_path="${1:-}"
if [[ -z "$app_path" ]]; then
  echo "usage: postbuild_macos_sanitize_app.sh /path/to/Minion.app" >&2
  exit 2
fi
if [[ ! -d "$app_path" ]]; then
  # In some build environments (e.g. IDE sandboxes), Tauri bundles into a temp
  # dir. Fall back to the most recent bundled Minion.app we can find.
  candidate="$(ls -td /var/folders/*/*/*/cursor-sandbox-cache/*/cargo-target/release/bundle/macos/Minion.app 2>/dev/null | head -n 1 || true)"
  if [[ -n "${candidate:-}" && -d "$candidate" ]]; then
    app_path="$candidate"
  else
    echo "not a directory: $app_path" >&2
    exit 2
  fi
fi

# Clear quarantine and provenance metadata if present.
xattr -dr com.apple.quarantine "$app_path" 2>/dev/null || true
xattr -dr com.apple.provenance "$app_path" 2>/dev/null || true

# Remove immutable flags if they exist (rare, but causes Finder "skipped items").
chflags -R nouchg "$app_path" 2>/dev/null || true

# Make sure the bundle is readable/traversable.
chmod -R u+rwX,go+rX "$app_path" 2>/dev/null || true

# Guardrail: refuse to ship obvious user data if it somehow got copied in.
python3 - "$app_path" <<'PY'
import os
import sys
from pathlib import Path

app = Path(sys.argv[1]).resolve()
bad = []
needles = {
    "memory.db",
    "telemetry.jsonl",
    "settings.json",
    "inbox",
}
for root, dirs, files in os.walk(app):
    rp = Path(root)
    name = rp.name
    if name in needles:
        bad.append(str(rp))
    for f in files:
        if f in needles or f.endswith((".db", ".sqlite", ".sqlite3")):
            bad.append(str(rp / f))

if bad:
    print("ERROR: app bundle appears to include user data files:", file=sys.stderr)
    for p in sorted(set(bad))[:200]:
        print(f"  - {p}", file=sys.stderr)
    sys.exit(3)
PY

echo "sanitized: $app_path"

