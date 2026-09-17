"""Reference solution: per customer, seed with a best-fit-decreasing
greedy bin-covering heuristic, then improve via simulated annealing over
reassignments (move a payment to a different invoice, or unapply it),
independently per customer (cross-customer matches are never legal
anyway). This is a genuinely different technique from an exact
subset-sum-style search, used to confirm the reachable floor is a real
property of the problem rather than an artifact of one specific
algorithm."""
import math
import random

TOLERANCE_CENTS = 50


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


def _anneal_customer(cust_payments, cust_invoices, seed_assignment, rng, iterations):
    if not cust_payments:
        return {}
    assignment = dict(seed_assignment)
    current_cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
    best_assignment = dict(assignment)
    best_cost = current_cost

    inv_ids = [i.invoice_id for i in cust_invoices] + [None]
    temperature = max(1.0, current_cost / 10.0)
    cooling = 0.999

    for _ in range(iterations):
        p = rng.choice(cust_payments)
        new_target = rng.choice(inv_ids)
        old_target = assignment.get(p.payment_id)
        if new_target == old_target:
            continue

        assignment[p.payment_id] = new_target
        new_cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
        delta = new_cost - current_cost

        if delta <= 0 or rng.random() < math.exp(-delta / max(temperature, 1e-6)):
            current_cost = new_cost
            if current_cost < best_cost:
                best_cost = current_cost
                best_assignment = dict(assignment)
        else:
            assignment[p.payment_id] = old_target

        temperature *= cooling

    return best_assignment


def match(payments, invoices):
    rng = random.Random(12345)
    result = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        seed_assignment = _best_fit_decreasing(cust_payments, cust_invoices)
        best_result = None
        best_cost = None
        for _ in range(8):
            candidate = _anneal_customer(cust_payments, cust_invoices, seed_assignment, rng, iterations=10000)
            cost = _cost_for_customer(cust_payments, cust_invoices, candidate)
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_result = candidate
        result.update(best_result)
    return result
