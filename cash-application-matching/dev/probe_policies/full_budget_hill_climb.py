"""Adversarial probe, tougher version: the exact algorithm the real
reviewer used to catch the previous bar as too loose -- best-fit-decreasing
seed followed by plain random-reassignment hill climbing (never accept a
worse move, no temperature/acceptance schedule) -- but now given the FULL
realistic grading budget (~80s of the 90s stage-1 window) rather than a
small fixed iteration count. Confirmed empirically to plateau around
6.3-6.6% of total value regardless of how much of that budget it actually
uses, since plain hill-climbing gets stuck in a local optimum quickly and
can't escape it with more time alone."""
import random
import time

TOLERANCE_CENTS = 50
TIME_BUDGET = 60.0  # match() is now called twice per grading run (determinism
                    # check), so this must comfortably fit within half of
                    # the Stage 1 timeout


def _by_customer(payments, invoices):
    customers = sorted(set(p.customer_id for p in payments) | set(i.customer_id for i in invoices))
    for cust in customers:
        yield [p for p in payments if p.customer_id == cust], [i for i in invoices if i.customer_id == cust]


def _best_fit_decreasing(cust_payments, cust_invoices):
    covered = {i.invoice_id: 0 for i in cust_invoices}
    inv_by_id = {i.invoice_id: i for i in cust_invoices}
    assignment = {}
    for p in sorted(cust_payments, key=lambda p: -p.amount_cents):
        open_invs = [iid for iid, c in covered.items() if c + TOLERANCE_CENTS < inv_by_id[iid].amount_due_cents]
        if not open_invs:
            assignment[p.payment_id] = None
            continue

        def gap_after(iid):
            return abs(inv_by_id[iid].amount_due_cents - (covered[iid] + p.amount_cents))

        chosen = min(open_invs, key=gap_after)
        assignment[p.payment_id] = chosen
        covered[chosen] += p.amount_cents
    return assignment


def _cost_for_customer(cust_payments, cust_invoices, assignment):
    covered = {i.invoice_id: 0 for i in cust_invoices}
    inv_by_id = {i.invoice_id: i for i in cust_invoices}
    unapplied = 0
    for p in cust_payments:
        inv_id = assignment.get(p.payment_id)
        if inv_id is None:
            unapplied += p.amount_cents
        else:
            covered[inv_id] += p.amount_cents
    uncleared = sum(max(0, inv.amount_due_cents - covered[inv.invoice_id] - TOLERANCE_CENTS) for inv in cust_invoices)
    return uncleared + unapplied


def match(payments, invoices):
    rng = random.Random(1)
    matching = {}
    customers = list(_by_customer(payments, invoices))
    per_customer_budget = TIME_BUDGET / max(1, len(customers))
    for cust_payments, cust_invoices in customers:
        if not cust_payments:
            continue
        cust_deadline = time.time() + per_customer_budget
        assignment = _best_fit_decreasing(cust_payments, cust_invoices)
        cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
        inv_ids = [i.invoice_id for i in cust_invoices] + [None]
        while time.time() < cust_deadline:
            p = rng.choice(cust_payments)
            new_target = rng.choice(inv_ids)
            old_target = assignment.get(p.payment_id)
            if new_target == old_target:
                continue
            assignment[p.payment_id] = new_target
            new_cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
            if new_cost <= cost:
                cost = new_cost
            else:
                assignment[p.payment_id] = old_target
        matching.update(assignment)
    return matching
