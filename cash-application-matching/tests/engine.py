"""
Authoritative scoring engine for the cash-application matching task.

This is the single source of truth for how a submitted match is scored. It
is copied byte-identical into environment/engine/ (agent-visible, full
source, nothing hidden) and tests/ (hidden verifier). Keep dev/sync_engine.sh
in sync after any edit here.

Rules (all disclosed to the agent -- see environment/engine/README.md):
  - Each payment may be applied to AT MOST ONE invoice (no splitting a
    single payment across multiple invoices).
  - A payment may only be applied to an invoice belonging to the SAME
    customer_id. An attempt to cross customers is dropped (treated as
    unapplied), not an error.
  - Multiple payments MAY be applied to the same invoice (they accumulate).
  - TOLERANCE_CENTS is a fixed short-pay allowance: an invoice's shortfall
    below this amount costs nothing.
  - Cost (lower is better):
      total_cost_cents = sum over invoices of max(0, amount_due_cents
                             - sum(applied payments) - TOLERANCE_CENTS)
                       + sum over payments not applied to any invoice of
                             that payment's amount_cents
    There is no penalty or bonus for overpaying an invoice beyond its
    amount_due -- payments are a scarce, zero-sum resource, so applying
    more than an invoice needs is only ever costly indirectly, by denying
    that payment to some other invoice that needed it.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

TOLERANCE_CENTS = 50  # $0.50, disclosed exactly


@dataclass(frozen=True)
class Payment:
    payment_id: str
    customer_id: str
    amount_cents: int


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    customer_id: str
    amount_due_cents: int


@dataclass
class ScoreResult:
    total_cost_cents: int
    uncleared_invoice_cents: int
    unapplied_payment_cents: int
    invoices_fully_cleared: int
    total_invoices: int
    dropped_assignments: List[str]  # human-readable reasons, for diagnostics


def load_scenario(data_dir: str):
    def read_csv(name):
        with open(os.path.join(data_dir, name), newline="") as f:
            return list(csv.DictReader(f))

    payments = [
        Payment(payment_id=r["payment_id"], customer_id=r["customer_id"], amount_cents=int(r["amount_cents"]))
        for r in read_csv("payments.csv")
    ]
    invoices = [
        Invoice(invoice_id=r["invoice_id"], customer_id=r["customer_id"], amount_due_cents=int(r["amount_due_cents"]))
        for r in read_csv("invoices.csv")
    ]
    return payments, invoices


def score_matching(payments: List[Payment], invoices: List[Invoice], matching: Dict[str, Optional[str]]) -> ScoreResult:
    """matching: dict mapping payment_id -> invoice_id (or None / absent
    means unapplied). Any payment_id not a real payment, any invoice_id not
    a real invoice, or a cross-customer assignment is dropped silently
    (treated as unapplied) -- it does not raise and does not affect other
    assignments."""
    payments_by_id = {p.payment_id: p for p in payments}
    invoices_by_id = {i.invoice_id: i for i in invoices}

    applied_to_invoice: Dict[str, int] = {i.invoice_id: 0 for i in invoices}
    unapplied_cents = 0
    dropped: List[str] = []

    seen_payments = set()
    for payment_id, invoice_id in matching.items():
        if payment_id in seen_payments:
            continue  # duplicate key impossible in a dict, kept for clarity
        seen_payments.add(payment_id)

        p = payments_by_id.get(payment_id)
        if p is None:
            dropped.append(f"{payment_id}: not a real payment_id")
            continue
        if invoice_id is None:
            continue  # explicitly left unapplied, not a drop

        inv = invoices_by_id.get(invoice_id)
        if inv is None:
            dropped.append(f"{payment_id}->{invoice_id}: not a real invoice_id")
            unapplied_cents += p.amount_cents
            continue
        if inv.customer_id != p.customer_id:
            dropped.append(f"{payment_id}->{invoice_id}: cross-customer assignment")
            unapplied_cents += p.amount_cents
            continue

        applied_to_invoice[invoice_id] += p.amount_cents

    # any real payment never mentioned in the matching at all is unapplied
    for p in payments:
        if p.payment_id not in matching or matching.get(p.payment_id) is None:
            unapplied_cents += p.amount_cents

    uncleared_cents = 0
    fully_cleared = 0
    for inv in invoices:
        shortfall = max(0, inv.amount_due_cents - applied_to_invoice[inv.invoice_id] - TOLERANCE_CENTS)
        uncleared_cents += shortfall
        if shortfall == 0:
            fully_cleared += 1

    total_cost = uncleared_cents + unapplied_cents
    return ScoreResult(
        total_cost_cents=total_cost,
        uncleared_invoice_cents=uncleared_cents,
        unapplied_payment_cents=unapplied_cents,
        invoices_fully_cleared=fully_cleared,
        total_invoices=len(invoices),
        dropped_assignments=dropped,
    )
