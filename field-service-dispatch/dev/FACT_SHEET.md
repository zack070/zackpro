# Fact sheet for instruction.md

Every fact below is something the sealed verifier actually depends on, or a
mechanical constraint on the instruction file itself. Write instruction.md
as a natural professional brief covering these -- do not transcribe this as
a bullet list, and do not restate `environment/sim/README.md`'s contract
verbatim; point to it as the authoritative reference and state only what a
professional brief needs to say beyond it (the deliverable, the grading
approach, the workflow). Nothing about the simulator's mechanics needs to
be hidden from the agent -- everything is disclosed, unlike a task with a
secret to discover.

## Mechanical requirements (non-negotiable)

- Closing paragraph, exact, nothing after it, one trailing newline:
  `You have 10800 seconds to complete this task. Do not cheat by using
  online solutions or hints specific to this task.`
  (10800 must match `[agent].timeout_sec` in task.toml.)
- Keep the whole file well under ~10,000 characters, and avoid restating
  `environment/sim/README.md`'s contract in full -- that document is
  agent-visible and authoritative; the instruction should describe the
  deliverable and grading, not re-derive every simulator rule.
- Do not state the exact pass bar cost (370.0), the exact reference
  policy's cost (318.5), or the exact naive baseline's cost (1451.5) -- say
  that a quality bar exists and that it was calibrated against measured
  baseline and reference performance, without giving the numbers.
- Do not name which of the two heuristics we tested performed better, or
  describe their logic -- that would hand the agent a specific design to
  copy rather than requiring their own empirical validation.

## What the agent is given (all under /app)

- `sim/README.md` -- the complete, authoritative simulator contract:
  exact timing model, fatigue formula (180 continuous minutes triggers a
  1.25x duration multiplier, reset by a 15-minute break), SLA-breach
  cascade rule (urgent jobs only, spawns one 30-minute follow-up with a
  60-minute deadline), overtime cap enforcement, and the exact cost
  formula (`overtime_minutes * 1.5 + breaches * 200 + followups_spawned * 50`,
  lower is better).
- `sim/simulator.py` -- the actual executable implementation of that
  contract; the agent can read or import it directly (e.g. to write their
  own local test harness against the sample scenarios).
- `data/sample_24/`, `data/sample_13/`, `data/sample_97/` -- three
  complete sample scenarios (`technicians.csv`, `jobs.csv`, `config.json`),
  each with a different technician roster and job mix, for the agent to
  develop and test a policy against locally. These are NOT the scenario
  used for grading.
## Required output

- `/app/outputs/policy.py` -- a Python module defining exactly one
  function: `def decide(state) -> list[tuple[str, str]]`. `state` exposes
  `current_time`, `free_technicians` (each with `tech_id`, `skills`,
  `continuous_work`, `shift_end`, `overtime_used`, `max_overtime`), and
  `pending_jobs` (each with `job_id`, `required_skill`, `duration`,
  `priority`, `deadline`, `arrival_time`) -- exact field names as given in
  `sim/README.md` and `sim/simulator.py`'s `TechSnapshot`/`JobSnapshot`.
  `decide` is called once at shift start and once whenever any technician
  becomes free or any job arrives, but only when at least one technician
  is free and at least one job is pending. It returns a list of
  `(technician_id, job_id)` pairs to assign immediately; `[]` means assign
  nothing right now.
- The module must contain no other required interface; the agent may
  define helper functions/classes/state inside it freely, but grading only
  ever calls `decide`.

## How grading works (state that this exists; do not give the numbers)

- The submitted `policy.py` is imported and run, via the real simulator,
  against a single held-out shift scenario the agent never sees the data
  for -- different technicians, different jobs, from any sample scenario
  provided. This is why testing only against the given samples is not
  suficient by itself; the policy needs to generalize.
- Only the sequence of assignments `decide()` actually returns is used for
  scoring; grading independently replays and re-validates that sequence
  under the same rules (an assignment that wasn't actually legal at that
  moment -- e.g. naming a technician who wasn't free, or a skill mismatch
  -- is simply not applied, not an error).
- There is a hidden pass/fail cost bar for the held-out scenario. It was
  calibrated by directly measuring a naive baseline policy and a
  considered reference policy's real performance on real scenarios and
  confirming a substantial, genuine gap between them -- state plainly that
  such a bar exists and must be cleared, without stating its value.
- `decide` must be deterministic: the same `state` must always produce the
  same returned list. Non-deterministic policies (e.g. depending on
  wall-clock time, unseeded randomness, or external state) may replay
  inconsistently and are the agent's own risk.
- Grading runs the whole held-out shift's simulation, calling `decide` at
  every decision point (dozens of calls), under a combined wall-clock
  budget of 120 seconds for the entire run. State this concrete number --
  heavy per-call computation (deep lookahead, search, simulation-based
  self-evaluation inside `decide`) counts against this same budget, and a
  policy that runs out of time fails the same way a crashing one does. The
  previous draft never disclosed that any time budget existed at all,
  which was flagged as an undisclosed operational constraint and caused a
  rejection -- this must be stated plainly this time.
- A policy.py that fails to import, does not define `decide`, or raises
  during a call is treated as a failing submission, not a partial-credit
  case.

## Suggested workflow to mention (not a required exact sequence)

The agent can write and run the simulator locally (it is plain Python,
fully given) against the three sample scenarios to develop and iterate on
a policy before submitting. There is no tool invocation required beyond
writing ordinary Python and running it -- unlike a task with a hidden fact
to discover via a specific command, this task's realism comes from
needing to actually test a design against simulated outcomes, which the
agent can do with the given `simulator.py` and sample data directly.
