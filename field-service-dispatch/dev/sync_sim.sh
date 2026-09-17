#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
for dest in "$ROOT/environment/sim/simulator.py" "$ROOT/tests/simulator.py"; do
  cp "$SCRIPT_DIR/simulator.py" "$dest"
  echo "synced -> $dest"
done
