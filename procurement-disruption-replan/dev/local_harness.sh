#!/usr/bin/env bash
# Local (no-Docker) verifier harness. Mirrors tests/test.sh's real flow
# against the real /app, /tests, /work, /logs paths, using a venv that
# matches tests/Dockerfile's exact pinned installs (pytest==9.1.1,
# pytest-json-ctrf==0.5.2, pulp==2.9.0) -- not the host's ambient Python.
#
# test.sh itself (the shipped artifact) is never modified: in the real
# container "python3" already resolves to the correct interpreter for both
# the root shell and any su'd runner shell. Locally, su resets PATH, so we
# temporarily replace /usr/local/bin/python3 with a wrapper that execs the
# real system interpreter with the tests venv's site-packages on
# PYTHONPATH. IMPORTANT: /usr/local/bin/python3 is normally a symlink, and
# writing to a path with `>` or `cat >` follows the symlink and clobbers
# whatever it points at -- so we always rm the existing link first and
# write a plain new file in its place, never redirect through it directly.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CANDIDATE_DIR="$1"
TESTS_VENV=/home/user/zackpro/.testsvenv
PY3_LINK=/usr/local/bin/python3
REAL_PYTHON=/usr/bin/python3.13
SITE_PACKAGES="$TESTS_VENV/lib/python3.13/site-packages"

restore_python3() {
  rm -f "$PY3_LINK"
  ln -s "$REAL_PYTHON" "$PY3_LINK"
}
trap restore_python3 EXIT

rm -rf /app /tests /work /logs
mkdir -p /app/outputs /work /logs/verifier

cp -r "$ROOT/tests/." /tests
cp "$CANDIDATE_DIR/baseline_plan.csv" /app/outputs/baseline_plan.csv 2>/dev/null || true
cp "$CANDIDATE_DIR/replan.csv" /app/outputs/replan.csv 2>/dev/null || true

id runner >/dev/null 2>&1 || useradd -m -u 1001 -s /bin/bash runner
chown runner:runner /work

rm -f "$PY3_LINK"
{
  echo '#!/bin/bash'
  echo "export PYTHONPATH=\"$SITE_PACKAGES\${PYTHONPATH:+:\$PYTHONPATH}\""
  echo "exec \"$REAL_PYTHON\" \"\$@\""
} > "$PY3_LINK"
chmod +x "$PY3_LINK"

echo "=== running tests/test.sh against $CANDIDATE_DIR ==="
bash /tests/test.sh
echo "=== reward.txt ==="
cat /logs/verifier/reward.txt
echo
echo "=== orphaned runner processes ==="
ps -u runner || echo "(none)"
