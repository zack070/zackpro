#!/usr/bin/env bash
# Local (no-Docker) verifier harness, matching tests/Dockerfile's exact
# pinned installs (identical to field-service-dispatch's, so the same venv
# is reused) via a dedicated venv, run against the real /app, /tests,
# /work, /logs paths. See field-service-dispatch/dev/local_harness.sh for
# the /usr/local/bin/python3 wrapper rationale -- never symlink into a
# venv's own python3, it creates a cycle; always a wrapper script that execs
# the real system interpreter with the venv's site-packages on PYTHONPATH,
# and always via a plain new file, never `cat >` through an existing
# symlink.
#
# Usage: dev/local_harness.sh <policy.py to submit as /app/outputs/policy.py>
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POLICY_FILE="$1"
VENV=/home/user/zackpro/.fsdvenv
PY3_LINK=/usr/local/bin/python3
REAL_PYTHON=/usr/bin/python3.13
SITE_PACKAGES="$VENV/lib/python3.13/site-packages"

restore_python3() {
  rm -f "$PY3_LINK"
  ln -s "$REAL_PYTHON" "$PY3_LINK"
}
trap restore_python3 EXIT

rm -rf /app /tests /work /logs
mkdir -p /app/outputs /work /logs/verifier

cp -r "$ROOT/tests/." /tests
if [ -f "$POLICY_FILE" ]; then
  cp "$POLICY_FILE" /app/outputs/policy.py
fi

id runner >/dev/null 2>&1 || useradd -m -u 1001 -s /bin/bash runner
chown runner:runner /work

rm -f "$PY3_LINK"
{
  echo '#!/bin/bash'
  echo "export PYTHONPATH=\"$SITE_PACKAGES\${PYTHONPATH:+:\$PYTHONPATH}\""
  echo "exec \"$REAL_PYTHON\" \"\$@\""
} > "$PY3_LINK"
chmod +x "$PY3_LINK"

echo "=== running tests/test.sh against $POLICY_FILE ==="
bash /tests/test.sh
echo "=== reward.txt ==="
cat /logs/verifier/reward.txt
echo
echo "=== orphaned runner processes ==="
ps -u runner || echo "(none)"
