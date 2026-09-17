"""Hand-designed edge cases guaranteeing coverage of every rule
interaction, so the held-out test set doesn't rely on random luck to
catch a specific bug (e.g. the late-fee-threshold boundary only differs
on ~2% of random cases -- a curated case lands exactly on it)."""
from datetime import date


def _rules(code, **overrides):
    base = {
        "code": code,
        "day_count_convention": "actual_365",
        "grace_period_days": 5,
        "compounding": "simple",
        "late_fee_type": "flat_cents",
        "late_fee_value": 5000,
        "late_fee_cap_cents": None,
        "late_fee_threshold_days": 30,
        "interest_rate_schedule": [{"effective_date": date(2023, 1, 1), "annual_rate": 0.10}],
        "payment_allocation_order": ["fees", "interest", "principal"],
    }
    base.update(overrides)
    return base


def build():
    """Returns (cases, jurisdictions) -- same shape as gen_cases.gen_all."""
    cases = []
    jurisdictions = {}

    def add(name, invoice, payments, rules, as_of_date):
        jurisdictions[rules["code"]] = rules
        cases.append({"invoice": invoice, "payments": payments, "as_of_date": as_of_date, "name": name})

    # 1. Exact grace-period boundary: due 2023-03-01, grace=5 -> accrual starts 2023-03-07.
    #    as_of = 2023-03-06 (still in grace, zero interest) vs 2023-03-07 (one day accrued).
    r = _rules("EDGE1", grace_period_days=5)
    inv = {"invoice_id": "E1", "customer_id": "C1", "jurisdiction_code": "EDGE1",
           "principal_cents": 1000000, "due_date": date(2023, 3, 1)}
    add("grace_boundary_still_in_grace", inv, [], r, date(2023, 3, 6))
    add("grace_boundary_first_accrual_day", inv, [], r, date(2023, 3, 7))

    # 2. Rate change exactly mid-accrual-window.
    r2 = _rules("EDGE2", grace_period_days=0, interest_rate_schedule=[
        {"effective_date": date(2023, 1, 1), "annual_rate": 0.06},
        {"effective_date": date(2023, 4, 1), "annual_rate": 0.18},
    ])
    inv2 = {"invoice_id": "E2", "customer_id": "C2", "jurisdiction_code": "EDGE2",
            "principal_cents": 2000000, "due_date": date(2023, 3, 1)}
    add("rate_change_mid_window", inv2, [], r2, date(2023, 4, 15))

    # 3. Late fee threshold exact boundary (threshold=30 -> trigger day = due+31).
    r3 = _rules("EDGE3", late_fee_threshold_days=30, late_fee_type="flat_cents", late_fee_value=7500)
    inv3 = {"invoice_id": "E3", "customer_id": "C3", "jurisdiction_code": "EDGE3",
            "principal_cents": 1000000, "due_date": date(2023, 2, 1)}
    add("fee_threshold_day_before", inv3, [], r3, date(2023, 3, 3))  # due+30, not yet
    add("fee_threshold_exact_trigger_day", inv3, [], r3, date(2023, 3, 4))  # due+31, triggers

    # 4. Percent-of-principal late fee WITH cap engaged.
    r4 = _rules("EDGE4", late_fee_type="percent_of_principal", late_fee_value=1000, late_fee_cap_cents=40000)
    inv4 = {"invoice_id": "E4", "customer_id": "C4", "jurisdiction_code": "EDGE4",
            "principal_cents": 10000000, "due_date": date(2023, 1, 1)}  # 10% of 10,000,000 = 1,000,000 >> cap
    add("fee_percent_cap_engaged", inv4, [], r4, date(2023, 3, 1))

    # 5. Monthly compounding across a calendar month boundary, incl. February (non-leap 2023).
    r5 = _rules("EDGE5", compounding="monthly", grace_period_days=0)
    inv5 = {"invoice_id": "E5", "customer_id": "C5", "jurisdiction_code": "EDGE5",
            "principal_cents": 5000000, "due_date": date(2023, 1, 15)}
    add("monthly_compounding_across_feb", inv5, [], r5, date(2023, 3, 20))

    # 6. Monthly compounding across a LEAP YEAR February (2024).
    r6 = _rules("EDGE6", compounding="monthly", grace_period_days=0,
                interest_rate_schedule=[{"effective_date": date(2024, 1, 1), "annual_rate": 0.12}])
    inv6 = {"invoice_id": "E6", "customer_id": "C6", "jurisdiction_code": "EDGE6",
            "principal_cents": 5000000, "due_date": date(2024, 1, 10)}
    add("monthly_compounding_leap_year_feb", inv6, [], r6, date(2024, 3, 15))

    # 7. Payment allocation order matters: a mid-stream payment covers fees+interest
    #    fully, leaving principal reduced (or not) depending on order.
    r7 = _rules("EDGE7", grace_period_days=0, late_fee_threshold_days=10,
                late_fee_type="flat_cents", late_fee_value=5000,
                payment_allocation_order=["fees", "interest", "principal"])
    inv7 = {"invoice_id": "E7", "customer_id": "C7", "jurisdiction_code": "EDGE7",
            "principal_cents": 1000000, "due_date": date(2023, 1, 1)}
    pay7 = [{"payment_id": "P7A", "invoice_id": "E7", "amount_cents": 30000, "payment_date": date(2023, 1, 25)}]
    add("allocation_order_fees_interest_principal", inv7, pay7, r7, date(2023, 2, 15))

    r7b = dict(r7)
    r7b["code"] = "EDGE7B"
    r7b["payment_allocation_order"] = ["principal", "interest", "fees"]
    inv7b = dict(inv7)
    inv7b["invoice_id"] = "E7B"
    inv7b["jurisdiction_code"] = "EDGE7B"
    pay7b = [{"payment_id": "P7B", "invoice_id": "E7B", "amount_cents": 30000, "payment_date": date(2023, 1, 25)}]
    add("allocation_order_principal_first", inv7b, pay7b, r7b, date(2023, 2, 15))

    # 8. actual_360 vs actual_365 on an otherwise-identical invoice.
    r8a = _rules("EDGE8A", day_count_convention="actual_365", grace_period_days=0)
    r8b = _rules("EDGE8B", day_count_convention="actual_360", grace_period_days=0)
    inv8a = {"invoice_id": "E8A", "customer_id": "C8", "jurisdiction_code": "EDGE8A",
             "principal_cents": 3000000, "due_date": date(2023, 5, 1)}
    inv8b = {"invoice_id": "E8B", "customer_id": "C8", "jurisdiction_code": "EDGE8B",
             "principal_cents": 3000000, "due_date": date(2023, 5, 1)}
    add("day_count_actual_365", inv8a, [], r8a, date(2023, 7, 1))
    add("day_count_actual_360", inv8b, [], r8b, date(2023, 7, 1))

    # 9. Multiple payments straddling both a rate change AND monthly compounding.
    r9 = _rules("EDGE9", compounding="monthly", grace_period_days=0,
                interest_rate_schedule=[
                    {"effective_date": date(2023, 1, 1), "annual_rate": 0.08},
                    {"effective_date": date(2023, 3, 1), "annual_rate": 0.15},
                ],
                late_fee_threshold_days=20, late_fee_type="percent_of_principal",
                late_fee_value=200, late_fee_cap_cents=None)
    inv9 = {"invoice_id": "E9", "customer_id": "C9", "jurisdiction_code": "EDGE9",
            "principal_cents": 4000000, "due_date": date(2023, 1, 5)}
    pay9 = [
        {"payment_id": "P9A", "invoice_id": "E9", "amount_cents": 200000, "payment_date": date(2023, 1, 20)},
        {"payment_id": "P9B", "invoice_id": "E9", "amount_cents": 150000, "payment_date": date(2023, 3, 10)},
    ]
    add("multi_payment_rate_change_and_compounding", inv9, pay9, r9, date(2023, 4, 30))

    # 10. Zero-interest edge: as_of_date == due_date (no accrual at all yet).
    r10 = _rules("EDGE10", grace_period_days=0)
    inv10 = {"invoice_id": "E10", "customer_id": "C10", "jurisdiction_code": "EDGE10",
             "principal_cents": 1000000, "due_date": date(2023, 6, 1)}
    add("as_of_equals_due_date", inv10, [], r10, date(2023, 6, 1))

    # 11. Long accrual horizon (~2 years) to amplify cumulative daily-rounding
    #     drift beyond a single cent -- catches an implementation that rounds
    #     each day's accrual instead of only the final total.
    r11 = _rules("EDGE11", grace_period_days=0,
                 interest_rate_schedule=[{"effective_date": date(2021, 1, 1), "annual_rate": 0.0733}])
    inv11 = {"invoice_id": "E11", "customer_id": "C11", "jurisdiction_code": "EDGE11",
             "principal_cents": 987654, "due_date": date(2021, 1, 1)}
    add("long_horizon_rounding_drift", inv11, [], r11, date(2023, 1, 1))

    return cases, jurisdictions
