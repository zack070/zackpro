# Cash-application scoring contract

`engine.py` is the complete, authoritative implementation of how a submitted
match is scored. This document explains it in prose; where the two differ,
the code is correct. Nothing about how scoring works is hidden from you.

## Data

You are given two lists for a batch of customers:

- **Payments**: each has `payment_id`, `customer_id`, `amount_cents`.
- **Invoices**: each has `invoice_id`, `customer_id`, `amount_due_cents`.

All amounts are integer cents (no floating point). Multiple customers are
present in the same batch; a payment and an invoice belonging to different
customers can never be matched to each other.

## Your submission

You submit a Python module exposing:

```python
def match(payments, invoices) -> dict[str, str]:
    ...
```

`payments` and `invoices` are the full lists for the batch (every
customer's payments and invoices together, not one customer at a time).
Return a dict mapping `payment_id -> invoice_id` for every payment you want
applied. Omitting a payment_id from the dict (or mapping it to `None`)
leaves it unapplied. `match` is called exactly once per grading run.

## Matching rules

- **A payment may be applied to at most one invoice.** There is no
  mechanism to split a single payment across multiple invoices.
- **Multiple payments may be applied to the same invoice.** Their amounts
  accumulate toward that invoice's `amount_due_cents`.
- **A payment may only be applied to an invoice with the same
  `customer_id`.** An attempt to cross customers is dropped silently
  (that payment reverts to unapplied) -- it does not raise an error and
  does not affect any other assignment in your submission.
- Referencing a `payment_id` or `invoice_id` that doesn't exist in the
  batch is dropped the same way.
- There is a fixed short-pay tolerance, `TOLERANCE_CENTS` (see
  `engine.py` for the exact value): an invoice whose applied total falls
  short of `amount_due_cents` by no more than this amount is treated as
  fully cleared.
- There is no cap on overpaying an invoice and no penalty for doing so
  directly -- but every payment is a limited, non-renewable resource, so
  applying more of it to one invoice than that invoice needs is never
  beneficial once every invoice's realistic needs are accounted for.

## Cost (lower is better; this is what you are scored on)

```
total_cost_cents = sum over invoices of
                        max(0, amount_due_cents - applied_total - TOLERANCE_CENTS)
                  + sum over payments never applied to any (valid) invoice
                        of that payment's amount_cents
```

The first term is money customers owe that never got recognized as paid.
The second is money received that never got applied anywhere. Both are
computed purely from your returned mapping and the batch data -- there is
no hidden "correct" matching your submission is compared against, and no
credit or penalty beyond this formula.
