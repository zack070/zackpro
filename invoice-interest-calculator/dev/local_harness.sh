#!/usr/bin/env bash
# Local (no-Docker) verifier harness, run against the real /app, /tests,
# /work, /logs paths -- same layout the Dockerfile's ENTRYPOINT expects.
# pytest + pytest-json-ctrf are installed directly into the system
# interpreter in this dev environment (no separate venv needed here).
#
# Usage: dev/local_harness.sh <policy.py to submit as /app/outputs/policy.py>
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POLICY_FILE="$1"

rm -rf /app /tests /work /logs
mkdir -p /app/outputs /work /logs/verifier

cp -r "$ROOT/tests/." /tests
if [ -f "$POLICY_FILE" ]; then
  cp "$POLICY_FILE" /app/outputs/policy.py
fi

id runner >/dev/null 2>&1 || useradd -m -u 1001 -s /bin/bash runner
chown runner:runner /work

echo "=== running tests/test.sh against $POLICY_FILE ==="
bash /tests/test.sh
echo "=== reward.txt ==="
cat /logs/verifier/reward.txt
echo
echo "=== orphaned runner processes ==="
ps -u runner || echo "(none)"
