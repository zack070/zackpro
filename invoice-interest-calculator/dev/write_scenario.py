"""Write a list of {invoice, payments, as_of_date} cases + jurisdictions
dict out as the on-disk scenario format (invoices.csv, payments.csv,
jurisdiction_rules.json, queries.csv)."""
import csv
import json
import os


def write_scenario(cases, jurisdictions, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    invoices_seen = {}
    all_payments = []
    queries = []
    for i, case in enumerate(cases):
        inv = case["invoice"]
        invoices_seen[inv["invoice_id"]] = inv
        all_payments.extend(case["payments"])
        queries.append({"query_id": f"Q{i}", "invoice_id": inv["invoice_id"], "as_of_date": case["as_of_date"]})

    with open(os.path.join(out_dir, "invoices.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["invoice_id", "customer_id", "jurisdiction_code", "principal_cents", "due_date"])
        for inv in invoices_seen.values():
            w.writerow([inv["invoice_id"], inv["customer_id"], inv["jurisdiction_code"],
                        inv["principal_cents"], inv["due_date"].isoformat()])

    with open(os.path.join(out_dir, "payments.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["payment_id", "invoice_id", "amount_cents", "payment_date"])
        for p in all_payments:
            w.writerow([p["payment_id"], p["invoice_id"], p["amount_cents"], p["payment_date"].isoformat()])

    rules_json = {}
    for code, r in jurisdictions.items():
        rules_json[code] = {
            "day_count_convention": r["day_count_convention"],
            "grace_period_days": r["grace_period_days"],
            "compounding": r["compounding"],
            "late_fee_type": r["late_fee_type"],
            "late_fee_value": r["late_fee_value"],
            "late_fee_cap_cents": r.get("late_fee_cap_cents"),
            "late_fee_threshold_days": r["late_fee_threshold_days"],
            "interest_rate_schedule": [
                {"effective_date": s["effective_date"].isoformat(), "annual_rate": s["annual_rate"]}
                for s in r["interest_rate_schedule"]
            ],
            "payment_allocation_order": r["payment_allocation_order"],
        }
    with open(os.path.join(out_dir, "jurisdiction_rules.json"), "w") as f:
        json.dump(rules_json, f, indent=2)

    with open(os.path.join(out_dir, "queries.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query_id", "invoice_id", "as_of_date"])
        for q in queries:
            w.writerow([q["query_id"], q["invoice_id"], q["as_of_date"].isoformat()])
