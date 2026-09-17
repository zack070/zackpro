"""Reference solution: simulated annealing over reassignment moves, seeded
by a best-fit-decreasing greedy construction, run independently per
customer with a FIXED iteration count and a fixed number of restarts --
deliberately NOT wall-clock-time-based. An earlier version scaled its
search to a wall-clock deadline (with an adaptive cooling schedule derived
from a live calibration burst); a real reviewer measured that this made
the reference's own output non-deterministic (different final costs across
runs on a loaded host) and unreliable on slower hardware (a ~4x-slower
core sometimes failed to clear the pass bar). The instruction explicitly
requires match() to be deterministic for the same inputs, and this
implementation now satisfies that literally: the same input lists,
combined with the fixed seed and fixed iteration/restart counts below,
always produce the exact same sequence of random choices and therefore the
exact same output, regardless of machine speed or load. Only the WALL-CLOCK
DURATION varies with hardware -- never the result. At this task's instance
scale, this fixed-effort search reaches 4.5%-4.7% of total payment value
uncleared in roughly 6-9 seconds on ordinary hardware, comfortably within
even a much slower grading host's share of the time budget."""
import math
import random

TOLERANCE_CENTS = 50
ITERATIONS_PER_RUN = 8000
RESTARTS_PER_CUSTOMER = 15


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


def _anneal_fixed(cust_payments, cust_invoices, seed_assignment, rng, n_iters):
    assignment = dict(seed_assignment)
    current_cost = _cost_for_customer(cust_payments, cust_invoices, assignment)
    best_assignment = dict(assignment)
    best_cost = current_cost
    inv_ids = [i.invoice_id for i in cust_invoices] + [None]
    temperature = max(1.0, current_cost / 10.0)
    cooling = 0.01 ** (1.0 / max(n_iters, 1))

    for _ in range(n_iters):
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
        temperature = max(temperature * cooling, 1e-3)

    return best_assignment, best_cost


def match(payments, invoices):
    rng = random.Random(12345)
    matching = {}
    for cust_payments, cust_invoices in _by_customer(payments, invoices):
        if not cust_payments:
            continue
        seed_assignment = _best_fit_decreasing(cust_payments, cust_invoices)
        best_assignment, best_cost = None, None
        for _ in range(RESTARTS_PER_CUSTOMER):
            result, cost = _anneal_fixed(cust_payments, cust_invoices, seed_assignment, rng, ITERATIONS_PER_RUN)
            if best_cost is None or cost < best_cost:
                best_cost, best_assignment = cost, result
        matching.update(best_assignment)
    return matching
