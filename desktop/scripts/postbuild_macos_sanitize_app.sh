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

echo "sanitized: $app_path"

