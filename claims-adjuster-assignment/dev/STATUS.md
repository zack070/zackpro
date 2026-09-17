# Status: abandoned before instruction.md, during difficulty validation

## What this was

A batch weighted bipartite matching task: assign claims to certified
adjusters (hard eligibility, one claim per adjuster per batch) to
maximize total captured value, with the reference computing the
provably exact optimum via a from-scratch Hungarian algorithm
(cross-validated against scipy.optimize.linear_sum_assignment on 40+
random trials, byte-exact match including edge cases).

This was chosen specifically because it matched the harbor-task-builder
skill's own documented "strongest pattern found so far": greedy,
one-at-a-time assignment is textbook-suboptimal for weighted bipartite
matching, versus a joint/optimal solver.

## What measurement found

That pattern did not replicate here. Swept multiple parameter regimes
(claim-type count, certification breadth, proficiency range, claims:
adjusters ratio, batch size from 5-7 up to 18-28 per region) plus a
cardinality-only objective (count of claims matched, not dollar value)
plus deliberately correlated adjuster skill (some adjusters globally
better, to create real "star" competition). In every configuration, the
best of 6 adversarial greedy probes landed within 0.0%-3.2% of the
provably exact optimum. This is not a measurement artifact -- it is a
real, known property of bipartite matching: greedy algorithms (both
"highest-value-first, best available" for weighted matching, and
"most-constrained-first" for cardinality matching) are close to optimal
on typical/random bipartite graphs, even though their WORST-CASE
approximation ratio is much weaker (1/2 for cardinality matching). The
worst case essentially never appears in naturally-generated data;
producing it requires deliberately adversarial instance construction,
which risks looking planted rather than like real business data, and
even then may not survive a reviewer trying yet another greedy variant.

## Why this matters beyond this one task

This is the SECOND unrelated task design (after cash-application-matching's
subset-sum-style partition problem) where a "textbook worst-case
suboptimality" argument for difficulty failed to survive direct
measurement against real generated data. The pattern across both:
worst-case complexity results (NP-hardness, greedy's 1/2-approximation
bound, etc.) describe adversarial instances, not typical ones, and
typical randomly-generated instances of a "search for a good
combinatorial structure" problem are usually much easier than the
complexity-class label suggests. See difficulty-calibration.md's
"Intractable-to-solve-exactly does not mean hard-to-approximate-well"
section (added after cash-application-matching) and the correction added
there after this task, which now qualifies the "greedy vs. joint
optimization" pattern instead of stating it as reliably strong.

## Decision

Set aside before writing any verifier, task.toml, or instruction.md --
caught during the required pre-build difficulty measurement, so no
review cycle was spent on it. Pivoting to a fundamentally different
difficulty mechanism: exact correctness against a complex, rule-heavy
specification (many interacting edge cases, binary pass/fail per case)
rather than numeric optimization quality against a heuristic baseline.
That axis does not depend on any claim about how hard a search problem
is in practice, so it isn't exposed to this failure mode at all.
