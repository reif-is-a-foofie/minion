#!/usr/bin/env bash
# Stage the Python sidecar source into src-tauri/resources/ so Tauri's bundler
# ships it inside the .app. Keeps the build reproducible: this runs as
# beforeBuildCommand, so `cargo tauri build` always gets a fresh copy and the
# resulting DMG is portable to any Mac.
#
# Layout after this runs:
#   src-tauri/resources/sidecar/
#     src/                      (api.py + helpers)
#     requirements.txt          (core deps)
#     requirements-docs.txt     (pdf/docx/html)
#     requirements-images.txt   (ocr)
#     VERSION                   (stamp for debug)

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
tauri_dir="$(cd "$here/.." && pwd)"
repo_root="$(cd "$tauri_dir/../.." && pwd)"

src="$repo_root/chatgpt_mcp_memory"
dst="$tauri_dir/resources/sidecar"

if [[ ! -d "$src/src" ]]; then
  echo "sync_sidecar: missing source at $src/src" >&2
  exit 1
fi

rm -rf "$dst"
mkdir -p "$dst"

rsync -a \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.venv' \
  --exclude 'venv' \
  --exclude '.pytest_cache' \
  --exclude '*.egg-info' \
  "$src/src/" "$dst/src/"

for req in requirements.txt requirements-docs.txt requirements-images.txt; do
  if [[ -f "$src/$req" ]]; then
    cp "$src/$req" "$dst/$req"
  fi
done

git_sha="$(cd "$repo_root" && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
printf 'sha=%s\nbuilt=%s\n' "$git_sha" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$dst/VERSION"

echo "sync_sidecar: staged $(find "$dst" -type f | wc -l | tr -d ' ') files into $dst"
