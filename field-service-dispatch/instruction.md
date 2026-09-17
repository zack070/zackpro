Work from `/app` and submit the finished policy as `/app/outputs/policy.py`.

The scheduling rules are already implemented. Read `/app/sim/README.md` for the simulator contract and use `/app/sim/simulator.py` when you need to check how that contract is represented in code. In particular, the `TechSnapshot` and `JobSnapshot` definitions describe the state passed to the policy.

The module needs one callable entry point:

`def decide(state) -> list[tuple[str, str]]`

A call happens when work can be assigned during the shift. Use the state you receive to choose immediate technician/job assignments. Returning an empty list is allowed. The simulator ignores an assignment that is not valid at that moment, and when a technician or job is named more than once in the same returned list, its first occurrence is the one that counts.

You can structure the module however you want, but the grader only relies on `decide`.

For development, use the three supplied scenarios:

`/app/data/sample_24/`
`/app/data/sample_13/`
`/app/data/sample_97/`

These are examples for testing, not the final workload. Test on all three before submitting. The actual evaluation uses a separate shift with different data, so behavior that only works for one particular sample is unlikely to be useful.

The evaluator imports your module and runs it with the real simulator. It then replays the assignments and calculates the resulting cost according to the simulator contract. A hidden quality threshold must be cleared. That threshold was established from measured baseline and reference performance on real scenarios; its value and the held-out scenario are not provided.

There is also a 120-second combined wall-clock limit for the simulation of the whole shift. Keep `decide` reasonably fast, especially if it performs work on every call.

Results need to be reproducible. Given the same state, `decide` should return the same list. Avoid unseeded randomness, wall-clock-dependent choices, or other changing external state.

Make sure the module imports successfully and that `decide` does not raise exceptions during a complete run. The simulator is part of the evaluation environment and should not be modified.

You have 10800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
