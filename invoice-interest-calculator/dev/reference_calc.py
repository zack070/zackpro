"""Exact reference implementation for overdue-invoice balance
calculation. Ground truth: all accrual arithmetic is done in exact
Decimal (no intermediate rounding); only the final returned total is
rounded to the nearest cent (round-half-up).

Rules (all disclosed to the agent -- see environment/engine/README.md):
  - Interest accrues DAILY on the current remaining principal balance,
    starting the day after (due_date + grace_period_days), through and
    including as_of_date (or the day before as_of_date if as_of_date
    equals a payment date -- see payment timing below).
  - The rate used for a given day is the LATEST entry in
    interest_rate_schedule whose effective_date is <= that day.
  - day_count_convention divides the annual rate into a daily rate:
    "actual_365" divides by 365, "actual_360" divides by 360, regardless
    of leap years -- the convention name is taken literally, not
    adjusted for the actual calendar.
  - compounding "simple": accrued interest is tracked separately and
    never added to the principal balance.
    compounding "monthly": at the end of each calendar month (the last
    day of that month, or as_of_date if the period ends mid-month),
    interest accrued so far in that segment since the last capitalization
    is added to the principal balance (capitalized), and future daily
    interest accrues on the new, larger principal balance. Capitalization
    also happens immediately before applying any payment that falls after
    an un-capitalized completed calendar month.
  - late fee: a ONE-TIME fee triggers on the first day that is MORE than
    late_fee_threshold_days after due_date (i.e., day due_date +
    late_fee_threshold_days + 1) AND the invoice still has a positive
    total balance owed (principal + accrued interest + fees) on that
    day, counted BEFORE that day's own interest accrual. Once triggered,
    it never triggers again for this invoice. late_fee_type
    "flat_cents": late_fee_value is the fee amount directly.
    "percent_of_principal": fee = remaining principal balance at the
    trigger day * (late_fee_value / 10000) [late_fee_value is basis
    points, so 500 = 5.00%], capped at late_fee_cap_cents if that key is
    present and not None.
  - payments are applied in (payment_date, payment_id) order. On its
    date, a payment is applied AFTER that day's own interest accrual
    (and after any capitalization or late fee trigger scheduled for that
    day), reducing balances in the order given by
    payment_allocation_order (each stage fully paid before moving to the
    next): e.g. ["fees", "interest", "principal"] pays down any unpaid
    accrued fees first, then unpaid accrued interest, then principal.
    Any amount left over after all three stages are fully satisfied
    (an overpayment) is discarded -- not carried forward, not refunded,
    not tracked as a credit.
  - Returned balance = remaining principal + unpaid accrued interest +
    unpaid accrued fees, as of end-of-day on as_of_date, rounded to the
    nearest cent (round-half-up applied ONLY to this final number, not
    to any intermediate accrual).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import calendar


def _daily_rate(annual_rate: Decimal, day_count_convention: str) -> Decimal:
    divisor = Decimal(365) if day_count_convention == "actual_365" else Decimal(360)
    return annual_rate / divisor


def _rate_for_day(schedule, day: date) -> Decimal:
    applicable = [s for s in schedule if s["effective_date"] <= day]
    latest = max(applicable, key=lambda s: s["effective_date"])
    return Decimal(str(latest["annual_rate"]))


def _last_day_of_month(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def compute_balance(invoice, payments, jurisdiction_rules, as_of_date) -> int:
    rules = jurisdiction_rules[invoice["jurisdiction_code"]]
    due_date = invoice["due_date"]
    principal = Decimal(invoice["principal_cents"])
    accrued_interest = Decimal(0)
    accrued_fees = Decimal(0)
    fee_triggered = False
    uncapitalized_interest = Decimal(0)  # since last capitalization, for monthly compounding

    accrual_start = due_date + timedelta(days=rules["grace_period_days"] + 1)
    fee_trigger_day = due_date + timedelta(days=rules["late_fee_threshold_days"] + 1)

    payments_sorted = sorted(
        [p for p in payments if p["invoice_id"] == invoice["invoice_id"]],
        key=lambda p: (p["payment_date"], p["payment_id"]),
    )
    payments_by_date = {}
    for p in payments_sorted:
        payments_by_date.setdefault(p["payment_date"], []).append(p)

    day = accrual_start
    while day <= as_of_date:
        if day >= accrual_start:
            rate = _rate_for_day(rules["interest_rate_schedule"], day)
            daily = _daily_rate(rate, rules["day_count_convention"])
            day_interest = principal * daily
            accrued_interest += day_interest
            uncapitalized_interest += day_interest

        if not fee_triggered and day == fee_trigger_day:
            total_owed_before_fee = principal + accrued_interest + accrued_fees
            if total_owed_before_fee > 0:
                if rules["late_fee_type"] == "flat_cents":
                    fee = Decimal(rules["late_fee_value"])
                else:
                    fee = principal * (Decimal(rules["late_fee_value"]) / Decimal(10000))
                    cap = rules.get("late_fee_cap_cents")
                    if cap is not None:
                        fee = min(fee, Decimal(cap))
                accrued_fees += fee
            fee_triggered = True

        if rules["compounding"] == "monthly" and day == _last_day_of_month(day) and uncapitalized_interest > 0:
            principal += uncapitalized_interest
            uncapitalized_interest = Decimal(0)

        for p in payments_by_date.get(day, []):
            amount = Decimal(p["amount_cents"])
            for stage in rules["payment_allocation_order"]:
                if amount <= 0:
                    break
                if stage == "fees":
                    pay = min(amount, accrued_fees)
                    accrued_fees -= pay
                    amount -= pay
                elif stage == "interest":
                    pay = min(amount, accrued_interest)
                    accrued_interest -= pay
                    amount -= pay
                    # paying accrued interest doesn't reduce uncapitalized_interest
                    # tracking below the principal separately -- but paid interest
                    # should not be capitalized later, so remove it from the
                    # uncapitalized bucket too (can't capitalize what's been paid)
                    uncapitalized_interest = max(Decimal(0), uncapitalized_interest - pay)
                elif stage == "principal":
                    pay = min(amount, principal)
                    principal -= pay
                    amount -= pay

        day += timedelta(days=1)

    total = principal + accrued_interest + accrued_fees
    cents = int(total.to_integral_value(rounding=ROUND_HALF_UP))
    return cents
