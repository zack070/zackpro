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
- Do not state the exact pass bar (1,200,000 cents / $12,000.00), or any
  of the calibration numbers measured on the held-out scenario (best
  adversarial probe $55,077.92, full-budget plain hill-climb $16,181.85,
  adaptive annealing reference $9,274.70) -- say that a quality bar exists
  and was calibrated by direct measurement, without giving the numbers.
  Also do not say anything about HOW MUCH of the 90-second time budget is
  worth using, or that using more time helps -- that is itself part of
  what a submission needs to work out (a plain hill climb given the full
  budget does not clear the bar; a better algorithm using the same budget
  does), and stating it directly would hand over the exact insight a
  reviewer's own measurement caught this task missing before.
- Do not describe the reference solution's specific approach (simulated
  annealing, or the bitmask-DP cross-check), AND do not name or hint at
  the underlying problem class (do not say "combinatorial matching,"
  "subset-sum," "partitioning," "NP-hard," or similar, and do not say
  that sorting-and-greedy approaches leave money unmatched). A prior task
  built this session (field-service-dispatch) failed its real difficulty
  probe (a live agent solved it 3 of 3 times at low effort) immediately
  after its instruction was written to include exactly this kind of "fair
  framing hint" -- recognizing the problem's true structure is a large
  part of the actual difficulty here, not a neutral detail that's safe to
  give away. State the deliverable, the rules, and that a quality bar
  exists, and let the agent discover on their own that pairing-by-size
  isn't enough.

## What the agent is given (all under /app)

- `engine/README.md` -- the complete, authoritative scoring contract:
  the matching rules (payments atomic, at most one invoice each; multiple
  payments may combine on one invoice; cross-customer matches dropped
  silently), the exact tolerance value, and the exact cost formula.
- `engine/engine.py` -- the actual executable implementation of that
  contract; the agent can read or import it directly (e.g. to write their
  own local scoring harness against the sample scenarios).
- `data/sample_51/`, `data/sample_52/`, `data/sample_53/` -- three
  complete sample scenarios (`payments.csv`, `invoices.csv`), each with a
  different set of customers/amounts, for the agent to develop and test a
  policy against locally. These are NOT the scenario used for grading. It
  is fine to state their scale plainly (how many customers, roughly how
  many payments/invoices each) since that's just descriptive of the data
  -- do not characterize what kind of reasoning or approach is needed to
  do well on them.

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
  performance on the held-out data and confirming a substantial, real gap
  between the weaker and stronger ones. State plainly that such a bar
  exists and must be cleared, without stating its value, without stating
  how many or what kind of approaches were measured, and without
  characterizing what distinguishes the weaker from the stronger ones.
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
required beyond writing ordinary Python and running it. Do not say
anything about what KIND of approach is likely to be needed (search,
optimization, sorting, or otherwise) -- working that out is the task.
