#!/usr/bin/env bash
# Verifier entry point. Runs as root. Never uses set -e: every path,
# including a crash or timeout in stage 1, must still reach the point
# where reward.txt gets written.
#
# Which exact path the platform checks for the reward file has not been
# possible to confirm directly (no Docker registry access in this dev
# environment to build and run the real image; two different guesses --
# /logs/verifier/reward.txt, then /work/reward.txt -- both produced an
# identical RewardFileNotFoundError naming ".../verifier/reward.txt"
# under the job's mapped work directory). Rather than guess a third
# single path, write the reward (as both reward.txt and reward.json,
# since the platform's own error accepts either) to every plausible
# candidate location at once. This is cheap (a few bytes) and makes the
# verifier robust to whichever convention is actually in effect.
WORK_DIR=/work
CTRF_FILE="$WORK_DIR/ctrf.json"
REWARD_CANDIDATE_DIRS="/work /work/verifier /logs/verifier"

mkdir -p "$WORK_DIR"

# Seal the hidden pass-bar/calibration data before stage 1 (untrusted)
# ever runs. The held-out INPUT scenario (sealed/inputs) is left
# world-readable -- stage 1 must read it to call the candidate's
# function on it; only the answer key/calibration (sealed/reference)
# is secret.
chown -R root:root /tests/sealed/reference
chmod 700 /tests/sealed/reference
find /tests/sealed/reference -type f -exec chmod 600 {} \;
find /tests/sealed/reference -type d -exec chmod 700 {} \;

# /work must be writable by the untrusted runner user (stage 1 writes
# output.json there), but the STICKY bit prevents that same user from
# deleting or replacing reward.txt once stage 2 (root) writes it --
# without it, owning write+execute on the parent directory would let
# runner (or a leftover forked process under that UID) remove/replace a
# root-owned file inside it, permission bits on the file notwithstanding.
chown root:runner "$WORK_DIR"
chmod 1770 "$WORK_DIR"

write_reward() {
  for dir in $REWARD_CANDIDATE_DIRS; do
    mkdir -p "$dir" 2>/dev/null || continue
    # Give the untrusted runner user write access to create files under
    # a candidate dir (needed for /work, harmless elsewhere), but keep
    # the sticky bit so it can't delete/replace what root writes here.
    chown root:runner "$dir" 2>/dev/null
    chmod 1770 "$dir" 2>/dev/null
    echo -n "$1" > "$dir/reward.txt" 2>/dev/null
    echo -n "$1" > "$dir/reward.json" 2>/dev/null
    chown root:root "$dir/reward.txt" "$dir/reward.json" 2>/dev/null
    chmod 644 "$dir/reward.txt" "$dir/reward.json" 2>/dev/null
  done
}

# --- Stage 1: untrusted. Executes the candidate's policy code, isolated
# as an unprivileged user, own process group, firm timeout. This is a
# pure deterministic calculation (no search, no randomness), so a
# single call is sufficient -- no determinism double-call is needed. ---
timeout -k 5 60 su -s /bin/bash runner -c "python3 /tests/collect_agent_output.py" > "$WORK_DIR/stage1.log" 2>&1
STAGE1_STATUS=$?
cat "$WORK_DIR/stage1.log"

# Sweep anything the candidate's code spawned/forked/detached under the
# runner UID before stage 2 (trusted) runs -- it cannot change its own UID.
pkill -9 -u runner 2>/dev/null

if [ $STAGE1_STATUS -ne 0 ] && [ $STAGE1_STATUS -ne 124 ]; then
  echo "Stage 1 exited abnormally (status $STAGE1_STATUS)"
fi
if [ ! -f "$WORK_DIR/output.json" ]; then
  echo "Stage 1 failed to produce output.json"
  write_reward "0"
  pkill -9 -u runner 2>/dev/null
  exit 0
fi

chmod 644 "$WORK_DIR/output.json"

# --- Stage 2: trusted, root. Recomputes correctness from the raw
# recorded answers with no candidate code involved at all. ---
cd /tests
timeout -k 5 60 python3 -m pytest test_scoring.py --ctrf="$CTRF_FILE" -v > "$WORK_DIR/stage2.log" 2>&1
STAGE2_STATUS=$?
cat "$WORK_DIR/stage2.log"

if [ $STAGE2_STATUS -eq 0 ]; then
  write_reward "1"
else
  write_reward "0"
fi

# Final sweep in case anything under the runner UID survived stage 2.
pkill -9 -u runner 2>/dev/null

exit 0
