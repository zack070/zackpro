Work in `/app`. The file to submit is `/app/outputs/policy.py`.

The matching engine is already provided. `/app/engine/README.md` is the authority for the matching rules and scoring, and `/app/engine/engine.py` contains the implementation if you need to check how those rules are applied. Read both before settling on the behavior of your policy.

Your module needs one required function:

`def match(payments, invoices) -> dict`

The two arguments contain the complete batch, with all customers together. Payment records use `payment_id`, `customer_id`, and `amount_cents`. Invoice records use `invoice_id`, `customer_id`, and `amount_due_cents`. The exact record definitions are available in the README and the engine code.

Return a mapping of `payment_id` to `invoice_id` for payments you want applied. A payment can also be left out of the mapping, or mapped to `None`, when you do not want to apply it. The grader only calls `match`, so any other helpers or internal code are up to you.

The engine's rules matter when deciding what to return. Payments are indivisible and each payment can be used for at most one invoice, while an invoice can receive more than one payment. Matches involving different customers are discarded by the engine. The README has the rest of the exact rules, including the tolerance and cost calculation, so use those rather than making assumptions about them.

There are three sample batches available for local testing:

`/app/data/sample_21/`
`/app/data/sample_22/`
`/app/data/sample_23/`

Each contains `payments.csv` and `invoices.csv`. They cover different customers and amounts and are not the batch used for grading. Run your policy against all three and inspect the actual scores before submitting.

The final run uses one separate held-out batch. Its customers and amounts are different from the supplied samples. The grader imports your module, calls `match()` once, and then calculates the score itself from the mapping you return. An invalid assignment, such as one using a nonexistent ID or crossing customers, is dropped during that replay rather than causing a special exception.

There is a hidden pass/fail quality bar for the held-out batch. It was calibrated by direct measurement of performance on that data. Clearing the bar is required; producing a mapping that merely runs is not enough.

Keep the result deterministic. The same input lists should always lead to the same mapping. This is one batch call, not an interactive process.

There is a combined 90-second wall-clock limit for the scoring pass. Time spent inside `match()` counts toward it, so make sure the final implementation actually finishes within that limit. A timeout is treated as a failed submission.

Before you finish, check that `policy.py` imports cleanly, defines `match`, and completes successfully on the supplied scenarios. The engine and sample data are there for you to test with. Leave the engine itself unchanged.

You have 10800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
