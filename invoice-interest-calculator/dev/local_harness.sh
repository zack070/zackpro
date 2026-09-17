#!/usr/bin/env bash
# Local (no-Docker) verifier harness, run against the real /app, /tests,
# /work paths -- same layout the Dockerfile's ENTRYPOINT expects.
# pytest + pytest-json-ctrf are installed directly into the system
# interpreter in this dev environment (no separate venv needed here).
#
# reward.txt lives at /work/reward.txt -- this is the path the real
# platform actually checks (confirmed via a RewardFileNotFoundError
# naming ".../verifier/reward.txt" under the job's mapped work
# directory, which maps to this container's /work). An earlier version
# of both this harness and tests/test.sh used /logs/verifier/reward.txt
# instead, which this local harness happily validated (it just cats
# whatever path test.sh itself writes to) while the real platform never
# looked there at all -- so a passing local run gave false confidence.
# test.sh itself is the source of truth for the reward path; this
# harness only reads it back to report the result.
#
# Usage: dev/local_harness.sh <policy.py to submit as /app/outputs/policy.py>
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POLICY_FILE="$1"

rm -rf /app /tests /work
mkdir -p /app/outputs /work

cp -r "$ROOT/tests/." /tests
if [ -f "$POLICY_FILE" ]; then
  cp "$POLICY_FILE" /app/outputs/policy.py
fi

id runner >/dev/null 2>&1 || useradd -m -u 1001 -s /bin/bash runner

echo "=== running tests/test.sh against $POLICY_FILE ==="
bash /tests/test.sh
echo "=== reward.txt ==="
cat /work/reward.txt
echo
echo "=== orphaned runner processes ==="
ps -u runner || echo "(none)"
