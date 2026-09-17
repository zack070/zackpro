#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
for dest in "$ROOT/environment/engine/engine.py" "$ROOT/tests/engine.py"; do
  cp "$SCRIPT_DIR/engine.py" "$dest"
  echo "synced -> $dest"
done
