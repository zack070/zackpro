"""Generate randomized overdue-invoice test cases exercising: grace
period boundaries, mid-accrual rate changes, monthly compounding across
month (and leap-year) boundaries, late fee threshold + cap, multiple
payments applied in varying allocation-order-relevant sequences, and
both day-count conventions."""
import random
from datetime import date, timedelta


def _random_date(rng, start, end):
    delta = (end - start).days
    return start + timedelta(days=rng.randint(0, delta))


def gen_jurisdiction(rng, code):
    day_count = rng.choice(["actual_365", "actual_360"])
    grace = rng.choice([0, 5, 10, 15])
    compounding = rng.choice(["simple", "monthly"])
    late_fee_type = rng.choice(["flat_cents", "percent_of_principal"])
    if late_fee_type == "flat_cents":
        late_fee_value = rng.choice([2500, 5000, 10000])
        late_fee_cap = None
    else:
        late_fee_value = rng.choice([300, 500, 1000])  # basis points
        late_fee_cap = rng.choice([None, 50000, 100000])
    late_fee_threshold = rng.choice([10, 15, 30, 45])

    # 1 or 2 rate periods
    n_periods = rng.choice([1, 1, 2])
    base_date = date(2023, 1, 1)
    schedule = [{"effective_date": base_date, "annual_rate": round(rng.uniform(0.04, 0.18), 4)}]
    if n_periods == 2:
        change_date = base_date + timedelta(days=rng.randint(30, 200))
        schedule.append({"effective_date": change_date, "annual_rate": round(rng.uniform(0.04, 0.18), 4)})

    allocation_order = rng.choice([
        ["fees", "interest", "principal"],
        ["interest", "fees", "principal"],
        ["principal", "fees", "interest"],
    ])

    return {
        "day_count_convention": day_count,
        "grace_period_days": grace,
        "compounding": compounding,
        "late_fee_type": late_fee_type,
        "late_fee_value": late_fee_value,
        "late_fee_cap_cents": late_fee_cap,
        "late_fee_threshold_days": late_fee_threshold,
        "interest_rate_schedule": schedule,
        "payment_allocation_order": allocation_order,
        "code": code,
    }


def gen_case(rng, case_id):
    jurisdiction_code = f"J{case_id % 5}"
    rules = gen_jurisdiction(rng, jurisdiction_code)

    due_date = date(2023, rng.randint(1, 6), rng.randint(1, 28))
    principal = rng.randint(50000, 2000000)
    invoice = {
        "invoice_id": f"INV{case_id}",
        "customer_id": f"CUST{case_id % 20}",
        "jurisdiction_code": jurisdiction_code,
        "principal_cents": principal,
        "due_date": due_date,
    }

    horizon = rng.randint(20, 300)
    as_of_date = due_date + timedelta(days=horizon)

    n_payments = rng.choice([0, 1, 1, 2, 3])
    payments = []
    for i in range(n_payments):
        pdate = _random_date(rng, due_date, as_of_date - timedelta(days=1))
        # keep payment amounts modest relative to principal to avoid overpayment
        amt = rng.randint(int(principal * 0.05), int(principal * 0.35))
        payments.append({
            "payment_id": f"PMT{case_id}-{i}",
            "invoice_id": invoice["invoice_id"],
            "amount_cents": amt,
            "payment_date": pdate,
        })

    return invoice, payments, rules, as_of_date


def gen_all(seed, n_cases):
    rng = random.Random(seed)
    cases = []
    jurisdictions = {}
    for i in range(n_cases):
        invoice, payments, rules, as_of_date = gen_case(rng, i)
        jurisdictions[rules["code"]] = rules
        cases.append({"invoice": invoice, "payments": payments, "as_of_date": as_of_date})
    return cases, jurisdictions
