#!/usr/bin/env bash
# Download Astral uv into resources/bin/uv (or uv.exe) for the app bundle.
set -euo pipefail

UV_VERSION="${MINION_UV_VERSION:-0.11.7}"
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/../resources/bin"
mkdir -p "$out"
rm -f "$out/uv" "$out/uv.exe"
rm -rf "$out"/uv-* 2>/dev/null || true

kernel="$(uname -s)"
arch="$(uname -m)"
asset=""

if [[ "$kernel" == Darwin* ]]; then
  case "$arch" in
    arm64)  asset="uv-aarch64-apple-darwin.tar.gz" ;;
    x86_64) asset="uv-x86_64-apple-darwin.tar.gz" ;;
  esac
elif [[ "$kernel" == Linux* ]]; then
  case "$arch" in
    x86_64)  asset="uv-x86_64-unknown-linux-gnu.tar.gz" ;;
    aarch64) asset="uv-aarch64-unknown-linux-gnu.tar.gz" ;;
    arm64)   asset="uv-aarch64-unknown-linux-gnu.tar.gz" ;;
  esac
elif [[ "$kernel" == MINGW* ]] || [[ "$kernel" == MSYS* ]] || [[ "$kernel" == CYGWIN* ]] || [[ "$kernel" == *_NT-* ]]; then
  case "$arch" in
    aarch64|arm64) asset="uv-aarch64-pc-windows-msvc.zip" ;;
    *)             asset="uv-x86_64-pc-windows-msvc.zip" ;;
  esac
fi

if [[ -z "$asset" ]]; then
  echo "ensure_uv: unsupported platform ${kernel}/${arch}" >&2
  exit 1
fi

base="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

if [[ "$asset" == *.zip ]]; then
  curl -fsSL "${base}/${asset}" -o "$tmp/u.zip"
  unzip -q "$tmp/u.zip" -d "$tmp"
  f="$(find "$tmp" -type f \( -name uv.exe -o -name uv \) | head -1)"
  if [[ -z "$f" ]]; then
    echo "ensure_uv: uv.exe not found in zip" >&2
    exit 1
  fi
  cp "$f" "$out/uv.exe"
  chmod +x "$out/uv.exe"
else
  curl -fsSL "${base}/${asset}" | tar xz -C "$tmp"
  f="$(find "$tmp" -type f -name uv ! -path '*/.*' | head -1)"
  if [[ -z "$f" ]]; then
    echo "ensure_uv: uv binary not found in tarball" >&2
    exit 1
  fi
  cp "$f" "$out/uv"
  chmod +x "$out/uv"
fi

echo "ensure_uv: uv ${UV_VERSION} → $out"
