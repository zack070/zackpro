"""Generate a deterministic cash-application scenario: several customers,
each with a moderate number of payments and open invoices whose amounts
are chosen so exact/near-exact coverage requires genuine subset-sum-style
search, not just sorting by size."""
import csv
import json
import os
import random


def gen_customer(rng, cust_id, n_payments, n_invoices, amount_range=(5000, 250000)):
    """Amounts in cents. Invoice total and payment total are kept close
    (within ~10%) so a low-cost solution is genuinely reachable -- but
    finding it requires the right partition, not just abundant supply."""
    invoices = []
    for i in range(n_invoices):
        amt = rng.randint(*amount_range)
        invoices.append({"invoice_id": f"{cust_id}-INV{i+1}", "customer_id": cust_id, "amount_due_cents": amt})

    total_due = sum(inv["amount_due_cents"] for inv in invoices)

    # build payments by "shredding" the invoice totals into a different
    # partition than the invoices themselves, so the natural grouping by
    # invoice is not recoverable by inspection -- then jitter the total
    # slightly so it isn't a perfectly balanced instance
    remaining = total_due
    raw_payments = []
    while remaining > 0 and len(raw_payments) < n_payments - 1:
        max_take = max(1, remaining // max(1, (n_payments - len(raw_payments))) * 2)
        take = rng.randint(1, min(max_take, remaining))
        raw_payments.append(take)
        remaining -= take
    if remaining > 0:
        raw_payments.append(remaining)
    while len(raw_payments) < n_payments:
        # split a random existing payment in two to hit the target count
        idx = rng.randrange(len(raw_payments))
        if raw_payments[idx] > 1:
            half = raw_payments[idx] // 2
            raw_payments[idx] -= half
            raw_payments.append(half)
        else:
            raw_payments.append(rng.randint(100, 5000))

    rng.shuffle(raw_payments)
    payments = [
        {"payment_id": f"{cust_id}-PMT{i+1}", "customer_id": cust_id, "amount_cents": amt}
        for i, amt in enumerate(raw_payments)
    ]
    return payments, invoices


def gen(seed, out_dir, n_customers=10, payments_range=(22, 30), invoices_range=(16, 22)):
    rng = random.Random(seed)
    all_payments = []
    all_invoices = []
    for c in range(n_customers):
        cust_id = f"C{c+1}"
        n_p = rng.randint(*payments_range)
        n_i = rng.randint(*invoices_range)
        payments, invoices = gen_customer(rng, cust_id, n_p, n_i)
        all_payments.extend(payments)
        all_invoices.extend(invoices)

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "payments.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["payment_id", "customer_id", "amount_cents"])
        for p in all_payments:
            w.writerow([p["payment_id"], p["customer_id"], p["amount_cents"]])
    with open(os.path.join(out_dir, "invoices.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["invoice_id", "customer_id", "amount_due_cents"])
        for i in all_invoices:
            w.writerow([i["invoice_id"], i["customer_id"], i["amount_due_cents"]])
    return all_payments, all_invoices


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1])
    out_dir = sys.argv[2]
    gen(seed, out_dir)
    print(f"wrote scenario seed={seed} to {out_dir}")
