#!/usr/bin/env bash
# Verifier entry point. Runs as root. Never uses set -e: every path,
# including a crash in either stage, must still reach the point where
# reward.txt gets written.

REWARD_DIR=/logs/verifier
REWARD_FILE="$REWARD_DIR/reward.txt"
WORK_DIR=/work
CTRF_FILE="$REWARD_DIR/ctrf.json"

mkdir -p "$REWARD_DIR" "$WORK_DIR"
chown root:root "$REWARD_DIR"
chmod 700 "$REWARD_DIR"

# Seal the hidden reference data before stage 1 (untrusted) ever runs.
chown -R root:root /tests/sealed/reference
chmod 700 /tests/sealed/reference
find /tests/sealed/reference -type f -exec chmod 600 {} \;
find /tests/sealed/reference -type d -exec chmod 700 {} \;

chown runner:runner "$WORK_DIR"
chmod 700 "$WORK_DIR"

write_reward() {
  echo -n "$1" > "$REWARD_FILE"
  chown root:root "$REWARD_FILE"
  chmod 600 "$REWARD_FILE"
}

# --- Stage 1: untrusted, unprivileged parsing of the candidate's artifacts ---
timeout -k 5 60 su -s /bin/bash runner -c "python3 /tests/collect_agent_output.py" > "$WORK_DIR/stage1.log" 2>&1
STAGE1_STATUS=$?
cat "$WORK_DIR/stage1.log"

# Sweep any process the candidate's artifacts might somehow have spawned
# under the runner UID before stage 2 (trusted) runs.
pkill -9 -u runner 2>/dev/null

if [ $STAGE1_STATUS -ne 0 ] || [ ! -f "$WORK_DIR/collected.json" ]; then
  echo "Stage 1 failed to produce collected.json (exit $STAGE1_STATUS)"
  write_reward "0"
  pkill -9 -u runner 2>/dev/null
  exit 0
fi

chmod 644 "$WORK_DIR/collected.json"

# --- Stage 2: trusted, root. Independently recomputes everything. ---
cd /tests
timeout -k 5 60 python3 -m pytest test_procurement_grading.py --ctrf="$CTRF_FILE" -v > "$WORK_DIR/stage2.log" 2>&1
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
