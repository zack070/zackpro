# Overdue-invoice balance calculation: rules

This is the complete, authoritative specification for computing how much
is owed on an overdue invoice as of a given date. Nothing about these
rules is hidden -- getting the right answer is a matter of implementing
them correctly, including how they interact.

`engine.py` in this directory loads the input files into plain Python
objects (dicts) but does not compute anything -- the calculation itself
is the task.

## Inputs

- **Invoice**: `invoice_id`, `customer_id`, `jurisdiction_code`,
  `principal_cents`, `due_date`.
- **Payments**: zero or more per invoice, each `payment_id`,
  `invoice_id`, `amount_cents`, `payment_date`.
- **Jurisdiction rules** (looked up by `invoice.jurisdiction_code`):
  `day_count_convention` (`"actual_365"` or `"actual_360"`),
  `grace_period_days`, `compounding` (`"simple"` or `"monthly"`),
  `late_fee_type` (`"flat_cents"` or `"percent_of_principal"`),
  `late_fee_value`, `late_fee_cap_cents` (may be `None`),
  `late_fee_threshold_days`, `interest_rate_schedule` (a list of
  `{effective_date, annual_rate}`, at least one entry), and
  `payment_allocation_order` (a permutation of
  `["fees", "interest", "principal"]`).
- **Query**: `query_id`, `invoice_id`, `as_of_date` -- asks for the total
  balance owed on that invoice at end-of-day on that date.

## The calculation

Interest accrues **daily** on the invoice's current remaining principal
balance, starting the day after `due_date + grace_period_days` (i.e. no
interest at all during the grace period), through and including
`as_of_date`.

The **annual rate** used for a given day is whichever entry in
`interest_rate_schedule` has the latest `effective_date` that is still
`<=` that day. A schedule can have more than one entry, meaning the rate
can change partway through an invoice's overdue life -- each day uses
whatever rate was in effect *on that specific day*, not the rate at
`due_date` or at `as_of_date`.

The **daily rate** is the annual rate divided by 365 for
`"actual_365"`, or by 360 for `"actual_360"` -- taken literally,
regardless of leap years.

**Compounding**: under `"simple"`, accrued interest is tracked
separately and never affects the principal balance. Under `"monthly"`,
at the end of each calendar month, the interest that has accrued since
the last such capitalization is added to (capitalizes into) the
principal balance -- so interest for the following month accrues on a
larger base. This includes across a February, leap year or not.

**Late fee**: triggers exactly **once**, on the first day that is more
than `late_fee_threshold_days` after `due_date`, provided the invoice
still has a positive total balance owed at that point (checked before
that day's own interest accrual). `"flat_cents"` uses `late_fee_value`
directly as the fee. `"percent_of_principal"` computes the fee as the
*current remaining principal balance* at the trigger day times
`late_fee_value` basis points (so `500` means 5.00%), capped at
`late_fee_cap_cents` if that field is not `None`.

**Payments**: applied in `(payment_date, payment_id)` order. On its own
date, a payment is applied *after* that day's interest accrual (and
after any capitalization or late-fee trigger scheduled for that same
day), and pays down balances in the exact order given by
`payment_allocation_order` -- each stage fully satisfied before any
amount moves to the next stage. Any amount left over after all three
stages are satisfied (an overpayment) is discarded, not carried forward
or refunded.

**Rounding**: do all accrual arithmetic in exact (non-floating-point)
arithmetic with no intermediate rounding. Round only the single final
number you return, to the nearest cent (round-half-up).

## Output

The returned balance for a query is:
`remaining principal + unpaid accrued interest + unpaid accrued fees`,
as of end-of-day on `as_of_date`, in cents.
