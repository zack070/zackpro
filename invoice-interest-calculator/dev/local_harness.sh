#!/usr/bin/env bash
# Local (no-Docker) verifier harness, run against the real /app, /tests,
# /work paths -- same layout the Dockerfile's ENTRYPOINT expects.
# pytest + pytest-json-ctrf are installed directly into the system
# interpreter in this dev environment (no separate venv needed here).
#
# Which exact path the platform checks for reward.txt could not be
# confirmed directly in this dev environment (no working Docker
# registry access to build and run the real image). Two different
# single-path guesses both produced an identical RewardFileNotFoundError
# from the platform, which is why test.sh now writes the reward to
# every plausible candidate location at once
# (/work, /work/verifier, /logs/verifier -- both .txt and .json). This
# harness checks all of them below rather than assuming one.
# test.sh itself is the source of truth for the reward paths; this
# harness only reads them back to report the result.
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
echo "=== reward (all candidate locations) ==="
for f in /work/reward.txt /work/reward.json /work/verifier/reward.txt /work/verifier/reward.json /logs/verifier/reward.txt /logs/verifier/reward.json; do
  if [ -f "$f" ]; then
    echo "$f: $(cat "$f")"
  else
    echo "$f: MISSING"
  fi
done
echo "=== orphaned runner processes ==="
ps -u runner || echo "(none)"
