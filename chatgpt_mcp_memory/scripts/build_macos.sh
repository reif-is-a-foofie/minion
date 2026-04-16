#!/usr/bin/env bash
set -euo pipefail

# Builds a standalone macOS executable for Claude Desktop:
# - dist/minion-mcp
#
# Note: This uses PyInstaller inside the local venv.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

source ".venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install pyinstaller

rm -rf build dist

pyinstaller \
  --clean \
  --name "minion-mcp" \
  --onefile \
  "src/mcp_server.py"

echo ""
echo "Built: $ROOT_DIR/dist/minion-mcp"
echo "Claude Desktop config should set command to that path."

