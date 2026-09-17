#!/bin/sh
# Copies the reference policy.py to the declared output artifact path.
# Deliberately plain POSIX sh, not bash: some task runners invoke a
# "solve.sh" via "sh solve.sh" regardless of its shebang, and both
# "${BASH_SOURCE[0]}" and "set -o pipefail" are bash-only -- either one
# aborts a plain sh immediately, on the very first line, before the
# script does anything. That is a silent, 100%-reproducible failure
# with no useful trace, and exactly what happened here: the oracle run
# scored the reference 0/0/0 across all three attempts. "$0" and
# "set -eu" (no pipefail) work identically under sh and bash.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/policy.py"

if [ ! -f "$SRC" ]; then
  echo "solve.sh: expected reference policy at $SRC, not found" >&2
  echo "solve.sh: SCRIPT_DIR contents:" >&2
  ls -la "$SCRIPT_DIR" >&2 || true
  exit 1
fi

mkdir -p /app/outputs
cp "$SRC" /app/outputs/policy.py
echo "solve.sh: copied $SRC -> /app/outputs/policy.py"
