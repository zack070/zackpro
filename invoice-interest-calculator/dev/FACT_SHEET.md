# Fact sheet for instruction.md

Every fact below is something the sealed verifier actually depends on, or a
mechanical constraint on the instruction file itself. Write instruction.md
as a natural professional brief covering these -- do not transcribe this as
a bullet list, and do not restate `environment/engine/README.md`'s full rule
text verbatim; point to it as the authoritative reference and state only
what a professional brief needs to say beyond it (the deliverable, the
grading approach, the workflow). Unlike the two previous tasks this
session, there is no "insight to withhold" about a hidden problem class --
the calculation rules themselves are meant to be fully disclosed (that's
the whole spec), same as `environment/engine/README.md` already does. What
must stay hidden is only the SPECIFIC grading numbers and which exact
scenarios/rule-interactions the held-out test emphasizes.

## Mechanical requirements (non-negotiable)

- Closing paragraph, exact, nothing after it, one trailing newline:
  `You have 10800 seconds to complete this task. Do not cheat by using
  online solutions or hints specific to this task.`
  (10800 must match `[agent].timeout_sec` in task.toml.)
- Keep the whole file well under ~10,000 characters, and avoid restating
  `environment/engine/README.md`'s rules in full.
- Do not state the exact pass bar (81/85 queries, 95.3%), the exact
  tolerance value's role as a "how close is close enough" lever (state
  the tolerance value itself is fine, since it's disclosed in
  README.md, but don't say "getting most rules right is probably
  enough" or similar), or any of the specific adversarial-probe
  percentages measured (worst 35.3%, best 82.4%). Say that a quality
  bar exists and was calibrated by direct measurement against many
  held-out test cases, without giving numbers.
- Do NOT hint at which specific rule interactions the grading data
  emphasizes (e.g. don't say "pay close attention to compounding across
  a leap year" or "grace period boundaries are commonly gotten wrong").
  The instruction should point the agent at the full rules in
  README.md and let them work out for themselves which edge cases
  matter and how to test for them -- do not do that analysis for them.
  This is different from the previous two tasks' "never name the
  algorithm/problem-class" rule (there is no hidden problem-class
  reframing here, the rules are the whole spec) but the SAME underlying
  principle: recognizing which parts of a fully-disclosed spec are
  easy to get subtly wrong, and proving it to yourself by testing, is
  part of the actual difficulty. Naming the specific traps away.

## What the agent is given (all under /app)

- `engine/README.md` -- the complete, authoritative rules: what interest
  accrues on and starting when, how the rate schedule is selected per
  day, day-count conventions, compounding timing and mechanics, the
  late-fee trigger condition and amount calculation (flat or percent
  with an optional cap), payment allocation order and what happens on
  overpayment, and the exact rounding rule (only the final number is
  rounded, nothing intermediate).
- `engine/engine.py` -- pure data-loading helpers (parses the CSV/JSON
  input files into plain Python dicts with real `datetime.date` values)
  -- it does NOT compute anything. The agent can read or import it
  directly.
- `data/sample_1/`, `data/sample_2/`, `data/sample_3/` -- three complete
  sample scenarios (`invoices.csv`, `payments.csv`,
  `jurisdiction_rules.json`, `queries.csv`), each independently
  generated with the same randomized rule variety (rate schedules,
  compounding, day-count conventions, late fee types, allocation
  orders) as the real grading data, for the agent to develop and test a
  policy against locally. These are NOT hand-picked to hit every edge
  case the way the held-out grading scenario is -- they are for
  general development, not a checklist of what to handle. It's fine to
  describe their scale plainly (how many invoices/payments/queries
  roughly) since that's just descriptive of the data.

## Required output

- `/app/outputs/policy.py` -- a Python module defining exactly one
  function: `def compute_balances(invoices, payments,
  jurisdiction_rules, queries) -> dict`. `invoices` and `payments` are
  lists of dicts (every field disclosed in README.md, with date fields
  as `datetime.date` objects, matching `engine.py`'s loaders exactly).
  `jurisdiction_rules` is a dict keyed by `jurisdiction_code`.
  `queries` is a list of dicts, each `{query_id, invoice_id,
  as_of_date}` -- asking for the total balance owed on that invoice as
  of that date. The function must return a dict mapping `query_id ->
  balance_cents` (an integer number of cents) for every query.
- The module must contain no other required interface; the agent may
  define helper functions/classes freely, but grading only ever calls
  `compute_balances`.

## How grading works (state that this exists; do not give the numbers)

- The submitted `policy.py` is imported and its `compute_balances()`
  function is called ONCE against a single held-out batch of invoices,
  payments, and queries the agent never sees -- different jurisdictions
  and dates from any sample scenario provided. This is why testing only
  against the given samples is not sufficient by itself; the policy
  needs to correctly implement the FULL rules, not just whatever
  happens to be exercised by the samples.
- This is a deterministic calculation with no search, no randomness,
  and no live/interactive element -- it is a pure function of its
  inputs. There is no separate determinism requirement to state (unlike
  a prior task this session with a search-based reference), because
  nothing about this computation is expected to vary run to run in the
  first place.
- Each query's submitted balance is checked against the correct value
  independently recomputed by the verifier, within a small, disclosed
  cents tolerance (see README.md's rounding section for why: a
  legitimate but different rounding order can differ by a cent or two
  over a long accrual period, and that's not meant to be penalized).
  There is a hidden pass/fail bar on how many queries must be answered
  correctly within that tolerance. State plainly that such a bar
  exists and was calibrated by directly measuring several plausible
  implementations' real performance on the held-out data and
  confirming a substantial, real gap between the weaker and stronger
  ones, without stating the bar's value or which implementations were
  tested.
- A policy.py that fails to import, does not define `compute_balances`,
  raises when called, or returns something that isn't a dict is treated
  as a failing submission, not a partial-credit case.
- Grading gives the single `compute_balances()` call a wall-clock budget
  of 60 seconds. State this concrete number as a safety ceiling against
  a runaway computation -- there is no reason a correct, reasonably
  written implementation should come close to it (this is a
  closed-form-per-day calculation over a modest number of invoices, not
  a search), so do not suggest that computation time is a meaningful
  axis of difficulty here at all.

## Suggested workflow to mention (not a required exact sequence)

The agent can write and run their own local scoring against the three
sample scenarios (comparing their function's output to whatever they
believe is correct, since no ground-truth answers are provided for the
samples) to develop and iterate on an implementation before submitting.
There is no tool invocation required beyond writing ordinary Python and
running it. Do not suggest which specific rule combinations are worth
testing by hand -- working that out from the full rules in README.md is
part of the task.
