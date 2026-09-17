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
- Do not state the exact pass bar (855,000 cents / $8,550.00), or any of
  the calibration numbers measured on the held-out scenario (best
  plain-greedy adversarial probe $55,077.92, DP-seed-plus-hill-climb
  probe $9,287.81, reference $8,104.33) -- say that a quality bar exists
  and was calibrated by direct measurement, without giving the numbers.
  Also do not say anything characterizing how much compute or what kind
  of algorithm is worth using -- working that out is part of the task,
  and stating it would hand over the exact insight two different
  reviewers' own measurements caught this task missing before (one
  earlier version implied "use more time" was the lever; it wasn't -- a
  plain hill climb given a full time budget still fails. A later reviewer
  found that a specific seeding construction -- assign invoices
  smallest-first, then find the closest achievable payment combination --
  beats naive greedy seeding by a wide margin; do not say anything that
  would point toward processing invoices in a particular order or
  "finding the closest achievable combination" as a sub-step).
- Do not describe the reference solution's specific approach (simulated
  annealing, the bitset subset-sum seeding construction, or the
  bitmask-DP cross-check), AND do not name or hint at the underlying
  problem class (do not say "combinatorial matching," "subset-sum,"
  "partitioning," "NP-hard," or similar, and do not say that
  sorting-and-greedy approaches leave money unmatched). A prior task
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
  `match` is called TWICE per grading run, with the same inputs both
  times, specifically to verify the determinism requirement below -- the
  agent needs to know this so they don't write anything with hidden state
  or side effects that would behave differently across the two calls. It
  returns a dict mapping
  `payment_id -> invoice_id` for every payment the agent wants applied;
  omitting a payment_id (or mapping it to `None`) leaves it unapplied.
- The module must contain no other required interface; the agent may
  define helper functions/classes freely, but grading only ever calls
  `match`.

## How grading works (state that this exists; do not give the numbers)

- The submitted `policy.py` is imported and its `match()` function is
  called TWICE against a single held-out batch the agent never sees the
  data for -- different customers, different amounts, from any sample
  scenario provided. This is why testing only against the given samples
  is not sufficient by itself; the policy needs to generalize.
- Both returned mappings are checked for exact equality (the determinism
  requirement, actually enforced -- see below); the first mapping is also
  independently rescored under the real rules (an assignment that wasn't
  actually legal -- e.g. a cross-customer match, or a nonexistent id -- is
  simply dropped, not an error).
- There is a hidden pass/fail cost bar for the held-out scenario. It was
  calibrated by directly measuring several different approaches' real
  performance on the held-out data and confirming a substantial, real gap
  between the weaker and stronger ones. State plainly that such a bar
  exists and must be cleared, without stating its value, without stating
  how many or what kind of approaches were measured, and without
  characterizing what distinguishes the weaker from the stronger ones.
- `match` must be deterministic: the same inputs should always produce
  the same returned mapping. This IS actually tested (the two calls above
  must return identical mappings) -- state this plainly and accurately,
  since a previous version stated this requirement without it being
  tested, which was itself flagged as a real problem. There is no
  live/interactive element to this task -- it is a batch computation, not
  something called repeatedly over simulated time.
- Grading gives the two `match()` calls together a combined wall-clock
  budget of 140 seconds. State this concrete number -- heavy computation
  counts against this budget, and a policy that runs out of time fails
  the same way a crashing one does. Do NOT suggest that using more of this
  budget helps quality, or that a specific amount of computation is
  needed -- a deterministic policy using a small, fixed, modest amount of
  computation is entirely capable of clearing the bar; the budget exists
  as a safety ceiling against runaway computation, not as a resource to
  maximize.
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
