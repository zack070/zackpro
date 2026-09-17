# Adversarial testing notes

Harbor never executes anything under this directory. It documents what was
tried against the real verifier (via the local no-Docker harness described
in `dev/local_harness.sh`, which runs the actual `tests/test.sh`,
`collect_agent_output.py`, and `test_procurement_grading.py` against real
`/app`, `/tests`, `/work`, `/logs` paths and a Python matching
`tests/Dockerfile`'s exact pinned installs) and the actual measured result
of each attempt, not a hypothetical.

## Why the standard code-execution exploits don't apply here

This task's grading path never executes anything the candidate supplies.
`collect_agent_output.py` (the untrusted stage) only opens
`baseline_plan.csv` and `replan.csv` with `csv.DictReader` and coerces a few
fields to `int`/`float`/`str`; there is no interpreter, subprocess, or
`import` of anything candidate-controlled anywhere in the pipeline. That
structurally rules out the usual "early exit / import hack" and "reward
forgery daemon" exploits described for tasks where the grader runs an
agent-modified program -- there is no code of the candidate's ever running
inside the verifier container to exit early, fork, or detach from. The
two-stage unprivileged/trusted split and the UID sweeps in `tests/test.sh`
are kept anyway, as defense in depth against a change to this design later,
but they are not covering a live attack surface today. This was not assumed
-- see "sealed file read" below for the one exploit in this family that
does still have a plausible vector (reading the sealed file directly,
independent of any code execution) and was tested for real.

## Exploits tried and measured results

### 1. Sealed reference file read (`sealed_file_read_attempt/`)

Attempt: as the unprivileged `runner` user (the identity the untrusted
stage runs as), read `/tests/sealed/reference/optimum.json` directly.

Measured result: `Permission denied`. `tests/test.sh` runs
`chown -R root:root /tests/sealed/reference` and `chmod 700`/`600` on it
before stage 1 ever executes; verified directly:

    $ su -s /bin/bash runner -c "cat /tests/sealed/reference/optimum.json"
    cat: /tests/sealed/reference/optimum.json: Permission denied

### 2. Guess the wrong disrupted supplier (`wrong_disrupted_supplier_guess/`)

Attempt: submit a valid baseline, then for the replan, guess that S1 (not
S2) is the disrupted supplier -- drop all S1 orders from periods 5-6 and
place S2 orders normally, as if nothing about it had changed. This tests
whether a candidate can skip actually running `advance_horizon.py` and
still pass by guessing generically "some supplier is disrupted, avoid the
most plausible one."

Measured result: **reward 0**. The live replay independently flags
`new order placed with disrupted supplier S2 in period 5` and, because the
S1 orders that were dropped were the ones actually needed, cascading unmet
demand for P1 and P3 in periods 7-8 (service ratios 0.50 and 0.58). Neither
`test_replan_feasible` nor `test_replan_cost_at_optimum` passes.

### 3. Full adversarial/malformed-input sweep

`dev/gen_adversarial_cases.py` generates 15 mutations of the oracle's own
valid submission (one control case left unmutated) and
`dev/local_harness.sh` runs every one through the real verifier. All 15
mutations score reward 0; the unmutated control scores reward 1. Covered:
duplicate rows, negative/zero/non-integer quantity, order from the
disrupted supplier inside the replan window, a replan row that tries to
rewrite a historical (period <= 4) commitment, an ineligible supplier/
product pair, an order below MOQ, supplier capacity exceeded in a single
period, warehouse capacity exceeded, a malformed CSV (missing column), an
empty baseline, an order placed after the planning horizon, right-total-
quantity-but-wrong-timing, and a 50,000-row garbage file (resource-
exhaustion attempt; rejected by `collect_agent_output.py`'s row cap without
hanging).

### 4. Empty / no-op submission

No `baseline_plan.csv` or `replan.csv` at all. Measured result: reward 0
(`collect_agent_output.py` reports `status: missing` for both files;
`test_baseline_parseable` and `test_replan_parseable` fail cleanly).
