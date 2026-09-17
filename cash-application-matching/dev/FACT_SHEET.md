# Fact sheet for instruction.md

Every fact below is something the sealed verifier actually depends on, or a
mechanical constraint on the instruction file itself. Write instruction.md
as a natural professional brief covering these -- do not transcribe this as
a bullet list, and do not restate `environment/engine/README.md`'s contract
verbatim; point to it as the authoritative reference and state only what a
professional brief needs to say beyond it (the deliverable, the grading
approach, the workflow). Nothing about the scoring mechanics needs to be
hidden from the agent -- everything is disclosed, unlike a task with a
secret to discover.

## Mechanical requirements (non-negotiable)

- Closing paragraph, exact, nothing after it, one trailing newline:
  `You have 10800 seconds to complete this task. Do not cheat by using
  online solutions or hints specific to this task.`
  (10800 must match `[agent].timeout_sec` in task.toml.)
- Keep the whole file well under ~10,000 characters, and avoid restating
  `environment/engine/README.md`'s contract in full.
- Do not state the exact pass bar (1,450,000 cents / $14,500.00), or any
  of the calibration numbers measured on the held-out scenario (best
  adversarial probe $26,962.59, reference $12,538.90, exact optimum
  $11,961.02) -- say that a quality bar exists and was calibrated by
  direct measurement, without giving the numbers.
- Do not describe the reference solution's specific approach (simulated
  annealing, or the bitmask-DP cross-check) -- it is fine, and probably
  useful, to say that this is fundamentally a combinatorial
  matching/partitioning problem and that sorting-and-greedy approaches
  reliably leave real money unmatched, since that framing is a fair
  description of the problem's nature, not a specific design to copy.

## What the agent is given (all under /app)

- `engine/README.md` -- the complete, authoritative scoring contract:
  the matching rules (payments atomic, at most one invoice each; multiple
  payments may combine on one invoice; cross-customer matches dropped
  silently), the exact tolerance value, and the exact cost formula.
- `engine/engine.py` -- the actual executable implementation of that
  contract; the agent can read or import it directly (e.g. to write their
  own local scoring harness against the sample scenarios).
- `data/sample_21/`, `data/sample_22/`, `data/sample_23/` -- three
  complete sample scenarios (`payments.csv`, `invoices.csv`), each with a
  different set of customers/amounts, for the agent to develop and test a
  policy against locally. These are NOT the scenario used for grading.
  Worth mentioning: every scenario spans many customers at once (dozens of
  payments and invoices total), and getting a low cost on any one customer
  requires deciding which of several payments combine to cover which
  invoice -- not simply pairing the payment that looks closest in size to
  each invoice.

## Required output

- `/app/outputs/policy.py` -- a Python module defining exactly one
  function: `def match(payments, invoices) -> dict`. `payments` and
  `invoices` are the full lists for the whole batch (every customer
  together, not one at a time); each item exposes `payment_id`/
  `customer_id`/`amount_cents` or `invoice_id`/`customer_id`/
  `amount_due_cents` respectively -- exact field names as given in
  `engine/README.md` and `engine.py`'s `Payment`/`Invoice` definitions.
  `match` is called exactly once. It returns a dict mapping
  `payment_id -> invoice_id` for every payment the agent wants applied;
  omitting a payment_id (or mapping it to `None`) leaves it unapplied.
- The module must contain no other required interface; the agent may
  define helper functions/classes freely, but grading only ever calls
  `match`.

## How grading works (state that this exists; do not give the numbers)

- The submitted `policy.py` is imported and its `match()` function is
  called once against a single held-out batch the agent never sees the
  data for -- different customers, different amounts, from any sample
  scenario provided. This is why testing only against the given samples
  is not sufficient by itself; the policy needs to generalize.
- Only the returned mapping is used for scoring; grading independently
  recomputes the cost from that mapping under the same rules (an
  assignment that wasn't actually legal -- e.g. a cross-customer match, or
  a nonexistent id -- is simply dropped, not an error).
- There is a hidden pass/fail cost bar for the held-out scenario. It was
  calibrated by directly measuring several different approaches' real
  performance on the held-out data -- multiple plausible sorting/greedy
  strategies, and an approach that instead treats the batch as a genuine
  combinatorial matching problem -- and confirming a substantial, real gap
  between the best greedy approach and a policy that searches the problem
  directly. State plainly that such a bar exists and must be cleared,
  without stating its value or describing the reference approach's
  specific algorithm.
- `match` must be deterministic: the same inputs should always produce
  the same returned mapping. There is no live/interactive element to this
  task -- it is a single batch computation, not something called
  repeatedly over simulated time.
- Grading runs the whole scoring pass under a combined wall-clock budget
  of 90 seconds for match() to return. State this concrete number --
  heavy computation (deep search, many restarts, exhaustive enumeration)
  counts against this budget, and a policy that runs out of time fails
  the same way a crashing one does.
- A policy.py that fails to import, does not define `match`, or raises
  when called is treated as a failing submission, not a partial-credit
  case.

## Suggested workflow to mention (not a required exact sequence)

The agent can write and run the scoring engine locally (it is plain
Python, fully given) against the three sample scenarios to develop and
iterate on a policy before submitting. There is no tool invocation
required beyond writing ordinary Python and running it. Since a low cost
requires genuinely partitioning payments among invoices (not just pairing
by size), it's worth mentioning that the agent will likely need to write
and test some kind of search or optimization approach rather than a single
sorting pass -- exactly how to do that is part of what the agent needs to
work out and validate against the sample scenarios.
