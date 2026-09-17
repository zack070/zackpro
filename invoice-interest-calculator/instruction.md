Work in `/app`. The file to submit is `/app/outputs/policy.py`.

The calculation engine is already provided. `/app/engine/README.md` is the authoritative description of the balance rules, including accrual, rate schedules, day counting, compounding, late fees, payment allocation, overpayments, and rounding. Use `/app/engine/engine.py` as needed to see how the input files are loaded. Its date fields are provided to the policy as real `datetime.date` values.

The module needs one required function:

`def compute_balances(invoices, payments, jurisdiction_rules, queries) -> dict`

The function receives the complete batch. `invoices` and `payments` are lists of dictionaries, `jurisdiction_rules` is keyed by `jurisdiction_code`, and each query contains `query_id`, `invoice_id`, and `as_of_date`. Return a dictionary containing the calculated balance in cents for every query, using its `query_id` as the key. The returned balances must be integers.

The rest of the module is yours to structure. Helpers and classes are fine, but `compute_balances` is the only interface that will be called.

Three sample datasets are available under `/app/data/sample_1/`, `/app/data/sample_2/`, and `/app/data/sample_3/`. Each has invoices, payments, jurisdiction rules, and queries. They were generated with varied rule configurations and are useful for exercising the implementation, but they are not the grading cases and are not intended to cover every possible situation. Run your implementation against all three before submitting.

There are no answer files for the samples. Build whatever local checks you need to convince yourself that the balances agree with the rules in the README. Pay attention to the fact that the verifier evaluates each query independently and expects the full calculation described by the supplied rules.

The final evaluation imports `policy.py` and calls `compute_balances()` once with a separate held-out batch. The invoices, payments, jurisdictions, and dates in that batch are different from those in the supplied samples. Each returned query balance is independently recomputed by the grader and checked against the correct result using the small cents tolerance disclosed in the README.

A hidden quality bar determines whether enough of the held-out queries are answered correctly. It was set by directly measuring several implementations on held-out data and confirming a meaningful gap in their results. The exact bar is not disclosed.

This is a deterministic calculation. The same inputs should give the same dictionary. The function also needs to finish within the grader's 60-second wall-clock limit for its single call. A normal implementation should have plenty of room under that limit.

An import failure, missing `compute_balances`, an exception during the call, or a return value that is not a dictionary is a failed submission rather than a partial result.

Leave the engine and its input data unchanged. The work belongs in `/app/outputs/policy.py`.

You have 10800 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
