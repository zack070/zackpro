#!/usr/bin/env bash
# Runs solution/solve.sh exactly as the platform's oracle run does, then
# feeds ITS ACTUAL OUTPUT through the verifier -- never solution/policy.py
# directly. This is the check that would have caught the bug where
# solve.sh's embedded heredoc copy of the calculation logic drifted out
# of sync with solution/policy.py after a fix was applied to policy.py,
# reference_calc.py, and the sealed reference, but NOT to solve.sh's own
# copy: testing policy.py directly always passed (it had the fix); only
# testing what solve.sh actually produces showed the oracle itself was
# still broken. Run this before every submission, not just "does
# solution/policy.py pass" -- they can silently diverge whenever solve.sh
# embeds a copy of the logic instead of referencing policy.py directly,
# so re-run this any time either file changes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR=$(mktemp -d)

rm -rf /app/outputs
sh "$ROOT/solution/solve.sh"
if [ ! -f /app/outputs/policy.py ]; then
  echo "test_oracle.sh: solve.sh did not produce /app/outputs/policy.py" >&2
  exit 1
fi
cp /app/outputs/policy.py "$TMP_DIR/policy.py"

if ! diff -q "$TMP_DIR/policy.py" "$ROOT/solution/policy.py" > /dev/null; then
  echo "=== WARNING: solve.sh's actual output differs from solution/policy.py ==="
  diff "$TMP_DIR/policy.py" "$ROOT/solution/policy.py" || true
  echo "=== investigate before trusting any 'solution passes' result ==="
fi

echo "=== running the real verifier against solve.sh's ACTUAL output ==="
bash "$ROOT/dev/local_harness.sh" "$TMP_DIR/policy.py"

rm -rf "$TMP_DIR"
