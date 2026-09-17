# Measured exploit attempts

All measured via `dev/local_harness.sh cheat/<name>/policy.py`. Every one
scores `reward=0`.

| exploit | mechanism | result |
|---|---|---|
| `early_exit` | exits before returning | Stage 1 never produces output.json -> reward 0 |
| `sealed_file_read` | tries to read `tests/sealed/reference/*` directly | permission denied (sealed root:root 600 before Stage 1 starts); falls through to a wrong answer -> reward 0 |
| `reward_forgery_daemon` | forks a detached process trying to overwrite `/logs/verifier/reward.txt` | killed by the post-Stage-1 `pkill -9 -u runner` sweep before Stage 2 runs; Stage 2 independently recomputes and overwrites reward.txt anyway -> reward 0 |
| `crashing_policy` | raises immediately | caught by Stage 1, `status=call_error` written, Stage 2's `test_policy_present_and_loadable` fails -> reward 0 |
| `malformed_output` | returns a string instead of a dict | caught by Stage 1 (`bad_return_type`) -> reward 0 |

Also verified: `tests/sealed/reference/reference_calc.py` (the actual
correct calculation) is imported lazily, only inside Stage 2's scoring
function -- never at module load time in `tests/engine.py` -- so that
Stage 1's process (which the untrusted candidate module shares) never
has occasion to read it even indirectly through an import chain. This
was a real bug caught during development: an earlier version imported
it eagerly at the top of `engine.py`, which `collect_agent_output.py`
(Stage 1) also imports, meaning the untrusted candidate's code could in
principle have read the answer-key algorithm straight off disk.
