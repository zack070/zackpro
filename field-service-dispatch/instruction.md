Work in `/app` and provide the scheduling policy at:

`/app/outputs/policy.py`

The simulator is already implemented. Its complete scheduling contract is in `/app/sim/README.md`, which is the authoritative reference for timing, fatigue, SLA handling, overtime, and scoring. The implementation in `/app/sim/simulator.py` is also available for inspection, including the `TechSnapshot` and `JobSnapshot` structures used by the policy interface.

Your module must define:

`def decide(state) -> list[tuple[str, str]]`

The simulator calls `decide` when a scheduling decision can be made. Return `(technician_id, job_id)` pairs for assignments to start immediately, or `[]` when you want to make no assignment. The state supplied to the function contains the current time, free technicians, and pending jobs using the snapshot structures defined by the simulator. You may use helper code or internal state, but `decide` is the only interface the grader will call.

Assignments are replayed under the simulator's actual rules. An assignment that is not legal when returned, such as one involving a technician who is no longer free or a skill mismatch, is not applied. If the same technician or job occurs more than once in one returned list, only its first occurrence is honored.

Three complete development scenarios are available at:

`/app/data/sample_24/`
`/app/data/sample_13/`
`/app/data/sample_97/`

Test your policy on all three samples before submitting. They are development cases only and are not the held-out grading scenario.

The final evaluation imports your policy and runs it through the real simulator on a separate shift scenario with a different technician and job mix. The grader replays the assignments produced by `decide` and scores the resulting schedule under the same contract. There is a hidden cost quality bar for this held-out run. It was calibrated from measured performance of baseline and reference policies, with a substantial gap between them. The exact threshold and held-out scenario are not disclosed.

The complete shift simulation is also subject to a combined wall-clock budget of 120 seconds. Keep the decision logic efficient enough to remain within that limit; expensive work repeated on every `decide` call can affect whether the submission completes in time.

The policy must be deterministic. The same state should produce the same returned list, so do not rely on unseeded randomness, wall-clock time, or changing external state.

A policy that fails to import, does not define `decide`, or raises an exception during a call is a failing submission. Do not modify the simulator. The visible scenarios should be used to check both execution and scheduling behavior before the final submission.

You have 10800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
