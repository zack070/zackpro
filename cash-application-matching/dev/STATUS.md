# Status: set aside after round 5

## Decision

Setting this task aside rather than resubmitting again. Bundle preserved
as-is (not deleted) in case a future redesign of the scoring formula makes
it viable.

## What round 5's reviewer found

A ~20-line best-fit-decreasing greedy (sort payments descending, place
each on the tightest-fitting invoice within tolerance, else the neediest)
scored 777,180 cents on the held-out scenario -- below the 855,000 bar
and below the shipped reference's own 810,433. Confirmed by direct
reproduction: this is real, not a measurement error on the reviewer's
part. My own adversarial `best_fit_decreasing.py` probe used a weaker
tie-break rule (`min(open_invs, key=gap_after)` treating overshoot and
undershoot symmetrically) that made a correctly-implemented version of
the same idea look far weaker (5,507,792) than it actually is.

## What I found chasing the fix

Rebuilt the reference around the correct greedy's construction (sort
payments descending, size-match to the neediest invoice) as the seed,
plus richer annealing moves (single reassignment + pairwise swap). This
got the reference down to 499,349 (1.97%) on held-out, a real 35.7%
improvement over the corrected greedy alone.

But then stress-tested it against the simplest thing a reviewer would
try next: the SAME greedy seed (in both ascending and descending payment
order, for seed diversity) refined by a **plain, deterministic,
non-annealing hill climb** -- fixed iteration/restart counts, no
wall-clock dependency, so it stays fully compliant with the task's own
determinism requirement. Given the *exact same fixed compute budget* as
the reference (25 restarts x 15,000 iterations x 2 seed variants, ~45-48s,
well inside the 140s budget), this plain hill climb reached:

| scenario | reference | plain hill climb (2 seeds, fixed budget) | margin |
|---|---|---|---|
| held_out | 499,349 | 518,790 | 3.7% |
| sample_51 | 659,764 | 663,592 | 0.6% |
| sample_52 | 500,378 | 498,351 | **-0.4% (hill climb wins)** |
| sample_53 | 589,549 | 612,882 | 3.8% |

On sample_52 the plain, unsophisticated, fully-deterministic hill climb
actually beat the annealing-based reference. There is no bar position
that survives this: any bar loose enough to admit the reference is loose
enough to admit this trivial hill climb too, at least some of the time.

Also tried and ruled out as fixes:
- **2x instance scale** (payments_range=(45,60), invoices_range=(30,45)):
  margin didn't widen (4.3%) -- relative cost actually improves for
  every approach as scale grows, because a larger shared payment pool
  makes near-exact coverage easier to find by any method, not harder.
- **Narrower payment/invoice amount range** (8000-15000 instead of
  5000-250000, removing the size hierarchy greedy exploits): made the
  problem uniformly worse (all approaches landed around 8.8%-9.0%) but
  did not separate simple from sophisticated approaches at all.

## Root cause

This is a different failure mode from field-service-dispatch's (which
was a noisy myopic-online-decision architecture). Cash-application-matching
is a clean batch/offline problem and the exact-solving intractability
claim (round 1) still holds. The issue is narrower: the scoring formula
is a **continuous, partial-credit cost** (sum of dollar shortfalls across
all invoices) rather than a strict pass/fail per invoice. That makes the
optimization landscape smooth -- lots of "almost as good" neighboring
solutions exist everywhere -- which is exactly the condition under which
plain local search (hill climbing, no annealing needed) reliably finds
solutions within a percent or two of much more sophisticated search, for
naturally-distributed random instances. NP-hardness of *exact* optimal
solving does not imply hardness of *near-optimal* solving, and for this
problem shape, near-optimal solving turned out to be easy for any
competently-written heuristic, not just a hand-tuned one.

A scoring formula with per-invoice binary credit (cleared/not cleared,
rather than proportional shortfall) might behave differently -- it would
remove the smooth gradient signal that makes local search so effective
here -- but that requires reworking the human-authored cost-formula
language in instruction.md, and was not tested before setting the task
aside; do not assume it would work without measuring it first.
