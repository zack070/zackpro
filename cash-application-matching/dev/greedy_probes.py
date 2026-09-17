"""Adversarial greedy probes: plausible, non-experimentation heuristics an
agent might write without realizing this is a combinatorial matching
problem. Each processes customers independently (a fair assumption since
cross-customer matching is disallowed anyway)."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from engine import TOLERANCE_CENTS


def _by_customer(payments, invoices):
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    for cust in customers:
        yield [p for p in payments if p.customer_id == cust], [i for i in invoices if i.customer_id == cust]


def naive_no_match(payments, invoices):
    """Baseline: apply nothing at all."""
    return {}


def one_to_one_nearest(payments, invoices):
    """For each invoice (largest first), find the single unused payment
    whose amount is closest to it, with no combining -- a very natural
    'match the check to the invoice it most looks like' approach."""
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        used = set()
        for inv in sorted(cust_invoices, key=lambda i: -i.amount_due_cents):
            candidates = [p for p in cust_payments if p.payment_id not in used]
            if not candidates:
                continue
            best = min(candidates, key=lambda p: abs(p.amount_cents - inv.amount_due_cents))
            matching[best.payment_id] = inv.invoice_id
            used.add(best.payment_id)
    return matching


def sorted_accumulate_desc(payments, invoices):
    """Sort invoices descending by amount, sort payments descending by
    amount; for each invoice in turn, greedily accumulate the largest
    remaining payments until the invoice is covered (or payments run out),
    then move to the next invoice."""
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        remaining = sorted(cust_payments, key=lambda p: -p.amount_cents)
        for inv in sorted(cust_invoices, key=lambda i: -i.amount_due_cents):
            total = 0
            still = []
            for p in remaining:
                if total >= inv.amount_due_cents:
                    still.append(p)
                    continue
                matching[p.payment_id] = inv.invoice_id
                total += p.amount_cents
            remaining = [p for p in remaining if matching.get(p.payment_id) != inv.invoice_id]
    return matching


def sorted_accumulate_asc(payments, invoices):
    """Same idea, smallest invoices and smallest payments first."""
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        remaining = sorted(cust_payments, key=lambda p: p.amount_cents)
        for inv in sorted(cust_invoices, key=lambda i: i.amount_due_cents):
            total = 0
            for p in list(remaining):
                if total >= inv.amount_due_cents:
                    break
                matching[p.payment_id] = inv.invoice_id
                total += p.amount_cents
                remaining.remove(p)
    return matching


def best_fit_decreasing(payments, invoices):
    """Classic bin-covering heuristic: process payments largest-first; each
    payment goes to whichever not-yet-cleared invoice it brings closest to
    (without excessively overshooting) full coverage."""
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        covered = {i.invoice_id: 0 for i in cust_invoices}
        inv_by_id = {i.invoice_id: i for i in cust_invoices}
        for p in sorted(cust_payments, key=lambda p: -p.amount_cents):
            open_invs = [iid for iid, c in covered.items() if c + TOLERANCE_CENTS < inv_by_id[iid].amount_due_cents]
            if not open_invs:
                continue

            def gap_after(iid):
                new_total = covered[iid] + p.amount_cents
                due = inv_by_id[iid].amount_due_cents
                return abs(due - new_total)

            chosen = min(open_invs, key=gap_after)
            matching[p.payment_id] = chosen
            covered[chosen] += p.amount_cents
    return matching


def fifo_order(payments, invoices):
    """Process payments and invoices in their given (id) order, a
    plausible 'just go through the list' approach with no sorting at all."""
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        covered = {i.invoice_id: 0 for i in cust_invoices}
        inv_by_id = {i.invoice_id: i for i in cust_invoices}
        inv_order = [i.invoice_id for i in cust_invoices]
        ptr = 0
        for p in cust_payments:
            while ptr < len(inv_order) and covered[inv_order[ptr]] + TOLERANCE_CENTS >= inv_by_id[inv_order[ptr]].amount_due_cents:
                ptr += 1
            if ptr >= len(inv_order):
                break
            matching[p.payment_id] = inv_order[ptr]
            covered[inv_order[ptr]] += p.amount_cents
    return matching


ALL_PROBES = {
    "naive_no_match": naive_no_match,
    "one_to_one_nearest": one_to_one_nearest,
    "sorted_accumulate_desc": sorted_accumulate_desc,
    "sorted_accumulate_asc": sorted_accumulate_asc,
    "best_fit_decreasing": best_fit_decreasing,
    "fifo_order": fifo_order,
}
