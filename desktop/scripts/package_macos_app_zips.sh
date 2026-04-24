#!/usr/bin/env bash
# Zip Minion.app per CPU for GitHub Releases (users unzip → drag Minion.app).
# Run from repo root or from desktop/ after dual-arch `tauri build`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION=""
OUT="${ROOT}/dist"
AS_APP=""
INTEL_APP=""

usage() {
  echo "Usage: $0 --version SEMVER [--out DIR] [--apple-silicon-app PATH] [--intel-app PATH]" >&2
  echo "Defaults: Apple Silicon app -> src-tauri/target/aarch64-apple-darwin/release/bundle/macos/Minion.app" >&2
  echo "          Intel app        -> src-tauri/target/x86_64-apple-darwin/release/bundle/macos/Minion.app" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="${2:-}"; shift 2 || usage ;;
    --out)
      OUT="${2:-}"; shift 2 || usage ;;
    --apple-silicon-app)
      AS_APP="${2:-}"; shift 2 || usage ;;
    --intel-app)
      INTEL_APP="${2:-}"; shift 2 || usage ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1" >&2; usage ;;
  esac
done

[[ -n "$VERSION" ]] || usage

AS_DEFAULT="${ROOT}/src-tauri/target/aarch64-apple-darwin/release/bundle/macos/Minion.app"
INTEL_DEFAULT="${ROOT}/src-tauri/target/x86_64-apple-darwin/release/bundle/macos/Minion.app"
AS_APP="${AS_APP:-$AS_DEFAULT}"
INTEL_APP="${INTEL_APP:-$INTEL_DEFAULT}"

mkdir -p "$OUT"
made=0

if [[ -d "$AS_APP" ]]; then
  out_zip="${OUT}/Minion_${VERSION}_macOS-Apple-Silicon.zip"
  ditto -c -k --sequesterRsrc --keepParent "$AS_APP" "$out_zip"
  echo "Wrote $out_zip"
  made=$((made + 1))
else
  echo "WARN: Apple Silicon bundle missing (skip): $AS_APP" >&2
fi

if [[ -d "$INTEL_APP" ]]; then
  out_zip="${OUT}/Minion_${VERSION}_macOS-Intel.zip"
  ditto -c -k --sequesterRsrc --keepParent "$INTEL_APP" "$out_zip"
  echo "Wrote $out_zip"
  made=$((made + 1))
else
  echo "WARN: Intel bundle missing (skip): $INTEL_APP" >&2
fi

if [[ "$made" -eq 0 ]]; then
  echo "ERROR: no zips produced; build both targets or pass --apple-silicon-app / --intel-app" >&2
  exit 1
fi
