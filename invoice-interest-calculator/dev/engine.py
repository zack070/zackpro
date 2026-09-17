"""
Authoritative scoring engine for the overdue-invoice balance calculator
task. Wraps reference_calc.compute_balance as the ground truth and
scores a submitted policy's answers against it.

Rules (all disclosed to the agent -- see environment/engine/README.md
and reference_calc.py's docstring, which is shipped verbatim).
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List

import reference_calc

TOLERANCE_CENTS = 5  # small implementation-variance margin, not a "close enough" loophole


def _parse_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def load_scenario(data_dir: str):
    def read_csv(name):
        with open(os.path.join(data_dir, name), newline="") as f:
            return list(csv.DictReader(f))

    invoices = {}
    for r in read_csv("invoices.csv"):
        invoices[r["invoice_id"]] = {
            "invoice_id": r["invoice_id"],
            "customer_id": r["customer_id"],
            "jurisdiction_code": r["jurisdiction_code"],
            "principal_cents": int(r["principal_cents"]),
            "due_date": _parse_date(r["due_date"]),
        }

    payments = [
        {
            "payment_id": r["payment_id"],
            "invoice_id": r["invoice_id"],
            "amount_cents": int(r["amount_cents"]),
            "payment_date": _parse_date(r["payment_date"]),
        }
        for r in read_csv("payments.csv")
    ]

    with open(os.path.join(data_dir, "jurisdiction_rules.json")) as f:
        raw_rules = json.load(f)
    jurisdiction_rules = {}
    for code, r in raw_rules.items():
        jurisdiction_rules[code] = {
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

    queries = [
        {"query_id": r["query_id"], "invoice_id": r["invoice_id"], "as_of_date": _parse_date(r["as_of_date"])}
        for r in read_csv("queries.csv")
    ]

    return invoices, payments, jurisdiction_rules, queries


@dataclass
class ScoreResult:
    total_queries: int
    correct_within_tolerance: int
    max_abs_error_cents: int
    worst_query_id: str
    missing_query_ids: List[str]


def score_answers(invoices, payments, jurisdiction_rules, queries, answers: Dict[str, int]) -> ScoreResult:
    """answers: dict query_id -> submitted balance in cents. A missing
    query_id, a non-integer value, or any exception while interpreting
    it counts as wrong for that query (not a crash)."""
    correct_count = 0
    max_err = 0
    worst_qid = ""
    missing = []

    for q in queries:
        invoice = invoices[q["invoice_id"]]
        true_val = reference_calc.compute_balance(invoice, payments, jurisdiction_rules, q["as_of_date"])
        submitted = answers.get(q["query_id"])
        if submitted is None:
            missing.append(q["query_id"])
            err = abs(true_val)
        else:
            try:
                submitted_int = int(submitted)
            except (TypeError, ValueError):
                submitted_int = None
            err = abs(submitted_int - true_val) if submitted_int is not None else abs(true_val) + 10**9
        if err > max_err:
            max_err = err
            worst_qid = q["query_id"]
        if err <= TOLERANCE_CENTS:
            correct_count += 1

    return ScoreResult(
        total_queries=len(queries),
        correct_within_tolerance=correct_count,
        max_abs_error_cents=max_err,
        worst_query_id=worst_qid,
        missing_query_ids=missing,
    )
