# Status: set aside after failed easiness probe

Real platform probe result (2026-09-17): 3 of 3 low-effort attempts solved
(allowed <=1). This is a stronger signal than the three prior review
rejections and confirms a structural problem, not a patchable one.

## Root cause

Three different candidate "difficulty mechanics" were tried across this
task's development, in this order:
1. Fatigue-awareness (duration multiplier after continuous work threshold)
2. Overtime-capacity reservation (prefer techs with more/less remaining
   capacity)
3. A scarcity-reservation exclusion bug (see dev/batch_matching_policy.py
   git history / this session's transcript), tested as a candidate
   "planted bug" for a diagnosis-and-repair redesign

All three showed the same failure mode when swept across multiple random
scenario instances: sometimes the "aware" policy beats the "unaware" one,
sometimes it's worse, with no consistent direction. This is not
calibration bad luck -- it appears to be a structural property of this
task's simulator: a myopic, per-event online decision loop (decide()
called repeatedly as state unfolds, no lookahead into future arrivals)
makes any local heuristic tie-break noisy, because "correct" often
depends on information the policy doesn't have yet.

The one mechanic that DID show a robust, non-noisy effect was skill
scarcity as a hard binary eligibility constraint (batch matching vs.
greedy, see the "Redesign around batch assignment matching" work) -- but
that alone reaches an apparent optimum via a fairly shallow insight
("solve the batch jointly, reserve scarce-skill techs"), which is
recognizable directly from the fully-disclosed simulator contract without
genuine experimentation. Combined with an instruction.md hint that named
this reframing directly (since retracted from the general playbook), this
made the task solvable by a low-effort agent close to 100% of the time.

## Decision

Cut losses here rather than attempt a 4th redesign. See
harbor-task-builder skill (references/difficulty-calibration.md, "When
the decision architecture itself resists robust difficulty") for the
generalized lesson this produced. Effort redirected to
cash-application-matching, a batch/offline combinatorial problem (NP-hard
Multiple Subset-Sum) whose hardness is a proven worst-case property
rather than an online-decision artifact -- it showed zero exceptions
across 20 test seeds in dev-time calibration, unlike anything tried here.

This task bundle is left in place (not deleted) in case a genuinely
different architectural approach is worth revisiting later -- e.g.
restructuring it as a batch/offline problem itself, rather than a live
decide()-per-event loop.
