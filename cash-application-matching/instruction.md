Work in `/app`. The file to submit is `/app/outputs/policy.py`.

The matching engine is already provided. `/app/engine/README.md` is the authority for the matching rules and scoring, and `/app/engine/engine.py` contains the implementation if you need to check how those rules are applied.

Your module needs one required function:

`def match(payments, invoices) -> dict`

The two arguments contain the complete batch, with all customers together. Payment records use `payment_id`, `customer_id`, and `amount_cents`. Invoice records use `invoice_id`, `customer_id`, and `amount_due_cents`. The exact record definitions are available in the README and the engine code.

Return a mapping of `payment_id` to `invoice_id` for payments you want applied. A payment can also be left out of the mapping, or mapped to `None`, when you do not want to apply it. The grader only calls `match`, so any other helpers or internal code are up to you.

The engine's rules matter when deciding what to return. Payments are indivisible and each payment can be used for at most one invoice, while an invoice can receive more than one payment. Matches involving different customers are discarded by the engine.

There are three sample batches available for local testing:

`/app/data/sample_51/`
`/app/data/sample_52/`
`/app/data/sample_53/`

Each contains `payments.csv` and `invoices.csv`. They cover different customers and amounts and are not the batch used for grading.

The final run uses one separate held-out batch. Its customers and amounts are different from the supplied samples. The grader imports your module and calls `match()` twice with the same held-out batch, to check the determinism requirement below, then calculates the score itself from the first call's returned mapping. An invalid assignment, such as one using a nonexistent ID or crossing customers, is dropped during that replay rather than causing a special exception.

There is a hidden pass/fail quality bar for the held-out batch. It was calibrated by direct measurement of performance on that data. Clearing the bar is required; producing a mapping that merely runs is not enough.

Keep the result deterministic. The same input lists should always lead to the same mapping, including across the two calls described above. This is a batch computation, not an interactive process.

There is a combined 140-second wall-clock limit for the two `match()` calls together. Time spent inside `match()` counts toward it, so make sure the final implementation actually finishes both calls within that limit. A timeout is treated as a failed submission.

The engine and sample data are there for you to test with. Leave the engine itself unchanged.

You have 10800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
