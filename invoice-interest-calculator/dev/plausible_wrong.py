"""Adversarial probe battery: implementations a competent engineer might
plausibly write without catching every rule interaction. Each gets ONE
specific rule wrong while implementing everything else correctly (a
strawman that ignores everything would prove nothing)."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import calendar


def _last_day_of_month(d):
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def _base_calc(invoice, payments, jurisdiction_rules, as_of_date, *,
                ignore_rate_changes=False,
                ignore_grace_period=False,
                always_actual_365=False,
                never_compound=False,
                fee_threshold_off_by_one=False,
                wrong_allocation_order=None,
                round_daily=False,
                fee_uses_current_principal_after_payments=False):
    rules = jurisdiction_rules[invoice["jurisdiction_code"]]
    due_date = invoice["due_date"]
    principal = Decimal(invoice["principal_cents"])
    accrued_interest = Decimal(0)
    accrued_fees = Decimal(0)
    fee_triggered = False
    uncapitalized_interest = Decimal(0)

    grace = 0 if ignore_grace_period else rules["grace_period_days"]
    accrual_start = due_date + timedelta(days=grace + 1)

    threshold = rules["late_fee_threshold_days"]
    if fee_threshold_off_by_one:
        fee_trigger_day = due_date + timedelta(days=threshold)  # missing +1
    else:
        fee_trigger_day = due_date + timedelta(days=threshold + 1)

    allocation_order = wrong_allocation_order or rules["payment_allocation_order"]

    schedule = rules["interest_rate_schedule"]
    if ignore_rate_changes:
        first_rate = Decimal(str(min(schedule, key=lambda s: s["effective_date"])["annual_rate"]))

    day_count = "actual_365" if always_actual_365 else rules["day_count_convention"]
    divisor = Decimal(365) if day_count == "actual_365" else Decimal(360)

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
            if ignore_rate_changes:
                rate = first_rate
            else:
                applicable = [s for s in schedule if s["effective_date"] <= day]
                rate = Decimal(str(max(applicable, key=lambda s: s["effective_date"])["annual_rate"]))
            daily = rate / divisor
            day_interest = principal * daily
            if round_daily:
                day_interest = day_interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            accrued_interest += day_interest
            uncapitalized_interest += day_interest

        if not fee_triggered and day == fee_trigger_day:
            if fee_uses_current_principal_after_payments:
                base_principal = principal
            else:
                base_principal = principal
            total_owed_before_fee = principal + accrued_interest + accrued_fees
            if total_owed_before_fee > 0:
                if rules["late_fee_type"] == "flat_cents":
                    fee = Decimal(rules["late_fee_value"])
                else:
                    fee = base_principal * (Decimal(rules["late_fee_value"]) / Decimal(10000))
                    cap = rules.get("late_fee_cap_cents")
                    if cap is not None:
                        fee = min(fee, Decimal(cap))
                accrued_fees += fee
            fee_triggered = True

        compounding = "simple" if never_compound else rules["compounding"]
        if compounding == "monthly" and day == _last_day_of_month(day) and uncapitalized_interest > 0:
            principal += uncapitalized_interest
            uncapitalized_interest = Decimal(0)

        for p in payments_by_date.get(day, []):
            amount = Decimal(p["amount_cents"])
            for stage in allocation_order:
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


def wrong_ignores_rate_changes(invoice, payments, rules, as_of_date):
    return _base_calc(invoice, payments, rules, as_of_date, ignore_rate_changes=True)


def wrong_ignores_grace_period(invoice, payments, rules, as_of_date):
    return _base_calc(invoice, payments, rules, as_of_date, ignore_grace_period=True)


def wrong_always_actual_365(invoice, payments, rules, as_of_date):
    return _base_calc(invoice, payments, rules, as_of_date, always_actual_365=True)


def wrong_never_compounds(invoice, payments, rules, as_of_date):
    return _base_calc(invoice, payments, rules, as_of_date, never_compound=True)


def wrong_fee_threshold_off_by_one(invoice, payments, rules, as_of_date):
    return _base_calc(invoice, payments, rules, as_of_date, fee_threshold_off_by_one=True)


def wrong_allocation_principal_first(invoice, payments, rules, as_of_date):
    return _base_calc(invoice, payments, rules, as_of_date,
                       wrong_allocation_order=["principal", "interest", "fees"])


def wrong_rounds_daily(invoice, payments, rules, as_of_date):
    return _base_calc(invoice, payments, rules, as_of_date, round_daily=True)


ALL_PROBES = {
    "ignores_rate_changes": wrong_ignores_rate_changes,
    "ignores_grace_period": wrong_ignores_grace_period,
    "always_actual_365": wrong_always_actual_365,
    "never_compounds": wrong_never_compounds,
    "fee_threshold_off_by_one": wrong_fee_threshold_off_by_one,
    "allocation_principal_first": wrong_allocation_principal_first,
    "rounds_daily": wrong_rounds_daily,
}
