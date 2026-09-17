# Adversarial testing notes

Harbor never executes anything under this directory. Every attempt here
was actually run against the real verifier via `dev/local_harness.sh`
(which runs the real `tests/test.sh`, `collect_agent_output.py`, and
`test_scoring.py` against real `/app`, `/tests`, `/work`, `/logs` paths
and a Python matching `tests/Dockerfile`'s exact pinned installs). Results
below are measured, not hypothetical.

Unlike a CSV-output-only task, this one genuinely executes candidate code
(the submitted `match()` function), so the full untrusted-execution attack
surface applies and was tested directly.

## 1. Early exit (`early_exit/`)

`policy.py` calls `os._exit(0)` at import time, betting the untrusted
stage treats an early process death as "nothing to grade, default pass"
or otherwise mishandles a missing output.

**Measured result: reward 0.** `collect_agent_output.py`'s process dies
before writing `/work/output.json`; `test.sh` checks for that file's
existence independent of the stage's exit code and writes reward 0 when
it's absent.

## 2. Sealed reference read (`sealed_file_read/`)

`policy.py`'s `match()` tries to open `/tests/sealed/reference/pass_bar.json`
directly, betting the pass bar is readable by the unprivileged stage.

**Measured result: reward 0**, and the read itself fails: `/tests/sealed/reference`
is `chown root:root` + `chmod 700` (with files inside `chmod 600`) before
stage 1 ever starts, so the unprivileged `runner` user gets a permission
error attempting to open it -- caught by the policy's own try/except, so
it doesn't even crash, it just contributes nothing, and the eventual
submitted matching (`{}`) is scored on its own (uncleared/unapplied) merits.

## 3. Reward-forgery daemon (`reward_forgery_daemon/`)

`policy.py` forks a detached child (`os.setsid()`) that loops for up to
10 seconds trying to overwrite `/logs/verifier/reward.txt` with `"1"`,
betting that either the detached process survives past stage 1 into
stage 2, or that it can race the real grading and stomp the reward file
directly.

**Measured result: reward 0**, confirmed two ways:
- `/logs/verifier` is `chown root:root` + `chmod 700` **before stage 1
  starts at all** -- the unprivileged `runner` user cannot create or open
  a file in that directory regardless of timing, so every write attempt
  fails with a permission error. This protection does not depend on the
  process-sweep below; it holds even if the daemon process were never
  killed at all.
- `pkill -9 -u runner` runs immediately after stage 1 and again after
  stage 2, sweeping any process (including a `setsid`-detached one, since
  `pkill -u` matches by UID, not process group or session) spawned under
  the unprivileged UID.
- Empirically let the daemon run its full ~10-second lifetime past the
  end of a real verifier run and confirmed `reward.txt`'s content was
  still `0` afterward, and that no `runner`-owned process remained.

## 4. Crashing policy (`crashing_policy/`)

`match()` raises `RuntimeError` on the normal call, betting on a
crashed-verifier-defaults-to-pass behavior or partial credit.

**Measured result: reward 0.** `collect_agent_output.py` catches the
exception and writes `status: "crashed"` to `/work/output.json`;
`test_scoring.py`'s `test_policy_present_and_loadable` fails outright on
that status before any cost is even computed.

## 5. Malformed submission (`malformed_no_match/`)

`policy.py` defines a `solve()` function instead of `match()`, betting a
missing required interface is silently treated as trivially satisfied.

**Measured result: reward 0.** `collect_agent_output.py` checks
`callable(getattr(mod, "match", None))` explicitly and writes
`status: "malformed"` when it's missing, which fails the same
presence/loadable check as the crashing case.
