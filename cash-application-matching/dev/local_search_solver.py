"""Independent second approach to the same problem: simulated annealing /
local search over the assignment, starting from a greedy seed, per
customer. Used to cross-validate that the exact bitmask-DP solver's floor
is a real property of the problem and not an artifact of that one
algorithm -- a structurally different technique should converge on the
same number if the floor is real."""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from engine import TOLERANCE_CENTS
from greedy_probes import best_fit_decreasing, _by_customer


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


def _anneal_customer(cust_payments, cust_invoices, seed_assignment, rng, iterations=4000):
    assignment = dict(seed_assignment)
    current_cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
    best_assignment = dict(assignment)
    best_cost = current_cost

    inv_ids = [i.invoice_id for i in cust_invoices] + [None]
    if not cust_payments:
        return assignment

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

        if delta <= 0 or rng.random() < pow(2.71828, -delta / max(temperature, 1e-6)):
            current_cost = new_cost
            if current_cost < best_cost:
                best_cost = current_cost
                best_assignment = dict(assignment)
        else:
            assignment[p.payment_id] = old_target

        temperature *= cooling

    return best_assignment


def solve_local_search(payments, invoices, seed=0, iterations=10000, restarts=8):
    rng = random.Random(seed)
    seed_matching = best_fit_decreasing(payments, invoices)
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        seed_for_cust = {p.payment_id: seed_matching.get(p.payment_id) for p in cust_payments}
        best_result = None
        best_cost = None
        for _ in range(restarts):
            result = _anneal_customer(cust_payments, cust_invoices, seed_for_cust, rng, iterations)
            cost = _cost_for_customer(cust_payments, cust_invoices, result)
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_result = result
        matching.update(best_result)
    return matching
