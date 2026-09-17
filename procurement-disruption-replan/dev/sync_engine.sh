#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
for dest in "$ROOT/environment/tools/engine_v1.py" "$ROOT/tests/engine_v1.py" "$ROOT/solution/engine_v1.py"; do
  cp "$SCRIPT_DIR/engine_v1.py" "$dest"
  echo "synced -> $dest"
done
cp "$SCRIPT_DIR/oracle.py" "$ROOT/solution/oracle.py"
echo "synced -> $ROOT/solution/oracle.py"
cp "$SCRIPT_DIR/oracle.py" "$ROOT/tests/reference_solver.py"
echo "synced -> $ROOT/tests/reference_solver.py"
