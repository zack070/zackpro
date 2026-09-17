#!/bin/sh
# Writes the reference policy.py directly to the declared output
# artifact path. Deliberately embeds the file content via heredoc
# instead of copying a sibling file: a prior version resolved its own
# directory (via "$0" / "${BASH_SOURCE[0]}") and copied policy.py from
# there, but the oracle run scored 0/0/0 even after fixing that
# version's bash-vs-sh portability bug, meaning the failure isn't (only)
# about shell syntax -- it may be about whether solution/'s sibling
# files are actually present alongside solve.sh wherever the oracle
# executes it. Embedding the content removes that dependency entirely:
# the only things this script needs are a POSIX shell, mkdir, and a
# heredoc redirect, and it does not need to find or read any other file.
set -eu

mkdir -p /app/outputs

cat > /app/outputs/policy.py << 'POLICY_PY_EOF'
"""Reference solution: exact overdue-invoice balance calculation per
README.md's rules. All accrual arithmetic uses Decimal with no
intermediate rounding; only the final returned value per query is
rounded to the nearest cent."""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import calendar


def _daily_rate(annual_rate, day_count_convention):
    divisor = Decimal(365) if day_count_convention == "actual_365" else Decimal(360)
    return Decimal(str(annual_rate)) / divisor


def _rate_for_day(schedule, day):
    applicable = [s for s in schedule if s["effective_date"] <= day]
    latest = max(applicable, key=lambda s: s["effective_date"])
    return Decimal(str(latest["annual_rate"]))


def _last_day_of_month(d):
    last = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=last)


def _compute_one(invoice, payments_for_invoice, rules, as_of_date):
    due_date = invoice["due_date"]
    principal = Decimal(invoice["principal_cents"])
    accrued_interest = Decimal(0)
    accrued_fees = Decimal(0)
    fee_triggered = False
    uncapitalized_interest = Decimal(0)

    accrual_start = due_date + timedelta(days=rules["grace_period_days"] + 1)
    fee_trigger_day = due_date + timedelta(days=rules["late_fee_threshold_days"] + 1)

    payments_by_date = {}
    for p in sorted(payments_for_invoice, key=lambda p: (p["payment_date"], p["payment_id"])):
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
                    uncapitalized_interest = max(Decimal(0), uncapitalized_interest - pay)
                elif stage == "principal":
                    pay = min(amount, principal)
                    principal -= pay
                    amount -= pay

        day += timedelta(days=1)

    total = principal + accrued_interest + accrued_fees
    return int(total.to_integral_value(rounding=ROUND_HALF_UP))


def compute_balances(invoices, payments, jurisdiction_rules, queries):
    invoices_by_id = {inv["invoice_id"]: inv for inv in invoices}
    payments_by_invoice = {}
    for p in payments:
        payments_by_invoice.setdefault(p["invoice_id"], []).append(p)

    answers = {}
    for q in queries:
        invoice = invoices_by_id[q["invoice_id"]]
        rules = jurisdiction_rules[invoice["jurisdiction_code"]]
        pmts = payments_by_invoice.get(invoice["invoice_id"], [])
        answers[q["query_id"]] = _compute_one(invoice, pmts, rules, q["as_of_date"])
    return answers
POLICY_PY_EOF

echo "solve.sh: wrote /app/outputs/policy.py"
