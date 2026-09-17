# Technician Scheduling Task

Work in `/app` and finish the scheduling policy in:

`/app/outputs/policy.py`

The simulator is already there, so this is a policy-writing task rather than a simulator implementation task. The full rules are in `/app/sim/README.md`. Use that file as the source of truth when deciding what a legal assignment means, how time advances, and how the final cost is calculated. `/app/sim/simulator.py` is the actual implementation and is worth reading alongside the README if you need to understand how the state is represented or how a decision is applied.

The only interface the grader needs from your module is:

`def decide(state) -> list[tuple[str, str]]`

The function is called when scheduling decisions can be made. At each call there is at least one free technician and at least one pending job. It may be called at the beginning of a shift, when a technician finishes work, or when another job arrives.

`state` gives you the current time, available technicians, and pending jobs. The snapshots expose the fields defined by the simulator. For technicians this includes `tech_id`, `skills`, `continuous_work`, `shift_end`, `overtime_used`, and `max_overtime`. Jobs provide `job_id`, `required_skill`, `duration`, `priority`, `deadline`, `arrival_time`, and `is_followup`. The last field identifies a job created by the simulator's follow-up cascade.

Return the work you want started immediately as pairs of technician ID and job ID. An empty list is valid when you choose to leave the available resources unassigned. If an assignment is illegal when the simulator receives it, the replay will simply not apply that assignment. This includes cases such as an unavailable technician or an incompatible skill. Also remember that if a technician or job is listed more than once in the same return value, only the first occurrence is used.

You can put whatever supporting code you need inside `policy.py`. Helpers, classes, and internal state are fine. The grader does not require any interface other than `decide`.

There are three scenarios available for development:

`/app/data/sample_56/`
`/app/data/sample_61/`
`/app/data/sample_15/`

They contain complete technician, job, and configuration data. None is the final grading scenario. Use all three when testing rather than judging the policy from one example.

A practical way to approach the task is to read the README first, inspect the simulator implementation, then make a simple policy and run it against the supplied scenarios. Look at the actual results and change the policy based on what the simulations show. Small local experiments are also useful when two possible scheduling choices have different effects later in the shift. The simulator is plain Python, so there is no special framework required for this work.

The final evaluator imports your `policy.py` and runs it through the real simulator on a separate held-out shift. The technicians and jobs in that run are different from the visible samples. The grader uses the assignments your `decide()` function actually returns and independently replays them under the simulator rules.

There is a hidden cost bar for the held-out run. It was set using measured results from a simple baseline and a stronger reference policy, with enough separation between those results to make the bar meaningful. Your policy has to clear that bar. The exact value and the held-out scenario are not provided.

Make the policy deterministic. Calling `decide()` twice with the same state should give the same result. In particular, avoid unseeded randomness, wall-clock-dependent choices, or other outside state that could change a replay.

Before finishing, make sure `policy.py` imports cleanly and that `decide()` can be called throughout a complete simulation without raising an exception. The supplied scenarios are there specifically to catch those problems and to give you a chance to compare different approaches.

The simulator itself and its rules are not the part to modify. Concentrate on the scheduling decisions made by `decide()` and use the visible scenarios to develop something that can generalize beyond them.

You have 10800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
