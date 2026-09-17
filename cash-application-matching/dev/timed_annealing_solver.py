"""Time-budget-aware simulated annealing: cooling rate is computed from a
brief calibration burst (how many iterations/sec this customer's cost
evaluation achieves) so temperature decays to near-zero exactly at the
per-customer deadline, regardless of machine speed or customer size.
Restarts (from a fresh cooling cycle) if time remains after one run
converges. This replaces the earlier fixed-iteration-count version, which
was recalibrated away by measuring that a real agent has a wall-clock
budget (up to ~90s), not a small fixed iteration count -- fixed exponential
cooling tuned for one iteration count either wastes remaining time doing
nothing useful (temperature hits ~0 early) or does not converge properly
(temperature still high at the deadline)."""
import math
import random
import time

from greedy_probes import _by_customer, best_fit_decreasing


def _cost_for_customer(cust_payments, cust_invoices, assignment, tolerance):
    covered = {i.invoice_id: 0 for i in cust_invoices}
    inv_by_id = {i.invoice_id: i for i in cust_invoices}
    unapplied = 0
    for p in cust_payments:
        inv_id = assignment.get(p.payment_id)
        if inv_id is None:
            unapplied += p.amount_cents
        else:
            covered[inv_id] += p.amount_cents
    uncleared = sum(max(0, inv.amount_due_cents - covered[inv.invoice_id] - tolerance) for inv in cust_invoices)
    return uncleared + unapplied


def _anneal_run(cust_payments, cust_invoices, seed_assignment, rng, deadline, tolerance):
    assignment = dict(seed_assignment)
    current_cost = _cost_for_customer(cust_payments, cust_invoices, assignment, tolerance)
    best_assignment = dict(assignment)
    best_cost = current_cost
    inv_ids = [i.invoice_id for i in cust_invoices] + [None]

    # calibration burst: measure real iteration throughput on this machine
    # for this customer, then pick a cooling factor so temperature decays
    # to ~1% of its start by the deadline
    calib_start = time.time()
    calib_iters = 0
    calib_deadline = min(deadline, calib_start + 0.05)
    while time.time() < calib_deadline:
        p = rng.choice(cust_payments)
        new_target = rng.choice(inv_ids)
        old_target = assignment.get(p.payment_id)
        assignment[p.payment_id] = new_target
        _cost_for_customer(cust_payments, cust_invoices, assignment, tolerance)
        assignment[p.payment_id] = old_target
        calib_iters += 1
    elapsed_calib = max(time.time() - calib_start, 1e-6)
    remaining = max(0.0, deadline - time.time())
    est_total_iters = max(1, int(calib_iters * (remaining / elapsed_calib))) if elapsed_calib > 0 else 1000
    # cooling^est_total_iters ~= 0.01  =>  cooling = 0.01 ** (1/est_total_iters)
    cooling = 0.01 ** (1.0 / max(est_total_iters, 1))

    temperature = max(1.0, current_cost / 10.0)
    while time.time() < deadline:
        p = rng.choice(cust_payments)
        new_target = rng.choice(inv_ids)
        old_target = assignment.get(p.payment_id)
        if new_target == old_target:
            continue
        assignment[p.payment_id] = new_target
        new_cost = _cost_for_customer(cust_payments, cust_invoices, assignment, tolerance)
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


def solve_timed_annealing(payments, invoices, tolerance=50, seed=0, total_time_budget=70.0):
    rng = random.Random(seed)
    matching = {}
    customers = list(_by_customer(payments, invoices))
    per_customer_budget = total_time_budget / max(1, len(customers))
    for cust_payments, cust_invoices in customers:
        if not cust_payments:
            continue
        seed_assignment = best_fit_decreasing(cust_payments, cust_invoices)
        cust_deadline = time.time() + per_customer_budget
        best_assignment, best_cost = _anneal_run(cust_payments, cust_invoices, seed_assignment, rng, cust_deadline, tolerance)
        # restart from the best-found-so-far if any time remains (rare, but
        # guards against an unlucky first run on a small customer)
        while time.time() < cust_deadline - 0.02:
            candidate, cand_cost = _anneal_run(cust_payments, cust_invoices, best_assignment, rng, cust_deadline, tolerance)
            if cand_cost < best_cost:
                best_cost, best_assignment = cand_cost, candidate
            else:
                break
        matching.update(best_assignment)
    return matching
