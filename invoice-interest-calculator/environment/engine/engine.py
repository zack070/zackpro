"""
Data loading helpers for the overdue-invoice balance calculator task.

This module ONLY parses the input files into plain Python objects --
it does not compute anything. Computing the correct overdue balance
(interest accrual, compounding, late fees, payment allocation) is the
task; see README.md in this directory for the complete rules.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import date


def _parse_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def load_invoices(data_dir: str):
    """Returns a list of dicts, each:
    {invoice_id, customer_id, jurisdiction_code, principal_cents, due_date}
    due_date is a datetime.date."""
    with open(os.path.join(data_dir, "invoices.csv"), newline="") as f:
        return [
            {
                "invoice_id": r["invoice_id"],
                "customer_id": r["customer_id"],
                "jurisdiction_code": r["jurisdiction_code"],
                "principal_cents": int(r["principal_cents"]),
                "due_date": _parse_date(r["due_date"]),
            }
            for r in csv.DictReader(f)
        ]


def load_payments(data_dir: str):
    """Returns a list of dicts, each:
    {payment_id, invoice_id, amount_cents, payment_date}
    payment_date is a datetime.date."""
    with open(os.path.join(data_dir, "payments.csv"), newline="") as f:
        return [
            {
                "payment_id": r["payment_id"],
                "invoice_id": r["invoice_id"],
                "amount_cents": int(r["amount_cents"]),
                "payment_date": _parse_date(r["payment_date"]),
            }
            for r in csv.DictReader(f)
        ]


def load_jurisdiction_rules(data_dir: str):
    """Returns a dict: jurisdiction_code -> {
        day_count_convention, grace_period_days, compounding,
        late_fee_type, late_fee_value, late_fee_cap_cents (or None),
        late_fee_threshold_days,
        interest_rate_schedule: [{effective_date, annual_rate}, ...],
        payment_allocation_order: [str, str, str],
    }
    effective_date is a datetime.date."""
    with open(os.path.join(data_dir, "jurisdiction_rules.json")) as f:
        raw = json.load(f)
    result = {}
    for code, r in raw.items():
        result[code] = {
            "day_count_convention": r["day_count_convention"],
            "grace_period_days": r["grace_period_days"],
            "compounding": r["compounding"],
            "late_fee_type": r["late_fee_type"],
            "late_fee_value": r["late_fee_value"],
            "late_fee_cap_cents": r.get("late_fee_cap_cents"),
            "late_fee_threshold_days": r["late_fee_threshold_days"],
            "interest_rate_schedule": [
                {"effective_date": _parse_date(s["effective_date"]), "annual_rate": s["annual_rate"]}
                for s in r["interest_rate_schedule"]
            ],
            "payment_allocation_order": r["payment_allocation_order"],
        }
    return result


def load_queries(data_dir: str):
    """Returns a list of dicts, each: {query_id, invoice_id, as_of_date}
    as_of_date is a datetime.date."""
    with open(os.path.join(data_dir, "queries.csv"), newline="") as f:
        return [
            {"query_id": r["query_id"], "invoice_id": r["invoice_id"], "as_of_date": _parse_date(r["as_of_date"])}
            for r in csv.DictReader(f)
        ]
